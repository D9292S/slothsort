from pathlib import Path
from slothsort.categorizer import is_safe_rename


def test_safe_rename_clean_format():
    """Valid standardizations should be accepted."""
    batch = ["IMG_20241019.jpg", "Screenshot 2024.png"]
    assert is_safe_rename("IMG_20241019.jpg", "photo-20241019.jpg", batch) is True
    assert is_safe_rename("Screenshot 2024.png", "screenshot-2024.png", batch) is True


def test_reject_cross_contamination():
    """A file must not borrow software/subject names from another file in the batch."""
    batch = [
        "ABDownloadManager_1.11.1_windows_x64.exe",
        "bitdefender_windows_installer.exe",
        "BatteryChecker_Setup.exe",
    ]

    # Attempting to rename ABDownloadManager to bitdefender.exe should be blocked
    assert is_safe_rename(
        "ABDownloadManager_1.11.1_windows_x64.exe",
        "bitdefender.exe",
        batch,
    ) is False

    # Attempting to rename BatteryChecker to bitdefender.exe should be blocked
    assert is_safe_rename(
        "BatteryChecker_Setup.exe",
        "bitdefender-1.exe",
        batch,
    ) is False


def test_allow_app_name_preservation():
    """Legitimate kebab-case cleanup of an installer should be accepted."""
    batch = [
        "ABDownloadManager_1.11.1_windows_x64.exe",
        "bitdefender_windows_installer.exe",
    ]
    assert is_safe_rename(
        "ABDownloadManager_1.11.1_windows_x64.exe",
        "ab-download-manager-1.11.1.exe",
        batch,
    ) is True
