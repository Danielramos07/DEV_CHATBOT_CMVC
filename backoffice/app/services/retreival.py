from ..db import get_conn
from sentence_transformers import SentenceTransformer
import numpy as np
import faiss
import pickle
import logging
from ..config import Config
import os
from .text import preprocess_text

embedding_model = SentenceTransformer('all-MiniLM-L12-v2')
PDF_STORAGE_PATH = Config.PDF_STORAGE_PATH
ICON_STORAGE_PATH = Config.ICON_STORAGE_PATH
os.makedirs(PDF_STORAGE_PATH, exist_ok=True)
os.makedirs(ICON_STORAGE_PATH, exist_ok=True)


def build_faiss_index(chatbot_id=None):
    conn = get_conn()
    cur = conn.cursor()
    try:
        if chatbot_id:
            cur.execute("SELECT faq_id, pergunta, resposta, chatbot_id FROM FAQ WHERE chatbot_id = %s", (chatbot_id,))
        else:
            cur.execute("SELECT faq_id, pergunta, resposta, chatbot_id FROM FAQ")
        faqs = cur.fetchall()
        perguntas = [f[1] for f in faqs]
        if not perguntas:
            emb_dim = embedding_model.get_sentence_embedding_dimension()
            embeddings = np.zeros((1, emb_dim), dtype=np.float32)
            index = faiss.IndexFlatIP(emb_dim)
        else:
            embeddings = embedding_model.encode(perguntas, show_progress_bar=True)
            embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
            index = faiss.IndexFlatIP(embeddings.shape[1])
            index.add(np.array(embeddings, dtype=np.float32))
        with open(Config.FAQ_EMBEDDINGS_PATH, 'wb') as f:
            pickle.dump({'faqs': faqs, 'embeddings': embeddings}, f)
        faiss.write_index(index, Config.INDEX_PATH)
        logging.info(f"Índice FAISS para FAQs salvo em {Config.INDEX_PATH}")
    except Exception as e:
        logging.error(f"Erro ao construir índice FAISS para FAQs: {e}")
        raise
    finally:
        cur.close()

def load_faiss_index():
    try:
        if not os.path.exists(Config.INDEX_PATH) or not os.path.exists(Config.FAQ_EMBEDDINGS_PATH):
            logging.info("Índice FAISS ou embeddings de FAQs não encontrados. Reconstruindo...")
            build_faiss_index()
        index = faiss.read_index(Config.INDEX_PATH)
        with open(Config.FAQ_EMBEDDINGS_PATH, 'rb') as f:
            data = pickle.load(f)
        return index, data['faqs'], data['embeddings']
    except Exception as e:
        logging.error(f"Erro ao carregar índice FAISS para FAQs: {e}")
        logging.info("Reconstruindo índice FAISS para FAQs...")
        build_faiss_index()
        index = faiss.read_index(Config.INDEX_PATH)
        with open(Config.FAQ_EMBEDDINGS_PATH, 'rb') as f:
            data = pickle.load(f)
        return index, data['faqs'], data['embeddings']

faiss_index, faqs_db, faq_embeddings = load_faiss_index()

def pesquisar_faiss(pergunta, chatbot_id=None, k=1, min_sim=0.7):
    pergunta = preprocess_text(pergunta)
    results = []
    if chatbot_id:
        faqs = [f for f in faqs_db if f[3] == int(chatbot_id)]
        if not faqs:
            return []
        perguntas = [preprocess_text(f[1]) for f in faqs]
        embeddings = embedding_model.encode(perguntas)
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        index = faiss.IndexFlatIP(embeddings.shape[1])
        index.add(np.array(embeddings, dtype=np.float32))
        query_emb = embedding_model.encode([pergunta])
        query_emb = query_emb / np.linalg.norm(query_emb, axis=1, keepdims=True)
        D, I = index.search(np.array(query_emb, dtype=np.float32), min(k, len(faqs)))
        for score, idx_faq in zip(D[0], I[0]):
            if idx_faq == -1 or score < min_sim:
                continue
            faq_id, pergunta_faq, resposta_faq, chatbot_id_faq = faqs[idx_faq]
            results.append({
                'faq_id': faq_id,
                'pergunta': pergunta_faq,
                'resposta': resposta_faq,
                'score': float(score)
            })
        return results
    else:
        if len(faqs_db) == 0:
            return []
        query_emb = embedding_model.encode([pergunta])
        query_emb = query_emb / np.linalg.norm(query_emb, axis=1, keepdims=True)
        D, I = faiss_index.search(np.array(query_emb, dtype=np.float32), min(k, len(faqs_db)))
        for score, idx_faq in zip(D[0], I[0]):
            if idx_faq == -1 or score < min_sim:
                continue
            faq_id, pergunta_faq, resposta_faq, chatbot_id_faq = faqs_db[idx_faq]
            results.append({
                'faq_id': faq_id,
                'pergunta': pergunta_faq,
                'resposta': resposta_faq,
                'score': float(score)
            })
        return results
    
def get_faqs_from_db(chatbot_id=None):
    conn = get_conn()
    cur = conn.cursor()
    try:
        if chatbot_id:
            cur.execute("SELECT faq_id, pergunta, resposta, chatbot_id FROM FAQ WHERE chatbot_id = %s", (chatbot_id,))
        else:
            cur.execute("SELECT faq_id, pergunta, resposta, chatbot_id FROM FAQ")
        return cur.fetchall()
    finally:
        cur.close()

def obter_faq_mais_semelhante(pergunta, chatbot_id, threshold=70):
    from rapidfuzz import fuzz
    from .text import preprocess_text_for_matching
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT faq_id, pergunta, resposta FROM FAQ WHERE chatbot_id = %s", (chatbot_id,))
        faqs = cur.fetchall()
        if not faqs:
            return None
        pergunta_processed = preprocess_text_for_matching(pergunta)
        melhor_score = 0
        melhor_faq = None
        for faq_id, pergunta_faq, resposta in faqs:
            pergunta_faq_processed = preprocess_text_for_matching(pergunta_faq)
            score = fuzz.ratio(pergunta_processed, pergunta_faq_processed)
            if score > melhor_score:
                melhor_score = score
                melhor_faq = {"faq_id": faq_id, "pergunta": pergunta_faq, "resposta": resposta, "score": score}
        if melhor_faq and melhor_faq["score"] >= threshold:
            return melhor_faq
        return None
    finally:
        cur.close()
