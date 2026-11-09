"""Lazy, process-wide loader for the Pygmalion model."""
import importlib.util
import logging
import os
import threading
import time

logger = logging.getLogger(__name__)

MODEL_ID = os.environ.get('PYGMALION_MODEL', 'PygmalionAI/pygmalion-1.3b')
CONTEXT_OVERRIDE = os.environ.get('PYGMALION_CONTEXT')
DEFAULT_CONTEXT_TOKENS = 2048


class ModelNotReady(Exception):
    def __init__(self, status):
        super().__init__(status['detail'])
        self.status = status


def _deps_installed() -> bool:
    return all(importlib.util.find_spec(m) is not None for m in ('torch', 'transformers'))


def weights_missing(exc) -> bool:
    """Transformers wraps a missing local file as a connection OSError."""
    current = exc
    seen = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if type(current).__name__ == 'LocalEntryNotFoundError':
            return True
        current = current.__cause__
    text = str(exc)
    return "couldn't find them in the cached files" in text or 'local_files_only' in text


class Engine:
    def __init__(self):
        self._state_lock = threading.Lock()
        self._generate_lock = threading.Lock()
        self._tokenizer = None
        self._model = None
        self._generation = 0
        self.model_id = None
        self.state = 'idle'
        self.detail = 'Not loaded.'
        self.device = None
        self.context_tokens = int(CONTEXT_OVERRIDE or DEFAULT_CONTEXT_TOKENS)

    def status(self) -> dict:
        if self.state == 'idle' and not _deps_installed():
            return self._status('unavailable', 'Install the model packages: pip install -r requirements-model.txt')
        return self._status(self.state, self.detail)

    def _status(self, state, detail):
        return {
            'model': self.model_id,
            'state': state,
            'detail': detail,
            'device': self.device,
            'context_tokens': self.context_tokens,
        }

    def release(self, repo_id=None):
        """Drop the loaded weights. An in-flight load of the same model is discarded."""
        with self._state_lock:
            if repo_id and self.model_id != repo_id:
                return self.status()
            self._generation += 1
            self._tokenizer = None
            self._model = None
            self.model_id = None
            self.device = None
            self.state = 'idle'
            self.detail = 'Not loaded.'
        try:
            import gc

            import torch

            gc.collect()
            if torch.backends.mps.is_available():
                torch.mps.empty_cache()
            elif torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            logger.exception('Failed to free model memory')
        return self.status()

    def start_loading(self, repo_id=None) -> dict:
        repo_id = repo_id or MODEL_ID
        with self._state_lock:
            if self.model_id == repo_id and self.state in ('loading', 'ready'):
                return self.status()
            if not _deps_installed():
                return self.status()
            self._generation += 1
            generation = self._generation
            self.model_id = repo_id
            self._tokenizer = None
            self._model = None
            self.device = None
            self.state = 'loading'
            self.detail = f'Loading {repo_id} into memory.'
        threading.Thread(target=self._load, args=(repo_id, generation), name='pygmalion-loader', daemon=True).start()
        return self.status()

    def ensure_ready(self, repo_id, timeout=300):
        """Load `repo_id` if needed and wait until it can reply."""
        status = self.start_loading(repo_id)
        if status['state'] == 'ready' and status['model'] == repo_id:
            return status
        if status['state'] != 'loading':
            raise ModelNotReady(status)
        deadline = time.time() + timeout
        while time.time() < deadline:
            time.sleep(0.25)
            with self._state_lock:
                if self.model_id != repo_id:
                    continue
                if self.state == 'ready':
                    return self.status()
                if self.state == 'error':
                    raise ModelNotReady(self.status())
        raise ModelNotReady(self._status('error', f'Timed out loading {repo_id}.'))

    def _load(self, repo_id, generation):
        try:
            import gc

            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer

            gc.collect()
            if torch.backends.mps.is_available():
                torch.mps.empty_cache()
            elif torch.cuda.is_available():
                torch.cuda.empty_cache()

            if torch.cuda.is_available():
                device, dtype = 'cuda', torch.float16
            elif torch.backends.mps.is_available():
                device, dtype = 'mps', torch.float32
            else:
                device, dtype = 'cpu', torch.float32

            tokenizer = AutoTokenizer.from_pretrained(repo_id, local_files_only=True)
            model = AutoModelForCausalLM.from_pretrained(
                repo_id, torch_dtype=dtype, local_files_only=True, low_cpu_mem_usage=True,
            )
            model.to(device)
            model.eval()
        except Exception as exc:
            logger.exception('Failed to load %s', repo_id)
            with self._state_lock:
                if generation != self._generation:
                    return
                self.state = 'error'
                if weights_missing(exc):
                    self.detail = 'Download this model before loading it.'
                else:
                    self.detail = f'{type(exc).__name__}: {exc}'
            return

        context = CONTEXT_OVERRIDE or getattr(model.config, 'max_position_embeddings', None)
        with self._state_lock:
            if generation != self._generation:
                return
            self._tokenizer, self._model, self.device = tokenizer, model, device
            self.context_tokens = int(context or DEFAULT_CONTEXT_TOKENS)
            self.state = 'ready'
            self.detail = f'{repo_id} is ready on {device}.'

    def count_tokens(self, text: str) -> int:
        if self._tokenizer is None:
            return len(text) // 4 + 1
        return len(self._tokenizer(text).input_ids)

    def generate(self, prompt, *, max_new_tokens, temperature, top_p, repetition_penalty) -> str:
        if self.state != 'ready':
            raise ModelNotReady(self.status())
        import torch

        tokenizer, model = self._tokenizer, self._model
        with self._generate_lock:
            inputs = tokenizer(prompt, return_tensors='pt').to(self.device)
            sampling = {'do_sample': temperature > 0}
            if temperature > 0:
                sampling.update(temperature=temperature, top_p=top_p)
            with torch.no_grad():
                output = model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    repetition_penalty=repetition_penalty,
                    pad_token_id=tokenizer.eos_token_id,
                    **sampling,
                )
        new_tokens = output[0][inputs['input_ids'].shape[1]:]
        return tokenizer.decode(new_tokens, skip_special_tokens=True)


engine = Engine()
