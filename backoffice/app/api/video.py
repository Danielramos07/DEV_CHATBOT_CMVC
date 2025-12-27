
import os
import shutil

from flask import Blueprint, jsonify, request, send_file, current_app

from ..db import get_conn
from ..config import Config
from ..services.signed_media import verify_media_sig, sign_media
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
        stream_url = None
        if status == "ready" and video_path:
            # Always return a fresh signed url to avoid cache issues (nonce)
            import time
            nonce = str(int(time.time() * 1000))
            exp = int(time.time()) + 3600
            sig = sign_media("faq", str(faq_id), exp, nonce, secret_fallback=Config.SECRET_KEY)
            stream_url = f"/video/faq/{faq_id}?exp={exp}&nonce={nonce}&sig={sig}"
        return jsonify(
            {
                "success": True,
                "faq_id": faq_id,
                "video_status": status,
                "video_path": video_path,
                "stream_url": stream_url,
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
        if Config.REQUIRE_SIGNED_MEDIA:
            exp = request.args.get("exp")
            nonce = request.args.get("nonce", "")
            sig = request.args.get("sig")
            if not (exp and sig and verify_media_sig("faq", str(faq_id), int(exp), str(nonce), str(sig), secret_fallback=Config.SECRET_KEY)):
                return jsonify({"success": False, "error": "Unauthorized"}), 403
    finally:
        cur.close()
        conn.close()

    return send_file(video_path, mimetype="video/mp4", as_attachment=False)


@app.route("/video/cancel", methods=["POST"])
def cancel_video_job():
    """Cancel the current job.

    If cancelling a chatbot job, requires {"delete_chatbot": true} and will delete the chatbot.
    """
    data = request.get_json(silent=True) or {}
    delete_chatbot = bool(data.get("delete_chatbot"))

    job = get_video_job_status()
    status = (job.get("status") or "idle")
    kind = job.get("kind")
    chatbot_id = job.get("chatbot_id")
    faq_id = job.get("faq_id")

    if status not in {"queued", "processing"}:
        return jsonify({"success": False, "error": "No job running."}), 409

    if kind == "chatbot" and not delete_chatbot:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Cancelling chatbot videos requires deleting the chatbot.",
                }
            ),
            400,
        )

    from ..services.video_service import request_cancel_current_job

    request_cancel_current_job()

    # If FAQ job: clean up temporary files
    if kind == "faq" and faq_id:
        try:
            from ..services.video_service import ROOT, RESULTS_DIR
            result_root = RESULTS_DIR if RESULTS_DIR.is_absolute() else (ROOT / RESULTS_DIR)
            faq_dir = result_root / f"faq_{faq_id}"
            if faq_dir.exists() and faq_dir.is_dir():
                shutil.rmtree(faq_dir, ignore_errors=True)
        except Exception:
            pass

    # If chatbot job: delete chatbot (and related content) as requested
    if kind == "chatbot" and chatbot_id:
        conn = get_conn()
        cur = conn.cursor()
        try:
            # Fetch icon_path before deleting the row so we can remove the file from disk
            cur.execute("SELECT icon_path FROM chatbot WHERE chatbot_id = %s", (chatbot_id,))
            row = cur.fetchone()
            icon_path = row[0] if row else None

            # Fetch FAQ IDs before deleting to clean up their video files
            cur.execute("SELECT faq_id FROM faq WHERE chatbot_id = %s", (chatbot_id,))
            faq_ids = [row[0] for row in cur.fetchall()]
            
            cur.execute(
                "DELETE FROM faq_relacionadas WHERE faq_id IN (SELECT faq_id FROM faq WHERE chatbot_id = %s)",
                (chatbot_id,),
            )
            cur.execute(
                "DELETE FROM faq_documento WHERE faq_id IN (SELECT faq_id FROM faq WHERE chatbot_id = %s)",
                (chatbot_id,),
            )
            cur.execute("DELETE FROM faq WHERE chatbot_id = %s", (chatbot_id,))
            cur.execute("DELETE FROM fonte_resposta WHERE chatbot_id = %s", (chatbot_id,))
            cur.execute("DELETE FROM pdf_documents WHERE chatbot_id = %s", (chatbot_id,))
            cur.execute("DELETE FROM chatbot WHERE chatbot_id = %s", (chatbot_id,))
            conn.commit()

            # Clean up FAQ video files
            try:
                from ..services.video_service import ROOT, RESULTS_DIR
                result_root = RESULTS_DIR if RESULTS_DIR.is_absolute() else (ROOT / RESULTS_DIR)
                for faq_id in faq_ids:
                    faq_dir = result_root / f"faq_{faq_id}"
                    if faq_dir.exists() and faq_dir.is_dir():
                        shutil.rmtree(faq_dir, ignore_errors=True)
            except Exception:
                pass

            # Best-effort cleanup: uploaded icon + results folder
            try:
                if icon_path and str(icon_path).startswith("/static/icons/"):
                    filename = str(icon_path).split("/")[-1]
                    icons_dir = os.path.join(current_app.static_folder, "icons")
                    fs_path = os.path.join(icons_dir, filename)
                    if os.path.isfile(fs_path):
                        try:
                            os.remove(fs_path)
                        except Exception:
                            pass
            except Exception:
                pass

            try:
                from ..services.video_service import ROOT, RESULTS_DIR
                import shutil
                result_root = RESULTS_DIR if RESULTS_DIR.is_absolute() else (ROOT / RESULTS_DIR)
                folder = result_root / f"chatbot_{chatbot_id}"
                if folder.exists() and folder.is_dir():
                    shutil.rmtree(folder, ignore_errors=True)
            except Exception:
                pass
        except Exception as e:
            conn.rollback()
            return jsonify({"success": False, "error": str(e)}), 500
        finally:
            cur.close()
            conn.close()

    return jsonify({"success": True, "kind": kind, "chatbot_id": chatbot_id, "faq_id": faq_id})


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
    if Config.REQUIRE_SIGNED_MEDIA:
        exp = request.args.get("exp")
        nonce = request.args.get("nonce", "")
        sig = request.args.get("sig")
        if not (exp and sig and verify_media_sig("idle", str(chatbot_id), int(exp), str(nonce), str(sig), secret_fallback=Config.SECRET_KEY)):
            return jsonify({"success": False, "error": "Unauthorized"}), 403
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
    if Config.REQUIRE_SIGNED_MEDIA:
        exp = request.args.get("exp")
        nonce = request.args.get("nonce", "")
        sig = request.args.get("sig")
        if not (exp and sig and verify_media_sig("greeting", str(chatbot_id), int(exp), str(nonce), str(sig), secret_fallback=Config.SECRET_KEY)):
            return jsonify({"success": False, "error": "Unauthorized"}), 403
    return send_file(path, mimetype="video/mp4", as_attachment=False)
