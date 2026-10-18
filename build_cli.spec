# Linux x86_64 headless package. Build natively on Ubuntu 22.04 or newer.
from pathlib import Path
import runpy

notices = runpy.run_path("scripts/build_notices.py")["build_notices"]()
from PyInstaller.utils.hooks import collect_all, collect_data_files

yt_data, yt_binaries, yt_hidden = collect_all('yt_dlp')
a = Analysis(
    ['src/main.py'], pathex=[str(Path('src').resolve())],
    binaries=yt_binaries, datas=yt_data + collect_data_files('imageio_ffmpeg') + [(notices, 'third-party-notices')],
    hiddenimports=yt_hidden + ['cli', 'imageio_ffmpeg'],
    excludes=['PyQt6', 'qasync', 'ui'],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True,
          name='clipcatcher', console=True, strip=False, upx=False)
coll = COLLECT(exe, a.binaries, a.datas, name='ClipCatcher-Linux-x86_64',
               strip=False, upx=False)
