#!/usr/bin/env python3
"""SadTalker environment/setup helper (project root)

Run this from the project root (same folder as wsgi.py):

  python setup.py              # full setup (requirements + models + verify)
  python setup.py --requirements-only
  python setup.py --models-only
  python setup.py --verify

It installs Python requirements using the ROOT requirements.txt and
downloads all SadTalker/GFPGAN/Piper assets under:
  backoffice/app/video/models/
"""

import sys
import subprocess
import shutil
import os
from pathlib import Path
from typing import Iterable, Tuple, Optional
import urllib.request
import zipfile


class SadTalkerSetup:
    def __init__(self) -> None:
        # Project root (where wsgi.py and the main requirements.txt live)
        self.project_root = Path(__file__).resolve().parent

        # Embedded SadTalker app under backoffice/app/video
        self.video_root = self.project_root / "backoffice" / "app" / "video"
        models_root = self.video_root / "models"

        self.checkpoints_dir = models_root / "checkpoints"
        self.gfpgan_weights_dir = models_root / "gfpgan" / "weights"
        self.piper_voices_dir = models_root / "voices"

        # Vosk model location (used by STT service)
        self.vosk_models_dir = self.project_root / "backoffice" / "app" / "extras" / "models"
        self.vosk_model_dir = self.vosk_models_dir / "vosk-model-small-pt-0.3"

    # --- helpers ---------------------------------------------------------

    def print_header(self, title: str) -> None:
        bar = "=" * 60
        print(f"\n{bar}\n{title}\n{bar}")

    def run_command(self, cmd: str, description: Optional[str] = None) -> bool:
        if description:
            print(f"{description}...")
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
            )
            if result.stdout:
                print(result.stdout.strip())
            if result.returncode != 0:
                print(f"Command failed: {cmd}")
                if result.stderr:
                    print(result.stderr.strip())
                return False
            return True
        except Exception as exc:  # pragma: no cover - best effort helper
            print(f"Error running command '{cmd}': {exc}")
            return False

    # --- steps -----------------------------------------------------------

    def check_python_version(self) -> bool:
        v = sys.version_info
        print(f"Python version: {v.major}.{v.minor}.{v.micro}")

        if v.major != 3 or v.minor < 8:
            print("SadTalker requires Python 3.8+.")
            return False
        if v.minor > 10:
            print("Warning: Python 3.11+ may have compatibility issues with some deps.")
        return True

    def check_system_tools(self) -> None:
        """Check for required system tools like ffmpeg and warn if missing."""
        if shutil.which("ffmpeg") is None:
            print("Warning: ffmpeg not found in PATH. Video writing may fail.")
            print("         On macOS you can install it with: brew install ffmpeg")

    def install_requirements(self) -> bool:
        self.print_header("Installing Python requirements")

        # Always upgrade core ML stack to latest compatible versions
        print("Upgrading torch, torchvision, torchaudio, transformers, sentence-transformers, soxr...")
        upgrade_cmd = (
            "pip install --upgrade torch torchvision torchaudio transformers sentence-transformers soxr"
        )
        if not self.run_command(upgrade_cmd, "Upgrading core ML stack"):
            print("Failed to upgrade core ML stack. Aborting requirements install.")
            return False

        # Use the main backoffice requirements (where you moved them)
        req_file = self.project_root / "backoffice" / "requirements.txt"
        if not req_file.exists():
            print(f"requirements.txt not found at {req_file}")
            return False

        ok = self.run_command("pip install -r backoffice/requirements.txt", "Installing requirements")
        if ok:
            print("Requirements installed successfully.")
            self.patch_gfpgan_paths()
            self.patch_functional_tensor_imports()
        return ok

    def patch_gfpgan_paths(self) -> None:
        """Best-effort patch of gfpgan.utils to honor models/ layout.

        This edits the installed gfpgan package so that FaceRestoreHelper
        uses models/gfpgan/weights as its model_rootpath (relative to the
        process cwd, which for SadTalker is the video app directory).
        """
        try:
            import importlib

            gfpgan_spec = importlib.util.find_spec("gfpgan")
            if gfpgan_spec is None or not gfpgan_spec.origin:
                return

            utils_path = Path(gfpgan_spec.origin).with_name("utils.py")
            if not utils_path.exists():
                return

            text = utils_path.read_text(encoding="utf-8")
            old = "model_rootpath='gfpgan/weights'"
            new = "model_rootpath='models/gfpgan/weights'"
            if old not in text:
                return

            utils_path.write_text(text.replace(old, new), encoding="utf-8")
            print(f"Patched gfpgan utils to use models/gfpgan/weights: {utils_path}")
        except Exception as exc:
            print(f"Warning: could not patch gfpgan paths automatically: {exc}")

    def patch_functional_tensor_imports(self) -> None:
        """Patch dependências que usam functional_tensor para usar functional."""
        import os
        import sys
        site_packages = next(p for p in sys.path if "site-packages" in p)
        targets = [
            "basicsr/data/degradations.py",
            # outros paths comuns onde isto aparece
            "realesrgan/data/degradations.py",
        ]
        for rel_path in targets:
            full_path = os.path.join(site_packages, rel_path)
            if not os.path.exists(full_path):
                print(f"[patch-functional-tensor] {full_path} não encontrado, ignorando.")
                continue
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            new_content = content
            # robust: swap any reference to torchvision.transforms.functional_tensor -> functional
            new_content = new_content.replace(
                "torchvision.transforms.functional_tensor",
                "torchvision.transforms.functional",
            )
            new_content = new_content.replace(
                "from torchvision.transforms import functional_tensor",
                "from torchvision.transforms import functional",
            )
            new_content = new_content.replace(
                "import torchvision.transforms.functional_tensor as",
                "import torchvision.transforms.functional as",
            )
            if new_content != content:
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"[patch-functional-tensor] Corrigido: {full_path}")
            else:
                print(f"[patch-functional-tensor] Nenhuma alteração: {full_path}")

    def _download_file(self, url: str, dest: Path) -> bool:
        dest.parent.mkdir(parents=True, exist_ok=True)

        if dest.exists():
            size_mb = dest.stat().st_size // (1024 * 1024)
            print(f"Already exists ({size_mb} MB): {dest}")
            return True

        print(f"Downloading:\n  URL : {url}\n  Dest: {dest}")
        try:
            with urllib.request.urlopen(url) as resp:
                total = resp.length or 0
                downloaded = 0
                chunk_size = 8192

                with open(dest, "wb") as f:
                    while True:
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total:
                            percent = downloaded * 100.0 / total
                            bar_len = 30
                            filled = int(bar_len * percent / 100.0)
                            bar = "#" * filled + "-" * (bar_len - filled)
                            print(f"\r  [{bar}] {percent:5.1f}%", end="", flush=True)
                if total:
                    print()
        except Exception as exc:
            print(f"Failed to download {url}: {exc}")
            if dest.exists():
                try:
                    dest.unlink()
                except OSError:
                    pass
            return False

        size_mb = dest.stat().st_size // (1024 * 1024)
        print(f"Downloaded {dest} ({size_mb} MB)")
        return True

    def download_models(self) -> bool:
        self.print_header("Downloading SadTalker checkpoints and enhancer weights")

        checkpoint_urls: Iterable[Tuple[str, Path]] = [
            (
                "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/mapping_00109-model.pth.tar",
                self.checkpoints_dir / "mapping_00109-model.pth.tar",
            ),
            (
                "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/mapping_00229-model.pth.tar",
                self.checkpoints_dir / "mapping_00229-model.pth.tar",
            ),
            (
                "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/SadTalker_V0.0.2_256.safetensors",
                self.checkpoints_dir / "SadTalker_V0.0.2_256.safetensors",
            ),
            (
                "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/SadTalker_V0.0.2_512.safetensors",
                self.checkpoints_dir / "SadTalker_V0.0.2_512.safetensors",
            ),
        ]

        enhancer_urls: Iterable[Tuple[str, Path]] = [
            (
                "https://github.com/xinntao/facexlib/releases/download/v0.1.0/alignment_WFLW_4HG.pth",
                self.gfpgan_weights_dir / "alignment_WFLW_4HG.pth",
            ),
            (
                "https://github.com/xinntao/facexlib/releases/download/v0.1.0/detection_Resnet50_Final.pth",
                self.gfpgan_weights_dir / "detection_Resnet50_Final.pth",
            ),
            (
                "https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth",
                self.gfpgan_weights_dir / "GFPGANv1.4.pth",
            ),
            (
                "https://github.com/xinntao/facexlib/releases/download/v0.2.2/parsing_parsenet.pth",
                self.gfpgan_weights_dir / "parsing_parsenet.pth",
            ),
        ]

        all_ok = True
        for url, dest in list(checkpoint_urls) + list(enhancer_urls):
            if not self._download_file(url, dest):
                all_ok = False

        if all_ok:
            print("All model files downloaded or already present.")
        else:
            print("Some model files failed to download. See messages above.")
        return all_ok

    def download_piper_voices(self) -> bool:
        """Download Piper voice models into models/voices under video app."""

        self.print_header("Downloading Piper voice models")

        voices_dir = self.piper_voices_dir
        voices_dir.mkdir(parents=True, exist_ok=True)

        tuga_onnx = voices_dir / "pt_PT-tugao-medium.onnx"
        tuga_json = voices_dir / "pt_PT-tugao-medium.onnx.json"
        dii_onnx = voices_dir / "dii_pt-PT.onnx"
        dii_json = voices_dir / "dii_pt-PT.onnx.json"

        if all(p.exists() for p in [tuga_onnx, tuga_json, dii_onnx, dii_json]):
            print("Piper voice models already present (Tuga + Dii).")
            return True

        tuga_onnx_url = (
            "https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_PT/"
            "tug%C3%A3o/medium/pt_PT-tug%C3%A3o-medium.onnx"
        )
        tuga_json_url = (
            "https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_PT/"
            "tug%C3%A3o/medium/pt_PT-tug%C3%A3o-medium.onnx.json"
        )
        dii_onnx_url = (
            "https://huggingface.co/OpenVoiceOS/phoonnx_pt-PT_dii_tugaphone/resolve/main/"
            "dii_pt-PT.onnx?download=true"
        )

        ok = True
        if not self._download_file(tuga_onnx_url, tuga_onnx):
            ok = False
        if not self._download_file(tuga_json_url, tuga_json):
            ok = False
        if not self._download_file(dii_onnx_url, dii_onnx):
            ok = False

        if tuga_json.exists() and not dii_json.exists():
            try:
                dii_json.write_bytes(tuga_json.read_bytes())
                print(f"Copied {tuga_json.name} to {dii_json.name}")
            except Exception as exc:
                print(f"Warning: could not copy {tuga_json.name} to {dii_json.name}: {exc}")
                ok = False

        if ok and all(p.exists() for p in [tuga_onnx, tuga_json, dii_onnx, dii_json]):
            print("Piper voice models downloaded successfully.")
            return True

        print("Some Piper voice files are missing. You can retry with: python setup.py --models-only")
        print(f"Expected directory: {voices_dir}")
        return False

    def download_vosk_model(self) -> bool:
        """Download and extract the Vosk Portuguese small model (pt) if missing."""

        self.print_header("Downloading Vosk model (pt) for STT")

        # Allow override via env (useful for mirrors/offline)
        default_url = "https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip"
        url = os.environ.get("VOSK_MODEL_URL", default_url)

        # Quick success path
        expected_file = self.vosk_model_dir / "README"
        if self.vosk_model_dir.exists() and expected_file.exists():
            print(f"Vosk model already present: {self.vosk_model_dir}")
            return True

        self.vosk_models_dir.mkdir(parents=True, exist_ok=True)
        zip_path = self.vosk_models_dir / "vosk-model-small-pt-0.3.zip"

        if not self._download_file(url, zip_path):
            return False

        try:
            print(f"Extracting: {zip_path} -> {self.vosk_models_dir}")
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(self.vosk_models_dir)
        except Exception as exc:
            print(f"Failed to extract Vosk model zip: {exc}")
            return False
        finally:
            try:
                zip_path.unlink()
            except Exception:
                pass

        if self.vosk_model_dir.exists():
            print(f"Vosk model ready: {self.vosk_model_dir}")
            return True

        print(f"Vosk model directory not found after extract: {self.vosk_model_dir}")
        return False

    def verify_setup(self) -> bool:
        self.print_header("Verifying SadTalker setup")

        required_paths = [
            ("requirements.txt", self.project_root / "backoffice" / "requirements.txt"),
            ("models/checkpoints directory", self.checkpoints_dir),
            ("models/gfpgan/weights directory", self.gfpgan_weights_dir),
            ("models/voices directory", self.piper_voices_dir),
            ("vosk model directory", self.vosk_model_dir),
        ]

        ok = True
        for name, path in required_paths:
            if path.exists():
                print(f"✅ {name}: {path}")
            else:
                print(f"❌ {name} missing: {path}")
                ok = False

        key_files = [
            self.checkpoints_dir / "SadTalker_V0.0.2_256.safetensors",
            self.checkpoints_dir / "SadTalker_V0.0.2_512.safetensors",
            self.gfpgan_weights_dir / "GFPGANv1.4.pth",
            self.piper_voices_dir / "pt_PT-tugao-medium.onnx",
            self.piper_voices_dir / "pt_PT-tugao-medium.onnx.json",
            self.piper_voices_dir / "dii_pt-PT.onnx",
            self.piper_voices_dir / "dii_pt-PT.onnx.json",
        ]
        for f in key_files:
            label = f.name
            if f.exists():
                size_mb = f.stat().st_size // (1024 * 1024)
                print(f"✅ {label} ({size_mb} MB)")
            else:
                print(f"❌ {label} not found at {f}")
                ok = False

        return ok

    def run_complete_setup(self) -> bool:
        print("SadTalker COMPLETE SETUP (project root)")
        print("=" * 60)

        if not self.check_python_version():
            return False

        self.check_system_tools()

        if not self.install_requirements():
            print("Failed to install Python requirements.")
            return False

        self.download_models()
        self.download_piper_voices()
        self.download_vosk_model()
        all_good = self.verify_setup()

        self.print_header("Setup summary")
        if all_good:
            print("SadTalker setup looks good. You can now run video generation.")
        else:
            print("Setup is partial. See missing items above.")
        return all_good


def main() -> None:
    setup = SadTalkerSetup()

    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "--requirements-only":
            setup.install_requirements()
        elif arg == "--models-only":
            setup.download_models()
            setup.download_piper_voices()
        elif arg == "--verify":
            setup.verify_setup()
        elif arg == "--patch-only":
            setup.patch_functional_tensor_imports()
        elif arg == "--vosk-only":
            setup.download_vosk_model()
        else:
            print("Usage: python setup.py [--requirements-only|--models-only|--vosk-only|--verify|--patch-only]")
    else:
        setup.run_complete_setup()


if __name__ == "__main__":
    main()
