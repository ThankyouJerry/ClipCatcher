"""
YouTube API — 시스템 yt-dlp 바이너리를 사용한 메타데이터 추출
Python yt_dlp 패키지(구버전)가 아닌 /opt/homebrew/bin/yt-dlp를 호출합니다.
"""
import json
import re
import shutil
import subprocess
from typing import Dict, List, Optional


YTDLP_BIN = shutil.which("yt-dlp") or "/opt/homebrew/bin/yt-dlp"


class YouTubeAPI:
    """YouTube video metadata extractor using system yt-dlp binary"""

    # ── URL 파싱 ────────────────────────────────────────────────

    @staticmethod
    def parse_url(url: str) -> Optional[Dict[str, str]]:
        """
        YouTube URL에서 video ID를 추출합니다.
        지원: youtube.com/watch?v=, youtu.be/, youtube.com/shorts/
        """
        m = re.search(
            r'(?:youtube\.com/watch\?.*v=|youtu\.be/|youtube\.com/shorts/)([a-zA-Z0-9_-]{11})',
            url
        )
        if m:
            return {'type': 'youtube', 'id': m.group(1), 'url': url}
        return None

    # ── 메타데이터 추출 ─────────────────────────────────────────

    def fetch_metadata(self, url: str) -> Dict:
        """
        시스템 yt-dlp 바이너리로 YouTube 영상 메타데이터를 가져옵니다.
        --dump-json 옵션을 통해 JSON으로 파싱합니다.
        """
        result = subprocess.run(
            [YTDLP_BIN, "--dump-json", "--no-warnings", url],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            err = result.stderr.strip()
            raise Exception(f"YouTube 정보 가져오기 실패:\n{err}")

        info = json.loads(result.stdout)
        resolutions = self._extract_resolutions(info)

        raw_date = info.get('upload_date', '')
        publish_date = (
            f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}"
            if len(raw_date) == 8 else raw_date
        )

        return {
            'id':              info.get('id', ''),
            'type':            'youtube',
            'title':           info.get('title', 'Untitled'),
            'thumbnail':       info.get('thumbnail', ''),
            'duration':        info.get('duration', 0) or 0,
            'channel_name':    info.get('channel') or info.get('uploader', 'Unknown'),
            'publish_date':    publish_date,
            'resolutions':     resolutions,
            'vod_status':      'ABR_HLS',   # yt-dlp 다운로드 모드 사용
            'is_downloadable': True,
            'url':             url,
        }

    # ── 내부 헬퍼 ───────────────────────────────────────────────

    @staticmethod
    def _extract_resolutions(info: dict) -> List[Dict]:
        """
        포맷 목록에서 사용 가능한 화질을 추출합니다.
        비디오 스트림(video-only or combined)을 높이 기준으로 정렬합니다.
        """
        formats = info.get('formats', [])

        # 비디오가 있는 포맷만 (vcodec != none, storyboard 제외)
        video_formats = [
            f for f in formats
            if f.get('vcodec') and f.get('vcodec') != 'none'
            and f.get('ext') not in ('mhtml',)
            and f.get('height')
        ]

        # 표준 해상도 목록에서 실제로 있는 것만 추출
        available_heights = sorted(
            {f['height'] for f in video_formats},
            reverse=True
        )
        standard = [4320, 2160, 1440, 1080, 720, 480, 360, 240, 144]
        available = [h for h in standard if h in available_heights]

        if not available:
            return [{
                'quality': 'best',
                'label':   'Best',
                'url':     info.get('webpage_url', ''),
                'height':  0,
                'bitrate': 0,
            }]

        resolutions = []
        for h in available:
            # 해당 높이 포맷들 중 최고 bitrate
            matching = [f for f in video_formats if f['height'] == h]
            bitrate = max((f.get('tbr') or 0 for f in matching), default=0)
            label = f"{h}p" if h < 2160 else ("4K" if h == 2160 else f"{h}p")
            resolutions.append({
                'quality':  f'{h}p',
                'label':    label,
                'url':      info.get('webpage_url', ''),
                'height':   h,
                'bitrate':  int(bitrate * 1000) if bitrate else 0,
            })

        return resolutions
