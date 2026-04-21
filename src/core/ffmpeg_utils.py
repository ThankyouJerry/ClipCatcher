"""
ffmpeg 바이너리 경로 결정 유틸리티

우선순위:
1. imageio-ffmpeg 패키지 (번들/설치 모두 지원, 정적 바이너리)
2. 시스템 PATH (shutil.which)
3. Homebrew 기본 경로 (macOS 폴백)
"""
import os
import sys
import shutil


def get_ffmpeg_binary() -> str:
    """
    사용 가능한 ffmpeg 바이너리 경로를 반환합니다.

    PyInstaller 번들 또는 pip 설치 환경에서 imageio-ffmpeg를 우선 사용합니다.
    """
    # 1) imageio-ffmpeg 패키지 (정적 바이너리, 번들 포함)
    try:
        import imageio_ffmpeg
        path = imageio_ffmpeg.get_ffmpeg_exe()
        if path and os.path.isfile(path):
            return path
    except Exception:
        pass

    # 2) 시스템 PATH
    found = shutil.which("ffmpeg")
    if found:
        return found

    # 3) macOS Homebrew 폴백
    if sys.platform == "darwin":
        candidates = [
            "/opt/homebrew/bin/ffmpeg",
            "/usr/local/bin/ffmpeg",
        ]
        for c in candidates:
            if os.path.isfile(c):
                return c

    # 4) Windows 기본 위치 폴백
    if sys.platform == "win32":
        candidates = [
            r"C:\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        ]
        for c in candidates:
            if os.path.isfile(c):
                return c

    return "ffmpeg"  # 마지막 폴백: PATH에서 찾기를 시도
