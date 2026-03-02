
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Always load the root .env (same folder as wsgi.py)
PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env")

# Only use variables from root .env


def _getenv_any(*keys: str) -> Optional[str]:
	for key in keys:
		val = os.getenv(key)
		if val is not None and str(val).strip() != "":
			return val
	return None


# Legacy keys (PIPER_VOICE_*) are supported, but preferred config is per-language.
PIPER_VOICE_MALE_PT = _getenv_any("PIPER_VOICE_MALE_PT", "PIPER_VOICE_MALE_pt")
PIPER_VOICE_FEMALE_PT = _getenv_any("PIPER_VOICE_FEMALE_PT", "PIPER_VOICE_FEMALE_pt")
PIPER_VOICE_DEFAULT_PT = _getenv_any("PIPER_VOICE_DEFAULT_PT", "PIPER_VOICE_DEFAULT_pt")

PIPER_VOICE_MALE = _getenv_any("PIPER_VOICE_MALE") or PIPER_VOICE_MALE_PT
PIPER_VOICE_FEMALE = _getenv_any("PIPER_VOICE_FEMALE") or PIPER_VOICE_FEMALE_PT
PIPER_VOICE_DEFAULT = _getenv_any("PIPER_VOICE_DEFAULT") or PIPER_VOICE_DEFAULT_PT or PIPER_VOICE_FEMALE
SADTALKER_PREPROCESS_DEFAULT = os.getenv("SADTALKER_PREPROCESS_DEFAULT")
SADTALKER_SIZE_DEFAULT = os.getenv("SADTALKER_SIZE_DEFAULT")
SADTALKER_BATCH_SIZE_DEFAULT = os.getenv("SADTALKER_BATCH_SIZE_DEFAULT")
SADTALKER_ENHANCER_DEFAULT = os.getenv("SADTALKER_ENHANCER_DEFAULT")
RESULTS_DIR = os.getenv("RESULTS_DIR")
