from flask import Blueprint, request, jsonify
from flask import send_file
from ..db import get_conn
from ..services.retreival import build_faiss_index
from ..services.text import normalizar_idioma
from ..config import Config
from ..services.video_service import can_start_new_video_job
import os
import traceback

# Importações opcionais para evitar erros se os pacotes não estiverem instalados
try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

app = Blueprint('uploads', __name__)


@app.route("/upload-pdf", methods=["POST"])
def upload_pdf():
    if not PDF_AVAILABLE:
        return jsonify({"success": False, "error": "PyPDF2 não está instalado."}), 500
    
    conn = get_conn()
    cur = conn.cursor()
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "Ficheiro não enviado."}), 400
    files = request.files.getlist('file')
    chatbot_id = request.form.get("chatbot_id")
    if not chatbot_id:
        return jsonify({"success": False, "error": "Chatbot ID não fornecido."}), 400
    uploaded_pdf_ids = []
    try:
        if not os.path.exists(Config.PDF_STORAGE_PATH):
            os.makedirs(Config.PDF_STORAGE_PATH, exist_ok=True)
        for file in files:
            filename = file.filename
            if not filename.lower().endswith('.pdf'):
                return jsonify({"success": False, "error": "Apenas ficheiros PDF são permitidos."}), 400
            # Store per chatbot to avoid name collisions
            chatbot_dir = os.path.join(Config.PDF_STORAGE_PATH, f"chatbot_{chatbot_id}")
            os.makedirs(chatbot_dir, exist_ok=True)
            file_path = os.path.join(chatbot_dir, filename)
            file.save(file_path)
            file.close()
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                if reader.is_encrypted:
                    return jsonify({"success": False, "error": f"O PDF '{filename}' está protegido por senha."}), 400
                if not reader.pages:
                    return jsonify({"success": False, "error": f"O PDF '{filename}' está vazio ou corrompido."}), 400
                cur.execute(
                    "INSERT INTO pdf_documents (chatbot_id, filename, file_path) VALUES (%s, %s, %s) RETURNING pdf_id",
                (chatbot_id, filename, file_path)
            )
            pdf_id = cur.fetchone()[0]
            uploaded_pdf_ids.append(pdf_id)
        conn.commit()
        return jsonify({"success": True, "pdf_ids": uploaded_pdf_ids, "message": "PDF(s) carregado(s) com sucesso."})
    except PyPDF2.errors.PdfReadError:
        return jsonify({"success": False, "error": "Erro ao ler o PDF. Verifique se o arquivo não está corrompido."}), 400
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


@app.route("/pdfs/<int:pdf_id>", methods=["GET"])
def get_pdf(pdf_id: int):
    """Serve an uploaded PDF from pdf_documents by id."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT file_path FROM pdf_documents WHERE pdf_id = %s", (pdf_id,))
        row = cur.fetchone()
        if not row or not row[0]:
            return jsonify({"success": False, "error": "PDF não encontrado."}), 404
        file_path = row[0]
        if not os.path.isfile(file_path):
            return jsonify({"success": False, "error": "Ficheiro PDF não existe no servidor."}), 404
        return send_file(file_path, mimetype="application/pdf", as_attachment=False)
    finally:
        cur.close()
        conn.close()

@app.route("/upload-faq-docx", methods=["POST"])
def upload_faq_docx():
    if not DOCX_AVAILABLE:
        return jsonify({"success": False, "error": "python-docx não está instalado."}), 500
    
    conn = get_conn()
    cur = conn.cursor()
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "Ficheiro não enviado."}), 400
    file = request.files['file']
    chatbot_id_raw = request.form.get("chatbot_id")
    if not chatbot_id_raw:
        return jsonify({"success": False, "error": "Chatbot ID não fornecido."}), 400
    try:
        doc = docx.Document(file)
        dados = {}
        for table in doc.tables:
            for row in table.rows:
                if len(row.cells) >= 2:
                    chave_raw = row.cells[0].text.strip().lower().replace("\u2019", "'")
                    valor = row.cells[1].text.strip()
                    chave = chave_raw.replace(":", "").strip()
                    if chave and valor:
                        dados[chave] = valor
        if not dados.get("designação da faq") or not dados.get("questão") or not dados.get("resposta"):
            raise Exception("Faltam campos obrigatórios: designação, questão ou resposta.")
        designacao = dados.get("designação da faq")
        pergunta = dados.get("questão")
        resposta = dados.get("resposta")
        categoria = dados.get("categoria")
        idioma_lido = dados.get("idioma", "Português")
        idioma = normalizar_idioma(idioma_lido)
        links_documentos = ""
        for key in ["documentos associados", "links de documentos"]:
            if key in dados:
                links_documentos = dados[key]
                break
        chatbot_ids = []
        if chatbot_id_raw == "todos":
            cur.execute("SELECT chatbot_id FROM chatbot")
            chatbot_ids = [row[0] for row in cur.fetchall()]
        else:
            chatbot_ids = [int(chatbot_id_raw)]
        for chatbot_id in chatbot_ids:
            cur.execute("""
                SELECT faq_id FROM faq
                WHERE chatbot_id = %s AND designacao = %s AND pergunta = %s AND resposta = %s AND idioma = %s
            """, (chatbot_id, designacao, pergunta, resposta, idioma))
            if cur.fetchone():
                continue
            cur.execute("""
                INSERT INTO faq (chatbot_id, designacao, pergunta, resposta, idioma, links_documentos)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING faq_id
            """, (chatbot_id, designacao, pergunta, resposta, idioma, links_documentos))
            faq_id = cur.fetchone()[0]
            if categoria:
                cur.execute("SELECT categoria_id FROM categoria WHERE nome ILIKE %s", (categoria,))
                result = cur.fetchone()
                if result:
                    cur.execute("UPDATE faq SET categoria_id = %s WHERE faq_id = %s", (result[0], faq_id))
            if links_documentos:
                for link in links_documentos.split(','):
                    link = link.strip()
                    if link:
                        cur.execute(
                            "INSERT INTO faq_documento (faq_id, link) VALUES (%s, %s)",
                            (faq_id, link)
                        )
        conn.commit()
        build_faiss_index()
        return jsonify({"success": True, "message": "FAQ e links inseridos com sucesso."})
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route("/upload-faq-docx-multiplos", methods=["POST"])
def upload_faq_docx_multiplos():
    if not DOCX_AVAILABLE:
        return jsonify({"success": False, "error": "python-docx não está instalado."}), 500
    
    conn = get_conn()
    cur = conn.cursor()
    if 'files' not in request.files and 'file' not in request.files:
        return jsonify({"success": False, "error": "Ficheiros não enviados."}), 400
    chatbot_id_raw = request.form.get("chatbot_id")
    if not chatbot_id_raw:
        return jsonify({"success": False, "error": "Chatbot ID não fornecido."}), 400
    # If a video job is active, only block when at least one target chatbot has video enabled
    if not can_start_new_video_job():
        try:
            cur2 = conn.cursor()
            if chatbot_id_raw == "todos":
                cur2.execute("SELECT 1 FROM chatbot WHERE video_enabled = TRUE LIMIT 1")
                any_video = cur2.fetchone() is not None
            else:
                cur2.execute("SELECT video_enabled FROM chatbot WHERE chatbot_id = %s", (int(chatbot_id_raw),))
                r = cur2.fetchone()
                any_video = bool(r[0]) if r else False
            cur2.close()
            if any_video:
                return jsonify({"success": False, "busy": True, "error": "Já existe um vídeo a ser gerado. Aguarde que termine."}), 409
        except Exception:
            return jsonify({"success": False, "busy": True, "error": "Já existe um vídeo a ser gerado. Aguarde que termine."}), 409
    files = request.files.getlist('files') or request.files.getlist('file')
    total_inseridas = 0
    erros = []
    for file in files:
        try:
            doc = docx.Document(file)
            dados = {}
            for table in doc.tables:
                for row in table.rows:
                    if len(row.cells) >= 2:
                        chave_raw = row.cells[0].text.strip().lower().replace("\u2019", "'")
                        valor = row.cells[1].text.strip()
                        chave = chave_raw.replace(":", "").strip()
                        if chave and valor:
                            dados[chave] = valor
            if not dados.get("designação da faq") or not dados.get("questão") or not dados.get("resposta"):
                raise Exception("Faltam campos obrigatórios: designação, questão ou resposta.")
            designacao = dados.get("designação da faq")
            identificador = dados.get("identificador") or dados.get("id") or ""
            pergunta = dados.get("questão")
            resposta = dados.get("resposta")
            categoria = dados.get("categoria")
            idioma_lido = dados.get("idioma", "Português")
            idioma = normalizar_idioma(idioma_lido)
            links_documentos = ""
            for key in ["documentos associados", "links de documentos"]:
                if key in dados:
                    links_documentos = dados[key]
                    break
            chatbot_ids = []
            if chatbot_id_raw == "todos":
                cur.execute("SELECT chatbot_id FROM chatbot")
                chatbot_ids = [row[0] for row in cur.fetchall()]
            else:
                chatbot_ids = [int(chatbot_id_raw)]
            for chatbot_id in chatbot_ids:
                cur.execute("""
                    SELECT faq_id FROM faq
                    WHERE chatbot_id = %s AND designacao = %s AND pergunta = %s AND resposta = %s AND idioma = %s
                """, (chatbot_id, designacao, pergunta, resposta, idioma))
                if cur.fetchone():
                    continue
                cur.execute("""
                    INSERT INTO faq (chatbot_id, designacao, identificador, pergunta, resposta, idioma, links_documentos)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING faq_id
                """, (chatbot_id, designacao, (identificador or "").strip() or None, pergunta, resposta, idioma, links_documentos))
                faq_id = cur.fetchone()[0]
                if categoria:
                    cur.execute("SELECT categoria_id FROM categoria WHERE nome ILIKE %s", (categoria,))
                    result = cur.fetchone()
                    if result:
                        cur.execute("UPDATE faq SET categoria_id = %s WHERE faq_id = %s", (result[0], faq_id))
                if links_documentos:
                    for link in links_documentos.split(','):
                        link = link.strip()
                        if link:
                            cur.execute(
                                "INSERT INTO faq_documento (faq_id, link) VALUES (%s, %s)",
                                (faq_id, link)
                            )
                total_inseridas += 1
        except Exception as e:
            erros.append(str(e))
            conn.rollback()
    conn.commit()
    build_faiss_index()
    return jsonify({"success": True, "inseridas": total_inseridas, "erros": erros})

