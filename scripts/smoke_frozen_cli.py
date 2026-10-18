"""Check the shipped CLI and bundled yt-dlp using a local generated video only."""
import functools
import http.server
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading


def main():
    executable = str(Path(sys.argv[1]).resolve())
    subprocess.run([executable, '--cli', 'check'], check=True, timeout=30)
    subprocess.run([executable, '--smoke'], check=True, timeout=30)
    subprocess.run([executable, '--run-yt-dlp', '--version'], check=True, timeout=30)
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        fixture = root / 'fixture.mp4'
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error',
                        '-f', 'lavfi', '-i', 'color=c=blue:s=64x64:r=10',
                        '-t', '1', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                        str(fixture)], check=True, timeout=30)
        server = http.server.ThreadingHTTPServer(
            ('127.0.0.1', 0), functools.partial(
                http.server.SimpleHTTPRequestHandler, directory=temp))
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            output = root / 'download.mp4'
            # No Python interpreter or external yt-dlp on PATH: the frozen helper
            # must provide the downloader instead of recursing into the app.
            env = dict(os.environ, PATH=str(root / 'empty-path'), HOME=temp,
                       XDG_DATA_HOME=str(root / 'data'))
            subprocess.run([executable, '--run-yt-dlp', '--ignore-config',
                            '--no-playlist', '-o', str(output),
                            f'http://127.0.0.1:{server.server_port}/fixture.mp4'],
                           env=env, check=True, timeout=60)
            assert output.read_bytes() == fixture.read_bytes()
            binaries = list((Path(executable).parent / '_internal' /
                             'imageio_ffmpeg' / 'binaries').glob('ffmpeg*'))
            ffmpeg = next(p for p in binaries if p.is_file())
            subprocess.run([executable, '--run-yt-dlp', '--ignore-config',
                            '--ffmpeg-location', str(ffmpeg), '--recode-video', 'avi',
                            '-o', str(root / 'converted.%(ext)s'),
                            f'http://127.0.0.1:{server.server_port}/fixture.mp4'],
                           env=env, check=True, timeout=60)
            converted = root / 'converted.avi'
            assert converted.stat().st_size > 0
            probe = subprocess.run(['ffprobe', '-v', 'error', '-show_entries',
                                    'format=duration', '-of', 'csv=p=0', str(converted)],
                                   capture_output=True, text=True, check=True, timeout=15)
            assert 0.9 <= float(probe.stdout) <= 1.1
            subprocess.run([executable, '--cli', 'check'], env=env,
                           check=True, timeout=30)
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=5)
    print('FROZEN_CLI_OK')


if __name__ == '__main__':
    main()
