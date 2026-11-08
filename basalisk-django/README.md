# The Forge

A Django app for shaping character personas and talking to them through a local
[Pygmalion](https://huggingface.co/PygmalionAI/pygmalion-1.3b) model.

## Run

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver
```

Open http://127.0.0.1:8000/ for the Basalisk UI, and http://127.0.0.1:8000/shelf/ for the Forge. You can build personas and preview prompts without the model.

To talk to a persona, install the model packages, then press **Load Pygmalion** in the page.
The first load downloads the weights (several GB).

```bash
uv pip install --python .venv/bin/python -r requirements-model.txt
```

| Variable | Default | Purpose |
| --- | --- | --- |
| `PYGMALION_MODEL` | `PygmalionAI/pygmalion-1.3b` | Hugging Face model id |
| `PYGMALION_CONTEXT` | model's own window | Context size in tokens |

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET`, `POST` | `/api/forge/personas/` | List or create personas |
| `GET`, `PUT`, `PATCH`, `DELETE` | `/api/forge/personas/<id>/` | One persona |
| `POST` | `/api/forge/mold/` | Prompt preview for an unsaved persona and conversation |
| `POST` | `/api/forge/speak/` | Generate the persona's next reply |
| `GET`, `POST` | `/api/forge/model/` | Model status, or start loading it |

## Test

```bash
.venv/bin/python manage.py test
```
