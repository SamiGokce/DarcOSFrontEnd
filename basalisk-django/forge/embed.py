"""Search is semantic and keyword, and the two scores are added to rerank.

BART writes the keywords and a few other ways to ask the question. Those wordings are
scored by keyword overlap (BM25). A sentence encoder embeds the question and each passage,
and their similarity is the semantic score. A passage that matches both ways ranks first.
"""
import threading

from . import rag
from .person import fact_statements

KEYWORD_MODEL = 'bloomberg/keybart'
PARAPHRASE_MODEL = 'eugenesiow/bart-paraphrase'
# MiniLM separates short facts such as "Occupation: Lighthouse keeper" from a reworded
# question. The BERT retrieval model that was tried ranked those facts almost equally.
ENCODER_MODEL = 'sentence-transformers/all-MiniLM-L6-v2'
QUERY_PREFIX = ''
VARIATIONS = 4

_lock = threading.Lock()
_loaded = {}
_cache = {}
# Tests assign these so a run does not download the models.
keyword_generator = None
variation_generator = None
encoder = None
_encoder = None


def status() -> dict:
    return {
        'kind': 'semantic+keyword',
        'encoder': ENCODER_MODEL,
        'keywords': KEYWORD_MODEL,
        'paraphrase': PARAPHRASE_MODEL,
        'loaded': _encoder is not None and KEYWORD_MODEL in _loaded and PARAPHRASE_MODEL in _loaded,
    }


def _device():
    import torch
    if torch.cuda.is_available():
        return 'cuda'
    if torch.backends.mps.is_available():
        return 'mps'
    return 'cpu'


def _load(repo: str):
    if repo in _loaded:
        return _loaded[repo]
    with _lock:
        if repo in _loaded:
            return _loaded[repo]
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(repo)
        model = AutoModelForSeq2SeqLM.from_pretrained(repo)
        model.eval()
        device = _device()
        model.to(device)
        _loaded[repo] = (tokenizer, model, device)
        return _loaded[repo]


def _generate(repo: str, text: str, **options) -> list[str]:
    import torch
    tokenizer, model, device = _load(repo)
    batch = tokenizer(text, truncation=True, max_length=256, return_tensors='pt')
    batch = {key: value.to(device) for key, value in batch.items()}
    with torch.no_grad():
        output = model.generate(**batch, **options)
    return [line.strip() for line in tokenizer.batch_decode(output, skip_special_tokens=True)]


def keywords(text: str) -> str:
    """The search words BART writes for one passage or question."""
    text = (text or '').strip()
    if not text:
        return ''
    cached = _cache.get(('keywords', text))
    if cached is not None:
        return cached
    if keyword_generator is not None:
        written = keyword_generator(text)
    else:
        written = _generate(KEYWORD_MODEL, text, num_beams=4, max_new_tokens=24)[0]
    written = written.replace('<sep>', ' ').replace(';', ' ')
    _cache[('keywords', text)] = written
    return written


def variations(text: str) -> list[str]:
    """Other ways to ask the same question, so the search is not tied to one wording."""
    text = (text or '').strip()
    if not text:
        return []
    cached = _cache.get(('variations', text))
    if cached is not None:
        return cached
    if variation_generator is not None:
        written = variation_generator(text)
    else:
        written = _generate(
            PARAPHRASE_MODEL, text,
            do_sample=True, top_p=0.92, temperature=1.2, num_beams=1,
            num_return_sequences=VARIATIONS, max_new_tokens=32,
        )
    unique = []
    for line in written:
        line = line.strip()
        if line and line.lower() != text.lower() and line.lower() not in {item.lower() for item in unique}:
            unique.append(line)
    _cache[('variations', text)] = unique
    return unique


def queries(text: str) -> list[str]:
    """The question, BART's keywords, and each rephrasing, without repeats."""
    found = []

    def add(item: str):
        item = (item or '').strip()
        if item and item.lower() not in {earlier.lower() for earlier in found}:
            found.append(item)

    add(text)
    add(keywords(text))
    for line in variations(text):
        add(line)
        add(keywords(line))
    return found


def _indexed(documents: list[str]) -> list[str]:
    """Each passage plus the keywords BART wrote for it."""
    indexed = []
    for document in documents:
        extra = keywords(document)
        indexed.append(f'{document}\n{extra}'.strip() if extra else document)
    return indexed


def encode(texts: list[str]) -> list[list[float]]:
    """Sentence embeddings, one per text. Each vector is normalized, so a dot product is cosine similarity."""
    if encoder is not None:
        return encoder(texts)
    missing = [text for text in texts if ('embed', text) not in _cache]
    if missing:
        import torch
        tokenizer, model, device = _load_encoder()
        batch = tokenizer(missing, padding=True, truncation=True, max_length=256, return_tensors='pt')
        batch = {key: value.to(device) for key, value in batch.items()}
        with torch.no_grad():
            hidden = model(**batch).last_hidden_state
            mask = batch['attention_mask'].unsqueeze(-1)
            hidden = (hidden * mask).sum(1) / mask.sum(1)
            hidden = torch.nn.functional.normalize(hidden, p=2, dim=1)
        for text, vector in zip(missing, hidden.tolist()):
            _cache[('embed', text)] = vector
    return [_cache[('embed', text)] for text in texts]


def _load_encoder():
    global _encoder
    if _encoder is None:
        with _lock:
            if _encoder is None:
                from transformers import AutoModel, AutoTokenizer
                tokenizer = AutoTokenizer.from_pretrained(ENCODER_MODEL)
                model = AutoModel.from_pretrained(ENCODER_MODEL)
                model.eval()
                device = _device()
                model.to(device)
                _encoder = (tokenizer, model, device)
    return _encoder


def _scale(values: list[float]) -> list[float]:
    """Scale positive scores so the strongest is 1. A score of 0 stays 0."""
    peak = max(values, default=0.0)
    if peak <= 0:
        return [0.0] * len(values)
    return [value / peak if value > 0 else 0.0 for value in values]


def search(query: str, documents: list[str]) -> list[dict]:
    """Score every passage by its own words and by its meaning, then rerank on the sum.

    The keyword score is the question against the passage. BART's rewordings are not
    included: they were matching facts the question was not about.
    """
    query = (query or '').strip()
    if not query or not documents:
        return []
    keyword_totals = rag.scores(query, documents)
    vectors = encode([QUERY_PREFIX + query, *documents])
    semantic_totals = [sum(left * right for left, right in zip(vectors[0], vector)) for vector in vectors[1:]]
    rows = []
    for index, (keyword, semantic) in enumerate(zip(_scale(keyword_totals), _scale(semantic_totals))):
        if keyword + semantic <= 0:
            continue
        rows.append({
            'index': index,
            'keyword': round(keyword, 3),
            'semantic': round(semantic, 3),
            'score': round(keyword + semantic, 3),
        })
    rows.sort(key=lambda row: (-row['score'], row['index']))
    return rows


def rank(query: str, documents: list[str], k: int = 3) -> list[int]:
    """Passages that match by keyword, by meaning, or both, best first."""
    return [row['index'] for row in search(query, documents)[:k]]


def semantic_rank(query: str, documents: list[str], k: int = 3) -> list[int]:
    """The passages closest in meaning to the query, best first.

    Cosine similarity of the MiniLM embeddings. A passage with no positive similarity is left out.
    """
    query = (query or '').strip()
    if not query or not documents or k <= 0:
        return []
    vectors = encode([QUERY_PREFIX + query, *documents])
    scored = []
    for index, vector in enumerate(vectors[1:]):
        score = sum(left * right for left, right in zip(vectors[0], vector))
        if score > 0:
            scored.append((score, index))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [index for _, index in scored[:k]]


def consistency(texts: list[str], facts: list[dict]) -> list[float]:
    """How closely each candidate reply matches the fact the question was about.

    `facts` is the ranked list from best_fact. The top fact is the one the question was
    about, so a reply that agrees with it scores highest. Scores are cosine similarities.
    """
    if not texts:
        return []
    if not facts:
        return [0.0] * len(texts)
    vectors = encode([*texts, facts[0]['text']])
    target = vectors[-1]
    return [round(sum(a * b for a, b in zip(vector, target)), 3) for vector in vectors[:-1]]


def best_fact(question: str, person) -> tuple[str | None, list[dict]]:
    """Person facts in the order the combined search found them."""
    statements = fact_statements(person)
    if not statements or not (question or '').strip():
        return None, []
    ranked = []
    for row in search(question, [item['text'] for item in statements]):
        statement = statements[row['index']]
        ranked.append({
            'key': statement['key'],
            'text': statement['text'],
            'keyword': row['keyword'],
            'semantic': row['semantic'],
        })
    return (ranked[0]['key'] if ranked else None), ranked
