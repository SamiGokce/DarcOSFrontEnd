"""Compose persona fields into the prompt format Pygmalion models were trained on.

    {name}'s Persona: ...
    Scenario: ...
    <START>
    You: ...
    {name}: ...
    <START>
    {name}: {greeting}
    You: {message}
    {name}:
"""
import re
from typing import Callable, Iterable, Mapping

from .models import TEMPERAMENT_AXES

USER_LABEL = 'You'
START = '<START>'
_USER_SPEAKER = re.compile(r'^\{\{user\}\}:', re.MULTILINE)
_CHAR_SPEAKER = re.compile(r'^\{\{char\}\}:', re.MULTILINE)


def _join_words(words: list[str]) -> str:
    if len(words) <= 2:
        return ' and '.join(words)
    return ', '.join(words[:-1]) + ', and ' + words[-1]


def temperament_words(temperament: Mapping[str, int]) -> list[str]:
    words = []
    for axis, (low, high) in TEMPERAMENT_AXES.items():
        value = int(temperament.get(axis, 50))
        if value <= 15:
            words.append(f'very {low}')
        elif value <= 35:
            words.append(low)
        elif value >= 85:
            words.append(f'very {high}')
        elif value >= 65:
            words.append(high)
    return words


def persona_text(persona: Mapping) -> str:
    name = persona['name'].strip()
    sentences = []
    epithet = persona.get('epithet', '').strip()
    if epithet:
        sentences.append(f'{name} is {epithet.rstrip(".")}.')

    described = temperament_words(persona.get('temperament') or {})
    described += [t.strip() for t in persona.get('traits') or [] if t.strip()]
    if described:
        sentences.append(f'{name} is {_join_words(described)}.')

    for field in ('personality', 'appearance', 'speaking_style'):
        text = persona.get(field, '').strip()
        if text:
            sentences.append(text)
    return ' '.join(sentences)


def _fill(text: str, name: str) -> str:
    """`{{user}}:` at a line start is the speaker label; anywhere else it reads as "you"."""
    text = _USER_SPEAKER.sub(f'{USER_LABEL}:', text)
    text = _CHAR_SPEAKER.sub(f'{name}:', text)
    return text.replace('{{char}}', name).replace('{{user}}', 'you').strip()


def _line(role: str, content: str, name: str) -> str:
    speaker = USER_LABEL if role == 'you' else name
    return f'{speaker}: {content.strip()}'


def build_prompt(
    persona: Mapping,
    history: Iterable[Mapping] = (),
    count_tokens: Callable[[str], int] | None = None,
    budget: int | None = None,
) -> str:
    """Build the prompt, dropping the oldest turns (then the examples) to fit `budget` tokens."""
    name = persona['name'].strip()
    header = [f"{name}'s Persona: {persona_text(persona)}"]
    scenario = persona.get('scenario', '').strip()
    if scenario:
        header.append(f'Scenario: {_fill(scenario, name)}')

    examples = _fill(persona.get('example_dialogue', ''), name)
    opening = []
    greeting = persona.get('greeting', '').strip()
    if greeting:
        opening.append(f'{name}: {_fill(greeting, name)}')

    turns = [_line(t['role'], t['content'], name) for t in history]

    def assemble(kept_turns: list[str], with_examples: bool) -> str:
        lines = list(header)
        if with_examples and examples:
            lines += [START, examples]
        lines.append(START)
        lines += opening + kept_turns
        lines.append(f'{name}:')
        return '\n'.join(lines)

    if count_tokens is None or budget is None:
        return assemble(turns, True)

    kept = list(turns)
    while len(kept) > 1 and count_tokens(assemble(kept, True)) > budget:
        kept.pop(0)
    prompt = assemble(kept, True)
    if count_tokens(prompt) > budget:
        prompt = assemble(kept, False)
    return prompt


def clean_reply(raw: str, name: str) -> str:
    """Keep only the character's next line; the model tends to keep writing both sides."""
    cut = len(raw)
    for stop in (f'\n{USER_LABEL}:', START, f'\n{name}:'):
        index = raw.find(stop)
        if index != -1:
            cut = min(cut, index)
    return raw[:cut].strip()
