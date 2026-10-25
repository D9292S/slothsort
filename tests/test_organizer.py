import tempfile
from pathlib import Path
from slothsort.categorizer import CategorizationResult
from slothsort.organizer import plan_organization, execute_organization, execute_undo
from slothsort.scanner import FileEntry
from datetime import datetime


def test_conflict_resolution():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        cat_dir = tmp / "Documents"
        cat_dir.mkdir()

        # Pre-create existing file
        (cat_dir / "report.pdf").write_text("existing", encoding="utf-8")

        f1 = tmp / "src_report.pdf"
        f1.write_text("new", encoding="utf-8")

        entry = FileEntry(
            path=f1,
            name="src_report.pdf",
            extension=".pdf",
            size_bytes=10,
            modified=datetime.now(),
        )

        res = [
            CategorizationResult(
                file_entry=entry,
                category="Documents",
                new_name="report.pdf",
                source="fallback",
            )
        ]

        plan = plan_organization(res, tmp)
        assert len(plan) == 1
        # Should resolve collision with suffix -1
        assert plan[0].target_name == "report-1.pdf"


def test_execute_and_undo_e2e():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        f1 = tmp / "notes.txt"
        f1.write_text("notes content", encoding="utf-8")

        entry = FileEntry(
            path=f1,
            name="notes.txt",
            extension=".txt",
            size_bytes=13,
            modified=datetime.now(),
        )

        res = [
            CategorizationResult(
                file_entry=entry,
                category="Documents",
                new_name="meeting-notes.txt",
                source="fallback",
            )
        ]

        plan = plan_organization(res, tmp)
        moved_count, undo_log = execute_organization(plan, tmp)

        assert moved_count == 1
        assert not f1.exists()
        assert (tmp / "Documents" / "meeting-notes.txt").exists()
        assert undo_log.exists()

        # Test Undo
        reverted, warnings = execute_undo(tmp)
        assert reverted == 1
        assert f1.exists()
        assert not (tmp / "Documents" / "meeting-notes.txt").exists()
        assert not (tmp / "Documents").exists()  # empty dir cleaned up
