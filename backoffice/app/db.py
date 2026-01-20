import psycopg2
from psycopg2.pool import SimpleConnectionPool
from pgvector.psycopg2 import register_vector
from .config import Config
from flask import g

_pool = None
_pgvector_registered = set()

def init_pool(app):
    global _pool
    _pool = SimpleConnectionPool(
        1, 10,
        host=app.config["PG_HOST"],
        port=app.config["PG_PORT"],
        dbname=app.config["PG_DB"],
        user=app.config["PG_USER"],
        password=app.config["PG_PASS"],
    )

def _ensure_pgvector(conn):
    if conn is None:
        return
    conn_id = id(conn)
    if conn_id in _pgvector_registered:
        return
    register_vector(conn)
    _pgvector_registered.add(conn_id)

def get_pool_conn():
    """Get a raw pooled connection (NOT bound to Flask request context)."""
    global _pool
    if _pool is None:
        raise RuntimeError("DB pool not initialized")
    conn = _pool.getconn()
    _ensure_pgvector(conn)
    return conn

def put_pool_conn(conn):
    """Return a raw pooled connection."""
    global _pool
    if _pool is None or conn is None:
        return
    _pool.putconn(conn)

def get_conn():
    if "db_conn" not in g:
        g.db_conn = _pool.getconn()
        _ensure_pgvector(g.db_conn)
    return g.db_conn   

def close_conn(e=None): 
    conn = g.pop("db_conn", None)
    if conn:
        _pool.putconn(conn)  


def ensure_schema() -> None:
    """Best-effort schema updates required for runtime features.

    - Adds chatbot.ativo (global active chatbot) if missing
    - Adds faq.identificador if missing
    - Creates/initializes video_job singleton row (global cross-worker video job status)
    - Ensures there is at least one active chatbot when any exist
    """
    global _pool
    if _pool is None:
        return
    conn = None
    cur = None
    try:
        conn = _pool.getconn()
        _ensure_pgvector(conn)
        cur = conn.cursor()
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        # Add global active flag for chatbots (safe to run repeatedly)
        cur.execute("ALTER TABLE chatbot ADD COLUMN IF NOT EXISTS ativo BOOLEAN NOT NULL DEFAULT FALSE;")
        # Customizable chatbot messages (safe to run repeatedly)
        cur.execute("ALTER TABLE chatbot ADD COLUMN IF NOT EXISTS greeting_video_text TEXT;")
        cur.execute("ALTER TABLE chatbot ADD COLUMN IF NOT EXISTS mensagem_inicial TEXT;")
        cur.execute("ALTER TABLE chatbot ADD COLUMN IF NOT EXISTS mensagem_feedback_positiva TEXT;")
        cur.execute("ALTER TABLE chatbot ADD COLUMN IF NOT EXISTS mensagem_feedback_negativa TEXT;")
        # Extra chatbot video paths (safe to run repeatedly)
        cur.execute("ALTER TABLE chatbot ADD COLUMN IF NOT EXISTS video_positive_path TEXT;")
        cur.execute("ALTER TABLE chatbot ADD COLUMN IF NOT EXISTS video_negative_path TEXT;")
        cur.execute("ALTER TABLE chatbot ADD COLUMN IF NOT EXISTS video_no_answer_path TEXT;")
        # Add FAQ identifier (safe to run repeatedly)
        cur.execute("ALTER TABLE faq ADD COLUMN IF NOT EXISTS identificador VARCHAR(120);")
        # Add FAQ 'serve' field (A quem se destina / para que serve)
        cur.execute("ALTER TABLE faq ADD COLUMN IF NOT EXISTS serve_text TEXT;")
        # Global video job status (singleton row)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS video_job (
                id INT PRIMARY KEY DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'idle',
                kind TEXT,
                faq_id INT,
                chatbot_id INT,
                progress INT NOT NULL DEFAULT 0,
                message TEXT NOT NULL DEFAULT '',
                error TEXT,
                cancel_requested BOOLEAN NOT NULL DEFAULT FALSE,
                started_at TIMESTAMPTZ,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )
        # RAG chunks stored in pgvector (safe to run repeatedly)
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS rag_chunks (
                chunk_id SERIAL PRIMARY KEY,
                chatbot_id INT REFERENCES chatbot(chatbot_id) ON DELETE CASCADE,
                pdf_id INT REFERENCES pdf_documents(pdf_id) ON DELETE CASCADE,
                page_num INT,
                chunk_index INT,
                content TEXT NOT NULL,
                embedding vector({Config.RAG_EMBEDDING_DIM}),
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS rag_chunks_chatbot_idx
            ON rag_chunks (chatbot_id);
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS rag_chunks_pdf_idx
            ON rag_chunks (pdf_id);
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS rag_chunks_embedding_idx
            ON rag_chunks USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100);
            """
        )
        # Ensure singleton row exists
        cur.execute("INSERT INTO video_job (id) VALUES (1) ON CONFLICT (id) DO NOTHING;")
        conn.commit()

        # Ensure at least one chatbot is active (if any exist)
        cur.execute("SELECT 1 FROM chatbot WHERE ativo = TRUE LIMIT 1;")
        has_active = cur.fetchone() is not None
        if not has_active:
            cur.execute(
                """
                UPDATE chatbot
                SET ativo = TRUE
                WHERE chatbot_id = (
                    SELECT chatbot_id FROM chatbot ORDER BY chatbot_id ASC LIMIT 1
                );
                """
            )
            conn.commit()
    except Exception:
        try:
            if conn:
                conn.rollback()
        except Exception:
            pass
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            if conn:
                _pool.putconn(conn)
        except Exception:
            pass




