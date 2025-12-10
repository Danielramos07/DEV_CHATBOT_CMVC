from flask import Blueprint, request, jsonify, current_app, url_for
from ..db import get_conn
from ..services.retreival import build_faiss_index
from werkzeug.utils import secure_filename
import traceback
import os
from ..config import Config

app = Blueprint('chatbots', __name__)


@app.route("/chatbots", methods=["GET"])
def get_chatbots():
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT c.chatbot_id,
                   c.nome,
                   c.descricao,
                   c.data_criacao,
                   c.cor,
                   c.icon_path,
                   c.genero,
                   fr.fonte,
                   array_remove(array_agg(cc.categoria_id), NULL) as categorias,
                   c.mensagem_sem_resposta
            FROM chatbot c
            LEFT JOIN fonte_resposta fr ON fr.chatbot_id = c.chatbot_id
            LEFT JOIN chatbot_categoria cc ON cc.chatbot_id = c.chatbot_id
            GROUP BY c.chatbot_id,
                     c.nome,
                     c.descricao,
                     c.data_criacao,
                     c.cor,
                     c.icon_path,
                     c.genero,
                     fr.fonte,
                     c.mensagem_sem_resposta
            ORDER BY c.chatbot_id ASC
        """)
        data = cur.fetchall()
        return jsonify([
            {
                "chatbot_id": row[0],
                "nome": row[1],
                "descricao": row[2],
                "data_criacao": row[3],
                "cor": row[4] if row[4] else "#d4af37",
                "icon_path": row[5] if row[5] else "/static/images/chatbot-icon.png",
                "genero": row[6] if row[6] else None,
                "fonte": row[7] if row[7] else "faq",
                "categorias": row[8] if row[8] is not None else [],
                "mensagem_sem_resposta": row[9] if len(row) > 9 else ""
            }
            for row in data
        ])
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route("/chatbots", methods=["POST"])
def criar_chatbot():
    conn = get_conn()
    cur = conn.cursor()
    data = request.get_json()
    nome = data.get("nome", "").strip()
    descricao = data.get("descricao", "").strip()
    categorias = data.get("categorias", [])
    cor = data.get("cor", "").strip() or "#d4af37"
    icon_path = data.get("icon_path", "/static/images/chatbot-icon.png")
    mensagem_sem_resposta = data.get("mensagem_sem_resposta", "").strip()
    genero = data.get("genero") or None
    if not nome:
        return jsonify({"success": False, "error": "Nome obrigatório."}), 400
    try:
        cur.execute(
            """
            INSERT INTO chatbot (nome, descricao, cor, icon_path, mensagem_sem_resposta, genero)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (nome) DO NOTHING
            RETURNING chatbot_id
            """,
            (nome, descricao, cor, icon_path, mensagem_sem_resposta, genero)
        )
        row = cur.fetchone()
        if not row:
            conn.rollback()
            return jsonify({"success": False, "error": "Já existe um chatbot com esse nome."}), 409
        chatbot_id = row[0]
        for categoria_id in categorias:
            cur.execute(
                "INSERT INTO chatbot_categoria (chatbot_id, categoria_id) VALUES (%s, %s)",
                (chatbot_id, categoria_id)
            )
        cur.execute(
            "INSERT INTO fonte_resposta (chatbot_id, fonte) VALUES (%s, %s)",
            (chatbot_id, "faq")
        )
        conn.commit()
        return jsonify({"success": True, "chatbot_id": chatbot_id})
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route("/chatbots/<int:chatbot_id>", methods=["GET"])
def obter_nome_chatbot(chatbot_id):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT nome, cor, icon_path, genero FROM chatbot WHERE chatbot_id = %s", (chatbot_id,))
        row = cur.fetchone()
        if row:
            return jsonify({
                "success": True,
                "nome": row[0],
                "cor": row[1] or "#d4af37",
                "icon": row[2] or "/static/images/chatbot-icon.png",
                "genero": row[3]
            })
        return jsonify({"success": False, "erro": "Chatbot não encontrado."}), 404
    except Exception as e:
        return jsonify({"success": False, "erro": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route("/chatbots/<int:chatbot_id>", methods=["PUT"])
def atualizar_chatbot(chatbot_id):
    conn = get_conn()
    cur = conn.cursor()
    try:
        print("Dados recebidos:", dict(request.form))
        nome = request.form.get("nome", "").strip()
        descricao = request.form.get("descricao", "").strip()
        fonte = request.form.get("fonte", "faq")
        categorias = request.form.getlist("categorias[]") if request.form.getlist("categorias[]") else []
        cor = request.form.get("cor", "").strip() or "#d4af37"
        mensagem_sem_resposta = request.form.get("mensagem_sem_resposta", "").strip()
        genero = request.form.get("genero") or None
        icon_path = None
        if 'icon' in request.files:
            file = request.files['icon']
            if file.filename:
                filename = secure_filename(file.filename)
                if filename:
                    # Guardar sempre os ícones na pasta static/icons
                    icons_dir = os.path.join(current_app.static_folder, 'icons')
                    if not os.path.exists(icons_dir):
                        os.makedirs(icons_dir, exist_ok=True)
                    fs_path = os.path.join(icons_dir, filename)
                    file.save(fs_path)
                    # Caminho usado pelo frontend
                    icon_path = url_for('static', filename=f'icons/{filename}')
        if not nome:
            return jsonify({"success": False, "error": "O nome do chatbot é obrigatório."}), 400
        if icon_path:
            cur.execute(
                "UPDATE chatbot SET nome=%s, descricao=%s, cor=%s, mensagem_sem_resposta=%s, icon_path=%s, genero=%s WHERE chatbot_id=%s",
                (nome, descricao, cor, mensagem_sem_resposta, icon_path, genero, chatbot_id)
            )
        else:
            cur.execute(
                "UPDATE chatbot SET nome=%s, descricao=%s, cor=%s, mensagem_sem_resposta=%s, genero=%s WHERE chatbot_id=%s",
                (nome, descricao, cor, mensagem_sem_resposta, genero, chatbot_id)
            )
        cur.execute("DELETE FROM chatbot_categoria WHERE chatbot_id=%s", (chatbot_id,))
        for categoria_id in categorias:
            cur.execute(
                "INSERT INTO ChatbotCategoria (chatbot_id, categoria_id) VALUES (%s, %s)",
                (chatbot_id, int(categoria_id))
            )
        cur.execute("SELECT 1 FROM fonte_resposta WHERE chatbot_id=%s", (chatbot_id,))
        if cur.fetchone():
            cur.execute("UPDATE fonte_resposta SET fonte=%s WHERE chatbot_id=%s", (fonte, chatbot_id))
        else:
            cur.execute("INSERT INTO fonte_resposta (chatbot_id, fonte) VALUES (%s, %s)", (chatbot_id, fonte))
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        conn.rollback()
        print(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route("/chatbots/<int:chatbot_id>", methods=["DELETE"])
def eliminar_chatbot(chatbot_id):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM faq_relacionadas WHERE faq_id IN (SELECT faq_id FROM faq WHERE chatbot_id = %s)", (chatbot_id,))
        cur.execute("DELETE FROM faq_documento WHERE faq_id IN (SELECT faq_id FROM faq WHERE chatbot_id = %s)", (chatbot_id,))
        cur.execute("DELETE FROM faq WHERE chatbot_id = %s", (chatbot_id,))
        cur.execute("DELETE FROM fonte_resposta WHERE chatbot_id = %s", (chatbot_id,))
        cur.execute("DELETE FROM pdf_documents WHERE chatbot_id = %s", (chatbot_id,))
        cur.execute("DELETE FROM chatbot WHERE chatbot_id = %s", (chatbot_id,))
        conn.commit()
        build_faiss_index()
        return jsonify({"success": True})
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cur.close()

@app.route("/fonte/<int:chatbot_id>", methods=["GET"])
def obter_fonte_chatbot(chatbot_id):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT fonte FROM fonte_resposta WHERE chatbot_id = %s", (chatbot_id,))
        row = cur.fetchone()
        if row:
            fonte = row[0] if row[0] else "faq"
            return jsonify({"success": True, "fonte": fonte})
        return jsonify({"success": False, "erro": "Chatbot não encontrado."}), 404
    except Exception as e:
        return jsonify({"success": False, "erro": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route("/fonte", methods=["POST"])
def definir_fonte_chatbot():
    conn = get_conn()
    cur = conn.cursor()
    data = request.get_json()
    chatbot_id = data.get("chatbot_id")
    fonte = data.get("fonte")
    if fonte not in ["faq", "faiss", "faq+raga"]:
        return jsonify({"success": False, "erro": "Fonte inválida."}), 400
    try:
        cur.execute("SELECT 1 FROM fonte_resposta WHERE chatbot_id = %s", (chatbot_id,))
        if not cur.fetchone():
            cur.execute("INSERT INTO fonte_resposta (chatbot_id, fonte) VALUES (%s, %s)", (chatbot_id, fonte))
        else:
            cur.execute("UPDATE fonte_resposta SET fonte = %s WHERE chatbot_id = %s", (fonte, chatbot_id))
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "erro": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route("/chatbots/<int:chatbot_id>/categorias", methods=["GET"])
def get_categorias_chatbot(chatbot_id):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT c.categoria_id, c.nome
            FROM categoria c
            JOIN chatbot_categoria cc ON c.categoria_id = cc.categoria_id
            WHERE cc.chatbot_id = %s
        """, (chatbot_id,))
        data = cur.fetchall()
        return jsonify([{"categoria_id": c[0], "nome": c[1]} for c in data])
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route("/chatbots/<int:chatbot_id>/categorias/<int:categoria_id>", methods=["DELETE"])
def remove_categoria_from_chatbot(chatbot_id, categoria_id):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM chatbot_categoria WHERE chatbot_id = %s AND categoria_id = %s", (chatbot_id, categoria_id))
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cur.close()

@app.route("/chatbots/<int:chatbot_id>/categorias", methods=["POST"])
def add_categoria_to_chatbot(chatbot_id):
    conn = get_conn()
    cur = conn.cursor()
    data = request.get_json()
    categoria_id = data.get("categoria_id")
    if not categoria_id:
        return jsonify({"success": False, "error": "ID da categoria é obrigatório."}), 400
    try:
        cur.execute("INSERT INTO chatbot_categoria (chatbot_id, categoria_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (chatbot_id, categoria_id))
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

