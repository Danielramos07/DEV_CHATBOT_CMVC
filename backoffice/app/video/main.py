

# Only import config from root .env
import threading
import uuid
import logging
import sys
import subprocess
import time
import os
from pathlib import Path
from typing import Optional
from .src.piper_tts import speak as piper_speak
from backoffice.app.video.config import (
    PIPER_VOICE_MALE,
    PIPER_VOICE_FEMALE,
    PIPER_VOICE_DEFAULT,
    SADTALKER_PREPROCESS_DEFAULT,
    SADTALKER_SIZE_DEFAULT,
    SADTALKER_BATCH_SIZE_DEFAULT,
    SADTALKER_ENHANCER_DEFAULT,
    RESULTS_DIR,
    PROJECT_ROOT,
)

logger = logging.getLogger("video_job")

# In-memory job status store
VIDEO_JOB_STATUS = {}

def _run_video_job(params, job_id, status_dict):
    """
    Internal: Run video job in thread, update status_dict.
    """
    status_dict[job_id] = {"status": "running"}
    try:
        result = generate_video_job(**params)
        status_dict[job_id] = result
    except Exception as e:
        status_dict[job_id] = {"status": "error", "error": str(e)}

def queue_video_job(
    text: str,
    avatar_path: str,
    voice: Optional[str] = None,
    preprocess: Optional[str] = None,
    size: Optional[str] = None,
    enhancer: Optional[str] = None,
    batch_size: Optional[int] = None,
    results_dir: Optional[str] = None,
) -> str:
    """
    Queue a video job to run in the background. Returns job_id.
    """
    job_id = str(uuid.uuid4())
    params = dict(
        text=text,
        avatar_path=avatar_path,
        voice=voice,
        preprocess=preprocess,
        size=size,
        enhancer=enhancer,
        batch_size=batch_size,
        results_dir=results_dir,
    )
    t = threading.Thread(target=_run_video_job, args=(params, job_id, VIDEO_JOB_STATUS))
    t.daemon = True
    t.start()
    VIDEO_JOB_STATUS[job_id] = {"status": "queued"}
    return job_id

def get_video_job_status(job_id: str) -> dict:
    """
    Get status/result for a queued video job.
    """
    return VIDEO_JOB_STATUS.get(job_id, {"status": "not_found"})

def generate_video_job(
    text: str,
    avatar_path: str,
    voice: Optional[str] = None,
    preprocess: Optional[str] = None,
    size: Optional[str] = None,
    enhancer: Optional[str] = None,
    batch_size: Optional[int] = None,
    results_dir: Optional[str] = None,
) -> dict:
    """
    Generate a talking head video using Piper TTS and SadTalker.
    Returns a dict with status, output paths, and error info.
    """
    try:
        logger.info("Starting video job")
        # Input validation
        if not text or not isinstance(text, str) or len(text.strip()) == 0:
            return {"status": "error", "error": "Text is required and must be non-empty."}
        avatar_path_obj = Path(avatar_path)
        if not avatar_path_obj.is_absolute():
            avatar_path_obj = PROJECT_ROOT / avatar_path_obj
        if not avatar_path_obj.exists() or not avatar_path_obj.is_file():
            logger.error(f"Avatar image not found: {avatar_path_obj}")
            return {"status": "error", "error": f"Avatar image not found: {avatar_path_obj}"}
        # Prevent directory traversal
        if ".." in str(avatar_path_obj.resolve().relative_to(PROJECT_ROOT)):
            return {"status": "error", "error": "Invalid avatar path."}
        # Validate batch_size
        try:
            batch_size = int(batch_size or SADTALKER_BATCH_SIZE_DEFAULT)
            if batch_size < 1 or batch_size > 16:
                return {"status": "error", "error": "Batch size must be between 1 and 16."}
        except Exception:
            return {"status": "error", "error": "Invalid batch size."}
        # Validate size
        if size is not None and size not in {"256", "512"}:
            return {"status": "error", "error": "Size must be 256 or 512."}
        # Validate preprocess
        if preprocess is not None and preprocess not in {"crop", "full", "extfull"}:
            return {"status": "error", "error": "Preprocess must be crop, full, or extfull."}
        # Validate voice model
        voice_model = voice or PIPER_VOICE_DEFAULT
        voice_model_path = Path(voice_model)
        if not voice_model_path.is_absolute():
            voice_model_path = PROJECT_ROOT / voice_model_path
        if not voice_model_path.exists():
            logger.error(f"Voice model not found: {voice_model_path}")
            return {"status": "error", "error": f"Voice model not found: {voice_model_path}"}
        # Validate results_dir
        results_dir = results_dir or RESULTS_DIR
        results_dir_path = Path(results_dir)
        if not results_dir_path.is_absolute():
            results_dir_path = PROJECT_ROOT / results_dir_path
        results_dir_path.mkdir(exist_ok=True)
        job_id = str(uuid.uuid4())
        params = dict(
            text=text,
            avatar_path=avatar_path,
            voice=str(voice) if voice is not None else None,
            preprocess=str(preprocess) if preprocess is not None else None,
            size=str(size) if size is not None else None,
            enhancer=str(enhancer) if enhancer is not None else None,
            batch_size=int(batch_size) if batch_size is not None and batch_size != "" else None,
            results_dir=str(results_dir) if results_dir is not None else None,
        )
        # Build SadTalker command
        checkpoint_dir = str(PROJECT_ROOT / "models/checkpoints")
        cmd = [
            sys.executable,
            "-m",
            "src.inference",
            "--driven_audio", wav_path,
            "--source_image", str(avatar_path_obj),
            "--checkpoint_dir", checkpoint_dir,
            "--result_dir", str(result_dir),
            "--batch_size", str(batch_size),
            "--size", str(size or SADTALKER_SIZE_DEFAULT),
            "--preprocess", preprocess or SADTALKER_PREPROCESS_DEFAULT,
        ]
        preprocess_val = preprocess or SADTALKER_PREPROCESS_DEFAULT
        still = isinstance(preprocess_val, str) and preprocess_val.startswith("full")
        if still:
            cmd.append("--still")
        if enhancer:
            cmd.extend(["--enhancer", enhancer])
        logger.info(f"Running SadTalker: {' '.join(cmd)}")
        try:
            subprocess.check_call(cmd, cwd=str(PROJECT_ROOT))
        except Exception as e:
            logger.error(f"SadTalker failed: {e}")
            return {"status": "error", "error": f"SadTalker failed: {e}"}
        mp4_files = sorted(result_dir.rglob("*.mp4"), key=os.path.getmtime)
        if mp4_files:
            output_video = str(mp4_files[-1])
            logger.info(f"Video generated: {output_video}")
            return {
                "status": "success",
                "output_video": output_video,
                "output_dir": str(result_dir),
                "run_id": run_id,
            }
        else:
            logger.error("No video file generated")
            return {"status": "error", "error": "No video file generated"}
    except Exception as e:
        logger.error(f"Unhandled error: {e}")
        return {"status": "error", "error": str(e)}
    except Exception as e:
        logger.error(f"Unhandled error: {e}")
        return {"status": "error", "error": str(e)}

def main():
    print("This script is now backend-ready. Use generate_video_job(), queue_video_job(), and get_video_job_status() from your Flask app or job manager.")

if __name__ == "__main__":
    main()
