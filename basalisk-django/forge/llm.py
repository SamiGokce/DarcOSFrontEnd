"""Lazy, process-wide loader for the Pygmalion model."""
import importlib.util
import logging
import os
import threading

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


class Engine:
    def __init__(self):
        self._state_lock = threading.Lock()
        self._generate_lock = threading.Lock()
        self._tokenizer = None
        self._model = None
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
            'model': MODEL_ID,
            'state': state,
            'detail': detail,
            'device': self.device,
            'context_tokens': self.context_tokens,
        }

    def start_loading(self) -> dict:
        with self._state_lock:
            if self.state in ('loading', 'ready'):
                return self.status()
            if not _deps_installed():
                return self.status()
            self.state = 'loading'
            self.detail = f'Downloading and loading {MODEL_ID}. The first load downloads several GB.'
        threading.Thread(target=self._load, name='pygmalion-loader', daemon=True).start()
        return self.status()

    def _load(self):
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer

            if torch.cuda.is_available():
                device, dtype = 'cuda', torch.float16
            elif torch.backends.mps.is_available():
                device, dtype = 'mps', torch.float32
            else:
                device, dtype = 'cpu', torch.float32

            tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
            model = AutoModelForCausalLM.from_pretrained(MODEL_ID, torch_dtype=dtype)
            model.to(device)
            model.eval()
        except Exception as exc:
            logger.exception('Failed to load %s', MODEL_ID)
            with self._state_lock:
                self.state = 'error'
                self.detail = f'{type(exc).__name__}: {exc}'
            return

        context = CONTEXT_OVERRIDE or getattr(model.config, 'max_position_embeddings', None)
        with self._state_lock:
            self._tokenizer, self._model, self.device = tokenizer, model, device
            self.context_tokens = int(context or DEFAULT_CONTEXT_TOKENS)
            self.state = 'ready'
            self.detail = f'{MODEL_ID} is ready on {device}.'

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
