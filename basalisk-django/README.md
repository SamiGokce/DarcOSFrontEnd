# Basalisk

A workbench for drafting characters as `soul.md` files and testing how they come
across on local [Pygmalion](https://huggingface.co/PygmalionAI) models of different sizes.

## Run

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt -r requirements-model.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver
```

Open http://127.0.0.1:8000/.

- **Figures**: each figure is `souls/<slug>/soul.md`. The first `# ` heading is its name,
  and every `##` section is something the model can be told about it.
- **Model**: download Pygmalion checkpoints. Downloads run in a separate worker process.
- **Threads**: pick a figure and a model, then chat. Each chat is tied to one model, so
  switching models starts a new chat. The model loads on the first message.

## Memory and context

Prompts use the Pygmalion format: persona, `<START>`, recent turns. Two simple retrieval
(BM25) steps keep long chats within the model's context window:

- Earlier exchanges that fall out of the last 6 turns are ranked against the new message,
  and the top 3 are added as `Memory:`.
- If the soul is too long for the window, only its intro and the sections most relevant
  to the message are kept.

Each reply shows which memories were recalled and the exact prompt that was sent.

| Variable | Default | Purpose |
| --- | --- | --- |
| `BASALISK_SOULS_DIR` | `souls/` | Where `soul.md` files live |
| `BASALISK_DOWNLOAD_DIR` | `var/downloads/` | Download worker status files |
| `PYGMALION_CONTEXT` | model's own window | Context size in tokens |

## API

All paths are under `/api/forge/`.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET`, `POST` | `souls/` | List figures, or create one from a name |
| `GET`, `PUT`, `DELETE` | `souls/<slug>/` | Read, save, or delete a `soul.md` (deleting also removes its chats) |
| `GET`, `POST` | `chats/?soul=<slug>` | List chats, or start one for a soul and `model_id` |
| `GET`, `DELETE` | `chats/<id>/` | One chat with its messages |
| `POST` | `chats/<id>/messages/` | Send a message; returns the reply, recalled memories, and prompt |
| `GET`, `POST` | `models/` | Model catalog |
| `POST` | `models/<id>/download/`, `models/<id>/load/` | Download or load a model |
| `GET` | `model/` | Loaded model status |

## Test

```bash
.venv/bin/python manage.py test
```
