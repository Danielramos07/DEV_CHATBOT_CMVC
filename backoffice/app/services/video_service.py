import os
import sys
import uuid
import subprocess
import time
from pathlib import Path
from threading import Lock, Thread
from typing import Optional, Dict, Any


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
RESULTS_DIR = Path(os.getenv("RESULTS_DIR", "backoffice/app/video/results"))

_job_lock = Lock()
_current_job: Dict[str, Any] = {
    "status": "idle",  # idle | queued | processing | done | error
    "faq_id": None,
    "progress": 0,
    "message": "",
    "error": None,
    "started_at": None,
}


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
                "progress": 0,
                "message": "A preparar geração de vídeo...",
                "error": None,
                "started_at": time.time(),
            }
        )

    from flask import current_app
    app = current_app._get_current_object()
    worker = Thread(target=_run_video_job, args=(faq_id, app), daemon=True)
    worker.start()
    return True


def _generate_video(text: str, genero: Optional[str], avatar_path: Optional[Path]) -> str:
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

    voice_model_path = voice_model if voice_model.is_absolute() else (ROOT / voice_model)
    if not voice_model_path.exists():
        raise FileNotFoundError(
            f"Piper voice model not found: {voice_model_path}. "
            "Verifique a instalação dos modelos Piper (setup.py --models-only)."
        )

    preprocess = SADTALKER_PREPROCESS_DEFAULT or "crop"
    size = SADTALKER_SIZE_DEFAULT if SADTALKER_SIZE_DEFAULT in {"256", "512"} else "256"
    enhancer = SADTALKER_ENHANCER_DEFAULT or ""
    batch_size = str(SADTALKER_BATCH_SIZE_DEFAULT or "1")

    result_root = RESULTS_DIR if RESULTS_DIR.is_absolute() else (ROOT / RESULTS_DIR)
    result_root.mkdir(exist_ok=True)

    run_id = str(uuid.uuid4())
    result_dir = result_root / run_id

    timestamp = time.strftime("%Y_%m_%d_%H.%M.%S", time.localtime())
    save_dir = result_dir / timestamp
    save_dir.mkdir(parents=True, exist_ok=True)

    wav_path = save_dir / "piper.wav"
    piper_speak(text, str(wav_path), str(voice_model_path))

    still = preprocess.startswith("full")

    cmd = [
        sys.executable,
        "-m",
        "src.inference",
        "--driven_audio",
        str(wav_path),
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

    if still:
        cmd.append("--still")

    if enhancer:
        cmd.extend(["--enhancer", enhancer])

    subprocess.check_call(cmd, cwd=str(VIDEO_ROOT))

    mp4_files = sorted(result_dir.rglob("*.mp4"), key=os.path.getmtime)
    if not mp4_files:
        raise RuntimeError(f"Nenhum ficheiro mp4 encontrado em {result_dir}.")

    return str(mp4_files[-1].resolve())


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
                       c.icon_path
                FROM faq f
                JOIN chatbot c ON f.chatbot_id = c.chatbot_id
                WHERE f.faq_id = %s
                """,
                (faq_id,),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError(f"FAQ com id {faq_id} não encontrada.")

            resposta, video_text, genero, icon_path = row
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

            video_path = _generate_video(video_text, genero, avatar_file)

            _set_job(progress=90, message="A finalizar vídeo...")
            cur.execute(
                "UPDATE faq SET video_status=%s, video_path=%s WHERE faq_id=%s",
                ("ready", video_path, faq_id),
            )
            conn.commit()

            _set_job(status="done", progress=100, message="Vídeo gerado com sucesso.", error=None)
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
