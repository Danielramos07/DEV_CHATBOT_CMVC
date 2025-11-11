import PyPDF2
import requests
from ..db import get_conn


def get_pdfs_from_db(chatbot_id=None):
    conn = get_conn()
    cur = conn.cursor()
    try:
        if chatbot_id:
            cur.execute("SELECT pdf_id, file_path FROM PDF_Documents WHERE chatbot_id = %s", (chatbot_id,))
        else:
            cur.execute("SELECT pdf_id, file_path FROM PDF_Documents")
        return cur.fetchall()
    finally:
        cur.close()

def obter_mensagem_sem_resposta(chatbot_id):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT mensagem_sem_resposta FROM Chatbot WHERE chatbot_id = %s", (chatbot_id,))
        row = cur.fetchone()
        if row and row[0]:
            return row[0]
        return "Desculpe, não encontrei uma resposta para a sua pergunta. Pode reformular a pergunta?"
    finally:
        cur.close()



def pesquisar_pdf_ollama(pergunta, chatbot_id=None, modelo="llama3", max_chars=18000):
    pdfs = get_pdfs_from_db(chatbot_id)
    contexto_pdf = ""
    for pdf_id, file_path in pdfs:
        try:
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    texto = page.extract_text()
                    if texto:
                        contexto_pdf += texto + "\n\n"
        except Exception as e:
            print(f"Erro lendo PDF: {file_path}", e)
    contexto_pdf = contexto_pdf[:max_chars]
    prompt = f"""Responda à pergunta abaixo UTILIZANDO APENAS o conteúdo extraído dos documentos PDF. Não invente informação. Seja objetivo.
Pergunta: {pergunta}
Conteúdo dos documentos:
{contexto_pdf}
"""
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": modelo,
        "prompt": prompt,
        "stream": False
    }
    try:
        resp = requests.post(url, json=payload, timeout=120)
        resp.raise_for_status()
        resposta = resp.json().get("response", "").strip()
        return resposta
    except Exception as e:
        print("Erro Ollama:", e)
        return None