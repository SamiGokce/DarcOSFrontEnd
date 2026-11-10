"""Simple retrieval: BM25 keyword scoring over soul.md sections and earlier chat turns."""
import math
import re
from collections import Counter

_WORD = re.compile(r"[a-z0-9']+")
_HEADING = re.compile(r'^(#{1,6})\s+(.+?)\s*#*\s*$')
STOPWORDS = frozenset(
    'a an and are as at be but by do does for from had has have he her his i if in into is it its '
    'me my not of on or our she so that the their them then there they this to was we were what '
    'when where which who why will with you your'.split()
)
MAX_SECTION_CHARS = 700


def tokenize(text: str) -> list[str]:
    return [word for word in _WORD.findall(text.lower()) if word not in STOPWORDS]


def scores(query: str, documents: list[str], k1: float = 1.5, b: float = 0.75) -> list[float]:
    """BM25 score of each document. A document with no shared word scores 0."""
    terms = set(tokenize(query))
    if not terms or not documents:
        return [0.0] * len(documents)
    bags = [Counter(tokenize(doc)) for doc in documents]
    lengths = [sum(bag.values()) for bag in bags]
    average = (sum(lengths) / len(lengths)) or 1.0
    count = len(documents)
    result = []
    for index, bag in enumerate(bags):
        score = 0.0
        for term in terms:
            frequency = bag.get(term, 0)
            if not frequency:
                continue
            holding = sum(1 for other in bags if term in other)
            idf = math.log(1 + (count - holding + 0.5) / (holding + 0.5))
            norm = frequency + k1 * (1 - b + b * lengths[index] / average)
            score += idf * frequency * (k1 + 1) / norm
        result.append(score)
    return result


def rank(query: str, documents: list[str], k: int = 3, k1: float = 1.5, b: float = 0.75) -> list[int]:
    """Indices of the `k` documents that best match `query`, best first. Documents with no overlap are skipped."""
    ordered = sorted(
        ((score, index) for index, score in enumerate(scores(query, documents, k1, b)) if score > 0),
        key=lambda item: (-item[0], item[1]),
    )
    return [index for _, index in ordered[:k]]


def soul_sections(markdown: str) -> list[dict]:
    """Split soul.md into sections by heading; long sections are split by paragraph."""
    sections, title, lines = [], '', []

    def close():
        body = '\n'.join(lines).strip()
        if not body and not title:
            return
        for part in _split(body):
            sections.append({'title': title, 'text': part})
        if not body:
            sections.append({'title': title, 'text': ''})

    for line in (markdown or '').splitlines():
        match = _HEADING.match(line)
        if match:
            close()
            title, lines = match.group(2).strip(), []
        else:
            lines.append(line)
    close()
    return sections


def _split(body: str) -> list[str]:
    if len(body) <= MAX_SECTION_CHARS:
        return [body] if body else []
    parts, current = [], ''
    for paragraph in re.split(r'\n\s*\n', body):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if current and len(current) + len(paragraph) + 2 > MAX_SECTION_CHARS:
            parts.append(current)
            current = paragraph
        else:
            current = f'{current}\n\n{paragraph}' if current else paragraph
    if current:
        parts.append(current)
    return parts


def exchanges(turns: list[dict], name: str, label: str = 'You') -> list[str]:
    """Group turns into one memory per message pair, so a recalled answer keeps its question."""
    memories, current = [], []
    for turn in turns:
        speaker = label if turn['role'] == 'you' else name
        if turn['role'] == 'you' and current:
            memories.append('\n'.join(current))
            current = []
        current.append(f"{speaker}: {turn['content'].strip()}")
    if current:
        memories.append('\n'.join(current))
    return memories
