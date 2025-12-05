from flask import Blueprint, request, jsonify
from ..db import get_conn

app = Blueprint('categorias', __name__)


@app.route("/categorias", methods=["GET"])
def get_categorias():
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT categoria_id, nome FROM categoria")
        data = cur.fetchall()
        return jsonify([{"categoria_id": c[0], "nome": c[1]} for c in data])
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route("/categorias", methods=["POST"])
def criar_categoria():
    conn = get_conn()
    cur = conn.cursor()
    data = request.get_json()
    nome = data.get("nome", "").strip()
    if not nome:
        return jsonify({"success": False, "error": "Nome da categoria é obrigatório."}), 400
    try:
        cur.execute("SELECT categoria_id FROM categoria WHERE LOWER(nome) = LOWER(%s)", (nome,))
        if cur.fetchone():
            return jsonify({"success": False, "error": "Já existe uma categoria com esse nome."}), 409
        cur.execute(
            "INSERT INTO categoria (nome) VALUES (%s) RETURNING categoria_id",
            (nome,)
        )
        categoria_id = cur.fetchone()[0]
        conn.commit()
        return jsonify({"categoria_id": categoria_id, "nome": nome}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

