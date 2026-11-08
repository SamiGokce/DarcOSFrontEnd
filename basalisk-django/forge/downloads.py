"""Background Hugging Face downloads and the byte progress the UI polls."""
import logging
import threading
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


def snapshot(repo_id):
    if not repo_id:
        return _view('catalog', 0, 0, 0, 'This model has no repository.')
    with _lock:
        job = _jobs.get(repo_id)
        if job:
            return dict(job)
    if _weights_cached(repo_id):
        return _view('downloaded', 100, 0, 0, 'Weights are on disk.')
    return _view('catalog', 0, 0, 0, 'On the shelf. Download fetches the weights from Hugging Face.')


def start(repo_id):
    with _lock:
        current = _jobs.get(repo_id)
        if current and current['state'] == 'downloading':
            return dict(current)
        busy = next((item['repo_id'] for item in _jobs.values() if item['state'] == 'downloading'), None)
        if busy:
            raise DownloadBusy(busy)
        _jobs[repo_id] = _view('downloading', 0, 0, 0, 'Checking files…', repo_id)
    threading.Thread(target=_run, args=(repo_id,), name=f'download-{repo_id}', daemon=True).start()
    return snapshot(repo_id)


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


def note_size(repo_id, total, done):
    with _lock:
        job = _jobs.get(repo_id)
        if not job or job['state'] != 'downloading':
            return
        job['total'] = max(0, int(total))
        job['done'] = max(0, int(done))
        job['percent'] = 0 if job['total'] <= 0 else min(99, int(job['done'] * 100 / job['total']))
        job['detail'] = _byte_detail(job['done'], job['total']) if job['total'] else 'Downloading…'


def finish(repo_id):
    with _lock:
        job = _jobs.get(repo_id)
        if not job:
            return
        job['state'] = 'downloaded'
        job['percent'] = 100
        job['detail'] = 'Weights are on disk.'


def fail(repo_id, exc):
    message = f'{type(exc).__name__}: {exc}'
    if len(message) > 300:
        message = message[:297] + '…'
    logger.exception('Download failed for %s', repo_id)
    with _lock:
        job = _jobs.get(repo_id)
        if not job:
            return
        job['state'] = 'error'
        job['detail'] = message


def _run(repo_id):
    try:
        import sys

        from huggingface_hub import HfApi, snapshot_download, try_to_load_from_cache
        import huggingface_hub.utils.tqdm  # noqa: F401  loads the module; the package attribute is the class

        files = [item for item in HfApi().list_repo_tree(repo_id, recursive=True) if hasattr(item, 'size')]
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
            snapshot_download(repo_id)
        finally:
            hf_tqdm.tqdm = original
        finish(repo_id)
    except Exception as exc:
        fail(repo_id, exc)


def _weights_cached(repo_id):
    folder = Path(HF_HUB_CACHE) / ('models--' + repo_id.replace('/', '--')) / 'snapshots'
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
    }
