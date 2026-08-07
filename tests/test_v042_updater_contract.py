from pathlib import Path
from unittest import mock
import io

import pytest

from tiny_rogues_tracker import __version__
from tiny_rogues_tracker import updater

ROOT = Path(__file__).resolve().parents[1]


def release(tag="v0.4.4", draft=False, prerelease=False, assets=None, body="## Fixes\nWorking auto-update"):
    return {
        "tag_name": tag,
        "draft": draft,
        "prerelease": prerelease,
        "html_url": f"https://github.com/JordanRooneyData/tiny-rogues-tracker/releases/tag/{tag}",
        "body": body,
        "assets": assets if assets is not None else [
            {"name": "TinyRoguesTracker-v0.4.4.exe", "browser_download_url": "https://example/app.exe"},
            {"name": "TinyRoguesTracker-v0.4.4-Setup.exe", "browser_download_url": "https://example/setup.exe"},
        ],
    }


def test_version_is_0431():
    assert __version__ == "0.4.4"


def test_043_detects_v0431_as_newer_and_leading_v_is_robust():
    info = updater.update_info_from_release_payload(release("v0.4.4"), current_version="0.4.3")
    assert info is not None
    assert info.latest_version == "0.4.4"
    assert info.asset_name == "TinyRoguesTracker-v0.4.4-Setup.exe"
    assert updater.is_newer_version("0.4.3", "v0.4.4")


def test_equal_and_older_remote_versions_do_not_trigger_update():
    assert updater.update_info_from_release_payload(release("v0.4.4"), current_version="0.4.4") is None
    assert updater.update_info_from_release_payload(release("v0.4.1"), current_version="0.4.4") is None


def test_drafts_and_prereleases_are_ignored_by_default():
    assert updater.update_info_from_release_payload(release(draft=True), current_version="0.4.1") is None
    assert updater.update_info_from_release_payload(release(prerelease=True), current_version="0.4.1") is None
    assert updater.update_info_from_release_payload(release(prerelease=True), current_version="0.4.1", allow_prerelease=True) is not None


def test_correct_installer_asset_selection_prefers_setup_not_standalone_exe():
    assets = [
        {"name": "TinyRoguesTracker-v0.4.4.exe", "browser_download_url": "https://example/app.exe"},
        {"name": "TinyRoguesTracker-v0.4.4-Setup.exe", "browser_download_url": "https://example/setup.exe"},
    ]
    chosen = updater.select_installer_asset(assets, "0.4.4")
    assert chosen["name"] == "TinyRoguesTracker-v0.4.4-Setup.exe"


def test_missing_installer_asset_is_recoverable_error(tmp_path):
    info = updater.update_info_from_release_payload(release(assets=[{"name": "TinyRoguesTracker-v0.4.4.exe", "browser_download_url": "https://example/app.exe"}]), current_version="0.4.1")
    assert info is not None and info.asset_url is None
    with pytest.raises(updater.UpdateError):
        updater.download_installer(info, target_dir=tmp_path)


def test_failed_download_does_not_require_app_crash(tmp_path):
    info = updater.UpdateInfo("0.4.1", "0.4.4", "", asset_name="TinyRoguesTracker-v0.4.4-Setup.exe", asset_url="https://example/fail.exe")
    with mock.patch("urllib.request.urlopen", side_effect=OSError("offline")):
        with pytest.raises(updater.UpdateError):
            updater.download_installer(info, target_dir=tmp_path)


def test_download_validation_requires_non_empty_windows_executable(tmp_path):
    good = tmp_path / "TinyRoguesTracker-v0.4.4-Setup.exe"
    good.write_bytes(b"MZ" + b"0" * updater.MIN_EXE_SIZE_BYTES)
    updater.validate_installer_download(good)
    bad = tmp_path / "bad.exe"
    bad.write_bytes(b"not an exe" * 200)
    with pytest.raises(updater.UpdateError):
        updater.validate_installer_download(bad)


def test_gui_startup_and_manual_update_are_wired_to_same_update_path():
    gui = (ROOT / "tiny_rogues_tracker" / "gui.py").read_text(encoding="utf-8")
    assert "self._check_updates()" in gui
    assert "update_check_started" in gui
    assert "Check for updates" in gui
    assert "manual_check_for_updates" in gui
    assert "check_latest_release()" in gui
    assert "download_and_launch_installer(info)" in gui
    assert "QApplication.quit()" in gui


def test_installer_appid_install_path_stable_and_relaunches_after_upgrade():
    iss = (ROOT / "installer" / "TinyRoguesTracker.iss").read_text(encoding="utf-8")
    assert "AppId={{B412CE11-FE99-4F12-B724-040040040040}}" in iss
    assert "DefaultDirName={localappdata}\\TinyRoguesTracker" in iss
    assert "UsePreviousAppDir=yes" in iss
    assert "PrivilegesRequired=lowest" in iss
    assert "skipifsilent" not in iss.lower()
    assert "TinyRoguesTracker-v0.4.4-Setup" in iss
