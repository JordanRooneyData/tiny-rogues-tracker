from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import threading
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from . import GITHUB_REPO, __version__

RELEASE_API = "https://api.github.com/repos/{repo}/releases/latest"

@dataclass
class UpdateInfo:
    current_version: str
    latest_version: str
    html_url: str
    asset_name: str | None = None
    asset_url: str | None = None

    @property
    def is_newer(self) -> bool:
        return version_tuple(self.latest_version) > version_tuple(self.current_version)

def version_tuple(v: str) -> tuple[int, ...]:
    v = v.strip().lstrip("v")
    parts = []
    for p in v.split("."):
        try:
            parts.append(int("".join(ch for ch in p if ch.isdigit()) or "0"))
        except ValueError:
            parts.append(0)
    return tuple(parts)

def check_latest_release(repo: str = GITHUB_REPO, timeout: float = 4.0) -> UpdateInfo | None:
    url = RELEASE_API.format(repo=repo)
    req = urllib.request.Request(url, headers={"User-Agent": "TinyRoguesTracker/" + __version__})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec: public GitHub release endpoint
        data = json.loads(resp.read().decode("utf-8"))
    tag = data.get("tag_name", "0.0.0")
    assets = data.get("assets", []) or []
    asset = next((a for a in assets if "installer" in a.get("name", "").lower() or a.get("name", "").lower().endswith(".exe")), None)
    return UpdateInfo(
        current_version=__version__,
        latest_version=tag.lstrip("v"),
        html_url=data.get("html_url", ""),
        asset_name=asset.get("name") if asset else None,
        asset_url=asset.get("browser_download_url") if asset else None,
    )

def check_async(callback: Callable[[UpdateInfo | None, Exception | None], None], repo: str = GITHUB_REPO) -> threading.Thread:
    def worker() -> None:
        try:
            info = check_latest_release(repo=repo)
            callback(info if info and info.is_newer else None, None)
        except Exception as exc:  # offline is non-fatal
            callback(None, exc)
    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return t

def download_and_launch_installer(info: UpdateInfo) -> Path:
    if not info.asset_url:
        raise RuntimeError("No downloadable installer asset found for latest release")
    target = Path(tempfile.gettempdir()) / (info.asset_name or "TinyRoguesTracker-installer.exe")
    urllib.request.urlretrieve(info.asset_url, target)  # nosec: public opt-in update URL from GitHub release metadata
    if target.stat().st_size <= 0:
        raise RuntimeError("Downloaded installer was empty")
    if sys.platform.startswith("win"):
        subprocess.Popen([str(target)], close_fds=True)
    else:
        subprocess.Popen(["xdg-open", str(target)], close_fds=True)
    return target
