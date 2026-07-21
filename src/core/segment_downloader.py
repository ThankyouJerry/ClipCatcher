"""
Manual Segment Downloader for Chzzk HLS streams
Handles downloading of fMP4 segments when yt-dlp fails
"""
import asyncio
import aiohttp
import re
from pathlib import Path
from typing import List, Dict, Callable, Optional, Tuple
from urllib.parse import urljoin
import urllib.parse


class SegmentDownloader:
    """Downloads HLS streams by manually fetching segments"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None

    @staticmethod
    def _playlist_duration(segments: List[Dict]) -> float:
        """Return the authoritative duration represented by an HLS playlist."""
        return sum(float(segment.get('duration', 0) or 0) for segment in segments)

    @classmethod
    def _select_media_segments(
        cls,
        segments: List[Dict],
        start_time: Optional[float],
        end_time: Optional[float],
    ) -> List[str]:
        """Validate a requested range against HLS and return overlapping URLs."""
        selected, _, _ = cls._select_media_range(
            segments,
            start_time,
            end_time,
        )
        return selected

    @classmethod
    def _select_media_range(
        cls,
        segments: List[Dict],
        start_time: Optional[float],
        end_time: Optional[float],
    ) -> Tuple[List[str], float, float]:
        """Return overlapping URLs plus exact trim offset and duration."""
        playlist_duration = cls._playlist_duration(segments)
        if playlist_duration <= 0:
            raise ValueError("HLS 재생목록의 영상 길이를 확인할 수 없습니다.")

        requested_start = max(float(start_time or 0), 0.0)
        if requested_start >= playlist_duration:
            raise ValueError(
                "시작 시간이 실제 다운로드 가능 길이를 초과했습니다. "
                f"(HLS 길이: {playlist_duration:.3f}초)"
            )

        if end_time is not None and float(end_time) > playlist_duration + 0.05:
            raise ValueError(
                "종료 시간이 실제 다운로드 가능 길이를 초과했습니다. "
                f"(HLS 길이: {playlist_duration:.3f}초)"
            )

        requested_end = min(
            float(end_time) if end_time is not None else playlist_duration,
            playlist_duration,
        )
        if requested_end <= requested_start:
            raise ValueError("종료 시간은 시작 시간보다 커야 합니다.")

        selected = []
        selected_start = None
        current_time = 0.0
        for segment in segments:
            duration = float(segment.get('duration', 0) or 0)
            segment_end_time = current_time + duration
            overlaps = segment_end_time > requested_start
            if end_time is not None and current_time >= float(end_time):
                overlaps = False
            if overlaps:
                if selected_start is None:
                    selected_start = current_time
                selected.append(segment['url'])
            current_time = segment_end_time

        if not selected:
            raise ValueError("요청한 시간 범위에 해당하는 HLS 세그먼트가 없습니다.")
        trim_start = requested_start - float(selected_start or 0.0)
        trim_duration = requested_end - requested_start
        return selected, trim_start, trim_duration
    
    async def download_video(
        self,
        m3u8_url: str,
        output_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
        max_segments: Optional[int] = None,
        target_quality: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None
    ) -> str:
        """
        Download video by fetching segments manually
        
        Args:
            m3u8_url: Master or variant playlist URL
            output_path: Output file path (without extension)
            progress_callback: Callback for progress updates (current, total)
            headers: HTTP headers to use
            cookies: HTTP cookies to use
            max_segments: Maximum number of segments to download (for testing)
            target_quality: Target quality (e.g. "1080p") if m3u8_url is a master playlist
            start_time: Start time in seconds
            end_time: End time in seconds
        
        Returns:
            Path to downloaded file
        """
        # Default headers if not provided
        if not headers:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://chzzk.naver.com/',
                'Origin': 'https://chzzk.naver.com'
            }
            
        async with aiohttp.ClientSession(headers=headers, cookies=cookies) as self.session:
            # Parse m3u8
            manifest_content = await self._fetch_text(m3u8_url)
            base_url = self._get_base_url(m3u8_url)
            
            # Check if it's a master playlist
            if "#EXT-X-STREAM-INF" in manifest_content:
                if not target_quality:
                    raise Exception("Target quality required for master playlist")
                
                # Extract media playlist URL
                media_url = self._extract_media_url(manifest_content, base_url, target_quality)
                if not media_url:
                    raise Exception(f"Quality {target_quality} not found in master playlist")
                
                # Fetch media playlist
                m3u8_url = media_url
                manifest = await self._fetch_m3u8(m3u8_url)
                base_url = self._get_base_url(m3u8_url)
            else:
                # It's already a media playlist
                manifest = self._parse_m3u8(manifest_content)
            
            # Extract segments
            init_segment = manifest.get('init_segment')
            all_segments = manifest.get('media_segments', [])
            
            if not all_segments:
                raise Exception("No media segments found in m3u8")
            
            # Filter segments by time range if specified
            trim_start = None
            trim_duration = None
            if start_time is not None or end_time is not None:
                media_segments, trim_start, trim_duration = self._select_media_range(
                    all_segments,
                    start_time,
                    end_time,
                )
            else:
                media_segments = [s['url'] for s in all_segments]
            
            # Apply max_segments limit for testing
            if max_segments and max_segments < len(media_segments):
                media_segments = media_segments[:max_segments]
            
            total_segments = len(media_segments) + (1 if init_segment else 0)
            current = 0
            
            # Create temp directory
            temp_dir = Path(output_path).parent / f"temp_{Path(output_path).stem}"
            temp_dir.mkdir(exist_ok=True)
            
            try:
                # Download init segment
                init_path = None
                if init_segment:
                    init_url = urljoin(base_url, init_segment)
                    init_path = temp_dir / "init.m4s"
                    await self._download_file(init_url, str(init_path))
                    current += 1
                    if progress_callback:
                        progress_callback(current, total_segments)
                
                # Download media segments
                segment_paths = []
                for idx, segment_url in enumerate(media_segments):
                    full_url = urljoin(base_url, segment_url)
                    seg_path = temp_dir / f"seg_{idx:04d}.m4v"
                    await self._download_file(full_url, str(seg_path))
                    segment_paths.append(seg_path)
                    
                    current += 1
                    if progress_callback:
                        progress_callback(current, total_segments)
                
                # Combine segments
                final_output = output_path if output_path.endswith('.mp4') else f"{output_path}.mp4"
                self._combine_segments(
                    init_path,
                    segment_paths,
                    final_output,
                    trim_start=trim_start,
                    trim_duration=trim_duration,
                )
                
                return final_output
                
            finally:
                # Cleanup temp files
                import shutil
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
    
    async def _fetch_text(self, url: str) -> str:
        """Fetch text content from URL"""
        async with self.session.get(url) as response:
            if response.status != 200:
                raise Exception(f"Failed to fetch content: HTTP {response.status}")
            return await response.text()

    async def _fetch_m3u8(self, url: str) -> Dict:
        """Fetch and parse m3u8 playlist"""
        content = await self._fetch_text(url)
        return self._parse_m3u8(content)

    def _extract_media_url(self, content: str, base_url: str, quality: str) -> Optional[str]:
        """Extract media playlist URL for specific quality from master playlist"""
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if line.startswith("#EXT-X-STREAM-INF"):
                # Check next line for URL
                if i + 1 < len(lines):
                    url_line = lines[i+1].strip()
                    # Check if quality matches (e.g. "720p")
                    # Chzzk quality string matching
                    if quality in url_line or f"/{quality}/" in url_line:
                        return urllib.parse.urljoin(base_url, url_line)
                    
                    # Fallback: check resolution if quality label fails
                    # 1080p -> 1920x1080
                    if quality == "1080p" and "1920x1080" in line:
                        return urllib.parse.urljoin(base_url, url_line)
                    if quality == "720p" and "1280x720" in line:
                        return urllib.parse.urljoin(base_url, url_line)
                    if quality == "480p" and "852x480" in line:
                        return urllib.parse.urljoin(base_url, url_line)
                    if quality == "360p" and "640x360" in line:
                        return urllib.parse.urljoin(base_url, url_line)
                    if quality == "144p" and "256x144" in line:
                        return urllib.parse.urljoin(base_url, url_line)
        return None
    
    def _parse_m3u8(self, content: str) -> Dict:
        """Parse m3u8 content including durations"""
        lines = content.strip().split('\n')
        
        init_segment = None
        media_segments = []
        current_duration = 0.0
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Find init segment
            if line.startswith('#EXT-X-MAP:'):
                uri_match = re.search(r'URI="([^"]+)"', line)
                if uri_match:
                    init_segment = uri_match.group(1)
            
            # Find duration
            elif line.startswith('#EXTINF:'):
                # Format: #EXTINF:4.000000,
                try:
                    duration_str = line.split(':')[1].split(',')[0]
                    current_duration = float(duration_str)
                except:
                    current_duration = 0.0
            
            # Find media segments
            elif line and not line.startswith('#'):
                media_segments.append({
                    'url': line,
                    'duration': current_duration
                })
                current_duration = 0.0
        
        return {
            'init_segment': init_segment,
            'media_segments': media_segments
        }
    
    def _get_base_url(self, m3u8_url: str) -> str:
        """Get base URL from m3u8 URL"""
        return m3u8_url.rsplit('/', 1)[0] + '/'
    
    async def _download_file(self, url: str, output_path: str):
        """Download a single file"""
        async with self.session.get(url) as response:
            if response.status != 200:
                raise Exception(f"Failed to download {url}: HTTP {response.status}")
            
            with open(output_path, 'wb') as f:
                while True:
                    chunk = await response.content.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
    
    def _combine_segments(
        self,
        init_path: Optional[Path],
        segment_paths: List[Path],
        output_path: str,
        trim_start: Optional[float] = None,
        trim_duration: Optional[float] = None,
    ):
        """
        Combine init segment and media segments into final video.
        
        fMP4 세그먼트를 바이트 단순 결합하면 moov 박스에 올바른 duration이
        기록되지 않아 QuickTime 등에서 1초만 재생됩니다.
        ffmpeg으로 재먹싱하여 정상적인 progressive MP4로 변환합니다.
        """
        import subprocess

        from core.ffmpeg_utils import get_ffmpeg_binary
        ffmpeg_bin = get_ffmpeg_binary()

        # ── Step 1: 바이트 결합 → 임시 fragmented MP4 ──────────────
        output = Path(output_path)
        temp_concat = output.with_name(f"{output.stem}_raw.mp4")
        temp_remux = output.with_name(f"{output.stem}_remux.mp4")
        with open(temp_concat, "wb") as outfile:
            if init_path and init_path.exists():
                with open(init_path, "rb") as f:
                    outfile.write(f.read())
            for seg_path in segment_paths:
                if seg_path.exists():
                    with open(seg_path, "rb") as f:
                        outfile.write(f.read())

        # ── Step 2: ffmpeg으로 remux → timestamp가 정규화된 MP4 ──────
        try:
            result = subprocess.run(
                [
                    ffmpeg_bin,
                    "-y",                    # 덮어쓰기 허용
                    "-i", temp_concat,       # 입력: fragmented MP4
                    "-c", "copy",            # 재인코딩 없이 컨테이너만 변환
                    "-avoid_negative_ts", "make_zero",
                    str(temp_remux),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if result.returncode != 0:
                print(f"[ffmpeg 경고] remux 실패, 원본 유지:\n{result.stderr[-500:]}")
                import os
                temp_remux.unlink(missing_ok=True)
                if trim_start is not None or trim_duration is not None:
                    temp_concat.unlink(missing_ok=True)
                    raise RuntimeError("정확한 시간 범위 처리를 위한 ffmpeg remux에 실패했습니다.")
                os.replace(temp_concat, output)
                return

            temp_concat.unlink(missing_ok=True)

            if trim_start is None and trim_duration is None:
                import os
                os.replace(temp_remux, output)
                return

            # Segment boundaries are only approximate. Re-encode the selected
            # interval so the requested start/end are frame-accurate and the
            # result remains H.264/AAC compatible with Final Cut Pro.
            trim_cmd = [ffmpeg_bin, "-y", "-i", str(temp_remux)]
            if trim_start and trim_start > 0:
                trim_cmd += ["-ss", f"{trim_start:.6f}"]
            if trim_duration is not None:
                trim_cmd += ["-t", f"{trim_duration:.6f}"]
            trim_cmd += [
                "-map", "0:v:0?",
                "-map", "0:a:0?",
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "18",
                "-c:a", "aac",
                "-b:a", "192k",
                "-movflags", "+faststart",
                str(output),
            ]
            trim_result = subprocess.run(
                trim_cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            temp_remux.unlink(missing_ok=True)
            if trim_result.returncode != 0:
                output.unlink(missing_ok=True)
                raise RuntimeError(
                    "정확한 시간 범위 인코딩에 실패했습니다.\n"
                    f"{trim_result.stderr[-500:]}"
                )
        except FileNotFoundError:
            import os
            if trim_start is not None or trim_duration is not None:
                temp_concat.unlink(missing_ok=True)
                temp_remux.unlink(missing_ok=True)
                raise RuntimeError("정확한 시간 범위 다운로드에는 ffmpeg가 필요합니다.")
            print("[경고] ffmpeg을 찾을 수 없습니다. 재생이 정상적이지 않을 수 있습니다.")
            os.replace(temp_concat, output)
