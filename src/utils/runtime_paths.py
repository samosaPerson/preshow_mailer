import sys
from pathlib import Path
from typing import Iterable, Optional


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


def _candidate_roots() -> Iterable[Path]:
    """
    Search roots for user-provided files when frozen:
    - Executable directory
    - Its parent chain (captures ../.. to reach the dist folder when inside a .app)
    - Bundled dir (PyInstaller _MEIPASS)
    """
    if getattr(sys, "frozen", False):
        exec_path = Path(sys.executable).resolve()
        roots = [exec_path.parent] + list(exec_path.parents)
    else:
        roots = [_source_root()]

    roots.append(bundle_dir())

    seen = set()
    for root in roots:
        if root in seen:
            continue
        seen.add(root)
        yield root


def _find_nearby(target: str, is_dir: bool = False) -> Optional[Path]:
    for root in _candidate_roots():
        candidate = root / target
        if is_dir and candidate.is_dir():
            return candidate
        if not is_dir and candidate.is_file():
            return candidate
    return None


def default_config_dir() -> Path:
    """
    Prefer a top-level config directory near the executable (.app parent included);
    fall back to bundled examples.
    """
    candidate = _find_nearby("config", is_dir=True)
    if candidate:
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
    Return the nearest .env (searches executable dir, its parents, then bundled root).
    """
    return _find_nearby(".env", is_dir=False)


def assets_path() -> Path:
    """
    Locate the Dash assets directory (bundled or beside the executable).
    """
    bundled = bundle_dir() / "assets"
    if bundled.exists():
        return bundled
    nearby = _find_nearby("assets", is_dir=True)
    if nearby:
        return nearby
    return user_dir() / "assets"
