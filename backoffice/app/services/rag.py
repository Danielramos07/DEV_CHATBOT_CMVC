import logging
import os

import PyPDF2
import requests
from sentence_transformers import SentenceTransformer

from ..config import Config
from ..db import get_conn

embedding_model = SentenceTransformer(Config.RAG_EMBEDDING_MODEL)


def get_pdfs_from_db(chatbot_id=None, pdf_ids=None):
    conn = get_conn()
    cur = conn.cursor()
    try:
        if pdf_ids:
            cur.execute(
                "SELECT pdf_id, chatbot_id, file_path, filename FROM pdf_documents WHERE pdf_id = ANY(%s)",
                (list(pdf_ids),),
            )
        elif chatbot_id:
            cur.execute(
                "SELECT pdf_id, chatbot_id, file_path, filename FROM pdf_documents WHERE chatbot_id = %s",
                (chatbot_id,),
            )
        else:
            cur.execute("SELECT pdf_id, chatbot_id, file_path, filename FROM pdf_documents")
        return cur.fetchall()
    finally:
        cur.close()


def obter_mensagem_sem_resposta(chatbot_id):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT mensagem_sem_resposta FROM chatbot WHERE chatbot_id = %s", (chatbot_id,))
        row = cur.fetchone()
        if row and row[0]:
            return row[0]
        return "Desculpe, nao encontrei uma resposta para a sua pergunta. Pode reformular?"
    finally:
        cur.close()


def _chunk_text(text, max_chars, overlap):
    cleaned = " ".join((text or "").split())
    if not cleaned:
        return []
    if max_chars <= 0:
        return []
    overlap = max(0, min(overlap, max_chars - 1))
    chunks = []
    start = 0
    while start < len(cleaned):
        end = min(start + max_chars, len(cleaned))
        chunk = cleaned[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(cleaned):
            break
        start = end - overlap
    return chunks


def _extract_pdf_pages(file_path):
    pages = []
    with open(file_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        if reader.is_encrypted:
            raise ValueError("PDF is encrypted")
        for idx, page in enumerate(reader.pages, start=1):
            text = page.extract_text()
            if text:
                pages.append((idx, text))
    return pages


def index_pdf_documents(chatbot_id=None, pdf_ids=None):
    pdfs = get_pdfs_from_db(chatbot_id=chatbot_id, pdf_ids=pdf_ids)
    if not pdfs:
        return 0

    conn = get_conn()
    cur = conn.cursor()
    total_inserted = 0

    chunk_size = Config.RAG_CHUNK_SIZE_CHARS
    overlap = Config.RAG_CHUNK_OVERLAP_CHARS

    for pdf_id, pdf_chatbot_id, file_path, _filename in pdfs:
        if not os.path.exists(file_path):
            logging.warning("RAG index: missing PDF at %s", file_path)
            continue
        try:
            pages = _extract_pdf_pages(file_path)
        except Exception as exc:
            logging.warning("RAG index: failed to read %s (%s)", file_path, exc)
            continue

        chunks = []
        metadata = []
        chunk_index = 0
        for page_num, text in pages:
            for chunk in _chunk_text(text, chunk_size, overlap):
                chunks.append(chunk)
                metadata.append((page_num, chunk_index))
                chunk_index += 1

        if not chunks:
            continue

        embeddings = embedding_model.encode(
            chunks,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        if embeddings.shape[1] != Config.RAG_EMBEDDING_DIM:
            raise ValueError(
                f"RAG embedding dim mismatch: got {embeddings.shape[1]}, expected {Config.RAG_EMBEDDING_DIM}"
            )

        cur.execute("DELETE FROM rag_chunks WHERE pdf_id = %s", (pdf_id,))

        rows = []
        for chunk, emb, meta in zip(chunks, embeddings, metadata):
            page_num, chunk_idx = meta
            rows.append(
                (
                    chatbot_id if chatbot_id is not None else pdf_chatbot_id,
                    pdf_id,
                    page_num,
                    chunk_idx,
                    chunk,
                    emb.tolist(),
                )
            )
        cur.executemany(
            """
            INSERT INTO rag_chunks
            (chatbot_id, pdf_id, page_num, chunk_index, content, embedding)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            rows,
        )
        total_inserted += len(rows)

    conn.commit()
    return total_inserted


def _search_pgvector(pergunta, chatbot_id, top_k):
    conn = get_conn()
    cur = conn.cursor()
    try:
        query_emb = embedding_model.encode(
            [pergunta],
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )[0].tolist()
        cur.execute(
            """
            SELECT c.content,
                   c.pdf_id,
                   c.page_num,
                   c.chunk_index,
                   d.filename,
                   1 - (c.embedding <=> %s::vector) AS score
            FROM rag_chunks c
            JOIN pdf_documents d ON d.pdf_id = c.pdf_id
            WHERE c.chatbot_id = %s
            ORDER BY c.embedding <=> %s::vector
            LIMIT %s
            """,
            (query_emb, chatbot_id, query_emb, top_k),
        )
        rows = cur.fetchall()
        results = []
        for content, pdf_id, page_num, chunk_index, filename, score in rows:
            results.append(
                {
                    "content": content,
                    "pdf_id": pdf_id,
                    "page_num": page_num,
                    "chunk_index": chunk_index,
                    "filename": filename,
                    "score": float(score) if score is not None else 0.0,
                }
            )
        return results
    finally:
        cur.close()


def _build_prompt(pergunta, chunks):
    context_parts = []
    sources = []
    total_chars = 0
    for idx, chunk in enumerate(chunks, start=1):
        header = f"[{idx}] {chunk['filename']}#p{chunk['page_num']}"
        entry = f"{header}\n{chunk['content']}\n"
        if total_chars + len(entry) > Config.RAG_MAX_CONTEXT_CHARS:
            break
        context_parts.append(entry)
        total_chars += len(entry)
        sources.append(
            {
                "pdf_id": chunk["pdf_id"],
                "page_num": chunk["page_num"],
                "filename": chunk["filename"],
                "score": chunk["score"],
            }
        )

    context = "\n".join(context_parts)
    prompt = (
        "Answer the question using ONLY the context below. "
        "If the answer is not in the context, say you do not know.\n\n"
        f"Question: {pergunta}\n\n"
        "Context:\n"
        f"{context}\n"
    )
    return prompt, sources


def _call_ollama(prompt):
    payload = {
        "model": Config.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }
    try:
        resp = requests.post(Config.OLLAMA_URL, json=payload, timeout=Config.OLLAMA_TIMEOUT)
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except Exception as exc:
        logging.error("Ollama error: %s", exc)
        return None


def pesquisar_pdf_pgvector(pergunta, chatbot_id=None):
    if not chatbot_id:
        return None, []
    results = _search_pgvector(pergunta, chatbot_id, Config.RAG_TOP_K)
    results = [r for r in results if r["score"] >= Config.RAG_MIN_SCORE]
    if not results:
        return None, []
    prompt, sources = _build_prompt(pergunta, results)
    resposta = _call_ollama(prompt)
    if not resposta:
        return None, sources
    return resposta, sources
