# SadTalker Core (Piper TTS → SadTalker)

Minimal, cleaned version of SadTalker focused on a lightweight local workflow:

1. Type a message
2. Generate speech with Piper TTS
3. Animate a single avatar image with SadTalker

No WebUI/Gradio, and no speech-to-text (Vosk) in this workflow.

## Features

- Local text-to-speech via Piper (`piper` CLI)
- High-quality talking-head animation via SadTalker
- Optional face enhancement via GFPGAN
- Simple interactive CLI + scriptable SadTalker runner (`python -m src.inference`)

## What this repo contains

- Core model code under `src/` (preprocess, audio2coeff, face renderer, utilities).
- `main.py`: interactive flow (type text → Piper voice → SadTalker settings → output video).
- `src/inference.py`: scriptable entrypoint for SadTalker (image + audio → mp4).
- Model files under `models/`:
  - `models/checkpoints/` (SadTalker weights)
  - `models/gfpgan/weights/` (enhancer weights)
  - `models/voices/` (Piper voice models)

Optional helper folders (examples, docs, results) can be ignored or deleted in downstream projects; they are not required by the core code.

## Requirements

- Python 3.8–3.10 is recommended (some deps may be flaky on 3.11+).
- FFmpeg available on PATH (recommended).
- PyTorch installed manually for your platform (CPU/GPU).

### FFmpeg

This project writes videos; having FFmpeg installed system-wide makes things more reliable.

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg
```

## Installation (local project)

From the project root:

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\\Scripts\\activate on Windows

# Install PyTorch (version combo known to work with basicsr/gfpgan)
# CPU-only example for macOS/Linux:
pip install "torch==1.12.1" "torchvision==0.13.1" "torchaudio==0.12.1" \
  --extra-index-url https://download.pytorch.org/whl/cpu

# Then install Python dependencies
pip install -r requirements.txt
```

This installs the non-PyTorch dependencies listed in requirements.txt.
PyTorch itself is not in requirements.txt because its wheels are
hardware/OS specific; if you target a different platform or want GPU
builds, use the selector on https://pytorch.org to adjust the command.

You can also use the helper script to install requirements and download all
SadTalker checkpoints, GFPGAN weights, and Piper voice models in one go:

```bash
python setup.py
```

Or run only specific steps:

```bash
python setup.py --requirements-only  # just pip install -r requirements.txt
python setup.py --models-only        # download model files + Piper voices
python setup.py --verify             # check that files exist
```

## Quickstart (interactive)

```bash
python main.py
```

Workflow:

1. Type a message and press Enter
2. Choose a Piper voice (press Enter to use the default)
3. Choose SadTalker settings (press Enter to use defaults)
4. The result is written under `results/<uuid>/<timestamp>.mp4`

## Script usage (SadTalker only)

```bash
python -m src.inference \
  --driven_audio /path/to/audio.wav \
  --source_image /path/to/image.png \
  --result_dir ./results \
  --save_dir ./results/run-1/2025_12_18_12.00.00 \
  --size 256 \
  --batch_size 1 \
  --preprocess crop \
  --enhancer gfpgan  # optional, requires GFPGAN weights
```

For backwards compatibility, `python inference.py ...` also works (shim).

This writes the output video into the results/ directory.

`--save_dir` is optional; when provided, it forces SadTalker to write all intermediate files into that exact folder.
This is used by `main.py` so the generated `piper.wav` is co-located with the run intermediates and gets cleaned up.

## Configuration

Defaults live in `config.py` and can be overridden via a `.env` file or changed in the file itself.

Key settings:

- `AVATAR_FACE` (default: `models/avatar.jpg`)
- `PIPER_VOICES_DIR` (default: `models/voices`)
- `PIPER_VOICE_MALE`, `PIPER_VOICE_FEMALE`, `PIPER_VOICE_DEFAULT`
- `SADTALKER_PREPROCESS_DEFAULT` (`crop|full|extfull`)
- `SADTALKER_SIZE_DEFAULT` (`256|512`)
- `SADTALKER_BATCH_SIZE_DEFAULT` (recommended `1`)
- `SADTALKER_ENHANCER_DEFAULT` (empty or `gfpgan`)

Example `.env`:

```bash
AVATAR_FACE=models/avatar.jpg
PIPER_VOICE_DEFAULT=models/voices/dii_pt-PT.onnx
SADTALKER_PREPROCESS_DEFAULT=crop
SADTALKER_SIZE_DEFAULT=256
SADTALKER_ENHANCER_DEFAULT=
```

## Integrating into another project

For a Flask / chatbot or other backend service:

- Treat this repo as a local package: pip install -e . inside your main project venv.
- Mirror the logic in `src/inference.py` inside your own service layer, or wrap it in a small helper that returns the generated video path.
- Ensure the models/checkpoints/ directory is available in your deployed environment and points to the correct model weights.

At runtime you generally:

1. Save the user image and audio to disk.
2. Call the inference script (directly, via main.py, or via a thin Python wrapper) with those paths and a result_dir you control.
3. Return the resulting mp4 path or URL from your Flask API so your chatbot can display or link it.

If you install this repo into another project with pip install -e ., you can
import the modules directly (e.g. import src.utils.preprocess) and build a
generate_talking_video(...) helper in that project that mirrors what
`src/inference.py` does.

### Windows notes

On Windows, inside a venv, you can run:

```powershell
python -m venv .venv
.\.venv\Scripts\activate

# Install PyTorch for your CPU/GPU from pytorch.org
pip install "torch==1.12.1" "torchvision==0.13.1" "torchaudio==0.12.1" `
  --extra-index-url https://download.pytorch.org/whl/cpu

pip install -r requirements.txt
python setup.py --models-only
python main.py
```

If you see compiler errors when installing basicsr or similar packages, install Build Tools for Visual Studio first so you have a working C/C++ toolchain.

### Troubleshooting

- If basicsr or gfpgan fail to install with wheel warnings, upgrade pip/setuptools/wheel in your venv and retry.
- If you see ModuleNotFoundError for torchvision.transforms.functional_tensor, pin torch/torchvision to 1.12.1 / 0.13.1 as in the README install example.
- On Apple Silicon (M1/M2), use a PyTorch build with MPS support so the heavy steps can run on the GPU instead of CPU.
- If `piper` is not found, ensure your venv is activated and `piper-tts` is installed; the CLI should be available as `piper`.
