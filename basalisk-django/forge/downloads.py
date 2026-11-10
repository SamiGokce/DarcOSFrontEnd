"""Hugging Face downloads in a separate worker process, with progress the UI polls.

The Django process only starts the worker and reads its status file. The worker
owns the download so a multi-gigabyte fetch does not run inside the web server.
"""
import json
import logging
import re
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

from huggingface_hub.constants import HF_HUB_CACHE

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_jobs = {}


class DownloadBusy(Exception):
    def __init__(self, repo_id):
        super().__init__(repo_id)
        self.repo_id = repo_id


def reset():
    with _lock:
        _jobs.clear()
    folder = _status_dir()
    if folder.is_dir():
        for path in folder.glob('*.json'):
            path.unlink(missing_ok=True)


def snapshot(repo_id):
    if not repo_id:
        return _view('catalog', 0, 0, 0, 'This model has no repository.')
    with _lock:
        job = _jobs.get(repo_id)
        if job:
            return dict(job)
    stored = _read_file(repo_id)
    if stored and stored.get('state') == 'downloading':
        if _is_active(stored):
            return stored
        stopped = dict(stored)
        stopped['state'] = 'error'
        stopped['detail'] = 'Download stopped.'
        return stopped
    if stored and stored.get('state') == 'error':
        return stored
    if _weights_cached(repo_id) or (stored and stored.get('state') == 'downloaded'):
        return _view('downloaded', 100, 0, 0, 'Weights are on disk.', repo_id)
    return _view('catalog', 0, 0, 0, 'On the shelf. Download fetches the weights from Hugging Face.', repo_id)


def start(repo_id):
    for job in _stored_jobs():
        if not _is_active(job):
            continue
        if job.get('repo_id') == repo_id:
            return snapshot(repo_id)
        raise DownloadBusy(job.get('repo_id') or repo_id)
    _write_file(_view('downloading', 0, 0, 0, 'Checking files…', repo_id))
    _spawn(repo_id)
    return snapshot(repo_id)


def run_worker(repo_id):
    """Entry point for the download worker process."""
    job = _read_file(repo_id) or _view('downloading', 0, 0, 0, 'Checking files…', repo_id)
    job['state'] = 'downloading'
    job['persist'] = True
    job['pid'] = os.getpid()
    with _lock:
        _jobs[repo_id] = job
    _flush(repo_id, force=True)
    _run(repo_id)


def add_bytes(repo_id, count):
    count = int(count or 0)
    if count <= 0:
        return
    with _lock:
        job = _jobs.get(repo_id)
        if not job or job['state'] != 'downloading':
            return
        job['done'] += count
        total = job['total']
        job['percent'] = 0 if total <= 0 else min(99, int(job['done'] * 100 / total))
        job['detail'] = _byte_detail(job['done'], total)
        _flush(repo_id)


def note_size(repo_id, total, done):
    with _lock:
        job = _jobs.get(repo_id)
        if not job or job['state'] != 'downloading':
            return
        job['total'] = max(0, int(total))
        job['done'] = max(0, int(done))
        job['percent'] = 0 if job['total'] <= 0 else min(99, int(job['done'] * 100 / job['total']))
        job['detail'] = _byte_detail(job['done'], job['total']) if job['total'] else 'Downloading…'
        _flush(repo_id)


def remove(repo_id):
    """Delete a model's downloaded weights. Refuses while a download is running."""
    if snapshot(repo_id)['state'] == 'downloading':
        raise DownloadBusy(repo_id)
    folder = _cache_folder(repo_id)
    if folder.is_dir():
        shutil.rmtree(folder)
    locks = Path(HF_HUB_CACHE) / '.locks' / folder.name
    if locks.is_dir():
        shutil.rmtree(locks)
    for path in (_status_path(repo_id), _status_path(repo_id).with_suffix('.log')):
        path.unlink(missing_ok=True)
    with _lock:
        _jobs.pop(repo_id, None)


def finish(repo_id):
    with _lock:
        job = _jobs.get(repo_id)
        if not job:
            return
        job['state'] = 'downloaded'
        job['percent'] = 100
        job['detail'] = 'Weights are on disk.'
        _flush(repo_id, force=True)


TOKEN_MESSAGE = 'Log in to Hugging Face and paste an access token.'


def asks_for_token(exc) -> bool:
    """Hugging Face answers gated and private repos by asking for a login."""
    if type(exc).__name__ in {'GatedRepoError', 'LocalTokenNotFoundError'}:
        return True
    status_code = getattr(getattr(exc, 'response', None), 'status_code', None)
    if status_code in (401, 403):
        return True
    text = str(exc).lower()
    return any(phrase in text for phrase in ('gated repo', 'unauthorized', 'access token', 'authenticate'))


def fail(repo_id, exc):
    auth = asks_for_token(exc)
    message = TOKEN_MESSAGE if auth else f'{type(exc).__name__}: {exc}'
    if len(message) > 300:
        message = message[:297] + '…'
    logger.exception('Download failed for %s', repo_id)
    with _lock:
        job = _jobs.get(repo_id)
        if not job:
            return
        job['state'] = 'error'
        job['needs_token'] = auth
        job['detail'] = message
        _flush(repo_id, force=True)


def _run(repo_id):
    try:
        import sys

        from huggingface_hub import HfApi, snapshot_download, try_to_load_from_cache
        import huggingface_hub.utils.tqdm  # noqa: F401  loads the module; the package attribute is the class

        token = read_token() or None
        files = [item for item in HfApi(token=token).list_repo_tree(repo_id, recursive=True) if hasattr(item, 'size')]
        total = sum(item.size or 0 for item in files)
        done = 0
        for item in files:
            cached = try_to_load_from_cache(repo_id, item.path)
            if isinstance(cached, str):
                done += item.size or 0
        note_size(repo_id, total, done)

        hf_tqdm = sys.modules['huggingface_hub.utils.tqdm']
        original = hf_tqdm.tqdm

        class TrackingTqdm(original):
            def __init__(self, *args, **kwargs):
                self._track_bytes = kwargs.get('unit') == 'B'
                super().__init__(*args, **kwargs)

            def update(self, n=1):
                result = super().update(n)
                if self._track_bytes:
                    add_bytes(repo_id, n)
                return result

        hf_tqdm.tqdm = TrackingTqdm
        try:
            snapshot_download(repo_id, token=token)
        finally:
            hf_tqdm.tqdm = original
        finish(repo_id)
    except Exception as exc:
        fail(repo_id, exc)


def _spawn(repo_id):
    root = Path(__file__).resolve().parent.parent
    env = os.environ.copy()
    env['PYTHONPATH'] = str(root) + os.pathsep + env.get('PYTHONPATH', '')
    log_path = _status_path(repo_id).with_suffix('.log')
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log = open(log_path, 'ab', buffering=0)
    try:
        proc = subprocess.Popen(
            [sys.executable, '-m', 'forge.download_worker', repo_id],
            cwd=str(root),
            env=env,
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=log,
        )
    finally:
        log.close()
    stored = _read_file(repo_id)
    if stored and not stored.get('pid'):
        stored['pid'] = proc.pid
        _write_file(stored)
    return proc


def _flush(repo_id, force=False):
    job = _jobs.get(repo_id)
    if not job or not job.get('persist'):
        return
    now = time.monotonic()
    if not force and now - job.get('_flushed', 0) < 0.3:
        return
    job['_flushed'] = now
    _write_file(job)


def token_path():
    override = os.environ.get('BASALISK_TOKEN_FILE')
    if override:
        return Path(override)
    return Path(__file__).resolve().parent.parent / 'var' / 'hf_token'


def read_token() -> str:
    path = token_path()
    if not path.is_file():
        return ''
    return path.read_text().strip()


def save_token(token: str):
    path = token_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(token.strip() + '\n')
    path.chmod(0o600)


def signed_in() -> bool:
    return bool(read_token())


def _status_dir():
    override = os.environ.get('BASALISK_DOWNLOAD_DIR')
    if override:
        return Path(override)
    return Path(__file__).resolve().parent.parent / 'var' / 'downloads'


def _status_path(repo_id):
    safe = repo_id.replace('/', '--').replace('..', '')
    return _status_dir() / f'{safe}.json'


def _write_file(job):
    path = _status_path(job['repo_id'])
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {key: value for key, value in job.items() if key != '_flushed'}
    temporary = path.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(payload))
    os.replace(temporary, path)


def _read_file(repo_id):
    path = _status_path(repo_id)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def _stored_jobs():
    folder = _status_dir()
    if not folder.is_dir():
        return []
    jobs = []
    for path in folder.glob('*.json'):
        try:
            jobs.append(json.loads(path.read_text()))
        except (OSError, json.JSONDecodeError):
            continue
    return jobs


def _is_active(job):
    if not job or job.get('state') != 'downloading':
        return False
    pid = job.get('pid')
    if not pid:
        return True
    try:
        os.kill(int(pid), 0)
    except OSError:
        return False
    return True


def _cache_folder(repo_id):
    return Path(HF_HUB_CACHE) / ('models--' + repo_id.replace('/', '--'))


def model_card(repo_id: str) -> list[dict]:
    """Fields read from the downloaded config and tokenizer files. Nothing is filled in by hand."""
    folder = _cache_folder(repo_id) / 'snapshots'
    configs = sorted(folder.glob('*/config.json')) if folder.is_dir() else []
    if not configs:
        return []
    config = json.loads(configs[-1].read_text())
    tokenizer_path = configs[-1].with_name('tokenizer_config.json')
    tokenizer = json.loads(tokenizer_path.read_text()) if tokenizer_path.is_file() else {}
    rows = []

    def take(label, source, *keys):
        for key in keys:
            if key in source and source[key] not in (None, ''):
                value = source[key]
                if isinstance(value, list):
                    value = ', '.join(str(item) for item in value)
                rows.append({'label': label, 'value': value})
                return

    take('Architecture', config, 'architectures')
    take('Model type', config, 'model_type')
    take('Layers', config, 'num_hidden_layers', 'num_layers', 'n_layer')
    take('Hidden size', config, 'hidden_size', 'n_embd')
    take('Attention heads', config, 'num_attention_heads', 'num_heads', 'n_head')
    take('Vocabulary', config, 'vocab_size')
    take('Max positions', config, 'max_position_embeddings', 'n_positions')
    take('Tokenizer', tokenizer, 'tokenizer_class')
    if not any(row['label'] == 'Tokenizer' for row in rows):
        take('Tokenizer', config, 'tokenizer_class')
    take('Dtype', config, 'torch_dtype')
    return rows


def prompt_structure(repo_id: str) -> str:
    """The prompt block from the model card, when the card includes one."""
    text = _readme(repo_id)
    if not text:
        return ''
    if text.startswith('---'):
        end = text.find('\n---', 3)
        if end != -1:
            text = text[end + 4 :]
    lowered = text.lower()
    start = len(text)
    found = False
    for marker in ('### the manual way', '## prompting', '### prompting'):
        index = lowered.find(marker)
        if index != -1 and index < start:
            start = index
            found = True
    if not found:
        return ''
    region = text[start:]
    nxt = re.search(r'\n## ', region[1:])
    if nxt:
        region = region[: nxt.start() + 1]
    match = re.search(r'```[^\n]*\n(.*?)```', region, re.DOTALL)
    return match.group(1).strip('\n') if match else ''


def _readme(repo_id: str) -> str:
    folder = _cache_folder(repo_id) / 'snapshots'
    files = sorted(folder.glob('*/README.md')) if folder.is_dir() else []
    if not files:
        return ''
    return files[-1].read_text()


def _weights_cached(repo_id):
    folder = _cache_folder(repo_id) / 'snapshots'
    if not folder.is_dir():
        return False
    for path in folder.rglob('*'):
        name = path.name
        if name.endswith('.safetensors') or (name.startswith('pytorch_model') and name.endswith('.bin')):
            return True
    return False


def _fmt(size):
    value = float(size or 0)
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if value < 1024 or unit == 'TB':
            return f'{int(value)} {unit}' if unit == 'B' else f'{value:.1f} {unit}'
        value /= 1024
    return f'{value:.1f} TB'


def _byte_detail(done, total):
    if total <= 0:
        return f'Downloading… {_fmt(done)}'
    return f'Downloading… {_fmt(min(done, total))} of {_fmt(total)}'


def _view(state, percent, done, total, detail, repo_id=''):
    return {
        'repo_id': repo_id,
        'state': state,
        'percent': percent,
        'done': done,
        'total': total,
        'detail': detail,
        'needs_token': False,
    }
