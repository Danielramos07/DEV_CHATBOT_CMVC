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

def get_conn():
    if "db_conn" not in g:
        g.db_conn = _pool.getconn()
    return g.db_conn   

def close_conn(e=None): 
    conn = g.pop("db_conn", None)
    if conn:
        _pool.putconn(conn)  




