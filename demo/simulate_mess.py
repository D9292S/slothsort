"""
Demo Helper Script for SlothSort 🦥
Creates a realistic, messy directory of ~30 dummy files for testing and showcasing the tool.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure UTF-8 output encoding on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SAMPLE_MESSY_FILES: list[tuple[str, str]] = [
    # Images & Screenshots
    ("IMG_20241019_142356.jpg", "JPEG image dummy binary data"),
    ("IMG_20241020_083211.jpg", "JPEG image dummy binary data"),
    ("Screenshot 2024-10-15 at 3.42.17 PM.png", "PNG screenshot mockup content"),
    ("photo_edited_v2_final.png", "PNG photo data"),
    ("wallpaper_4k_mountain.jpg", "JPEG mountain wallpaper"),
    ("logo_sketch_export.svg", "<svg><circle cx='50' cy='50' r='40'/></svg>"),
    # Documents
    ("document(1).pdf", "%PDF-1.4 dummy document binary header"),
    ("document(2).pdf", "%PDF-1.4 dummy document binary header"),
    ("final_report_FINAL_v3_USETHISONE.docx", "Word document binary package"),
    ("quarterly_taxes_2024_draft.pdf", "%PDF-1.4 tax document dummy"),
    ("meeting_notes_oct.txt", "1. Sloth day celebration\n2. AI model benchmarking\n3. Cleanup"),
    ("resume_updated_2024.docx", "Resume binary format"),
    ("budget_forecast_q4.xlsx", "Excel spreadsheet binary contents"),
    # Code & Scripts
    ("untitled.py", "def main():\n    print('Hello world!')\n"),
    ("scratch_test_api.py", "import requests\nprint('Testing local api...')\n"),
    ("docker-compose.yaml", "version: '3.8'\nservices:\n  app:\n    image: python:3.11\n"),
    ("quick_fix.sh", "#!/bin/bash\necho 'Running quick fix script'\n"),
    ("index.html", "<!DOCTYPE html><html><body><h1>Demo</h1></body></html>"),
    # Data
    ("random_data_export.csv", "id,name,role\n1,Alice,Dev\n2,Bob,Sloth\n"),
    ("customers_dump.json", '{"users": [{"id": 1, "status": "active"}]}\n'),
    ("analytics_october_metrics.csv", "date,visitors,conversions\n2024-10-01,1200,45\n"),
    ("database_backup.sql", "CREATE TABLE users (id INT PRIMARY KEY);\n"),
    # Archives
    ("backup.tar.gz", "Tar gzip archive compressed stream"),
    ("old_photos_2023.zip", "PK Zip binary archive file dummy"),
    ("project_assets_bundle.7z", "7z archive binary stream"),
    # Audio & Video
    ("song (copy).mp3", "ID3 MP3 audio stream dummy data"),
    ("zoom_recording_weekly_sync.mp4", "MP4 video movie stream dummy"),
    ("voice_memo_idea.m4a", "M4A audio recording stream"),
    # Installers
    ("setup_installer_x64.exe", "MZ PE32 Windows executable setup dummy"),
    ("VSCodeUserSetup-x64-1.92.0.exe", "MZ PE32 VS Code installer binary"),
    # Design
    ("hero_banner_mockup.psd", "Adobe Photoshop document dummy file"),
]


def create_messy_folder(target_dir: Path) -> Path:
    """Populate a directory with realistic messy dummy files."""
    dest = target_dir.expanduser().resolve()
    dest.mkdir(parents=True, exist_ok=True)

    print(f"🦥 Generating demo mess in: {dest}")

    for filename, content in SAMPLE_MESSY_FILES:
        file_path = dest / filename
        file_path.write_text(content, encoding="utf-8")

    print(f"✨ Created {len(SAMPLE_MESSY_FILES)} messy files successfully!")
    print(f"\nTry running:\n  slothsort \"{dest}\"")
    return dest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a realistic messy directory for testing SlothSort."
    )
    parser.add_argument(
        "--target",
        "-t",
        default="demo_mess",
        help="Target folder path (default: demo_mess)",
    )
    args = parser.parse_args()

    create_messy_folder(Path(args.target))


if __name__ == "__main__":
    main()
