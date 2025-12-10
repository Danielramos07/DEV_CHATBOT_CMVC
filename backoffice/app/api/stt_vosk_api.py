from flask import Blueprint, request, jsonify
from ..services.stt_vosk import transcribe_wav_bytes


app = Blueprint("stt_vosk", __name__)


@app.route("/vosk/transcribe", methods=["POST"])
def vosk_transcribe():
  """Receive an audio file and return its transcription.

  Expects a multipart/form-data request with field name "audio" containing
  a small mono 16 kHz WAV file. Returns JSON {"success": bool, "text": str}.
  """

  if "audio" not in request.files:
    return jsonify({"success": False, "error": "Missing 'audio' file field"}), 400

  file = request.files["audio"]
  audio_bytes = file.read()
  if not audio_bytes:
    return jsonify({"success": False, "error": "Empty audio data"}), 400

  try:
    text = transcribe_wav_bytes(audio_bytes)
    return jsonify({"success": True, "text": text})
  except Exception as e:
    return jsonify({"success": False, "error": str(e)}), 500
