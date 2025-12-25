
import os
from pathlib import Path
from dotenv import load_dotenv

# Always load the root .env (same folder as wsgi.py)
PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env")

# Only use variables from root .env
PIPER_VOICE_MALE = os.getenv("PIPER_VOICE_MALE")
PIPER_VOICE_FEMALE = os.getenv("PIPER_VOICE_FEMALE")
PIPER_VOICE_DEFAULT = os.getenv("PIPER_VOICE_DEFAULT", PIPER_VOICE_FEMALE)
SADTALKER_PREPROCESS_DEFAULT = os.getenv("SADTALKER_PREPROCESS_DEFAULT")
SADTALKER_SIZE_DEFAULT = os.getenv("SADTALKER_SIZE_DEFAULT")
SADTALKER_BATCH_SIZE_DEFAULT = os.getenv("SADTALKER_BATCH_SIZE_DEFAULT")
SADTALKER_ENHANCER_DEFAULT = os.getenv("SADTALKER_ENHANCER_DEFAULT")
RESULTS_DIR = os.getenv("RESULTS_DIR")
