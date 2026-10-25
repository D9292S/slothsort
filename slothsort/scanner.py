"""
Directory scanning, file metadata extraction, and safe content previewing.
"""

from __future__ import annotations

import fnmatch
import hashlib
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel, Field

from slothsort.config import UNDO_LOG_FILENAME

# System files to automatically ignore
IGNORED_SYSTEM_NAMES = {
    "desktop.ini",
    "thumbs.db",
    ".ds_store",
    "icon\r",
    "$recycle.bin",
}

TEXT_SNIPPET_EXTENSIONS = {
    ".txt",
    ".md",
    ".markdown",
    ".csv",
    ".tsv",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".py",
    ".js",
    ".ts",
    ".sh",
    ".html",
    ".xml",
    ".sql",
}


class FileEntry(BaseModel):
    """Metadata for a scanned file."""

    path: Path
    name: str
    extension: str
    size_bytes: int = Field(ge=0)
    modified: datetime
    snippet: str | None = None
    duplicate_of: Path | None = None

    @property
    def is_duplicate(self) -> bool:
        return self.duplicate_of is not None

    @property
    def size_formatted(self) -> str:
        """Return human-readable file size."""
        bytes_val = float(self.size_bytes)
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if bytes_val < 1024.0:
                return f"{bytes_val:.1f} {unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.1f} PB"

    @property
    def size_mb(self) -> float:
        """Return file size in megabytes."""
        return self.size_bytes / (1024 * 1024)

    model_config = {
        "arbitrary_types_allowed": True,
    }


def should_skip_file(path: Path, ignore_patterns: list[str] | None = None) -> bool:
    """Determine whether a file should be skipped during scan."""
    filename = path.name

    # Skip hidden files and dotfiles
    if filename.startswith("."):
        return True

    # Skip undo log specifically
    if filename == UNDO_LOG_FILENAME:
        return True

    # Skip known system clutter
    if filename.lower() in IGNORED_SYSTEM_NAMES:
        return True

    # Check against user ignore patterns
    if ignore_patterns:
        for pattern in ignore_patterns:
            if fnmatch.fnmatch(filename, pattern) or fnmatch.fnmatch(str(path), pattern):
                return True

    try:
        stat_result = path.stat()
        # Skip zero-byte files
        if stat_result.st_size == 0:
            return True
    except (OSError, PermissionError):
        return True

    return False


def extract_content_snippet(path: Path, max_chars: int = 300) -> str | None:
    """Safely read a short snippet from small text-based files to give LLM grounded context."""
    ext = path.suffix.lower()
    if ext not in TEXT_SNIPPET_EXTENSIONS:
        return None

    try:
        # Avoid reading large files for snippets
        if path.stat().st_size > 2 * 1024 * 1024:  # > 2MB
            return None

        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            chunk = f.read(max_chars).strip()
            if not chunk:
                return None
            # Normalize whitespace/newlines into a compact single-line preview
            return " ".join(chunk.split())
    except Exception:
        return None


def compute_file_hash(path: Path, max_bytes: int = 10 * 1024 * 1024) -> str:
    """Compute quick SHA-256 hash of a file for duplicate matching."""
    hasher = hashlib.sha256()
    bytes_read = 0
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
            bytes_read += len(chunk)
            if bytes_read >= max_bytes:
                break
    return hasher.hexdigest()


def detect_duplicates(entries: list[FileEntry]) -> list[FileEntry]:
    """
    Find duplicate files based on size matching and cryptographic hashing.
    Marks duplicates with reference to the original file.
    """
    # Group by file size first
    size_map: dict[int, list[FileEntry]] = {}
    for e in entries:
        if e.size_bytes > 0:
            size_map.setdefault(e.size_bytes, []).append(e)

    # For sizes with multiple files, compare hashes
    for size, candidates in size_map.items():
        if len(candidates) < 2:
            continue

        seen_hashes: dict[str, Path] = {}
        for candidate in candidates:
            try:
                f_hash = compute_file_hash(candidate.path)
                if f_hash in seen_hashes:
                    candidate.duplicate_of = seen_hashes[f_hash]
                else:
                    seen_hashes[f_hash] = candidate.path
            except (OSError, PermissionError):
                continue

    return entries


def scan_directory(
    source_dir: Path,
    recursive: bool = False,
    peek_content: bool = True,
    dedupe: bool = False,
    ignore_patterns: list[str] | None = None,
    verbose: bool = False,
) -> list[FileEntry]:
    """
    Scan the target directory and collect valid file entries.

    Args:
        source_dir: Directory path to scan.
        recursive: Whether to scan child directories recursively.
        peek_content: Whether to extract short text snippets for richer context.
        ignore_patterns: Glob patterns of files to ignore.
        verbose: Output detailed scanning info if true.

    Returns:
        A list of FileEntry instances.
    """
    source_path = Path(source_dir).expanduser().resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"Source directory does not exist: {source_path}")
    if not source_path.is_dir():
        raise NotADirectoryError(f"Source path is not a directory: {source_path}")

    entries: list[FileEntry] = []

    if recursive:
        iterator = source_path.rglob("*")
    else:
        iterator = source_path.glob("*")

    for item in iterator:
        try:
            if not item.is_file():
                continue

            if should_skip_file(item, ignore_patterns=ignore_patterns):
                continue

            stat_info = item.stat()
            mod_dt = datetime.fromtimestamp(stat_info.st_mtime)

            snippet = extract_content_snippet(item) if peek_content else None

            entry = FileEntry(
                path=item,
                name=item.name,
                extension=item.suffix.lower(),
                size_bytes=stat_info.st_size,
                modified=mod_dt,
                snippet=snippet,
            )
            entries.append(entry)
        except (PermissionError, OSError):
            continue

    # Return sorted by filename
    entries.sort(key=lambda e: e.name.lower())

    # Detect duplicates if requested
    if dedupe:
        detect_duplicates(entries)

    return entries
