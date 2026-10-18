"""Record native dependency versions, licenses and FFmpeg build provenance."""
from importlib import metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys


def build_notices():
    import imageio_ffmpeg
    target = Path('build/third-party-notices').resolve()
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy2('docs/licenses/FFmpeg-GPL-3.txt', target)
    packages = ['yt-dlp', 'aiohttp', 'imageio-ffmpeg', 'PyQt6', 'PyQt6-Qt6',
                'PyQt6-sip', 'qasync', 'Pillow', 'aiohappyeyeballs', 'aiosignal',
                'attrs', 'frozenlist', 'multidict', 'propcache', 'yarl', 'idna',
                'certifi', 'requests', 'urllib3', 'charset-normalizer',
                'websockets', 'mutagen', 'pycryptodomex', 'brotli', 'curl-cffi',
                'PyInstaller']
    versions = {'Python': sys.version}
    for name in packages:
        try:
            dist = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            continue
        versions[name] = dist.version
        for item in dist.files or []:
            if any(part.lower().startswith(('license', 'copying', 'notice'))
                   for part in item.parts):
                source = Path(dist.locate_file(item))
                if source.is_file():
                    dest = target / name / Path(*item.parts)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, dest)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    for flag, name in [('-version', 'FFmpeg-build.txt'), ('-L', 'FFmpeg-license.txt')]:
        run = subprocess.run([ffmpeg, flag], check=True, capture_output=True, text=True)
        (target / name).write_text(run.stdout + run.stderr, encoding='utf-8')
    (target / 'versions.json').write_text(json.dumps(versions, indent=2), encoding='utf-8')
    (target / 'PROVENANCE.txt').write_text(
        'FFmpeg is an unmodified separate executable supplied by imageio-ffmpeg.\n'
        'FFprobe is not included. FFmpeg-build.txt records the exact native build.\n'
        'Package and build scripts: https://github.com/imageio/imageio-ffmpeg\n'
        'Distributed binaries: https://github.com/imageio/imageio-binaries/tree/master/ffmpeg\n'
        'FFmpeg upstream source: https://ffmpeg.org/releases/\n'
        'Linux binary provider and corresponding source: https://johnvansickle.com/ffmpeg/\n'
        'Consult binary build output and imageio upstream for platform-specific provenance.\n'
        'yt-dlp source: https://github.com/yt-dlp/yt-dlp\n'
        'Python source and license: https://www.python.org/downloads/source/\n'
        'Other dependency license files and exact versions are retained in this folder.\n',
        encoding='utf-8')
    return str(target)


if __name__ == '__main__':
    print(build_notices())
