import os
import sys
import uuid
import subprocess
import time
from pathlib import Path
from threading import Lock, Thread
from typing import Optional, Dict, Any
import shutil


from dotenv import load_dotenv

from ..db import get_pool_conn, put_pool_conn
from ..video.src.piper_tts import speak as piper_speak
from flask import current_app


# Project root (where .env lives)
ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / ".env")

# Embedded SadTalker app location
VIDEO_ROOT = ROOT / "backoffice" / "app" / "video"

# Icons base (relative to project root)
ICON_DIR = Path(os.getenv("ICON_PATH", "backoffice/app/static/icons"))

# Piper / SadTalker paths (relative to project root by default)
PIPER_VOICES_DIR = Path(
    os.getenv("PIPER_VOICES_DIR", "backoffice/app/video/models/voices")
)
PIPER_VOICE_MALE = Path(
    os.getenv("PIPER_VOICE_MALE", str(PIPER_VOICES_DIR / "pt_PT-tugao-medium.onnx"))
)
PIPER_VOICE_FEMALE = Path(
    os.getenv("PIPER_VOICE_FEMALE", str(PIPER_VOICES_DIR / "dii_pt-PT.onnx"))
)
PIPER_VOICE_DEFAULT = Path(
    os.getenv("PIPER_VOICE_DEFAULT", str(PIPER_VOICE_FEMALE))
)

SADTALKER_PREPROCESS_DEFAULT = os.getenv("SADTALKER_PREPROCESS_DEFAULT", "crop")
SADTALKER_SIZE_DEFAULT = os.getenv("SADTALKER_SIZE_DEFAULT", "256")
SADTALKER_BATCH_SIZE_DEFAULT = os.getenv("SADTALKER_BATCH_SIZE_DEFAULT", "1")
SADTALKER_ENHANCER_DEFAULT = os.getenv("SADTALKER_ENHANCER_DEFAULT", "")
SADTALKER_IDLE_SECONDS = float(os.getenv("SADTALKER_IDLE_SECONDS", "2"))
RESULTS_DIR = Path(os.getenv("RESULTS_DIR", "backoffice/app/video/results"))

_job_lock = Lock()
_current_job: Dict[str, Any] = {
    "status": "idle",  # idle | queued | processing | done | error
    "faq_id": None,
    "chatbot_id": None,
    "kind": None,  # faq | chatbot
    "progress": 0,
    "message": "",
    "error": None,
    "started_at": None,
}

_cancel_requested = False
_current_process: Optional[subprocess.Popen] = None
_current_tmp_root: Optional[Path] = None
_current_final_dir: Optional[Path] = None

# Cross-worker/process global lock via Postgres advisory lock.
# This makes "one global video job at a time" true even with multiple gunicorn workers/instances.
_PG_VIDEO_LOCK_KEY = 912340981273  # bigint constant; must match across all app instances
_lock_conn = None  # pooled connection kept open for the duration of the job while holding advisory lock


def _db_update_video_job(**fields: Any) -> None:
    """Best-effort update of the singleton row in video_job using the lock connection if available."""
    global _lock_conn
    conn = _lock_conn
    if conn is None:
        return
    if not fields:
        return
    # always bump updated_at
    cols = []
    vals = []
    for k, v in fields.items():
        cols.append(f"{k}=%s")
        vals.append(v)
    cols.append("updated_at=NOW()")
    sql = f"UPDATE video_job SET {', '.join(cols)} WHERE id=1"
    try:
        cur = conn.cursor()
        cur.execute(sql, tuple(vals))
        conn.commit()
        cur.close()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass


def _db_request_cancel() -> None:
    """Request cancel globally (works even if the current HTTP request hits a different worker)."""
    conn = None
    cur = None
    try:
        conn = get_pool_conn()
        cur = conn.cursor()
        cur.execute("UPDATE video_job SET cancel_requested=TRUE, updated_at=NOW() WHERE id=1;")
        conn.commit()
    except Exception:
        try:
            if conn:
                conn.rollback()
        except Exception:
            pass
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            if conn:
                put_pool_conn(conn)
        except Exception:
            pass


def _db_is_cancel_requested() -> bool:
    """Read cancel flag from DB using lock connection if available."""
    global _lock_conn
    conn = _lock_conn
    if conn is None:
        return False
    try:
        cur = conn.cursor()
        cur.execute("SELECT cancel_requested FROM video_job WHERE id=1;")
        row = cur.fetchone()
        cur.close()
        return bool(row[0]) if row else False
    except Exception:
        return False


def _db_reset_video_job_row() -> None:
    _db_update_video_job(
        status="idle",
        kind=None,
        faq_id=None,
        chatbot_id=None,
        progress=0,
        message="",
        error=None,
        cancel_requested=False,
        started_at=None,
    )


def _try_acquire_global_video_lock(kind: str, *, faq_id: Optional[int], chatbot_id: Optional[int], message: str) -> bool:
    """Attempt to acquire the global advisory lock and initialize video_job row.

    IMPORTANT: advisory locks are held per-connection, so we keep this pooled connection open
    for the duration of the job.
    """
    global _lock_conn
    conn = None
    cur = None
    try:
        conn = get_pool_conn()
        cur = conn.cursor()
        cur.execute("SELECT pg_try_advisory_lock(%s);", (_PG_VIDEO_LOCK_KEY,))
        ok = bool(cur.fetchone()[0])
        if not ok:
            return False
        # Hold lock by keeping conn open in global
        _lock_conn = conn
        conn = None  # prevent returning it to pool
        # Initialize DB job row
        _db_update_video_job(
            status="queued",
            kind=kind,
            faq_id=faq_id,
            chatbot_id=chatbot_id,
            progress=0,
            message=message,
            error=None,
            cancel_requested=False,
            started_at=None,
        )
        return True
    except Exception:
        return False
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            if conn:
                put_pool_conn(conn)
        except Exception:
            pass


def _release_global_video_lock() -> None:
    global _lock_conn, _cancel_requested
    conn = _lock_conn
    _lock_conn = None
    _cancel_requested = False
    if conn is None:
        return
    try:
        # Clear DB job state first (best effort)
        try:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE video_job
                SET status='idle',
                    kind=NULL,
                    faq_id=NULL,
                    chatbot_id=NULL,
                    progress=0,
                    message='',
                    error=NULL,
                    cancel_requested=FALSE,
                    started_at=NULL,
                    updated_at=NOW()
                WHERE id=1;
                """
            )
            conn.commit()
            cur.close()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass

        # Release advisory lock
        try:
            cur = conn.cursor()
            cur.execute("SELECT pg_advisory_unlock(%s);", (_PG_VIDEO_LOCK_KEY,))
            conn.commit()
            cur.close()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
    finally:
        try:
            put_pool_conn(conn)
        except Exception:
            pass


def _set_job(**kwargs: Any) -> None:
    """Safely update the in-memory job state."""

    with _job_lock:
        _current_job.update(kwargs)
    # Best-effort DB sync (for cross-worker status visibility)
    if kwargs:
        _db_update_video_job(**kwargs)


def get_video_job_status() -> Dict[str, Any]:
    """Return a snapshot of the current video job status (DB-backed for multi-worker deployments)."""
    conn = None
    cur = None
    try:
        conn = get_pool_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT status, kind, faq_id, chatbot_id, progress, message, error, cancel_requested, started_at, updated_at
            FROM video_job
            WHERE id=1;
            """
        )
        row = cur.fetchone()
        if not row:
            # Fallback to in-memory if schema is not present for some reason
            with _job_lock:
                return dict(_current_job)

        status, kind, faq_id, chatbot_id, progress, message, error, cancel_requested, started_at, updated_at = row

        # If DB says we're busy but nobody holds the lock, treat as stale and reset.
        if status in {"queued", "processing"}:
            cur.execute("SELECT pg_try_advisory_lock(%s);", (_PG_VIDEO_LOCK_KEY,))
            got = bool(cur.fetchone()[0])
            if got:
                # no one is holding it -> stale
                cur.execute("UPDATE video_job SET status='idle', kind=NULL, faq_id=NULL, chatbot_id=NULL, progress=0, message='', error=NULL, cancel_requested=FALSE, started_at=NULL, updated_at=NOW() WHERE id=1;")
                cur.execute("SELECT pg_advisory_unlock(%s);", (_PG_VIDEO_LOCK_KEY,))
                conn.commit()
                status, kind, faq_id, chatbot_id, progress, message, error, cancel_requested, started_at, updated_at = (
                    "idle", None, None, None, 0, "", None, False, None, updated_at
                )

        return {
            "status": status,
            "kind": kind,
            "faq_id": faq_id,
            "chatbot_id": chatbot_id,
            "progress": int(progress or 0),
            "message": message or "",
            "error": error,
            "started_at": started_at.isoformat() if started_at else None,
            "updated_at": updated_at.isoformat() if updated_at else None,
            "cancel_requested": bool(cancel_requested),
        }
    except Exception:
        with _job_lock:
            return dict(_current_job)
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            if conn:
                put_pool_conn(conn)
        except Exception:
            pass


def can_start_new_video_job() -> bool:
    """Return True if there is no job currently queued/processing (cross-worker safe)."""
    conn = None
    cur = None
    try:
        conn = get_pool_conn()
        cur = conn.cursor()
        cur.execute("SELECT pg_try_advisory_lock(%s);", (_PG_VIDEO_LOCK_KEY,))
        got = bool(cur.fetchone()[0])
        if got:
            cur.execute("SELECT pg_advisory_unlock(%s);", (_PG_VIDEO_LOCK_KEY,))
            conn.commit()
            return True
        return False
    except Exception:
        # best-effort fallback
        with _job_lock:
            return _current_job.get("status") not in {"queued", "processing"}
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            if conn:
                put_pool_conn(conn)
        except Exception:
            pass


def _reset_job_state() -> None:
    # In-memory reset only; DB reset + lock release happens in _release_global_video_lock().
    with _job_lock:
        _current_job.update(
            {
                "status": "idle",
                "faq_id": None,
                "chatbot_id": None,
                "kind": None,
                "progress": 0,
                "message": "",
                "error": None,
                "started_at": None,
            }
        )


def queue_videos_for_chatbot(chatbot_id: int) -> bool:
    """Queue generation of greeting and idle videos for the given chatbot.

    Returns False if another job is already running.
    """

    if not _try_acquire_global_video_lock(
        "chatbot",
        faq_id=None,
        chatbot_id=chatbot_id,
        message="A preparar geração de vídeos do chatbot...",
    ):
        return False

    with _job_lock:
        _current_job.update(
            {
                "status": "queued",
                "chatbot_id": chatbot_id,
                "faq_id": None,
                "kind": "chatbot",
                "progress": 0,
                "message": "A preparar geração de vídeos do chatbot...",
                "error": None,
                "started_at": time.time(),
            }
        )

    from flask import current_app
    app = current_app._get_current_object()
    worker = Thread(target=_run_idle_video_job, args=(chatbot_id, app), daemon=True)
    worker.start()
    return True


def queue_video_for_faq(faq_id: int) -> bool:
    """Queue a new video generation job for the given FAQ.

    Returns False if another job is already running.
    """

    if not _try_acquire_global_video_lock(
        "faq",
        faq_id=faq_id,
        chatbot_id=None,
        message="A preparar geração de vídeo...",
    ):
        return False

    with _job_lock:
        _current_job.update(
            {
                "status": "queued",
                "faq_id": faq_id,
                "chatbot_id": None,
                "kind": "faq",
                "progress": 0,
                "message": "A preparar geração de vídeo...",
                "error": None,
                "started_at": time.time(),
            }
        )

    # Update DB status early so UI doesn't get stuck waiting with NULL
    conn = None
    cur = None
    try:
        conn = get_pool_conn()
        cur = conn.cursor()
        cur.execute("UPDATE faq SET video_status=%s WHERE faq_id=%s", ("queued", faq_id))
        conn.commit()
    except Exception:
        # Best-effort only; the worker will update status again.
        try:
            if conn:
                conn.rollback()
        except Exception:
            pass
    finally:
        try:
            if cur:
                cur.close()
        except Exception:
            pass
        try:
            if conn:
                put_pool_conn(conn)
        except Exception:
            pass

    from flask import current_app
    app = current_app._get_current_object()
    worker = Thread(target=_run_video_job, args=(faq_id, app), daemon=True)
    worker.start()
    return True


def request_cancel_current_job() -> Dict[str, Any]:
    """Request cancellation of the currently running job (best-effort)."""
    global _cancel_requested, _current_process
    _cancel_requested = True
    _db_request_cancel()
    try:
        if _current_process and _current_process.poll() is None:
            _current_process.terminate()
    except Exception:
        pass
    return get_video_job_status()


class VideoJobCancelled(RuntimeError):
    pass


def _generate_video(
    text: str,
    genero: Optional[str],
    avatar_path: Optional[Path],
    *,
    final_dir: Path,
    final_filename: str,
    is_idle: bool = False,
) -> str:
    """Generate a talking-head video for the given text and gender.

    Returns the absolute path to the resulting MP4 file.
    """

    if avatar_path is None:
        raise FileNotFoundError("Avatar image file not provided for video generation.")

    genero = (genero or "").strip().lower()
    if genero == "m":
        voice_model = PIPER_VOICE_MALE
    elif genero == "f":
        voice_model = PIPER_VOICE_FEMALE
    else:
        voice_model = PIPER_VOICE_DEFAULT

    # Resolve paths relative to project root when necessary
    avatar_path = avatar_path if avatar_path.is_absolute() else (ROOT / avatar_path)
    if not avatar_path.exists():
        raise FileNotFoundError(f"Avatar image not found at: {avatar_path}")

    preprocess = SADTALKER_PREPROCESS_DEFAULT or "crop"
    size = SADTALKER_SIZE_DEFAULT if SADTALKER_SIZE_DEFAULT in {"256", "512"} else "256"
    enhancer = (SADTALKER_ENHANCER_DEFAULT or "").strip()
    if enhancer:
        weights_ok = (ROOT / "backoffice/app/video/models/gfpgan/weights/GFPGANv1.4.pth").exists()
        if not weights_ok:
            enhancer = ""
    batch_size = str(SADTALKER_BATCH_SIZE_DEFAULT or "1")

    result_root = RESULTS_DIR if RESULTS_DIR.is_absolute() else (ROOT / RESULTS_DIR)
    result_root.mkdir(parents=True, exist_ok=True)

    # Keep a stable folder per entity and only keep the final MP4 inside it.
    final_dir = final_dir if final_dir.is_absolute() else (ROOT / final_dir)
    final_dir.mkdir(parents=True, exist_ok=True)

    # tmp workspace under final_dir
    tmp_root = final_dir / "_tmp"
    run_id = str(uuid.uuid4())
    result_dir = tmp_root / run_id

    timestamp = time.strftime("%Y_%m_%d_%H.%M.%S", time.localtime())
    save_dir = result_dir / timestamp
    save_dir.mkdir(parents=True, exist_ok=True)

    global _cancel_requested, _current_process, _current_tmp_root, _current_final_dir
    _cancel_requested = False
    _current_tmp_root = tmp_root
    _current_final_dir = final_dir

    try:
        if is_idle:
            # For idle video, no audio needed, use idle mode
            wav_path = None
            _set_job(progress=50, message="A gerar animação idle...")
        else:
            # Generate audio for speaking video
            voice_model_path = voice_model if voice_model.is_absolute() else (ROOT / voice_model)
            if not voice_model_path.exists():
                raise FileNotFoundError(
                    f"Piper voice model not found: {voice_model_path}. "
                    "Verifique a instalação dos modelos Piper (setup.py --models-only)."
                )

            wav_path = save_dir / "piper.wav"
            piper_speak(text, str(wav_path), str(voice_model_path))
            _set_job(progress=50, message="A processar vídeo...")

        still = preprocess.startswith("full")

        cmd = [
            sys.executable,
            "-m",
            "src.inference",
            "--source_image",
            str(avatar_path),
            "--result_dir",
            str(result_dir),
            "--save_dir",
            str(save_dir),
            "--size",
            str(size),
            "--batch_size",
            str(batch_size),
            "--preprocess",
            preprocess,
        ]

        if is_idle:
            cmd.extend(["--use_idle_mode", "--length_of_audio", str(SADTALKER_IDLE_SECONDS)])
        else:
            cmd.extend(["--driven_audio", str(wav_path)])

        if still:
            cmd.append("--still")

        if enhancer:
            cmd.extend(["--enhancer", enhancer])

        # Run SadTalker process (allow cancellation)
        _current_process = subprocess.Popen(cmd, cwd=str(VIDEO_ROOT))
        last_db_cancel_check = 0.0
        while True:
            # Check both local cancel (same worker) and DB cancel (any worker)
            if _cancel_requested or (time.time() - last_db_cancel_check) > 0.8:
                if (time.time() - last_db_cancel_check) > 0.8:
                    last_db_cancel_check = time.time()
                    if _db_is_cancel_requested():
                        _cancel_requested = True
            if _cancel_requested:
                try:
                    _current_process.terminate()
                except Exception:
                    pass
                raise VideoJobCancelled("Cancelled by user")
            rc = _current_process.poll()
            if rc is not None:
                if rc != 0:
                    raise subprocess.CalledProcessError(rc, cmd)
                break
            time.sleep(0.2)

        _set_job(progress=80, message="A finalizar vídeo...")

        # Wait a bit for the file to be fully written (inference.py creates save_dir + ".mp4")
        time.sleep(1)
        
        # Search for MP4 files in result_dir (including subdirectories like timestamp folders)
        # The inference.py creates the file as save_dir + ".mp4" (e.g., "2025_12_27_17.58.02.mp4")
        # save_dir is result_dir / timestamp, so the file is created as result_dir / (timestamp + ".mp4")
        mp4_files = sorted(result_dir.rglob("*.mp4"), key=os.path.getmtime)
        # Also check if the file was created directly in result_dir (inference.py pattern: save_dir + ".mp4")
        # Since save_dir = result_dir / timestamp, the file is at result_dir / (timestamp + ".mp4")
        if result_dir.exists():
            result_dir_mp4s = list(result_dir.glob("*.mp4"))
            if result_dir_mp4s:
                mp4_files.extend(result_dir_mp4s)
        # Also check the expected location: result_dir / (timestamp + ".mp4")
        expected_file = result_dir / (timestamp + ".mp4")
        if expected_file.exists() and expected_file not in mp4_files:
            mp4_files.append(expected_file)
        # Remove duplicates and sort by modification time
        mp4_files = sorted(set(mp4_files), key=os.path.getmtime)
        if not mp4_files:
            # Debug: list what's actually in result_dir
            debug_files = list(result_dir.iterdir()) if result_dir.exists() else []
            raise RuntimeError(f"Nenhum ficheiro mp4 encontrado em {result_dir}. Ficheiros encontrados: {[str(f) for f in debug_files]}. Esperado: {expected_file}")

        # Move the MP4 to final_dir/{final_filename}
        final_mp4 = mp4_files[-1]
        final_path = final_dir / final_filename
        if final_path.exists():
            try:
                final_path.unlink()
            except Exception:
                pass
        
        # Use shutil.move instead of rename to handle cross-filesystem moves
        import shutil
        shutil.move(str(final_mp4), str(final_path))

        return str(final_path.resolve())
    finally:
        # Clean up tmp workspace (leave only final file in final_dir)
        try:
            if tmp_root.exists():
                shutil.rmtree(tmp_root, ignore_errors=True)
        except Exception:
            pass
        _current_process = None


def _run_video_job(faq_id: int, app) -> None:
    with app.app_context():
        conn = get_pool_conn()
        cur = conn.cursor()
        chatbot_id = None  # Initialize to ensure it's available in exception handlers
        try:
            _set_job(status="processing", progress=10, message="A preparar dados da FAQ...")

            cur.execute(
                """
                SELECT f.resposta,
                       COALESCE(f.video_text, f.resposta) AS video_text,
                       c.genero,
                       c.icon_path,
                       c.chatbot_id
                FROM faq f
                JOIN chatbot c ON f.chatbot_id = c.chatbot_id
                WHERE f.faq_id = %s
                """,
                (faq_id,),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError(f"FAQ com id {faq_id} não encontrada.")

            resposta, video_text, genero, icon_path, chatbot_id = row
            # Expose chatbot_id in job status for UI label (best-effort)
            _set_job(chatbot_id=chatbot_id)
            video_text = (video_text or resposta or "").strip()
            if not video_text:
                raise ValueError("Texto para vídeo vazio.")

            cur.execute(
                "UPDATE faq SET video_status=%s, video_text=%s WHERE faq_id=%s",
                ("processing", video_text, faq_id),
            )
            conn.commit()

            _set_job(progress=25, message="A gerar áudio com Piper...")

            # Resolver avatar: se o chatbot tiver um icon_path (ex: "/static/icons/nome.png"),
            # usar o ficheiro correspondente dentro de ICON_PATH (definido no .env).
            avatar_file: Optional[Path] = None
            if icon_path:
                try:
                    filename = str(icon_path).split("/")[-1]
                    icon_base = ICON_DIR if ICON_DIR.is_absolute() else (ROOT / ICON_DIR)
                    candidate = icon_base / filename
                    if candidate.exists():
                        avatar_file = candidate
                    else:
                        raise FileNotFoundError(f"Avatar image not found at: {candidate}")
                except Exception as e:
                    raise FileNotFoundError(f"Could not resolve avatar path from icon_path '{icon_path}': {e}")
            
            if avatar_file is None:
                raise FileNotFoundError(f"Chatbot {chatbot_id} não tem um avatar (icon_path) configurado. Configure um avatar antes de gerar vídeos.")

            # Store FAQ videos inside the chatbot's folder: chatbot_{id}/faq_{faq_id}/
            base_dir = (RESULTS_DIR if RESULTS_DIR.is_absolute() else (ROOT / RESULTS_DIR)) / f"chatbot_{chatbot_id}"
            video_path = _generate_video(
                video_text,
                genero,
                avatar_file,
                final_dir=base_dir / f"faq_{faq_id}",
                final_filename="final.mp4",
                is_idle=False,
            )

            _set_job(progress=90, message="A finalizar vídeo...")
            cur.execute(
                "UPDATE faq SET video_status=%s, video_path=%s WHERE faq_id=%s",
                ("ready", video_path, faq_id),
            )
            conn.commit()

            _set_job(status="done", progress=100, message="Vídeo gerado com sucesso.", error=None)
        except VideoJobCancelled:
            conn.rollback()
            _reset_job_state()
            try:
                cur.execute("UPDATE faq SET video_status=%s, video_path=NULL WHERE faq_id=%s", ("cancelled", faq_id))
                conn.commit()
            except Exception:
                conn.rollback()
            # remove final folder entirely
            try:
                base_dir = (RESULTS_DIR if RESULTS_DIR.is_absolute() else (ROOT / RESULTS_DIR)) / f"chatbot_{chatbot_id}"
                final_dir = base_dir / f"faq_{faq_id}"
                shutil.rmtree(final_dir, ignore_errors=True)
            except Exception:
                pass
        except Exception as e:
            conn.rollback()
            _set_job(status="error", progress=100, message="Falha ao gerar vídeo.", error=str(e))
            try:
                cur.execute(
                    "UPDATE faq SET video_status=%s WHERE faq_id=%s",
                    ("failed", faq_id),
                )
                conn.commit()
            except Exception:
                conn.rollback()
        finally:
            cur.close()
            put_pool_conn(conn)
            _release_global_video_lock()
            _reset_job_state()


def _run_idle_video_job(chatbot_id: int, app) -> None:
    with app.app_context():
        conn = get_pool_conn()
        cur = conn.cursor()
        try:
            _set_job(status="processing", progress=10, message="A preparar dados do chatbot...")

            cur.execute(
                "SELECT nome, genero, icon_path FROM chatbot WHERE chatbot_id = %s",
                (chatbot_id,),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Chatbot {chatbot_id} não encontrado.")
            nome, genero, icon_path = row

            # Resolver avatar
            avatar_file: Optional[Path] = None
            if icon_path:
                try:
                    filename = str(icon_path).split("/")[-1]
                    icon_base = ICON_DIR if ICON_DIR.is_absolute() else (ROOT / ICON_DIR)
                    candidate = icon_base / filename
                    if candidate.exists():
                        avatar_file = candidate
                except Exception:
                    avatar_file = None

            # Generate greeting video
            _set_job(progress=25, message="A gerar vídeo de saudação...")
            video_text = f"Olá, sou o {nome}. Como posso ajudar?"
            base_dir = (RESULTS_DIR if RESULTS_DIR.is_absolute() else (ROOT / RESULTS_DIR)) / f"chatbot_{chatbot_id}"
            greeting_path = _generate_video(
                video_text,
                genero,
                avatar_file,
                final_dir=base_dir,
                final_filename="greeting.mp4",
                is_idle=False,
            )
            
            # Save greeting_path immediately (even if idle fails later)
            cur.execute(
                "UPDATE chatbot SET video_greeting_path=%s WHERE chatbot_id=%s",
                (greeting_path, chatbot_id),
            )
            conn.commit()

            # Generate idle video
            _set_job(progress=60, message="A gerar vídeo idle...")
            idle_path = None
            try:
                idle_path = _generate_video(
                    "",
                    genero,
                    avatar_file,
                    final_dir=base_dir,
                    final_filename="idle.mp4",
                    is_idle=True,
                )
            except Exception as idle_error:
                # If idle generation fails, log but continue (greeting is already saved)
                print(f"Erro ao gerar vídeo idle: {idle_error}")
                _set_job(progress=90, message=f"Vídeo idle falhou, mas greeting foi gerado. Erro: {str(idle_error)}")

            _set_job(progress=90, message="A finalizar vídeos...")
            if idle_path:
                cur.execute(
                    "UPDATE chatbot SET video_greeting_path=%s, video_idle_path=%s WHERE chatbot_id=%s",
                    (greeting_path, idle_path, chatbot_id),
                )
            else:
                # Only update greeting if idle failed
                cur.execute(
                    "UPDATE chatbot SET video_greeting_path=%s WHERE chatbot_id=%s",
                    (greeting_path, chatbot_id),
                )
            conn.commit()

            _set_job(status="done", progress=100, message="Vídeos gerados com sucesso.", error=None)
        except VideoJobCancelled:
            conn.rollback()
            _reset_job_state()
            # Cleanup folder for this chatbot videos
            try:
                base_dir = (RESULTS_DIR if RESULTS_DIR.is_absolute() else (ROOT / RESULTS_DIR)) / f"chatbot_{chatbot_id}"
                shutil.rmtree(base_dir, ignore_errors=True)
            except Exception:
                pass
        except Exception as e:
            conn.rollback()
            _set_job(status="error", progress=100, message="Falha ao gerar vídeos.", error=str(e))
            # Even if idle failed, try to save greeting_path if it was generated
            try:
                if 'greeting_path' in locals() and greeting_path:
                    cur.execute(
                        "UPDATE chatbot SET video_greeting_path=%s WHERE chatbot_id=%s",
                        (greeting_path, chatbot_id),
                    )
                    conn.commit()
            except Exception:
                conn.rollback()
            # Also try to save idle_path if it was generated but not saved
            try:
                if 'idle_path' in locals() and idle_path:
                    cur.execute(
                        "UPDATE chatbot SET video_idle_path=%s WHERE chatbot_id=%s",
                        (idle_path, chatbot_id),
                    )
                    conn.commit()
            except Exception:
                conn.rollback()
        finally:
            cur.close()
            put_pool_conn(conn)
            _release_global_video_lock()
            _reset_job_state()
