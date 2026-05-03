"""
Application-owned external tool paths.
"""
from __future__ import annotations

import os
import shutil
import stat
import sys
import urllib.request
from pathlib import Path
from typing import Optional


def get_app_support_dir() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "ClipCatcher"
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "ClipCatcher"
    return Path.home() / ".local" / "share" / "ClipCatcher"


def get_app_bin_dir(create: bool = True) -> Path:
    bin_dir = get_app_support_dir() / "bin"
    if create:
        bin_dir.mkdir(parents=True, exist_ok=True)
    return bin_dir


def executable_name(name: str) -> str:
    if sys.platform == "win32" and not name.endswith(".exe"):
        return f"{name}.exe"
    return name


def find_app_tool(name: str) -> Optional[str]:
    candidate = get_app_bin_dir(create=False) / executable_name(name)
    if candidate.is_file() and os.access(candidate, os.X_OK):
        return str(candidate)
    return None


def install_app_tool_from_path(name: str, source_path: str) -> Optional[str]:
    source = Path(source_path)
    if not source.is_file():
        return None

    target = get_app_bin_dir(create=True) / executable_name(name)
    try:
        if source.resolve() == target.resolve():
            return str(target)
    except FileNotFoundError:
        pass

    try:
        shutil.copy2(source, target)
        current_mode = target.stat().st_mode
        target.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        return str(target)
    except Exception as exc:
        print(f"[tool cache] failed to install {name}: {exc}")
        return None


def get_yt_dlp_download_url() -> str:
    if sys.platform == "win32":
        return "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
    if sys.platform == "darwin":
        return "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_macos"
    return "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp"


def install_or_update_yt_dlp() -> str:
    """Download the official standalone yt-dlp binary into the app-owned bin dir."""
    target = get_app_bin_dir(create=True) / executable_name("yt-dlp")
    tmp_target = target.with_suffix(target.suffix + ".download")
    url = get_yt_dlp_download_url()

    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            data = response.read()
        with open(tmp_target, "wb") as f:
            f.write(data)
        current_mode = tmp_target.stat().st_mode
        tmp_target.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        tmp_target.replace(target)
    finally:
        if tmp_target.exists():
            try:
                tmp_target.unlink()
            except OSError:
                pass

    return str(target)
