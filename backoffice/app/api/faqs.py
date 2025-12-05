from flask import Blueprint, request, jsonify
from ..db import get_conn
from ..services.retreival import build_faiss_index

app = Blueprint('faqs', __name__)


@app.route("/faqs", methods=["GET"])
def get_faqs():
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT faq_id, chatbot_id, designacao, pergunta, resposta FROM faq")
        data = cur.fetchall()
        return jsonify([
            {"faq_id": f[0], "chatbot_id": f[1], "designacao": f[2], "pergunta": f[3], "resposta": f[4]} for f in data
        ])
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route("/faqs/<int:faq_id>", methods=["GET"])
def get_faq_by_id(faq_id):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT f.faq_id, f.chatbot_id, f.categoria_id, f.designacao, f.pergunta, f.resposta, f.idioma, f.links_documentos,
                   c.nome as categoria_nome, f.recomendado
            FROM faq f
            LEFT JOIN categoria c ON f.categoria_id = c.categoria_id
            WHERE f.faq_id = %s
        """, (faq_id,))
        faq = cur.fetchone()
        if not faq:
            return jsonify({"success": False, "error": "FAQ não encontrada."}), 404
        return jsonify({
            "success": True,
            "faq": {
                "faq_id": faq[0],
                "chatbot_id": faq[1],
                "categoria_id": faq[2],
                "designacao": faq[3],
                "pergunta": faq[4],
                "resposta": faq[5],
                "idioma": faq[6],
                "links_documentos": faq[7],
                "categoria_nome": faq[8],
                "recomendado": faq[9]
            }
        })
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route("/faqs/chatbot/<int:chatbot_id>", methods=["GET"])
def get_faqs_por_chatbot(chatbot_id):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT f.faq_id, c.nome, f.pergunta, f.resposta
            FROM faq f
            LEFT JOIN categoria c ON f.categoria_id = c.categoria_id
            WHERE f.chatbot_id = %s
        """, (chatbot_id,))
        data = cur.fetchall()
        return jsonify([
            {
                "faq_id": row[0],
                "categoria": row[1],
                "pergunta": row[2],
                "resposta": row[3]
            }
            for row in data
        ])
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route("/faqs/<int:faq_id>", methods=["PUT"])
def update_faq(faq_id):
    conn = get_conn()
    cur = conn.cursor()
    data = request.get_json()
    try:
        pergunta = data.get("pergunta", "").strip()
        resposta = data.get("resposta", "").strip()
        idioma = data.get("idioma", "pt").strip()
        categorias = data.get("categorias", [])
        recomendado = data.get("recomendado", False)
        categoria_id = categorias[0] if categorias else None
        cur.execute("""
            UPDATE faq SET pergunta=%s, resposta=%s, idioma=%s, categoria_id=%s, recomendado=%s
            WHERE faq_id=%s
        """, (pergunta, resposta, idioma, categoria_id, recomendado, faq_id))
        conn.commit()
        build_faiss_index()
        return jsonify({"success": True})
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route("/faqs", methods=["POST"])
def add_faq():
    conn = get_conn()
    cur = conn.cursor()
    data = request.get_json()
    try:
        idioma = data.get("idioma", "").strip()
        if not idioma:
            return jsonify({"success": False, "error": "O campo 'idioma' é obrigatório."}), 400
        links_documentos = data.get("links_documentos", "").strip()
        recomendado = data.get("recomendado", False)
        cur.execute("""
            SELECT faq_id FROM faq
            WHERE chatbot_id = %s AND designacao = %s AND pergunta = %s AND resposta = %s AND idioma = %s
        """, (data["chatbot_id"], data["designacao"], data["pergunta"], data["resposta"], idioma))
        if cur.fetchone():
            return jsonify({"success": False, "error": "Esta FAQ já está inserida."}), 409
        cur.execute("""
            INSERT INTO faq (chatbot_id, categoria_id, designacao, pergunta, resposta, idioma, links_documentos, recomendado)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING faq_id
        """, (
            data["chatbot_id"],
            data["categoria_id"],
            data["designacao"],
            data["pergunta"],
            data["resposta"],
            idioma,
            links_documentos,
            recomendado
        ))
        faq_id = cur.fetchone()[0]
        if links_documentos:
            for link in links_documentos.split(','):
                link = link.strip()
                if link:
                    cur.execute(
                        "INSERT INTO faq_documento (faq_id, link) VALUES (%s, %s)",
                        (faq_id, link)
                    )
        if "relacionadas" in data and data["relacionadas"].strip():
            for rel_id in data["relacionadas"].split(','):
                cur.execute("INSERT INTO faq_relacionadas (faq_id, faq_relacionada_id) VALUES (%s, %s)", (faq_id, int(rel_id.strip())))
        conn.commit()
        build_faiss_index()
        return jsonify({"success": True, "faq_id": faq_id})
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route("/faqs/<int:faq_id>", methods=["DELETE"])
def delete_faq(faq_id):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM faq WHERE faq_id = %s", (faq_id,))
        conn.commit()
        build_faiss_index()
        return jsonify({"success": True})
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route("/faqs/detalhes", methods=["GET"])
def get_faqs_detalhes():
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT f.faq_id, f.chatbot_id, f.designacao, f.pergunta, f.resposta, f.idioma, f.links_documentos,
                   f.categoria_id, c.nome AS categoria_nome, ch.nome AS chatbot_nome, f.recomendado
            FROM faq f
            LEFT JOIN categoria c ON f.categoria_id = c.categoria_id
            LEFT JOIN chatbot ch ON f.chatbot_id = ch.chatbot_id
            ORDER BY f.faq_id
        """)
        data = cur.fetchall()
        return jsonify([
            {
                "faq_id": r[0],
                "chatbot_id": r[1],
                "designacao": r[2],
                "pergunta": r[3],
                "resposta": r[4],
                "idioma": r[5],
                "links_documentos": r[6],
                "categoria_id": r[7],
                "categoria_nome": r[8],
                "chatbot_nome": r[9],
                "recomendado": r[10]
            }
            for r in data
        ])
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

