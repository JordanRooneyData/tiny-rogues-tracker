from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from . import GITHUB_REPO, __version__

RELEASE_API = "https://api.github.com/repos/{repo}/releases/latest"
USER_AGENT = "TinyRoguesTracker/{version}"
DOWNLOAD_TIMEOUT_SECONDS = 20.0
CHECK_TIMEOUT_SECONDS = 3.0
MIN_EXE_SIZE_BYTES = 1024


@dataclass(frozen=True)
class UpdateInfo:
    current_version: str
    latest_version: str
    html_url: str
    release_notes: str = ""
    asset_name: str | None = None
    asset_url: str | None = None

    @property
    def is_newer(self) -> bool:
        return is_newer_version(self.current_version, self.latest_version)

    @property
    def summary(self) -> str:
        text = (self.release_notes or "").strip()
        if not text:
            return ""
        first_lines = [line.strip("# -*\t") for line in text.splitlines() if line.strip()]
        return "\n".join(first_lines[:4])[:700]


class UpdateError(RuntimeError):
    """Recoverable updater failure; callers should show a non-blocking message."""


def parse_version(value: str) -> tuple[tuple[int, ...], tuple[str, ...]]:
    """Parse semantic-ish versions with a leading v and any numeric depth."""
    raw = (value or "0.0.0").strip().lstrip("vV")
    main, *suffix = re.split(r"[-+]", raw, maxsplit=1)
    nums: list[int] = []
    for part in main.split("."):
        m = re.match(r"(\d+)", part)
        nums.append(int(m.group(1)) if m else 0)
    while len(nums) > 1 and nums[-1] == 0:
        nums.pop()
    return tuple(nums or [0]), tuple(suffix)


def is_newer_version(current: str, remote: str) -> bool:
    remote_nums = parse_version(remote)[0]
    current_nums = parse_version(current)[0]
    width = max(len(remote_nums), len(current_nums))
    return remote_nums + (0,) * (width - len(remote_nums)) > current_nums + (0,) * (width - len(current_nums))


def select_installer_asset(assets: Iterable[dict], latest_version: str) -> dict | None:
    """Select the Inno installer asset, never the standalone one-file app exe."""
    assets = list(assets or [])
    version = latest_version.strip().lstrip("vV")
    exact_names = {
        f"TinyRoguesTracker-v{version}-Setup.exe".lower(),
        f"TinyRoguesTracker-{version}-Setup.exe".lower(),
    }
    for asset in assets:
        if asset.get("name", "").lower() in exact_names:
            return asset
    setup_assets = [a for a in assets if a.get("name", "").lower().endswith("setup.exe")]
    if setup_assets:
        return sorted(setup_assets, key=lambda a: a.get("name", ""))[0]
    installer_assets = [a for a in assets if "installer" in a.get("name", "").lower() and a.get("name", "").lower().endswith(".exe")]
    if installer_assets:
        return sorted(installer_assets, key=lambda a: a.get("name", ""))[0]
    return None


def update_info_from_release_payload(data: dict, current_version: str = __version__, allow_prerelease: bool = False) -> UpdateInfo | None:
    if not data or data.get("draft"):
        return None
    if data.get("prerelease") and not allow_prerelease:
        return None
    tag = str(data.get("tag_name") or "0.0.0")
    latest = tag.lstrip("vV")
    if not is_newer_version(current_version, latest):
        return None
    asset = select_installer_asset(data.get("assets", []) or [], latest)
    return UpdateInfo(
        current_version=current_version,
        latest_version=latest,
        html_url=data.get("html_url", ""),
        release_notes=data.get("body", "") or "",
        asset_name=asset.get("name") if asset else None,
        asset_url=asset.get("browser_download_url") if asset else None,
    )


def check_latest_release(
    repo: str = GITHUB_REPO,
    timeout: float = CHECK_TIMEOUT_SECONDS,
    current_version: str = __version__,
    allow_prerelease: bool = False,
) -> UpdateInfo | None:
    url = RELEASE_API.format(repo=repo)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT.format(version=current_version), "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec: public GitHub release endpoint
        data = json.loads(resp.read().decode("utf-8"))
    return update_info_from_release_payload(data, current_version=current_version, allow_prerelease=allow_prerelease)


def check_async(
    callback: Callable[[UpdateInfo | None, Exception | None], None],
    repo: str = GITHUB_REPO,
    current_version: str = __version__,
    allow_prerelease: bool = False,
) -> threading.Thread:
    def worker() -> None:
        try:
            callback(check_latest_release(repo=repo, current_version=current_version, allow_prerelease=allow_prerelease), None)
        except Exception as exc:  # offline is non-fatal
            callback(None, exc)
    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return t


def download_installer(info: UpdateInfo, target_dir: str | Path | None = None, timeout: float = DOWNLOAD_TIMEOUT_SECONDS) -> Path:
    if not info.asset_url or not info.asset_name:
        raise UpdateError("No Windows installer asset was found on the latest release.")
    target_root = Path(target_dir) if target_dir else Path(tempfile.gettempdir())
    target_root.mkdir(parents=True, exist_ok=True)
    target = target_root / info.asset_name
    req = urllib.request.Request(info.asset_url, headers={"User-Agent": USER_AGENT.format(version=info.current_version)})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp, target.open("wb") as fh:  # nosec: URL from GitHub release metadata
            while True:
                chunk = resp.read(1024 * 256)
                if not chunk:
                    break
                fh.write(chunk)
    except (OSError, urllib.error.URLError) as exc:
        raise UpdateError(f"Update download failed: {exc}") from exc
    validate_installer_download(target)
    return target


def validate_installer_download(path: str | Path) -> None:
    path = Path(path)
    if not path.exists() or path.stat().st_size < MIN_EXE_SIZE_BYTES:
        raise UpdateError("Downloaded installer is missing or unexpectedly small.")
    with path.open("rb") as fh:
        if fh.read(2) != b"MZ":
            raise UpdateError("Downloaded update is not a valid Windows executable.")


def launch_installer_in_update_mode(installer_path: str | Path) -> subprocess.Popen:
    path = Path(installer_path)
    args = [str(path)]
    if sys.platform.startswith("win"):
        args += ["/CURRENTUSER", "/NORESTART", "/CLOSEAPPLICATIONS", "/RESTARTAPPLICATIONS"]
    return subprocess.Popen(args, close_fds=True)


def download_and_launch_installer(info: UpdateInfo) -> Path:
    target = download_installer(info)
    launch_installer_in_update_mode(target)
    return target
