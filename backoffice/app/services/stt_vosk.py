import io
import os
import wave

import numpy as np
from flask import current_app
import vosk


_vosk_model = None


def get_vosk_model():
    global _vosk_model
    if _vosk_model is None:
        # Path can be absolute or relative; if relative, anchor at app root.
        model_path = current_app.config.get(
            "VOSK_MODEL_PATH", "extras/models/vosk-model-small-pt-0.3"
        )
        if not os.path.isabs(model_path):
            model_path = os.path.join(current_app.root_path, model_path)
        _vosk_model = vosk.Model(model_path)
    return _vosk_model


def transcribe_wav_bytes(wav_bytes: bytes) -> str:
    """Transcribe a WAV byte stream using Vosk.

    Accepts 16‑bit PCM mono/stereo WAV from the browser. Uses the
    WAV's own sample rate so we don't need to resample in JS.
    """

    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        sample_rate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())

    if sampwidth != 2:
        # Expect 16‑bit PCM; if not, return empty for now.
        return ""

    audio = np.frombuffer(frames, dtype=np.int16)
    if n_channels == 2:
        # Downmix stereo to mono by taking one channel
        audio = audio[::2]
    pcm_bytes = audio.tobytes()

    model = get_vosk_model()
    rec = vosk.KaldiRecognizer(model, sample_rate)
    rec.AcceptWaveform(pcm_bytes)

    result_json = rec.Result()
    try:
        import json

        result = json.loads(result_json)
        return (result.get("text") or "").strip()
    except Exception:
        return ""
