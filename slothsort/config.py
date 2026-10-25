"""
Configuration, constants, and user overrides for SlothSort.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

# Python 3.11+ has built-in tomllib
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        tomllib = None  # type: ignore

# Standard category taxonomy with purpose descriptions
DEFAULT_CATEGORIES: dict[str, str] = {
    "Documents": "PDFs, Word docs, spreadsheets, slides, text files, eBooks",
    "Images": "Photos, screenshots, graphics, icons, wallpapers",
    "Videos": "Movies, screen recordings, clips, animations",
    "Audio": "Music, podcasts, voice memos, sound effects",
    "Code": "Source code, scripts, notebooks, config files, repos",
    "Archives": "ZIPs, tarballs, RARs, 7z, disk images",
    "Installers": "EXE, MSI, MSIX, DMG, DEB, AppImage, setup packages",
    "Data": "CSVs, JSON, XML, SQL dumps, databases, datasets",
    "Design": "Figma exports, Sketch files, PSDs, SVGs, 3D models",
    "Duplicates": "Identical copies of files already present in the folder",
    "Misc": "Anything that does not fit the other categories",
}

# Extension-based mapping for fallback and ultra-large files
EXTENSION_MAP: dict[str, str] = {
    # Documents
    ".pdf": "Documents",
    ".doc": "Documents",
    ".docx": "Documents",
    ".odt": "Documents",
    ".rtf": "Documents",
    ".tex": "Documents",
    ".txt": "Documents",
    ".md": "Documents",
    ".epub": "Documents",
    ".mobi": "Documents",
    ".xls": "Documents",
    ".xlsx": "Documents",
    ".ods": "Documents",
    ".ppt": "Documents",
    ".pptx": "Documents",
    ".odp": "Documents",
    # Images
    ".png": "Images",
    ".jpg": "Images",
    ".jpeg": "Images",
    ".gif": "Images",
    ".bmp": "Images",
    ".webp": "Images",
    ".tiff": "Images",
    ".raw": "Images",
    ".ico": "Images",
    ".heic": "Images",
    # Videos
    ".mp4": "Videos",
    ".mkv": "Videos",
    ".mov": "Videos",
    ".avi": "Videos",
    ".wmv": "Videos",
    ".flv": "Videos",
    ".webm": "Videos",
    ".m4v": "Videos",
    # Audio
    ".mp3": "Audio",
    ".wav": "Audio",
    ".flac": "Audio",
    ".aac": "Audio",
    ".ogg": "Audio",
    ".m4a": "Audio",
    ".wma": "Audio",
    ".opus": "Audio",
    # Code
    ".py": "Code",
    ".js": "Code",
    ".ts": "Code",
    ".jsx": "Code",
    ".tsx": "Code",
    ".html": "Code",
    ".css": "Code",
    ".scss": "Code",
    ".java": "Code",
    ".c": "Code",
    ".cpp": "Code",
    ".h": "Code",
    ".cs": "Code",
    ".go": "Code",
    ".rs": "Code",
    ".php": "Code",
    ".rb": "Code",
    ".sh": "Code",
    ".bat": "Code",
    ".ps1": "Code",
    ".yaml": "Code",
    ".yml": "Code",
    ".toml": "Code",
    ".ini": "Code",
    ".ipynb": "Code",
    # Archives
    ".zip": "Archives",
    ".tar": "Archives",
    ".gz": "Archives",
    ".bz2": "Archives",
    ".7z": "Archives",
    ".rar": "Archives",
    ".xz": "Archives",
    ".iso": "Archives",
    ".tgz": "Archives",
    # Installers
    ".exe": "Installers",
    ".msi": "Installers",
    ".msix": "Installers",
    ".msu": "Installers",
    ".dmg": "Installers",
    ".pkg": "Installers",
    ".deb": "Installers",
    ".rpm": "Installers",
    ".appimage": "Installers",
    # Data
    ".csv": "Data",
    ".tsv": "Data",
    ".json": "Data",
    ".xml": "Data",
    ".sql": "Data",
    ".sqlite": "Data",
    ".db": "Data",
    ".parquet": "Data",
    # Design
    ".psd": "Design",
    ".ai": "Design",
    ".svg": "Design",
    ".fig": "Design",
    ".sketch": "Design",
    ".blend": "Design",
    ".obj": "Design",
    ".fbx": "Design",
    ".stl": "Design",
}

# LLM Defaults
DEFAULT_MODEL = "llama3.2"
FALLBACK_MODELS = ["mistral", "phi3", "gemma2"]
MAX_FILE_SIZE_MB = 500
UNDO_LOG_FILENAME = ".slothsort-undo.json"
CONFIG_FILE_NAME = ".slothsort.toml"


@dataclass
class SortConfig:
    """Runtime configuration for SlothSort operations."""

    source_dir: Path
    dest_dir: Path | None = None
    model: str = DEFAULT_MODEL
    dry_run: bool = True
    recursive: bool = False
    no_rename: bool = False
    interactive: bool = False
    peek_content: bool = True
    dedupe: bool = False
    watch: bool = False
    watch_interval: int = 60
    verbose: bool = False
    batch_size: int = 15
    categories: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_CATEGORIES))
    ignore_patterns: list[str] = field(default_factory=lambda: ["*.tmp", "*.crdownload", "*.part", "node_modules/*"])

    def __post_init__(self) -> None:
        self.source_dir = Path(self.source_dir).expanduser().resolve()
        if self.dest_dir is not None:
            self.dest_dir = Path(self.dest_dir).expanduser().resolve()
        else:
            self.dest_dir = self.source_dir


def load_user_config(config_path: Path | None = None) -> dict:
    """
    Look for .slothsort.toml in specified path, current directory, or user home directory.
    """
    candidates = []
    if config_path:
        candidates.append(Path(config_path).expanduser().resolve())
    candidates.append(Path.cwd() / CONFIG_FILE_NAME)
    candidates.append(Path.home() / CONFIG_FILE_NAME)
    candidates.append(Path.home() / ".config" / "slothsort" / "config.toml")

    if tomllib is None:
        return {}

    for path in candidates:
        if path.is_file():
            try:
                with open(path, "rb") as f:
                    return tomllib.load(f)
            except Exception:
                continue

    return {}
