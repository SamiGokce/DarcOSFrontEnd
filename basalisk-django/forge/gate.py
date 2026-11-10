"""Explicit-content gate for the message a user sends.

A BERT-family classifier (DistilBERT) scores the message before the search or the
figure's model sees it. A message at or above THRESHOLD is refused. The gate is
separate from the BART search: BART writes keywords and rewordings, it does not judge.
"""
import threading

from transformers import pipeline

MODEL = 'eliasalbouzidi/distilbert-nsfw-text-classifier'
THRESHOLD = 0.5
MAX_TOKENS = 512  # DistilBERT's input limit

_lock = threading.Lock()
_classifier = None
# Test hook: replace with a function from text to a 0..1 score.
scorer = None


def _load():
    global _classifier
    if _classifier is None:
        with _lock:
            if _classifier is None:
                _classifier = pipeline('text-classification', model=MODEL, top_k=None)
    return _classifier


def score(text: str) -> float:
    """How explicit the text is, from 0 (safe) to 1 (explicit)."""
    if scorer is not None:
        return scorer(text)
    rows = _load()(text, truncation=True, max_length=MAX_TOKENS)[0]
    return next(row['score'] for row in rows if row['label'] == 'nsfw')


def blocked(text: str) -> bool:
    return score(text) >= THRESHOLD
