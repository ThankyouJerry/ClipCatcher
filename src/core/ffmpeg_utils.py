"""
ffmpeg 바이너리 경로 결정 유틸리티

우선순위:
1. PyInstaller 번들 — 다양한 경로 탐색 (_MEIPASS, Resources, Frameworks)
2. imageio-ffmpeg 패키지 API (소스 실행 환경)
3. 시스템 PATH (shutil.which)
4. 플랫폼별 기본 경로 폴백
"""
import os
import sys
import shutil
import glob


def _find_in_dir(base_dir: str) -> str:
    """base_dir/imageio_ffmpeg/binaries/ 안에서 ffmpeg 바이너리를 찾습니다."""
    binaries_dir = os.path.join(base_dir, 'imageio_ffmpeg', 'binaries')
    if not os.path.isdir(binaries_dir):
        return ''
    for fname in os.listdir(binaries_dir):
        if not fname.startswith('ffmpeg'):
            continue
        full = os.path.join(binaries_dir, fname)
        if not os.path.isfile(full):
            continue
        # macOS/Linux: 실행 권한 보장
        if sys.platform != 'win32':
            try:
                os.chmod(full, 0o755)
            except OSError:
                pass
        return full
    return ''


def get_ffmpeg_binary() -> str:
    """
    사용 가능한 ffmpeg 바이너리 경로를 반환합니다.
    """
    # ── 1) PyInstaller 번들 환경 ─────────────────────────────────────────
    if getattr(sys, 'frozen', False):
        # 탐색 후보 디렉터리 목록
        candidates = []

        # 1-a) sys._MEIPASS (Windows onedir, Linux)
        meipass = getattr(sys, '_MEIPASS', '')
        if meipass:
            candidates.append(meipass)

        # 1-b) sys.executable 기준 상대 경로 (macOS .app 구조 대응)
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        # Contents/MacOS → Contents → Resources / Frameworks
        contents = os.path.dirname(exe_dir)
        candidates += [
            os.path.join(contents, 'Resources'),    # macOS .app Resources
            os.path.join(contents, 'Frameworks'),   # macOS .app Frameworks
            os.path.join(exe_dir, '_internal'),     # PyInstaller 6.x onedir
            exe_dir,                                # Windows .exe 디렉터리
        ]

        for base in candidates:
            found = _find_in_dir(base)
            if found:
                return found

    # ── 2) imageio-ffmpeg 패키지 API (소스 실행 환경) ────────────────────
    try:
        import imageio_ffmpeg
        path = imageio_ffmpeg.get_ffmpeg_exe()
        if path and os.path.isfile(path):
            return path
    except Exception:
        pass

    # ── 3) 시스템 PATH ────────────────────────────────────────────────────
    found = shutil.which('ffmpeg')
    if found:
        return found

    # ── 4) macOS Homebrew 폴백 ────────────────────────────────────────────
    if sys.platform == 'darwin':
        for c in ('/opt/homebrew/bin/ffmpeg', '/usr/local/bin/ffmpeg'):
            if os.path.isfile(c):
                return c

    # ── 5) Windows 기본 위치 폴백 ─────────────────────────────────────────
    if sys.platform == 'win32':
        for c in (
            r'C:\ffmpeg\bin\ffmpeg.exe',
            r'C:\Program Files\ffmpeg\bin\ffmpeg.exe',
        ):
            if os.path.isfile(c):
                return c

    return 'ffmpeg'
