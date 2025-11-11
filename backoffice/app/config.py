import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change")
    PG_HOST = os.getenv("PG_HOST", "localhost")
    PG_PORT = int(os.getenv("PG_PORT", "5432"))
    PG_DB   = os.getenv("PG_DB", "AI4Governance")
    PG_USER = os.getenv("PG_USER", "postgres")
    PG_PASS = os.getenv("PG_PASS", "admin")
    INDEX_PATH = os.getenv("INDEX_PATH", "data/vectorstore/faiss.index")
    FAQ_EMBEDDINGS_PATH = os.getenv("FAQ_EMB_PATH", "data/vectorstore/faq_embeddings.pkl")
    PDF_STORAGE_PATH = os.getenv("PDF_PATH", "data/docs")
    ICON_STORAGE_PATH = os.getenv("ICON_PATH", "data/icons")
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")