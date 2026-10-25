import tempfile
from pathlib import Path
from slothsort.scanner import scan_directory, extract_content_snippet, compute_file_hash


def test_scan_and_skip():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        # Create valid files
        (tmp / "valid.txt").write_text("Hello world", encoding="utf-8")
        (tmp / "code.py").write_text("print('test')", encoding="utf-8")

        # Create files that should be skipped
        (tmp / ".hidden.txt").write_text("hidden", encoding="utf-8")
        (tmp / ".slothsort-undo.json").write_text("[]", encoding="utf-8")
        (tmp / "empty.pdf").write_bytes(b"")  # 0 bytes

        entries = scan_directory(tmp)
        names = [e.name for e in entries]

        assert "valid.txt" in names
        assert "code.py" in names
        assert ".hidden.txt" not in names
        assert ".slothsort-undo.json" not in names
        assert "empty.pdf" not in names


def test_content_snippet_extraction():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        sample = tmp / "meeting.txt"
        sample.write_text("Roadmap discussion with team regarding Q4 OKRs.", encoding="utf-8")

        snippet = extract_content_snippet(sample)
        assert snippet is not None
        assert "Roadmap discussion" in snippet


def test_duplicate_detection():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        content = "Identical duplicate file payload content."

        # Create identical files
        (tmp / "invoice.pdf").write_text(content, encoding="utf-8")
        (tmp / "invoice (1).pdf").write_text(content, encoding="utf-8")

        entries = scan_directory(tmp, dedupe=True)
        assert len(entries) == 2

        duplicates = [e for e in entries if e.is_duplicate]
        assert len(duplicates) == 1
        assert duplicates[0].duplicate_of is not None
