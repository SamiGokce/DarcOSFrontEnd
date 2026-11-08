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


def clean_reply(raw: str, name: str) -> str:
    """Keep only the character's next line; the model tends to keep writing both sides."""
    cut = len(raw)
    for stop in (f'\n{USER_LABEL}:', START, f'\n{name}:', '\nMemory:'):
        index = raw.find(stop)
        if index != -1:
            cut = min(cut, index)
    speaker = SPEAKER_LINE.search(raw)
    if speaker:
        cut = min(cut, speaker.start())
    return raw[:cut].strip()
