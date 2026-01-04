import psycopg2
from psycopg2.pool import SimpleConnectionPool
from flask import g

_pool = None

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

def get_pool_conn():
    """Get a raw pooled connection (NOT bound to Flask request context)."""
    global _pool
    if _pool is None:
        raise RuntimeError("DB pool not initialized")
    return _pool.getconn()

def put_pool_conn(conn):
    """Return a raw pooled connection."""
    global _pool
    if _pool is None or conn is None:
        return
    _pool.putconn(conn)

def get_conn():
    if "db_conn" not in g:
        g.db_conn = _pool.getconn()
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
        cur = conn.cursor()
        # Add global active flag for chatbots (safe to run repeatedly)
        cur.execute("ALTER TABLE chatbot ADD COLUMN IF NOT EXISTS ativo BOOLEAN NOT NULL DEFAULT FALSE;")
        # Add FAQ identifier (safe to run repeatedly)
        cur.execute("ALTER TABLE faq ADD COLUMN IF NOT EXISTS identificador VARCHAR(120);")
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




