"""
External dependency detection helpers for yt-dlp and ffmpeg.
"""
from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from typing import List, Optional

from core.app_tools import get_yt_dlp_binary_candidates
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


def _release_date(version):
    match = re.match(r"^(\d{4})[.](\d{1,2})[.](\d{1,2})(?:$|[.\-+])", version or "")
    return tuple(map(int, match.groups())) if match else None


def resolve_yt_dlp_binary() -> Optional[str]:
    """Do not let an older external engine shadow the newer bundled engine."""
    try:
        import yt_dlp
        bundled_date = _release_date(yt_dlp.version.__version__)
    except (ImportError, AttributeError):
        bundled_date = None
    checked = set()
    for candidate in get_yt_dlp_binary_candidates():
        if not candidate or candidate in checked:
            continue
        checked.add(candidate)
        if not os.path.isfile(candidate) or not os.access(candidate, os.X_OK):
            continue
        status = _run_version(candidate, "--version")
        if not status.available:
            continue
        external_date = _release_date(status.version)
        if bundled_date and external_date and external_date < bundled_date:
            continue
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
