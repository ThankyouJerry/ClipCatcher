"""
Download Manager with automatic method selection
"""
import os
import uuid
import tempfile
import asyncio
from pathlib import Path
from typing import Dict, Optional
from PyQt6.QtCore import QObject, pyqtSignal, QThread
import yt_dlp

from core.segment_downloader import SegmentDownloader
from core.ffmpeg_utils import get_ffmpeg_binary

class DownloadWorker(QThread):
    """Worker thread for downloading videos"""
    
    progress_updated = pyqtSignal(int, float, int)  # progress%, speed, eta
    status_changed = pyqtSignal(str)  # status message
    download_completed = pyqtSignal(str)  # output_path
    download_error = pyqtSignal(str)  # error_message
    
    def __init__(
        self, 
        url: str, 
        output_path: str, 
        cookies: str = "",
        use_manual_download: bool = False,
        video_id: Optional[str] = None,
        quality: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        format_selector: Optional[str] = None,  # yt-dlp format selector (YouTube quality)
    ):
        super().__init__()
        self.url = url
        self.output_path = output_path
        self.cookies = cookies
        self.use_manual_download = use_manual_download
        self.video_id = video_id
        self.quality = quality
        self.start_time = start_time
        self.end_time = end_time
        self.format_selector = format_selector
        self.should_stop = False
        self.cookie_file = None
    
    def run(self):
        """Run the download"""
        try:
            if self.use_manual_download:
                self._run_manual_download()
            else:
                self._run_ytdlp_download()
        except Exception as e:
            self.download_error.emit(str(e))
    
    def _run_manual_download(self):
        """Run manual segment download"""
        try:
            self.status_changed.emit("수동 다운로드 시작 중...")
            
            # Create event loop for async operations
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Fetch fresh m3u8 URL (signatures expire quickly)
            from core.chzzk_api import ChzzkAPI
            api = ChzzkAPI()
            
            try:
                # Get fresh metadata with valid m3u8 URL
                fresh_metadata = loop.run_until_complete(
                    api.fetch_vod_metadata(self.video_id, self.cookies)
                )
                
                # Extract Master Playlist URL first
                m3u8_url = api.get_master_playlist_url(fresh_metadata)
                
                # Fallback to direct media URL if master not available
                if not m3u8_url:
                    m3u8_url = api.get_m3u8_url(fresh_metadata, self.quality)
                
                if not m3u8_url:
                    raise Exception("Failed to extract m3u8 URL from metadata")
                    
            except Exception as e:
                raise Exception(f"Failed to fetch fresh m3u8 URL: {str(e)}")
            
            downloader = SegmentDownloader()
            
            def progress_callback(current, total):
                if self.should_stop:
                    raise Exception("Download cancelled by user")
                
                progress = int((current / total) * 100) if total > 0 else 0
                self.progress_updated.emit(progress, 0, 0)
                self.status_changed.emit(f"다운로드 중... ({current}/{total} 세그먼트)")
            
            # Parse cookies
            cookies_dict = {}
            if self.cookies:
                for cookie in self.cookies.split(';'):
                    if '=' in cookie:
                        key, value = cookie.strip().split('=', 1)
                        cookies_dict[key] = value
            
            # Use same headers as yt-dlp
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://chzzk.naver.com/',
                'Origin': 'https://chzzk.naver.com'
            }
            
            # Run async download
            output_path = loop.run_until_complete(
                downloader.download_video(
                    m3u8_url,
                    self.output_path,
                    progress_callback,
                    headers=headers,
                    cookies=cookies_dict,
                    target_quality=self.quality,
                    start_time=self.start_time,
                    end_time=self.end_time
                )
            )
            
            loop.close()
            
            self.status_changed.emit("완료")
            self.download_completed.emit(output_path)
            
        except Exception as e:
            self.download_error.emit(f"수동 다운로드 실패: {str(e)}")
    
    def _run_ytdlp_download(self):
        """Run yt-dlp download.
        
        YouTube (format_selector 있음): 시스템 yt-dlp 바이너리 사용 (최신 버전)
        Chzzk   (format_selector 없음): Python yt_dlp 패키지 사용 (기존 방식)
        """
        if self.format_selector is not None:
            self._run_ytdlp_binary_download()
        else:
            self._run_ytdlp_package_download()

    def _run_ytdlp_binary_download(self):
        """YouTube 전용: 시스템 yt-dlp 바이너리로 다운로드"""
        import shutil
        import subprocess
        import re as _re
        import os

        ytdlp_bin = shutil.which("yt-dlp") or "/opt/homebrew/bin/yt-dlp"
        output_template = self.output_path + ".%(ext)s"

        cmd = [
            ytdlp_bin,
            "-f", self.format_selector,
            "--merge-output-format", "mp4",
            "--newline",            # 진행률 한 줄씩 출력
            "--no-warnings",
            "-o", output_template,
            self.url,
        ]

        # 시간 범위 다운로드
        if self.start_time is not None or self.end_time is not None:
            start = self.start_time or 0
            end   = self.end_time or float('inf')
            # yt-dlp download-sections 형식: "*start-end"
            if end == float('inf'):
                section = f"*{start}-inf"
            else:
                section = f"*{start}-{end}"
            cmd += ["--download-sections", section]

        print(f"DEBUG: Running yt-dlp binary: {' '.join(cmd)}")
        self.status_changed.emit("다운로드 시작 중...")

        # 진행률 파싱용 패턴
        pct_re   = _re.compile(r'\[download\]\s+([\d.]+)%')
        speed_re = _re.compile(r'([\d.]+)([KMG]?)iB/s')
        eta_re   = _re.compile(r'ETA\s+([\d:]+)')

        def _parse_speed(m):
            val = float(m.group(1))
            unit = m.group(2)
            mul = {'K': 1024, 'M': 1024**2, 'G': 1024**3}.get(unit, 1)
            return int(val * mul)

        def _parse_eta(s):
            parts = s.split(':')
            try:
                if len(parts) == 3:
                    return int(parts[0])*3600 + int(parts[1])*60 + int(parts[2])
                elif len(parts) == 2:
                    return int(parts[0])*60 + int(parts[1])
                return int(parts[0])
            except Exception:
                return 0

        # ffmpeg 경로 확보 (imageio-ffmpeg 번들 우선)
        ffmpeg_path = get_ffmpeg_binary()
        ffmpeg_dir  = os.path.dirname(ffmpeg_path)
        env = os.environ.copy()
        env['PATH'] = f"{ffmpeg_dir}:/opt/homebrew/bin:/usr/local/bin:{env.get('PATH', '')}"

        # yt-dlp에 ffmpeg 위치 명시
        cmd += ["--ffmpeg-location", ffmpeg_path]

        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1, env=env
        )

        output_path = self.output_path + ".mp4"
        for line in proc.stdout:
            if self.should_stop:
                proc.terminate()
                return

            line = line.strip()
            print(f"YTDLP OUT: {line}")
            pm = pct_re.search(line)
            if pm:
                pct   = int(float(pm.group(1)))
                speed = _parse_speed(speed_re.search(line)) if speed_re.search(line) else 0
                eta   = _parse_eta(eta_re.search(line).group(1)) if eta_re.search(line) else 0
                self.progress_updated.emit(pct, speed, eta)
                self.status_changed.emit(f"다운로드 중... {pm.group(1)}%")

            # yt-dlp가 저장한 실제 파일 경로 추적
            dest_m = _re.search(r'\[download\] Destination: (.+)', line)
            if dest_m:
                output_path = dest_m.group(1).strip()
            merge_m = _re.search(r'\[Merger\] Merging formats into "(.+)"', line)
            if merge_m:
                output_path = merge_m.group(1).strip()

        proc.wait()
        print(f"DEBUG: yt-dlp finished with code {proc.returncode}")
        if proc.returncode != 0:
            raise Exception(f"yt-dlp 다운로드 실패 (코드 {proc.returncode})")

        self.status_changed.emit("완료")
        self.download_completed.emit(output_path)

    def _run_ytdlp_package_download(self):
        """Chzzk 전용: Python yt_dlp 패키지로 다운로드"""
        actual_output_path = None
        
        try:
            # Create cookie file if cookies provided
            if self.cookies:
                self.cookie_file = tempfile.NamedTemporaryFile(
                    mode='w', 
                    suffix='.txt', 
                    delete=False
                )
                self.cookie_file.write(self.cookies)
                self.cookie_file.close()
            
            fmt = self.format_selector or 'bestvideo+bestaudio/best'
            ffmpeg_path = get_ffmpeg_binary()
            ydl_opts = {
                'format': fmt,
                'outtmpl': self.output_path + '.%(ext)s',
                'merge_output_format': 'mp4',
                'progress_hooks': [self._progress_hook],
                'quiet': True,
                'no_warnings': True,
                'ffmpeg_location': ffmpeg_path,
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }],
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                }
            }
            
            # Add range download support
            if self.start_time is not None or self.end_time is not None:
                def download_ranges_callback(info_dict, ydl):
                    return [{
                        'start_time': self.start_time if self.start_time is not None else 0,
                        'end_time': self.end_time if self.end_time is not None else float('inf')
                    }]
                ydl_opts['download_ranges'] = download_ranges_callback
            
            if self.cookie_file:
                ydl_opts['cookiefile'] = self.cookie_file.name
            
            self.status_changed.emit("다운로드 시작 중...")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                if self.should_stop:
                    return
                info = ydl.extract_info(self.url, download=True)
                if info:
                    actual_output_path = ydl.prepare_filename(info)
            
            self.status_changed.emit("완료")
            final_path = actual_output_path if actual_output_path else (self.output_path + '.mp4')
            self.download_completed.emit(final_path)
            
        except Exception as e:
            self.download_error.emit(str(e))
        
        finally:
            if self.cookie_file and os.path.exists(self.cookie_file.name):
                try:
                    os.remove(self.cookie_file.name)
                except:
                    pass
    
    def _progress_hook(self, d):
        """Progress hook for yt-dlp"""
        if self.should_stop:
            raise Exception("Download cancelled by user")
        
        if d['status'] == 'downloading':
            try:
                total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                downloaded_bytes = d.get('downloaded_bytes', 0)
                
                progress = 0
                if total_bytes > 0:
                    progress = int((downloaded_bytes / total_bytes) * 100)
                
                speed = d.get('speed', 0) or 0
                eta = d.get('eta', 0) or 0
                
                self.progress_updated.emit(progress, speed, eta)
                
                # Update status with fragment info if available
                fragment_index = d.get('fragment_index', 0)
                fragment_count = d.get('fragment_count', 0)
                if fragment_count > 0:
                    self.status_changed.emit(
                        f"다운로드 중... ({fragment_index}/{fragment_count} 조각)"
                    )
                else:
                    self.status_changed.emit("다운로드 중...")
                    
            except Exception:
                pass
        
        elif d['status'] == 'finished':
            self.status_changed.emit("병합 중...")
            self.progress_updated.emit(100, 0, 0)
    
    def stop(self):
        """Stop the download"""
        self.should_stop = True


class DownloadManager(QObject):
    """Manages multiple downloads"""
    
    def __init__(self):
        super().__init__()
        self.active_downloads: Dict[str, DownloadWorker] = {}
    
    def start_download(
        self, 
        video_id: str,
        url: str,
        title: str,
        quality: str,
        output_dir: Path,
        cookies: str = "",
        use_manual_download: bool = False,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        format_selector: Optional[str] = None,
    ) -> str:
        """
        Start a new download
        
        Args:
            video_id: Video ID
            url: Video URL
            title: Video title
            quality: Quality label (e.g., "1080p", "720p")
            output_dir: Output directory
            cookies: Cookie string
            use_manual_download: Whether to use manual segment download
            start_time: Start time in seconds
            end_time: End time in seconds
            format_selector: yt-dlp format selector string (YouTube quality)
        
        Returns:
            download_id
        """
        download_id = str(uuid.uuid4())
        
        # Sanitize filename
        safe_title = self._sanitize_filename(title)
        filename_suffix = quality
        filename = f"{safe_title}_{filename_suffix}"
        output_path = str(Path(output_dir) / filename)
        
        # Create worker
        worker = DownloadWorker(
            url, 
            output_path, 
            cookies, 
            use_manual_download=use_manual_download,
            video_id=video_id,
            quality=quality,
            start_time=start_time,
            end_time=end_time,
            format_selector=format_selector,
        )
        self.active_downloads[download_id] = worker
        
        # NOTE: Worker is NOT started here. 
        # Caller must connect signals first and then call worker.start()
        
        return download_id
    
    def cancel_download(self, download_id: str):
        """Cancel a download"""
        if download_id in self.active_downloads:
            worker = self.active_downloads[download_id]
            worker.stop()
            worker.wait()  # Wait for thread to finish
            del self.active_downloads[download_id]
    
    def get_worker(self, download_id: str) -> Optional[DownloadWorker]:
        """Get download worker by ID"""
        return self.active_downloads.get(download_id)
    
    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """Sanitize filename to remove invalid characters"""
        # Remove invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Limit length
        if len(filename) > 200:
            filename = filename[:200]
        
        return filename
