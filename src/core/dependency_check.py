"""
External dependency detection helpers for yt-dlp and ffmpeg.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import List, Optional

from core.app_tools import find_app_tool
from core.ffmpeg_utils import get_ffmpeg_binary


@dataclass
class ToolStatus:
    name: str
    binary: Optional[str]
    available: bool
    version: Optional[str] = None
    error: Optional[str] = None


def _run_version(binary: str, version_arg: str) -> ToolStatus:
    try:
        result = subprocess.run(
            [binary, version_arg],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=3,
            check=False,
        )
    except Exception as exc:
        return ToolStatus(name="", binary=binary, available=False, error=str(exc))

    if result.returncode != 0:
        msg = (result.stderr or result.stdout or "").strip()
        return ToolStatus(name="", binary=binary, available=False, error=msg[:200] or "failed")

    first_line = (result.stdout or result.stderr or "").splitlines()
    version = first_line[0].strip() if first_line else "ok"
    return ToolStatus(name="", binary=binary, available=True, version=version)


def is_yt_dlp_binary_usable(binary: Optional[str]) -> bool:
    """Return whether a yt-dlp path is executable and can actually start."""
    if not binary or not os.path.isfile(binary) or not os.access(binary, os.X_OK):
        return False
    return _run_version(binary, "--version").available


def resolve_yt_dlp_binary() -> Optional[str]:
    candidates: List[Optional[str]] = [
        find_app_tool("yt-dlp"),
        shutil.which("yt-dlp"),
    ]
    if sys.platform == "darwin":
        candidates.extend(["/opt/homebrew/bin/yt-dlp", "/usr/local/bin/yt-dlp"])
    elif sys.platform == "win32":
        candidates.extend(
            [
                os.path.expandvars(
                    r"%LOCALAPPDATA%\Microsoft\WinGet\Links\yt-dlp.exe"
                ),
                r"C:\yt-dlp\yt-dlp.exe",
            ]
        )
    else:
        candidates.extend(["/usr/local/bin/yt-dlp", "/usr/bin/yt-dlp"])

    checked = set()
    for candidate in candidates:
        if not candidate or candidate in checked:
            continue
        checked.add(candidate)
        if is_yt_dlp_binary_usable(candidate):
            return candidate
    return None


def check_yt_dlp() -> ToolStatus:
    binary = resolve_yt_dlp_binary()
    if not binary:
        try:
            import yt_dlp
            version = getattr(yt_dlp.version, "__version__", "bundled")
            return ToolStatus(
                name="yt-dlp",
                binary="bundled Python package",
                available=True,
                version=version,
            )
        except Exception as exc:
            return ToolStatus(name="yt-dlp", binary=None, available=False, error=str(exc))

    status = _run_version(binary, "--version")
    status.name = "yt-dlp"
    return status


def check_ffmpeg() -> ToolStatus:
    binary = get_ffmpeg_binary()
    status = _run_version(binary, "-version")
    status.name = "ffmpeg"
    if status.available:
        status.binary = binary
    return status


def get_missing_dependencies() -> List[ToolStatus]:
    checks = [check_yt_dlp(), check_ffmpeg()]
    return [item for item in checks if not item.available]
