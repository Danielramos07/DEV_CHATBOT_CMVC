import os
from pathlib import Path
from dotenv import load_dotenv

# Project root (where `.env` and `wsgi.py` live)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


def _resolve_path(value: str) -> str:
    """Resolve a filesystem path.

    If `value` is relative, we anchor it at PROJECT_ROOT so running the app from
    different CWDs won't create paths like backoffice/backoffice/...
    """
    if value is None:
        return value
    value = str(value).strip()
    if not value:
        return value
    p = Path(value)
    if p.is_absolute():
        return str(p)
    return str((PROJECT_ROOT / p).resolve())

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change")
    REQUIRE_SIGNED_MEDIA = os.getenv("REQUIRE_SIGNED_MEDIA", "0").strip().lower() in {"1", "true", "yes", "on"}
    PG_HOST = os.getenv("PG_HOST", "localhost")
    PG_PORT = int(os.getenv("PG_PORT", "5432"))
    PG_DB   = os.getenv("PG_DB", "ai4governance")
    PG_USER = os.getenv("PG_USER", "postgres")
    PG_PASS = os.getenv("PG_PASS", "admin")
    INDEX_PATH = _resolve_path(os.getenv("INDEX_PATH", "backoffice/faiss.index"))
    FAQ_EMBEDDINGS_PATH = _resolve_path(os.getenv("FAQ_EMB_PATH", "backoffice/faq_embeddings.pkl"))
    # Store uploaded PDF documents under extras/documents (ignored by git)
    PDF_STORAGE_PATH = _resolve_path(os.getenv("PDF_PATH", "backoffice/app/extras/documents"))
    ICON_STORAGE_PATH = _resolve_path(os.getenv("ICON_PATH", "backoffice/app/static/icons"))
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
    RAG_EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "all-MiniLM-L12-v2")
    RAG_EMBEDDING_DIM = int(os.getenv("RAG_EMBEDDING_DIM", "384"))
    RAG_CHUNK_SIZE_CHARS = int(os.getenv("RAG_CHUNK_SIZE_CHARS", "1000"))
    RAG_CHUNK_OVERLAP_CHARS = int(os.getenv("RAG_CHUNK_OVERLAP_CHARS", "150"))
    RAG_TOP_K = int(os.getenv("RAG_TOP_K", "6"))
    RAG_MIN_SCORE = float(os.getenv("RAG_MIN_SCORE", "0.2"))
    RAG_MAX_CONTEXT_CHARS = int(os.getenv("RAG_MAX_CONTEXT_CHARS", "12000"))
    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
    OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))
