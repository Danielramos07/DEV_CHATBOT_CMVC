# DEV_CHATBOT_CMVC – Setup & Run Manual

This manual explains how to set up and run the chatbot backoffice locally on macOS using Python + virtualenv.

## 1. Prerequisites

- Machine with:
  - Python 3.9+ installed (`python3 --version`)
  - PostgreSQL running locally

Repo layout (relevant parts):

- `wsgi.py` – Flask entrypoint
- `backoffice/` – Flask app package
- `backoffice/requirements.txt` – Python dependencies
- `backoffice/db/init.sql` – DB schema & seed data
- `.env` – environment variables for DB and paths

All commands below assume the user is in the project root.

Adjust the path if your clone is elsewhere.

---

## 2. Database setup (PostgreSQL)

1. Make sure PostgreSQL is running locally (default port 5432).
2. Create the database `AI4Governance`:

   ```zsh
   psql -U postgres -c "CREATE DATABASE ai4governance";
   ```

3. Import the schema and initial data from `backoffice/db/init.sql`:

   ```bash
   psql -U postgres -d ai4governance -f backoffice/db/init.sql
   ```

   - You may need `-h localhost -p 5432` depending on your setup.

---

## 3. Environment variables (`.env`)

At the project root there is a `.env` file. Example contents:

```dotenv
PG_HOST=localhost
PG_PORT=5432
PG_DB=ai4governance
PG_USER=postgres
PG_PASS=admin

INDEX_PATH=backoffice/faiss.index
FAQ_EMB_PATH=backoffice/faq_embeddings.pkl
PDF_PATH=backoffice/pdfs
ICON_PATH=backoffice/static/icons

CORS_ORIGINS=http://localhost:5000,http://127.0.0.1:5000,http://localhost:3000,http://127.0.0.1:3000
```

Adjust values only if your DB or paths differ.

---

## 4. Python virtual environment

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate   # activate venv (macOS/Linux)
```

You should see something like `(.venv)` or `(dnl)` at the start of your shell prompt, indicating the venv is active.

To deactivate later:

```bash
deactivate
```

---

## 5. Install Python dependencies

With the virtualenv **activated** and from the project root:

```bash
pip install --upgrade pip
pip install -r backoffice/requirements.txt
```

---

## 6. Run the Flask application

With the virtualenv still active and from the project root:

```bash
export FLASK_APP=wsgi.py
export FLASK_ENV=development   # optional, enables debug reload
flask run
flask run --debug
```

You should see output similar to:

```text
 * Serving Flask app 'wsgi.py'
 * Debug mode: on
 * Running on http://127.0.0.1:5000
```

Keep this terminal open while the app is running.

---

## 7. Accessing the web UI

Open your browser and visit:

- `http://127.0.0.1:5000/` – main entry (landing page)
- `http://127.0.0.1:5000/login` – backoffice login (if enabled)

Other backoffice views are under routes wired in `backoffice/app/admin.py` and `backoffice/app/auth.py`, backed by templates in `backoffice/app/templates/`:

- `recursos.html`
- `respostas.html`
- `nao-respondidas.html`
- `contexto.html`
- `metricas.html`
- `landing.html`
- `landing-2.html`

---

## 8. Vector index & documents

The app uses FAISS and sentence-transformers for retrieval.

Paths (relative to project root):

- FAISS index: `backoffice/faiss.index`
- FAQ embeddings: `backoffice/faq_embeddings.pkl` (optional, may be created by the app)
- PDF documents: `backoffice/pdfs/`
- Icons: `backoffice/static/icons/`

If you add new documents, there may be an admin action or API endpoint to rebuild the FAISS index (check `backoffice/app/services/rag.py` and API routes under `backoffice/app/api/`).
