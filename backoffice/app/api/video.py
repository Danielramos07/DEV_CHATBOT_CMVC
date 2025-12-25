
from flask import Blueprint, jsonify, request, send_file

from ..db import get_conn
from ..services.video_service import (
    queue_video_for_faq,
    get_video_job_status,
    can_start_new_video_job,
)


app = Blueprint("video", __name__)

@app.route("/video/queue", methods=["POST"])
def queue_video():
    data = request.get_json() or {}
    faq_id = data.get("faq_id")

    if faq_id is None:
        return jsonify({"success": False, "error": "faq_id é obrigatório."}), 400

    try:
        faq_id = int(faq_id)
    except Exception:
        return jsonify({"success": False, "error": "faq_id inválido."}), 400

    if not can_start_new_video_job():
        return (
            jsonify(
                {
                    "success": False,
                    "busy": True,
                    "error": "Já existe um vídeo a ser gerado. Aguarde que termine.",
                }
            ),
            409,
        )

    # Confirm that the FAQ exists before queueing
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT 1 FROM faq WHERE faq_id = %s", (faq_id,))
        if not cur.fetchone():
            return jsonify({"success": False, "error": "FAQ não encontrada."}), 404
    finally:
        cur.close()
        conn.close()

    ok = queue_video_for_faq(faq_id)
    if not ok:
        return (
            jsonify(
                {
                    "success": False,
                    "busy": True,
                    "error": "Já existe um vídeo a ser gerado. Aguarde que termine.",
                }
            ),
            409,
        )

    return jsonify({"success": True})


@app.route("/video/status", methods=["GET"])
def video_status():
    status = get_video_job_status()
    return jsonify({"success": True, "job": status})


@app.route("/video/faq/status/<int:faq_id>", methods=["GET"])
def video_status_for_faq(faq_id: int):
    """DB-backed per-FAQ status (used by frontend polling)."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT video_path, video_status FROM faq WHERE faq_id = %s",
            (faq_id,),
        )
        row = cur.fetchone()
        if not row:
            return jsonify({"success": False, "error": "FAQ não encontrada."}), 404
        video_path, status = row
        return jsonify(
            {
                "success": True,
                "faq_id": faq_id,
                "video_status": status,
                "video_path": video_path,
            }
        )
    finally:
        cur.close()
        conn.close()


@app.route("/video/faq/<int:faq_id>", methods=["GET"])
def video_for_faq(faq_id: int):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT video_path, video_status FROM faq WHERE faq_id = %s",
            (faq_id,),
        )
        row = cur.fetchone()
        if not row:
            return jsonify({"success": False, "error": "FAQ não encontrada."}), 404
        video_path, status = row
        if not video_path or status != "ready":
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Vídeo ainda não está disponível para esta FAQ.",
                    }
                ),
                404,
            )
    finally:
        cur.close()
        conn.close()

    return send_file(video_path, mimetype="video/mp4", as_attachment=False)


@app.route("/video/chatbot/<int:chatbot_id>/idle", methods=["GET"])
def video_idle_for_chatbot(chatbot_id: int):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT video_idle_path FROM chatbot WHERE chatbot_id = %s",
            (chatbot_id,),
        )
        row = cur.fetchone()
        if not row or not row[0]:
            return jsonify({"success": False, "error": "Vídeo idle não disponível."}), 404
        path = row[0]
    finally:
        cur.close()
        conn.close()
    return send_file(path, mimetype="video/mp4", as_attachment=False)


@app.route("/video/chatbot/<int:chatbot_id>/greeting", methods=["GET"])
def video_greeting_for_chatbot(chatbot_id: int):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT video_greeting_path FROM chatbot WHERE chatbot_id = %s",
            (chatbot_id,),
        )
        row = cur.fetchone()
        if not row or not row[0]:
            return jsonify({"success": False, "error": "Vídeo de saudação não disponível."}), 404
        path = row[0]
    finally:
        cur.close()
        conn.close()
    return send_file(path, mimetype="video/mp4", as_attachment=False)
