from flask import Blueprint, request, jsonify
from ..db import get_conn
from ..services.retreival import build_faiss_index
from ..services.video_service import can_start_new_video_job, queue_video_for_faq
import os
from pathlib import Path
from ..services.video_service import ROOT, RESULTS_DIR

app = Blueprint('faqs', __name__)


@app.route("/faqs", methods=["GET"])
def get_faqs():
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT faq_id, chatbot_id, identificador, designacao, pergunta, resposta, video_status, video_path FROM faq")
        data = cur.fetchall()
        return jsonify([
            {
                "faq_id": f[0],
                "chatbot_id": f[1],
                "identificador": f[2],
                "designacao": f[3],
                "pergunta": f[4],
                "resposta": f[5],
                "video_status": f[6],
                "video_path": f[7],
            }
            for f in data
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
            SELECT f.faq_id,
                   f.chatbot_id,
                   f.categoria_id,
                   f.designacao,
                   f.pergunta,
                   f.resposta,
                   f.idioma,
                   f.links_documentos,
                   c.nome as categoria_nome,
                   f.recomendado,
                   f.video_status,
                   f.video_path,
                   f.video_text,
                   f.identificador,
                   COALESCE(rel.relacionadas, ARRAY[]::int[]) AS relacionadas
            FROM faq f
            LEFT JOIN categoria c ON f.categoria_id = c.categoria_id
            LEFT JOIN (
                SELECT faq_id, array_agg(faq_relacionada_id) FILTER (WHERE faq_relacionada_id IS NOT NULL) AS relacionadas
                FROM faq_relacionadas
                GROUP BY faq_id
            ) rel ON rel.faq_id = f.faq_id
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
                "recomendado": faq[9],
                "video_status": faq[10],
                "video_path": faq[11],
                "video_text": faq[12],
                "identificador": faq[13],
                "relacionadas": faq[14] or [],
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
            SELECT f.faq_id, c.nome, f.pergunta, f.resposta, f.identificador
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
                "resposta": row[3],
                "identificador": row[4],
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
        # Accept either categoria_id (single select) or categorias[] (legacy multi)
        if "categoria_id" in data:
            raw_cat = data.get("categoria_id")
            try:
                categoria_id = int(raw_cat) if raw_cat is not None and str(raw_cat).strip() != "" else None
            except Exception:
                categoria_id = None
        else:
            categoria_id = categorias[0] if categorias else None
        identificador = (data.get("identificador") or "").strip()
        relacionadas_raw = data.get("relacionadas", None)
        relacionadas_ids = []
        if relacionadas_raw is not None:
            if isinstance(relacionadas_raw, list):
                relacionadas_ids = [int(x) for x in relacionadas_raw if str(x).strip().isdigit()]
            else:
                relacionadas_ids = [
                    int(x.strip()) for x in str(relacionadas_raw).split(",") if x.strip().isdigit()
                ]
            relacionadas_ids = [rid for rid in relacionadas_ids if rid != faq_id]
        # Optional field used by video generation (can be null)
        video_text_in_payload = "video_text" in data
        video_text_value = (data.get("video_text", "") or "").strip() or None
        # Fetch current values to check if resposta or video_text changed
        cur.execute("SELECT resposta, video_text, chatbot_id, designacao, pergunta, idioma, identificador FROM faq WHERE faq_id = %s", (faq_id,))
        old = cur.fetchone()
        old_resposta = old[0] if old else None
        old_video_text = old[1] if old else None
        chatbot_id = old[2] if old else None
        old_designacao = old[3] if old else None
        old_pergunta = old[4] if old else None
        old_idioma = old[5] if old else None
        old_identificador = old[6] if old else None

        # Check if the new values would create a duplicate (excluding current FAQ)
        # Use old_designacao if designacao is not provided in the update
        designacao = data.get("designacao", "").strip()
        if not designacao:
            designacao = old_designacao or ""
        
        # Only check for duplicates if at least one field changed
        if designacao == (old_designacao or "") and pergunta == (old_pergunta or "") and resposta == (old_resposta or "") and idioma == (old_idioma or "pt"):
            # No changes, skip duplicate check
            pass
        else:
            cur.execute("""
                SELECT faq_id FROM faq
                WHERE chatbot_id = %s AND designacao = %s AND pergunta = %s AND resposta = %s AND idioma = %s
                AND faq_id != %s
            """, (chatbot_id, designacao, pergunta, resposta, idioma, faq_id))
            if cur.fetchone():
                return jsonify({"success": False, "error": "Esta combinação (chatbot, designação, pergunta, resposta e idioma) já existe noutra FAQ."}), 409

        try:
            if video_text_in_payload:
                cur.execute(
                    """
                    UPDATE faq
                    SET pergunta=%s,
                        resposta=%s,
                        idioma=%s,
                        categoria_id=%s,
                        recomendado=%s,
                        designacao=%s,
                        video_text=%s,
                        identificador=%s
                    WHERE faq_id=%s
                    """,
                    (pergunta, resposta, idioma, categoria_id, recomendado, designacao, video_text_value, identificador or None, faq_id),
                )
            else:
                cur.execute(
                    """
                    UPDATE faq
                    SET pergunta=%s,
                        resposta=%s,
                        idioma=%s,
                        categoria_id=%s,
                        recomendado=%s,
                        designacao=%s,
                        identificador=%s
                    WHERE faq_id=%s
                    """,
                    (pergunta, resposta, idioma, categoria_id, recomendado, designacao, identificador or None, faq_id),
                )
            # Atualizar FAQs relacionadas (se fornecidas)
            if relacionadas_raw is not None:
                cur.execute("DELETE FROM faq_relacionadas WHERE faq_id = %s", (faq_id,))
                for rel_id in relacionadas_ids:
                    cur.execute(
                        "INSERT INTO faq_relacionadas (faq_id, faq_relacionada_id) VALUES (%s, %s)",
                        (faq_id, rel_id),
                    )
            conn.commit()
            build_faiss_index()
        except Exception as update_error:
            error_msg = str(update_error)
            # Check for unique constraint violation
            if "duplicate key value violates unique constraint" in error_msg.lower() or "faq_chatbot_id_designacao_pergunta_resposta_idioma_key" in error_msg:
                return jsonify({"success": False, "error": "Esta combinação (chatbot, designação, pergunta, resposta e idioma) já existe noutra FAQ."}), 409
            raise  # Re-raise if it's a different error

        # Check if chatbot has video_enabled
        video_enabled = False
        if chatbot_id:
            cur.execute("SELECT video_enabled FROM chatbot WHERE chatbot_id = %s", (chatbot_id,))
            row = cur.fetchone()
            video_enabled = bool(row[0]) if row else False

        # Only queue video if resposta or video_text changed (not for recomendado/categorias changes)
        # Check if resposta or video_text actually changed
        resposta_changed = resposta and resposta != old_resposta
        video_text_changed = video_text_in_payload and (video_text_value or "") != (old_video_text or "")
        
        # If resposta or video_text changed, and video_enabled, queue video
        if video_enabled and (resposta_changed or video_text_changed):
            if can_start_new_video_job():
                queue_video_for_faq(faq_id)
                return jsonify({"success": True, "video_queued": True})
            else:
                return jsonify({"success": True, "video_queued": False, "busy": True})

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
        identificador = (data.get("identificador") or "").strip()
        video_text = data.get("video_text", "").strip() or None
        # gerar_video pode chegar como bool (JSON) ou string (ex: "on")
        # Se não vier no payload e o chatbot tem vídeo ativo, assumimos True (comportamento esperado: gerar vídeo por defeito).
        raw_gerar_video = data.get("gerar_video", None)
        if raw_gerar_video is None:
            gerar_video = True
        elif isinstance(raw_gerar_video, str):
            gerar_video = raw_gerar_video.strip().lower() in {"1", "true", "yes", "on"}
        else:
            gerar_video = bool(raw_gerar_video)
        cur.execute("""
            SELECT faq_id FROM faq
            WHERE chatbot_id = %s AND designacao = %s AND pergunta = %s AND resposta = %s AND idioma = %s
        """, (data["chatbot_id"], data["designacao"], data["pergunta"], data["resposta"], idioma))
        if cur.fetchone():
            return jsonify({"success": False, "error": "Esta FAQ já está inserida."}), 409

        # Always check if chatbot has video_enabled
        cur.execute("SELECT video_enabled FROM chatbot WHERE chatbot_id = %s", (data["chatbot_id"],))
        row = cur.fetchone()
        video_enabled = bool(row[0]) if row else False

        # If video is disabled for this chatbot, force-disable gerar_video
        if not video_enabled:
            gerar_video = False

        # Só enfileirar vídeo se o chatbot permitir E se o utilizador pediu para gerar vídeo.
        # (evita gerar vídeo quando o chatbot está com vídeo desativado, mesmo que o checkbox venha marcado por engano)
        should_queue_video = bool(video_enabled and gerar_video)

        # Se for para gerar vídeo, garantir que não há outro job em curso.
        if should_queue_video and not can_start_new_video_job():
            return jsonify({
                "success": False,
                "busy": True,
                "error": "Já existe um vídeo a ser gerado. Aguarde que termine ou desative a opção de gerar vídeo."
            }), 409

        try:
            cur.execute("""
                INSERT INTO faq (chatbot_id, categoria_id, designacao, identificador, pergunta, resposta, idioma, links_documentos, recomendado, video_text)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING faq_id
            """, (
                data["chatbot_id"],
                data["categoria_id"],
                data["designacao"],
                identificador or None,
                data["pergunta"],
                data["resposta"],
                idioma,
                links_documentos,
                recomendado,
                video_text,
            ))
            faq_id = cur.fetchone()[0]
        except Exception as insert_error:
            error_msg = str(insert_error)
            # Check for unique constraint violation
            if "duplicate key value violates unique constraint" in error_msg.lower() or "faq_chatbot_id_designacao_pergunta_resposta_idioma_key" in error_msg:
                return jsonify({"success": False, "error": "Esta FAQ já existe com os mesmos valores (chatbot, designação, pergunta, resposta e idioma)."}), 409
            raise  # Re-raise if it's a different error
        if links_documentos:
            for link in links_documentos.split(','):
                link = link.strip()
                if link:
                    cur.execute(
                        "INSERT INTO faq_documento (faq_id, link) VALUES (%s, %s)",
                        (faq_id, link)
                    )
        if "relacionadas" in data:
            relacionadas_raw = data.get("relacionadas") or []
            if isinstance(relacionadas_raw, list):
                relacionadas_ids = [int(x) for x in relacionadas_raw if str(x).strip().isdigit()]
            else:
                relacionadas_ids = [
                    int(x.strip()) for x in str(relacionadas_raw).split(",") if x.strip().isdigit()
                ]
            relacionadas_ids = [rid for rid in relacionadas_ids if rid != faq_id]
            for rel_id in relacionadas_ids:
                cur.execute(
                    "INSERT INTO faq_relacionadas (faq_id, faq_relacionada_id) VALUES (%s, %s)",
                    (faq_id, rel_id),
                )
        conn.commit()
        build_faiss_index()

        if should_queue_video:
            queue_video_for_faq(faq_id)
            return jsonify({"success": True, "faq_id": faq_id, "video_queued": True})

        return jsonify({"success": True, "faq_id": faq_id, "video_queued": False})
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
        # Fetch video_path and chatbot_id before deleting
        cur.execute("SELECT video_path, chatbot_id FROM faq WHERE faq_id = %s", (faq_id,))
        row = cur.fetchone()
        video_path = row[0] if row else None
        chatbot_id = row[1] if row else None

        cur.execute("DELETE FROM faq WHERE faq_id = %s", (faq_id,))
        conn.commit()
        build_faiss_index()

        # Delete video file if it exists
        if video_path and os.path.isfile(video_path):
            try:
                os.remove(video_path)
            except Exception:
                pass

        # Best-effort cleanup for current naming scheme (results/chatbot_{id}/faq_{faq_id}/final.mp4)
        try:
            result_root = RESULTS_DIR if RESULTS_DIR.is_absolute() else (ROOT / RESULTS_DIR)
            if chatbot_id:
                # New location: chatbot_{id}/faq_{faq_id}/
                expected_dir = result_root / f"chatbot_{chatbot_id}" / f"faq_{faq_id}"
                if expected_dir.exists() and expected_dir.is_dir():
                    import shutil
                    shutil.rmtree(expected_dir, ignore_errors=True)
            # Also try legacy location (results/faq_{faq_id}/) for backwards compatibility
            legacy_dir = result_root / f"faq_{faq_id}"
            if legacy_dir.exists() and legacy_dir.is_dir():
                import shutil
                shutil.rmtree(legacy_dir, ignore_errors=True)
            # also remove any legacy variants
            for p in result_root.glob(f"faq_{faq_id}*.mp4"):
                try:
                    if p.is_file():
                        p.unlink()
                except Exception:
                    pass
        except Exception:
            pass

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
                   f.categoria_id, c.nome AS categoria_nome, ch.nome AS chatbot_nome, f.recomendado,
                   f.video_status, f.video_path, f.video_text, f.identificador
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
                "recomendado": r[10],
                "video_status": r[11],
                "video_path": r[12],
                "video_text": r[13],
                "identificador": r[14],
            }
            for r in data
        ])
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

