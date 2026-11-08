"""Figures are `souls/<slug>/soul.md` files you draft by hand."""
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

SOUL_FILE = 'soul.md'
_SLUG = re.compile(r'^[a-z0-9][a-z0-9-]{0,62}$')
_TITLE = re.compile(r'^#\s+(.+?)\s*#*\s*$', re.MULTILINE)


class SoulError(Exception):
    pass


class SoulNotFound(SoulError):
    pass


def souls_dir() -> Path:
    override = os.environ.get('BASALISK_SOULS_DIR')
    if override:
        return Path(override)
    return Path(__file__).resolve().parent.parent / 'souls'


def slugify(name: str) -> str:
    slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')[:63].strip('-')
    return slug or 'figure'


def title_of(content: str, fallback: str) -> str:
    match = _TITLE.search(content or '')
    return match.group(1).strip() if match else fallback


def template(name: str) -> str:
    return (
        f'# {name}\n\n'
        f'Who {name} is, in your own words. Everything in this file is what the model is told about {name}.\n\n'
        '## Personality\n\n'
        '## Voice\n\n'
        '## History\n'
    )


def _path(slug: str) -> Path:
    if not _SLUG.match(slug or ''):
        raise SoulNotFound(slug)
    return souls_dir() / slug / SOUL_FILE


def _describe(slug: str, path: Path, content: str | None = None) -> dict:
    text = path.read_text(encoding='utf-8') if content is None else content
    modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return {
        'slug': slug,
        'name': title_of(text, slug),
        'file': f'souls/{slug}/{SOUL_FILE}',
        'content': text,
        'updated_at': modified.isoformat(),
    }


def list_souls() -> list[dict]:
    root = souls_dir()
    if not root.is_dir():
        return []
    souls = []
    for folder in root.iterdir():
        path = folder / SOUL_FILE
        if folder.is_dir() and _SLUG.match(folder.name) and path.is_file():
            entry = _describe(folder.name, path)
            entry.pop('content')
            souls.append(entry)
    souls.sort(key=lambda soul: soul['updated_at'], reverse=True)
    return souls


def get(slug: str) -> dict:
    path = _path(slug)
    if not path.is_file():
        raise SoulNotFound(slug)
    return _describe(slug, path)


def create(name: str) -> dict:
    name = (name or '').strip()
    if not name:
        raise SoulError('Give the figure a name.')
    base = slugify(name)
    slug, n = base, 2
    while (souls_dir() / slug).exists():
        slug = f'{base}-{n}'[:63]
        n += 1
    path = souls_dir() / slug / SOUL_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    content = template(name)
    path.write_text(content, encoding='utf-8')
    return _describe(slug, path, content)


def save(slug: str, content: str) -> dict:
    path = _path(slug)
    if not path.is_file():
        raise SoulNotFound(slug)
    temporary = path.with_suffix('.md.tmp')
    temporary.write_text(content, encoding='utf-8')
    os.replace(temporary, path)
    return _describe(slug, path, content)


def delete(slug: str) -> None:
    path = _path(slug)
    if not path.is_file():
        raise SoulNotFound(slug)
    shutil.rmtree(path.parent)
