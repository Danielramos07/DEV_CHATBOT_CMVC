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

from ..db import get_conn
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
SADTALKER_IDLE_SECONDS = float(os.getenv("SADTALKER_IDLE_SECONDS", "4"))
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


def _set_job(**kwargs: Any) -> None:
    """Safely update the in-memory job state."""

    with _job_lock:
        _current_job.update(kwargs)


def get_video_job_status() -> Dict[str, Any]:
    """Return a snapshot of the current video job status."""

    with _job_lock:
        return dict(_current_job)


def can_start_new_video_job() -> bool:
    """Return True if there is no job currently queued/processing."""

    with _job_lock:
        return _current_job.get("status") not in {"queued", "processing"}


def _reset_job_state() -> None:
    _set_job(
        status="idle",
        faq_id=None,
        chatbot_id=None,
        kind=None,
        progress=0,
        message="",
        error=None,
        started_at=None,
    )


def queue_videos_for_chatbot(chatbot_id: int) -> bool:
    """Queue generation of greeting and idle videos for the given chatbot.

    Returns False if another job is already running.
    """

    with _job_lock:
        if _current_job.get("status") in {"queued", "processing"}:
            return False
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

    with _job_lock:
        if _current_job.get("status") in {"queued", "processing"}:
            return False
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
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("UPDATE faq SET video_status=%s WHERE faq_id=%s", ("queued", faq_id))
        conn.commit()
        cur.close()
        conn.close()
    except Exception:
        # Best-effort only; the worker will update status again.
        try:
            conn.rollback()
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
        while True:
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

        mp4_files = sorted(result_dir.rglob("*.mp4"), key=os.path.getmtime)
        if not mp4_files:
            raise RuntimeError(f"Nenhum ficheiro mp4 encontrado em {result_dir}.")

        # Move the MP4 to final_dir/{final_filename}
        final_mp4 = mp4_files[-1]
        final_path = final_dir / final_filename
        if final_path.exists():
            try:
                final_path.unlink()
            except Exception:
                pass
        final_mp4.rename(final_path)

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
        conn = get_conn()
        cur = conn.cursor()
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
                except Exception:
                    avatar_file = None

            video_path = _generate_video(
                video_text,
                genero,
                avatar_file,
                final_dir=(RESULTS_DIR if RESULTS_DIR.is_absolute() else (ROOT / RESULTS_DIR)) / f"faq_{faq_id}",
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
                final_dir = (RESULTS_DIR if RESULTS_DIR.is_absolute() else (ROOT / RESULTS_DIR)) / f"faq_{faq_id}"
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
            conn.close()


def _run_idle_video_job(chatbot_id: int, app) -> None:
    with app.app_context():
        conn = get_conn()
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

            # Generate idle video
            _set_job(progress=60, message="A gerar vídeo idle...")
            idle_path = _generate_video(
                "",
                genero,
                avatar_file,
                final_dir=base_dir,
                final_filename="idle.mp4",
                is_idle=True,
            )

            _set_job(progress=90, message="A finalizar vídeos...")
            cur.execute(
                "UPDATE chatbot SET video_greeting_path=%s, video_idle_path=%s WHERE chatbot_id=%s",
                (greeting_path, idle_path, chatbot_id),
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
        finally:
            cur.close()
            conn.close()
