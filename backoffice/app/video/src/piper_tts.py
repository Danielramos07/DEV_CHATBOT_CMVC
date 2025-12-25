from __future__ import annotations


import os
import subprocess
import logging
from typing import Optional


def speak(text: str, output_wav_path: str, voice_model: str, *, extra_args: Optional[list[str]] = None) -> str:
    """
    Generate speech audio using the `piper` CLI.
    Returns the output_wav_path, or raises RuntimeError on failure.
    """
    logger = logging.getLogger("piper_tts")
    out_dir = os.path.dirname(output_wav_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    cmd = ["piper", "-m", voice_model, "-t", text, "-f", output_wav_path]
    if extra_args:
        cmd.extend(extra_args)

    logger.info(f"Running Piper TTS: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except Exception as e:
        logger.error(f"Failed to run Piper CLI: {e}")
        raise RuntimeError(f"Failed to run Piper CLI: {e}")

    if result.returncode != 0:
        logger.error(f"Piper failed. Command: {' '.join(cmd)}\nStderr: {result.stderr.strip()}")
        raise RuntimeError(
            f"Piper failed. Command: {' '.join(cmd)}\nStderr: {result.stderr.strip()}"
        )

    if not os.path.exists(output_wav_path) or os.path.getsize(output_wav_path) == 0:
        logger.error(f"Empty audio file generated: {output_wav_path}")
        raise RuntimeError(f"Empty audio file generated: {output_wav_path}")

    logger.info(f"Piper TTS succeeded, output: {output_wav_path}")
    return output_wav_path
