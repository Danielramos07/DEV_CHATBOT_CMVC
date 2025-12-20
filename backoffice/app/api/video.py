
from flask import Blueprint, jsonify, request, send_file
from backoffice.app.video.main import queue_video_job, get_video_job_status

from ..db import get_conn
from ..services.video_service import (
    queue_video_for_faq,
    get_video_job_status,
    can_start_new_video_job,
)


app = Blueprint("video", __name__)

# --- Generic video job endpoints ---

@app.route("/video/job/queue", methods=["POST"])
def queue_generic_video():
    data = request.get_json() or {}
    text = data.get("text")
    avatar_path = data.get("avatar_path")
    voice = data.get("voice")
    preprocess = data.get("preprocess")
    size = data.get("size")
    enhancer = data.get("enhancer")
    batch_size = data.get("batch_size")
    results_dir = data.get("results_dir")

    if not text or not avatar_path:
        return jsonify({"success": False, "error": "text and avatar_path are required."}), 400

    job_id = queue_video_job(
        text=text,
        avatar_path=avatar_path,
        voice=str(voice) if voice is not None else None,
        preprocess=str(preprocess) if preprocess is not None else None,
        size=str(size) if size is not None else None,
        enhancer=str(enhancer) if enhancer is not None else None,
        batch_size=int(batch_size) if batch_size is not None else None,
        results_dir=str(results_dir) if results_dir is not None else None,
    )
    return jsonify({"success": True, "job_id": job_id})


@app.route("/video/job/status/<job_id>", methods=["GET"])
def generic_video_status(job_id):
    status = get_video_job_status(job_id)
    return jsonify({"success": True, "job": status})


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
