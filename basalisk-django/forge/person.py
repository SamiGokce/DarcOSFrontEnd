"""General facts about a figure, chosen from a fixed set rather than typed.

Stored as `souls/<slug>/person.json` beside `soul.md`. The choices are written into the prompt. The model writes the reply.
"""


SELECTS = (
    ('age', 'Age', ('Child', 'Teenager', 'Young adult', 'Adult', 'Middle-aged', 'Elder')),
    ('gender', 'Gender', ('Woman', 'Man', 'Nonbinary')),
    ('pronouns', 'Pronouns', ('she/her', 'he/him', 'they/them')),
    ('occupation', 'Occupation', (
        'Lighthouse keeper', 'Sailor', 'Scholar', 'Merchant', 'Soldier', 'Healer',
        'Artist', 'Teacher', 'Farmer', 'Noble', 'Wanderer',
    )),
    ('home', 'Home', ('A coast', 'A city', 'A village', 'The mountains', 'At sea', 'Inland')),
    ('relation', 'How they know you', ('Stranger', 'Acquaintance', 'Friend', 'Family', 'Rival', 'Mentor')),
)

MULTIS = (
    ('traits', 'Traits', (
        'patient', 'dry humor', 'suspicious', 'warm', 'blunt', 'curious',
        'guarded', 'loyal', 'restless', 'formal',
    )),
    ('speech', 'Speech', (
        'short sentences', 'mentions the weather', 'formal address', 'slang',
        'asks questions', 'tells long stories', 'quiet',
    )),
    ('interests', 'Interests', (
        'the sea', 'ships', 'books', 'music', 'food', 'maps', 'machines',
        'gardens', 'history', 'weather',
    )),
)


def schema() -> list[dict]:
    fields = [{'key': key, 'label': label, 'kind': 'select', 'options': list(options)} for key, label, options in SELECTS]
    fields += [{'key': key, 'label': label, 'kind': 'multi', 'options': list(options)} for key, label, options in MULTIS]
    return fields


def empty_person() -> dict:
    person = {key: '' for key, _label, _options in SELECTS}
    person.update({key: [] for key, _label, _options in MULTIS})
    return person


def normalize_person(data) -> dict:
    """Keep only known choices. Anything else is left unset."""
    incoming = data if isinstance(data, dict) else {}
    person = empty_person()
    for key, _label, options in SELECTS:
        value = incoming.get(key) or ''
        if value in options:
            person[key] = value
    for key, _label, options in MULTIS:
        chosen = incoming.get(key) or []
        if isinstance(chosen, list):
            person[key] = [option for option in options if option in chosen]
    return person


def person_block(person) -> str:
    """The facts, as a soul section the model can be told."""
    clean = normalize_person(person)
    lines = [f'{label}: {clean[key]}' for key, label, _options in SELECTS if clean[key]]
    lines += [f'{label}: {", ".join(clean[key])}' for key, label, _options in MULTIS if clean[key]]
    if not lines:
        return ''
    return '## Person\n' + '\n'.join(lines)


def fact_statements(person) -> list[dict]:
    """One line per chosen fact, which an embedding model can compare to a question."""
    clean = normalize_person(person)
    rows = []
    for key, label, _options in SELECTS:
        if clean[key]:
            rows.append({'key': key, 'value': clean[key], 'text': f'{label}: {clean[key]}'})
    for key, label, _options in MULTIS:
        if clean[key]:
            rows.append({'key': key, 'value': clean[key], 'text': f'{label}: {", ".join(clean[key])}'})
    return rows


def with_person(content: str, person) -> str:
    block = person_block(person)
    if not block:
        return content
    return f'{content.rstrip()}\n\n{block}\n'
