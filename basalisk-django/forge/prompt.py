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

from . import embed, rag

USER_LABEL = 'You'
START = '<START>'
# Placeholders in a model card. They are exact strings, found with Knuth-Morris-Pratt (KMT).
RECENT_TURNS = 2
MEMORY_LIMIT = 3
SPEAKER_LINE = re.compile(r"\n[ \t]*[A-Z][\w' .-]{0,30}:")
SENTENCE = re.compile(r'.*?[.!?…](?:\s+|$)', re.DOTALL)
FLAG = re.compile(r'<([A-Za-z][A-Za-z0-9_]*)>|\[([A-Za-z][A-Za-z0-9_]*)\]|\{([A-Za-z][A-Za-z0-9_]*)\}')
# Roleplay beats written between asterisks: *leans in* or **leans in**.
ACTION = re.compile(r'\*\*([^*]+)\*\*|\*([^*]+)\*')
ACTION_TAG = '[ACTION]'
MAX_REPLY_CHARS = 240
MAX_REPLY_SENTENCES = 2
# Safety filter: a reply that uses explicit sexual wording is dropped when the filter is on.
EXPLICIT = re.compile(
    r"\b(sexual(?:ly)?|porn\w*|erotic\w*|nude|nudity|naked|orgasm\w*|genitals?|horny|blowjob|fuck\w*)\b",
    re.IGNORECASE,
)


@dataclass
class Prompt:
    text: str
    document: dict = field(default_factory=dict)
    memories: list[str] = field(default_factory=list)
    soul_sections: list[str] = field(default_factory=list)


# The short tag for the persona slot, and the wording model cards use for it.
PERSONA_TAG = '[PERSONA]'
CARD_PERSONA_TAGS = (
    '[A few sentences about the character you want the model to play]',
    '{{persona}}',
)


def shorten_tags(template: str) -> str:
    """Replace each card's persona wording with [PERSONA], found with KMT."""
    for card_tag in CARD_PERSONA_TAGS:
        template = kmt_replace(template, card_tag, PERSONA_TAG)
    return template


# The card's marks, and the one data field each mark reads. A field is stored once.
TAG_FIELDS = (
    ('[PERSONA]', 'persona'),
    ('[DIALOGUE HISTORY]', 'dialogue_history'),
    ('[Your input message here]', 'message'),
    ('[CHARACTER]', 'character'),
    ('{{char}}', 'character'),
    ('[MEMORY]', 'memory'),
)
DEFAULT_TEMPLATE = (
    "[CHARACTER]'s Persona: [PERSONA]\n"
    '[MEMORY]\n'
    '<START>\n'
    '[DIALOGUE HISTORY]\n'
    'You: [Your input message here]\n'
    '[CHARACTER]:'
)


def _section_text(section: Mapping) -> str:
    if section['title'] and section['text']:
        return f"{section['title']}: {section['text']}"
    return section['title'] or section['text']


def soul_text(sections: list[Mapping]) -> str:
    return '\n'.join(part for part in (_section_text(s) for s in sections) if part)


def _line(role: str, content: str, name: str) -> str:
    speaker = USER_LABEL if role == 'you' else name
    return f'{speaker}: {content.strip()}'


def _kmt_prefix(pattern: str) -> list[int]:
    """Longest proper prefix of pattern[:i+1] that is also a suffix."""
    pi = [0] * len(pattern)
    length = 0
    for i in range(1, len(pattern)):
        while length > 0 and pattern[length] != pattern[i]:
            length = pi[length - 1]
        if pattern[length] == pattern[i]:
            length += 1
        pi[i] = length
    return pi


def kmt_find(text: str, pattern: str) -> list[int]:
    """Start indexes of every exact occurrence of pattern in text.

    Knuth-Morris-Pratt. The text is read once. On a mismatch the prefix table
    says how much of the pattern is still matched, so the scan does not go back.
    """
    if not pattern or len(pattern) > len(text):
        return []
    pi = _kmt_prefix(pattern)
    found = []
    matched = 0
    for i, character in enumerate(text):
        while matched > 0 and pattern[matched] != character:
            matched = pi[matched - 1]
        if pattern[matched] == character:
            matched += 1
        if matched == len(pattern):
            found.append(i - len(pattern) + 1)
            matched = pi[matched - 1]
    return found


def kmt_replace(text: str, pattern: str, replacement: str) -> str:
    """Replace each exact occurrence of pattern, using KMT to find them."""
    starts = kmt_find(text, pattern)
    if not starts:
        return text
    parts = []
    cursor = 0
    span = len(pattern)
    for start in starts:
        if start < cursor:
            continue
        parts.append(text[cursor:start])
        parts.append(replacement)
        cursor = start + span
    parts.append(text[cursor:])
    return ''.join(parts)


def prompt_json(template: str, *, character: str, persona: str, dialogue_history: str, message: str, memory: str = '') -> dict:
    """The prompt as JSON: the card text, the tags KMT finds in it, and the data those tags take."""
    template = shorten_tags(template.strip())
    if kmt_find(template, '<|system|>') and not kmt_find(template, '<|user|>') and not kmt_find(template, '[Your input message here]'):
        template = f'{template}\n<|user|>[Your input message here]\n<|model|>'
    values = {
        'character': character,
        'persona': persona.strip(),
        'dialogue_history': dialogue_history,
        'message': message.strip(),
        'memory': memory,
    }
    found = [tag for tag, _field in TAG_FIELDS if kmt_find(template, tag)]
    found.sort(key=lambda tag: kmt_find(template, tag)[0])
    data = {}
    for tag in found:
        field_name = dict(TAG_FIELDS)[tag]
        data[field_name] = values[field_name]
    return {'template': template, 'tags': found, 'data': data}


def decode_prompt(document: Mapping) -> str:
    """Replace each tag with its data field. Empty data drops the tag's line."""
    text = document['template']
    data = document['data']
    fields = dict(TAG_FIELDS)
    for tag in sorted(document['tags'], key=len, reverse=True):
        value = data.get(fields[tag], '')
        if value:
            text = kmt_replace(text, tag, value)
        else:
            text = kmt_replace(text, '\n' + tag, '')
            text = kmt_replace(text, tag, '')
    return re.sub(r'\n{3,}', '\n\n', text).strip()


def fill_template(template: str, name: str, persona: str, turns: Iterable[Mapping]) -> str:
    """Fill a model card's prompt. Character, persona, dialogue history, and the message are tags."""
    return decode_prompt(_document_for(template, name, persona, turns))


def _needs_message_slot(template: str) -> bool:
    if kmt_find(template, '[Your input message here]'):
        return True
    return bool(kmt_find(template, '<|system|>') and not kmt_find(template, '<|user|>'))


def _document_for(template: str, name: str, persona: str, turns: Iterable[Mapping], memory: str = '') -> dict:
    turns = list(turns)
    message = ''
    if _needs_message_slot(template) and turns and turns[-1].get('role') == 'you':
        message = turns[-1]['content']
        turns = turns[:-1]
    return prompt_json(
        template,
        character=name,
        persona=persona,
        dialogue_history='\n'.join(_line(t['role'], t['content'], name) for t in turns),
        message=message,
        memory=memory,
    )


def build_prompt(
    name: str,
    soul: str,
    history: Iterable[Mapping] = (),
    count_tokens: Callable[[str], int] | None = None,
    budget: int | None = None,
    rank: Callable[..., list[int]] | None = None,
    template: str | None = None,
) -> Prompt:
    name = name.strip() or 'Figure'
    template = (template or '').strip()
    turns = list(history)
    query = next((t['content'] for t in reversed(turns) if t['role'] == 'you'), '')

    rank = rank or rag.rank
    sections = rag.soul_sections(soul)
    intro = sections[:1]
    # The Person facts are the figure's own facts. They are always kept, never trimmed for length.
    pinned = [s for s in sections[1:] if s['title'] == 'Person']
    rest = [s for s in sections[1:] if s['title'] != 'Person']
    matched = [rest[i] for i in rank(query, [_section_text(s) for s in rest], k=3)]

    recent = turns[-RECENT_TURNS:]
    older = turns[:-RECENT_TURNS] if len(turns) > RECENT_TURNS else []
    pool = rag.exchanges(older, name, USER_LABEL)
    # Key parts of the earlier chat, by meaning. The last reply stays in the dialogue itself.
    memories = [pool[i] for i in embed.semantic_rank(query, pool, k=MEMORY_LIMIT)]

    def assemble(soul_parts, memory_parts, kept):
        persona = soul_text(soul_parts)
        memory = ('Memory:\n' + '\n'.join(memory_parts)) if memory_parts else ''
        return _document_for(template or DEFAULT_TEMPLATE, name, persona, kept, memory)

    soul_parts, memory_parts, kept = sections, list(memories), list(recent)

    def result():
        document = assemble(soul_parts, memory_parts, kept)
        return Prompt(
            text=decode_prompt(document),
            document=document,
            memories=list(memory_parts),
            soul_sections=[s['title'] for s in soul_parts if s['title']],
        )

    if count_tokens is None or budget is None:
        return result()

    def fits():
        return count_tokens(decode_prompt(assemble(soul_parts, memory_parts, kept))) <= budget

    if not fits():
        soul_parts = intro + pinned + matched
    while not fits() and memory_parts:
        memory_parts.pop()
    while not fits() and len(kept) > 1:
        kept.pop(0)
    while not fits() and len(soul_parts) > len(intro) + len(pinned):
        soul_parts = soul_parts[:-1]
    return result()


FINISHED_ENDINGS = ('.', '!', '?', '…', '"', '”', "'", '*', ')')


def reply_drafts(raw: str, name: str) -> list[str]:
    """Split a generation into the separate drafts it usually writes one after another.

    Blank lines, a new speaker, and forum marks like ``[CONTINUE]`` start another
    draft. Each draft is one way the reply could have gone, untrimmed.
    """
    cut = len(raw)
    for stop in (f'\n{USER_LABEL}:', f'\n{name}:', '\nMemory:', '<|user|>', '<|model|>', '<|system|>', '<START'):
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


def _clean_piece(text: str) -> str:
    piece = re.sub(r'\s+', ' ', text).strip()
    return re.sub(r'\s+([.!?…,])', r'\1', piece)


def _join(spoken: str, piece: str) -> str:
    if not piece:
        return spoken
    if not spoken or piece[0] in '.!?…,':
        return spoken + piece
    return f'{spoken} {piece}'


def split_actions(text: str) -> tuple[str, list[dict]]:
    """Split a line into what was said and the *beat* actions, keeping their order.

    Each action records `at`: how many characters of the spoken text come before it.
    The list is a stack: the last tag is the top. Later these can drive a face, a gesture, or a control.
    """
    spoken, actions, cursor = '', [], 0
    source = text or ''
    for match in ACTION.finditer(source):
        spoken = _join(spoken, _clean_piece(source[cursor:match.start()]))
        beat = (match.group(1) or match.group(2) or '').strip()
        if beat:
            actions.append({'tag': ACTION_TAG, 'text': beat, 'at': len(spoken)})
        cursor = match.end()
    return _join(spoken, _clean_piece(source[cursor:])), actions


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


def render_reply(raw: str, name: str, flags: dict | None = None, safety_filter: bool = False) -> dict:
    """Turn one generation into ranked options. Blank lines are the rerank boundaries.

    With the safety filter on, options that use explicit sexual wording are dropped.
    """
    options = []
    for draft in reply_drafts(raw, name):
        text, used = apply_flags(draft, flags or {})
        spoken, actions = split_actions(text)
        spoken = _shorten(spoken)
        # A beat after the sentences that were cut off is dropped with them.
        actions = [action for action in actions if action['at'] <= len(spoken.rstrip('…'))]
        if not spoken and not actions:
            continue
        if safety_filter and EXPLICIT.search(spoken):
            continue
        options.append({'rank': len(options) + 1, 'text': spoken, 'flags': used, 'actions': actions})
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
