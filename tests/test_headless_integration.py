"""Real media pipeline smoke using only a generated one-second local fixture."""
import functools
import http.server
from pathlib import Path
import shutil
import subprocess
import threading

import pytest

from core.download_job import DownloadJob


@pytest.mark.skipif(not (shutil.which("ffmpeg") and shutil.which("ffprobe")), reason="System FFmpeg and FFprobe required")
def test_real_local_fixture_with_package_subprocess(tmp_path, monkeypatch):
    fixture = tmp_path / "fixture.mp4"
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
        "color=c=blue:s=64x64:r=10", "-t", "1", "-c:v", "libx264",
        "-pix_fmt", "yuv420p", str(fixture),
    ], check=True, timeout=15)
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(tmp_path))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        job = DownloadJob(
            f"http://127.0.0.1:{server.server_port}/fixture.mp4",
            str(tmp_path / "result 100% %(title)s"),
            format_selector="best", use_subprocess=True,
        )
        completed, errors = [], []
        job.download_completed.connect(completed.append)
        job.download_error.connect(errors.append)
        # Force only discovery, not downloading: execute real python -m yt_dlp.
        monkeypatch.setattr("core.download_job.resolve_yt_dlp_binary", lambda: None)
        job.run()
        assert not errors, errors
        assert completed and Path(completed[-1]).stat().st_size > 0
        assert Path(completed[-1]).name == "result 100% %(title)s.mp4"
        probe = subprocess.run([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=nw=1:nk=1", completed[-1],
        ], check=True, capture_output=True, text=True, timeout=15)
        assert 0.9 <= float(probe.stdout) <= 1.1
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
