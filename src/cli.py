"""Headless ClipCatcher interface. No Qt, display server, or saved cookies needed."""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import math
from pathlib import Path
import re
import signal
import sys
import uuid

from core.url_utils import parse_media_url


def parse_time(value: str) -> float:
    """Accept seconds, MM:SS, or HH:MM:SS (fractional seconds allowed)."""
    try:
        parts = value.split(":")
        if not 1 <= len(parts) <= 3 or any(not part for part in parts):
            raise ValueError
        numbers = [float(part) for part in parts]
        if any(not math.isfinite(n) or n < 0 for n in numbers):
            raise ValueError
        if len(numbers) > 1 and (any(n >= 60 for n in numbers[1:]) or
                                any(not n.is_integer() for n in numbers[:-1])):
            raise ValueError
        return sum(n * 60 ** i for i, n in enumerate(reversed(numbers)))
    except ValueError:
        raise argparse.ArgumentTypeError("Use nonnegative seconds, MM:SS, or HH:MM:SS")


def positive_height(value: str) -> int:
    try:
        height = int(value.removesuffix("p"))
        if height <= 0:
            raise ValueError
        return height
    except ValueError:
        raise argparse.ArgumentTypeError("Quality must be a positive height, e.g. 720p")


def supported_url(value: str) -> str:
    if not parse_media_url(value):
        raise argparse.ArgumentTypeError("Use an HTTPS CHZZK VOD/clip or YouTube video URL")
    return value.strip()


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="Report local dependencies without accessing video services")
    info = commands.add_parser("info", help="Read public metadata without downloading media")
    info.add_argument("url", type=supported_url)
    download = commands.add_parser("download", help="Download one public video or time range")
    download.add_argument("url", type=supported_url)
    download.add_argument("-o", "--output-dir", type=Path, default=Path.cwd() / "downloads")
    download.add_argument("--quality", type=positive_height, help="Maximum video height, e.g. 720p")
    download.add_argument("--start", type=parse_time)
    download.add_argument("--end", type=parse_time)
    return parser


def fetch_metadata(url):
    parsed = parse_media_url(url)
    if parsed["type"] == "youtube":
        from core.youtube_api import YouTubeAPI
        return YouTubeAPI().fetch_metadata(url)
    from core.chzzk_api import ChzzkAPI
    api = ChzzkAPI()
    if parsed["type"] == "vod":
        return asyncio.run(api.fetch_vod_metadata(parsed["id"], ""))
    return asyncio.run(api.fetch_clip_metadata(parsed["id"], ""))


def select_resolution(metadata, max_height=None):
    resolutions = metadata.get("resolutions") or []
    if max_height is not None:
        resolutions = [r for r in resolutions if 0 < (r.get("height") or 0) <= max_height]
    if not resolutions:
        raise ValueError("No matching playable quality found; try info or omit --quality")
    return max(resolutions, key=lambda r: r.get("height") or 0)


def output_stem(directory, metadata, resolution):
    # Unique suffix prevents concurrent jobs and repeated ranges overwriting files.
    title = re.sub(r'[\x00-\x1f<>:"/\\|?*]', "_", str(metadata.get("title") or "video"))
    title = title.encode("utf-8")[:160].decode("utf-8", errors="ignore").rstrip(" .") or "video"
    return str(directory / f"{title}_{uuid.uuid4().hex[:12]}")


def run_download(args, metadata):
    from core.download_job import DownloadJob
    resolution = select_resolution(metadata, args.quality)
    directory = args.output_dir.expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)
    content_type = metadata.get("type", parse_media_url(args.url)["type"])
    manual = content_type == "vod" and metadata.get("vod_status") != "ABR_HLS"
    height = resolution.get("height") or args.quality
    fmt = (f"bestvideo[height<={height}]+bestaudio/best[height<={height}]"
           if height else "bestvideo+bestaudio/best")
    job = DownloadJob(
        metadata.get("url") or args.url, output_stem(directory, metadata, resolution),
        use_manual_download=manual, video_id=metadata.get("id"),
        quality=resolution.get("label"), start_time=args.start, end_time=args.end,
        format_selector="best" if content_type == "clip" else fmt,
        use_subprocess=True,
    )
    completed, errors = [], []
    job.download_completed.connect(completed.append)
    job.download_error.connect(errors.append)
    job.status_changed.connect(lambda status: print(status, file=sys.stderr))
    previous = {}
    cancelled = False

    def cancel(signum, frame):
        nonlocal cancelled
        cancelled = True
        job.stop()

    try:
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous[signum] = signal.signal(signum, cancel)
        # Existing downloader diagnostics belong on stderr; stdout is the final path.
        with contextlib.redirect_stdout(sys.stderr):
            job.run()
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)
    if cancelled:
        print("Download cancelled", file=sys.stderr)
        return 130
    if errors:
        raise RuntimeError(errors[-1])
    if not completed or not Path(completed[-1]).is_file() or Path(completed[-1]).stat().st_size == 0:
        raise RuntimeError("Downloader did not produce a nonempty output file")
    print(completed[-1])
    return 0


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "download" and args.end is not None and args.end <= (args.start or 0):
        parser.error("--end must be greater than --start")
    try:
        from core.dependency_check import check_ffmpeg, check_yt_dlp
        if args.command == "check":
            from dataclasses import asdict
            statuses = [check_yt_dlp(), check_ffmpeg()]
            print(json.dumps([asdict(item) for item in statuses], ensure_ascii=False, indent=2))
            return 0 if all(item.available for item in statuses) else 1
        if args.command == "download":
            missing = [item.name for item in (check_yt_dlp(), check_ffmpeg()) if not item.available]
            if missing:
                raise RuntimeError("Missing dependencies: " + ", ".join(missing) + "; run check")
        with contextlib.redirect_stdout(sys.stderr):
            metadata = fetch_metadata(args.url)
        if args.command == "info":
            # Do not expose expiring signed stream URLs in structured output.
            summary = {key: metadata.get(key) for key in ("id", "type", "title", "duration", "vod_status")}
            summary["qualities"] = [r.get("label") for r in metadata.get("resolutions", [])]
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            return 0
        return run_download(args, metadata)
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print(f"ClipCatcher: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
