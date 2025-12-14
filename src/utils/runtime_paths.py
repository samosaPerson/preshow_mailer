import sys
from pathlib import Path
from typing import Optional


# Resolve the repository root when running from source; fall back to the
# executable directory when frozen (PyInstaller).
def _source_root() -> Path:
    return Path(__file__).resolve().parents[2]


def bundle_dir() -> Path:
    """
    Directory that contains bundled assets/templates.
    In frozen builds this points to the PyInstaller extraction dir (_MEIPASS),
    otherwise it is the repository root.
    """
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return _source_root()


def user_dir() -> Path:
    """
    User-facing directory where config/.env live.
    In frozen builds this is the folder beside the executable; otherwise the repo root.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return _source_root()


def default_config_dir() -> Path:
    """
    Prefer a top-level config directory beside the executable; fall back to bundled examples.
    """
    candidate = user_dir() / "config"
    if candidate.exists():
        return candidate
    return bundle_dir() / "data" / "examples"


def default_config_paths():
    """
    Return default theatre/show config file paths.
    """
    cfg_dir = default_config_dir()
    return cfg_dir / "theatre_config.yaml", cfg_dir / "show_info.json"


def env_file() -> Optional[Path]:
    """
    Return the .env path beside the executable (or repo root) if present.
    """
    candidate = user_dir() / ".env"
    return candidate if candidate.exists() else None


def assets_path() -> Path:
    """
    Locate the Dash assets directory (bundled or beside the executable).
    """
    bundled = bundle_dir() / "assets"
    if bundled.exists():
        return bundled
    return user_dir() / "assets"
