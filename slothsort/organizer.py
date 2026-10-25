"""
File organization, renaming, conflict resolution, and undo logging.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from slothsort.categorizer import CategorizationResult
from slothsort.config import UNDO_LOG_FILENAME


@dataclass
class PlannedAction:
    """Represents a planned file move and rename operation."""

    source_path: Path
    dest_path: Path
    category: str
    original_name: str
    target_name: str
    reason: str
    source_type: str  # "ai" or "fallback"

    @property
    def is_renamed(self) -> bool:
        return self.original_name != self.target_name

    @property
    def is_moved(self) -> bool:
        return self.source_path.resolve() != self.dest_path.resolve()


def resolve_destination_path(
    category_dir: Path,
    desired_name: str,
    reserved_paths: set[Path],
) -> Path:
    """
    Resolve destination path ensuring no collisions with existing files or earlier batch targets.
    Appends numeric suffix -1, -2, etc. when collisions occur.
    """
    stem = Path(desired_name).stem
    suffix = Path(desired_name).suffix
    candidate = category_dir / desired_name

    counter = 1
    while candidate.exists() or candidate in reserved_paths:
        candidate = category_dir / f"{stem}-{counter}{suffix}"
        counter += 1

    reserved_paths.add(candidate)
    return candidate


def plan_organization(
    results: list[CategorizationResult],
    dest_dir: Path,
) -> list[PlannedAction]:
    """
    Generate an actionable plan mapping every file to its target category and path.
    """
    dest_path = Path(dest_dir).expanduser().resolve()
    planned_actions: list[PlannedAction] = []
    reserved_paths: set[Path] = set()

    for item in results:
        cat_dir = dest_path / item.category
        final_dest = resolve_destination_path(
            category_dir=cat_dir,
            desired_name=item.new_name,
            reserved_paths=reserved_paths,
        )

        planned_actions.append(
            PlannedAction(
                source_path=item.file_entry.path,
                dest_path=final_dest,
                category=item.category,
                original_name=item.file_entry.name,
                target_name=final_dest.name,
                reason=item.reason,
                source_type=item.source,
            )
        )

    return planned_actions


def execute_organization(
    plan: list[PlannedAction],
    dest_dir: Path,
) -> tuple[int, Path]:
    """
    Execute file moves according to the plan and write an atomic undo log.

    Returns:
        A tuple of (number of files moved, path to undo log).
    """
    dest_path = Path(dest_dir).expanduser().resolve()
    dest_path.mkdir(parents=True, exist_ok=True)
    undo_entries: list[dict[str, str]] = []
    moved_count = 0

    for action in plan:
        if not action.is_moved:
            continue

        # Ensure category folder exists
        action.dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Move file safely
        shutil.move(str(action.source_path), str(action.dest_path))
        moved_count += 1

        undo_entries.append(
            {
                "from": str(action.source_path.resolve()),
                "to": str(action.dest_path.resolve()),
            }
        )

    # Write undo log atomically
    undo_file = dest_path / UNDO_LOG_FILENAME
    temp_dir = dest_path
    with tempfile.NamedTemporaryFile("w", dir=temp_dir, delete=False, encoding="utf-8") as tf:
        json.dump(undo_entries, tf, indent=2, ensure_ascii=False)
        temp_file_path = Path(tf.name)

    # Replace undo log atomically
    if undo_file.exists():
        undo_file.unlink()
    temp_file_path.rename(undo_file)

    return moved_count, undo_file


def execute_undo(target_dir: Path) -> tuple[int, list[str]]:
    """
    Reverses the last organization run using the undo log.

    Returns:
        Tuple of (count of files reverted, list of any warnings/skipped files).
    """
    target_path = Path(target_dir).expanduser().resolve()
    undo_file = target_path / UNDO_LOG_FILENAME

    if not undo_file.exists():
        raise FileNotFoundError(f"No undo log found at: {undo_file}")

    with open(undo_file, "r", encoding="utf-8") as f:
        entries: list[dict[str, str]] = json.load(f)

    reverted_count = 0
    warnings: list[str] = []

    # Reverse in opposite order
    for entry in reversed(entries):
        src = Path(entry["to"])
        dst = Path(entry["from"])

        if not src.exists():
            warnings.append(f"Source file missing, cannot restore: {src}")
            continue

        dst.parent.mkdir(parents=True, exist_ok=True)

        # If destination was recreated in the meantime, add suffix
        if dst.exists() and dst.resolve() != src.resolve():
            stem = dst.stem
            suffix = dst.suffix
            counter = 1
            while dst.exists():
                dst = dst.parent / f"{stem}-restored-{counter}{suffix}"
                counter += 1

        shutil.move(str(src), str(dst))
        reverted_count += 1

    # Clean up empty category directories if they exist in target_path
    for item in target_path.iterdir():
        if item.is_dir() and not item.name.startswith("."):
            try:
                # Remove if empty
                item.rmdir()
            except OSError:
                pass

    # Remove the undo log after successful restoration
    try:
        undo_file.unlink()
    except OSError:
        pass

    return reverted_count, warnings
