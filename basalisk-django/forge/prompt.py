"""Turn a soul.md and a chat into the prompt format Pygmalion models were trained on.

    {name}'s Persona: <soul.md>
    Memory: <earlier exchanges recalled for this message>
    <START>
    You: ...
    {name}: ...
    You: {message}
    {name}:

Recent turns go in verbatim. Older turns are only recalled when they match the
new message, so a long chat keeps its memory without overflowing the context.
When soul.md itself is too long, its opening plus the sections that match the
message are kept.
"""
import re
from dataclasses import dataclass, field
from typing import Callable, Iterable, Mapping

from . import rag

USER_LABEL = 'You'
START = '<START>'
RECENT_TURNS = 6
MEMORY_LIMIT = 3
SPEAKER_LINE = re.compile(r"\n[ \t]*[A-Z][\w' .-]{0,30}:")
SENTENCE = re.compile(r'.*?[.!?…](?:\s+|$)', re.DOTALL)
FLAG = re.compile(r'<([A-Za-z][A-Za-z0-9_]*)>|\[([A-Za-z][A-Za-z0-9_]*)\]|\{([A-Za-z][A-Za-z0-9_]*)\}')
MAX_REPLY_CHARS = 240
MAX_REPLY_SENTENCES = 2


@dataclass
class Prompt:
    text: str
    memories: list[str] = field(default_factory=list)
    soul_sections: list[str] = field(default_factory=list)


def _section_text(section: Mapping) -> str:
    if section['title'] and section['text']:
        return f"{section['title']}: {section['text']}"
    return section['title'] or section['text']


def soul_text(sections: list[Mapping]) -> str:
    return '\n'.join(part for part in (_section_text(s) for s in sections) if part)


def _line(role: str, content: str, name: str) -> str:
    speaker = USER_LABEL if role == 'you' else name
    return f'{speaker}: {content.strip()}'


def build_prompt(
    name: str,
    soul: str,
    history: Iterable[Mapping] = (),
    count_tokens: Callable[[str], int] | None = None,
    budget: int | None = None,
) -> Prompt:
    name = name.strip() or 'Figure'
    turns = list(history)
    query = next((t['content'] for t in reversed(turns) if t['role'] == 'you'), '')

    sections = rag.soul_sections(soul)
    intro, rest = sections[:1], sections[1:]
    matched = [rest[i] for i in rag.rank(query, [_section_text(s) for s in rest], k=3)]

    recent = turns[-RECENT_TURNS:]
    older = turns[:-RECENT_TURNS] if len(turns) > RECENT_TURNS else []
    pool = rag.exchanges(older, name, USER_LABEL)
    memories = [pool[i] for i in rag.rank(query, pool, k=MEMORY_LIMIT)]

    def assemble(soul_parts, memory_parts, kept):
        lines = [f"{name}'s Persona: {soul_text(soul_parts)}".rstrip()]
        if memory_parts:
            lines.append('Memory:')
            lines += memory_parts
        lines.append(START)
        lines += [_line(t['role'], t['content'], name) for t in kept]
        lines.append(f'{name}:')
        return '\n'.join(lines)

    soul_parts, memory_parts, kept = sections, list(memories), list(recent)

    def result():
        return Prompt(
            text=assemble(soul_parts, memory_parts, kept),
            memories=list(memory_parts),
            soul_sections=[s['title'] for s in soul_parts if s['title']],
        )

    if count_tokens is None or budget is None:
        return result()

    def fits():
        return count_tokens(assemble(soul_parts, memory_parts, kept)) <= budget

    if not fits():
        soul_parts = intro + matched
    while not fits() and memory_parts:
        memory_parts.pop()
    while not fits() and len(kept) > 1:
        kept.pop(0)
    while not fits() and len(soul_parts) > 1:
        soul_parts = soul_parts[:-1]
    return result()


FINISHED_ENDINGS = ('.', '!', '?', '…', '"', '”', "'", '*', ')')


def reply_drafts(raw: str, name: str) -> list[str]:
    """Split a generation into the separate drafts it usually writes one after another.

    Blank lines, a new speaker, and forum marks like ``[CONTINUE]`` start another
    draft. Each draft is one way the reply could have gone, untrimmed.
    """
    cut = len(raw)
    for stop in (f'\n{USER_LABEL}:', START, f'\n{name}:', '\nMemory:'):
        index = raw.find(stop)
        if index != -1:
            cut = min(cut, index)
    speaker = SPEAKER_LINE.search(raw)
    if speaker:
        cut = min(cut, speaker.start())
    drafts = []
    for part in re.split(r'\n\s*\n', raw[:cut]):
        line = re.sub(r'\s+', ' ', part).strip()
        line = re.sub(r'(?<!\.)\.\.(?!\.)', '.', line)
        if line:
            drafts.append(line)
    return drafts


def _flag_name(match: re.Match) -> str:
    return next(group for group in match.groups() if group).upper()


def apply_flags(text: str, flags: dict) -> tuple[str, list[dict]]:
    """Replace `<USER>`, `[CONTINUE]`, and `{NAME}` with the value defined for that flag.

    The mark is a placeholder, the way `{name}` is in an f-string. It is not text to show.
    """
    table = {str(key).upper(): '' if value is None else str(value) for key, value in (flags or {}).items()}
    used = []

    def replace(match):
        name = _flag_name(match)
        used.append({'name': name, 'value': table.get(name, ''), 'defined': name in table})
        return table.get(name, '')

    rendered = FLAG.sub(replace, text)
    rendered = re.sub(r'\s+([.!?…])', r'\1', rendered)
    rendered = re.sub(r'\s{2,}', ' ', rendered).strip()
    return rendered, used


def render_reply(raw: str, name: str, flags: dict | None = None) -> dict:
    """Turn one generation into ranked options. Blank lines are the rerank boundaries."""
    options = []
    for draft in reply_drafts(raw, name):
        text, used = apply_flags(draft, flags or {})
        text = _shorten(text)
        if not text:
            continue
        options.append({'rank': len(options) + 1, 'text': text, 'flags': used})
    return {'options': options}


def is_unfinished(raw: str, name: str) -> bool:
    """True when the first draft was cut off by the token limit rather than ending on its own."""
    drafts = reply_drafts(raw, name)
    return bool(drafts) and not drafts[0].endswith(FINISHED_ENDINGS)


def reply_options(raw: str, name: str, flags: dict | None = None) -> list[str]:
    return [option['text'] for option in render_reply(raw, name, flags)['options']]


def _shorten(line: str) -> str:
    """Keep a draft to a couple of finished sentences.

    A thought the token limit cut off is kept as a trailing thought: the fragment
    with an ellipsis, so it reads as the speaker trailing off rather than as an error.
    """
    sentences = SENTENCE.findall(line)
    consumed = ''.join(sentences)
    tail = line[len(consumed):].strip()
    if len(sentences) > MAX_REPLY_SENTENCES:
        line = ''.join(sentences[:MAX_REPLY_SENTENCES]).strip()
    elif tail and not tail.endswith(FINISHED_ENDINGS):
        head = consumed.strip()
        trailing = tail.rstrip(' ,;:')
        line = f'{head} {trailing}…'.strip()
    if len(line) > MAX_REPLY_CHARS:
        clipped = line[:MAX_REPLY_CHARS].rsplit(' ', 1)[0].rstrip('.,;:')
        line = f'{clipped}…' if clipped else line[:MAX_REPLY_CHARS]
    return line.strip()


def clean_reply(raw: str, name: str, flags: dict | None = None) -> str:
    """The reply sent to the chat: the top-ranked option, with flags filled in."""
    options = reply_options(raw, name, flags)
    return options[0] if options else ''
