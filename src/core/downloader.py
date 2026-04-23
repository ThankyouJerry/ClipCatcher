"""
Download Manager using yt-dlp
"""
import os
import uuid
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Optional, List
from PyQt6.QtCore import QObject, pyqtSignal, QThread
import yt_dlp


def _candidate_bin_dirs() -> List[str]:
    """Return candidate binary directories for app and shell launches."""
    dirs = []

    # Keep current PATH first.
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        if entry:
            dirs.append(entry)

    # Common macOS and Unix binary locations.
    dirs.extend([
        "/opt/homebrew/bin",
        "/usr/local/bin",
        "/opt/local/bin",
        "/usr/bin",
        "/bin",
        "/usr/sbin",
        "/sbin",
    ])

    # Deduplicate while preserving order.
    seen = set()
    unique = []
    for entry in dirs:
        if entry not in seen:
            seen.add(entry)
            unique.append(entry)
    return unique


def resolve_binary(binary_name: str) -> Optional[str]:
    """Resolve binary path from PATH and known fallback locations."""
    direct = shutil.which(binary_name)
    if direct:
        return direct

    for bin_dir in _candidate_bin_dirs():
        candidate = Path(bin_dir) / binary_name
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def get_binary_paths() -> Dict[str, str]:
    """Return resolved binary paths for required external tools."""
    binaries = {}
    ffmpeg_path = resolve_binary("ffmpeg")
    ffprobe_path = resolve_binary("ffprobe")

    if ffmpeg_path:
        binaries["ffmpeg"] = ffmpeg_path
    if ffprobe_path:
        binaries["ffprobe"] = ffprobe_path
    return binaries


def get_missing_binary_dependencies() -> List[str]:
    """Return missing external binaries required by yt-dlp merge workflow."""
    resolved = get_binary_paths()
    missing = []
    if "ffmpeg" not in resolved:
        missing.append("ffmpeg")
    if "ffprobe" not in resolved:
        missing.append("ffprobe")
    return missing

class DownloadWorker(QThread):
    """Worker thread for downloading videos"""
    
    progress_updated = pyqtSignal(int, float, int)  # progress%, speed, eta
    status_changed = pyqtSignal(str)  # status message
    download_completed = pyqtSignal(str)  # output_path
    download_error = pyqtSignal(str)  # error_message
    
    def __init__(self, url: str, output_path: str, cookies: str = ""):
        super().__init__()
        self.url = url
        self.output_path = output_path
        self.cookies = cookies
        self.should_stop = False
        self.cookie_file = None
    
    def run(self):
        """Run the download"""
        actual_output_path = None
        
        try:
            binary_paths = get_binary_paths()
            missing_binaries = []
            if "ffmpeg" not in binary_paths:
                missing_binaries.append("ffmpeg")
            if "ffprobe" not in binary_paths:
                missing_binaries.append("ffprobe")

            if missing_binaries:
                missing_text = ", ".join(missing_binaries)
                self.download_error.emit(
                    f"필수 도구가 없습니다: {missing_text}\n"
                    "설정 안내 팝업의 설치 링크/CLI 예시를 확인해주세요."
                )
                return

            # Create cookie file if cookies provided
            if self.cookies:
                self.cookie_file = tempfile.NamedTemporaryFile(
                    mode='w', 
                    suffix='.txt', 
                    delete=False
                )
                self.cookie_file.write(self.cookies)
                self.cookie_file.close()
            
            # Configure yt-dlp options
            ydl_opts = {
                'format': 'bestvideo+bestaudio/best',
                'outtmpl': self.output_path + '.%(ext)s',  # Let yt-dlp add extension
                'merge_output_format': 'mp4',
                'progress_hooks': [self._progress_hook],
                'quiet': True,
                'no_warnings': True,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                }
            }

            # Ensure yt-dlp can invoke ffmpeg/ffprobe even when app PATH is restricted.
            ffmpeg_path = binary_paths.get("ffmpeg")
            ffmpeg_dir = str(Path(ffmpeg_path).parent) if ffmpeg_path else ""
            if ffmpeg_dir:
                ydl_opts['ffmpeg_location'] = ffmpeg_dir
                existing_path = os.environ.get("PATH", "")
                if ffmpeg_dir not in existing_path.split(os.pathsep):
                    os.environ["PATH"] = ffmpeg_dir + os.pathsep + existing_path
            
            if self.cookie_file:
                ydl_opts['cookiefile'] = self.cookie_file.name
            
            # Start download
            self.status_changed.emit("다운로드 시작 중...")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                if self.should_stop:
                    return
                
                # Download and get info
                info = ydl.extract_info(self.url, download=True)
                
                # Get the actual output filename
                if info:
                    actual_output_path = ydl.prepare_filename(info)
            
            self.status_changed.emit("완료")
            
            # Use actual path if available, otherwise fallback to expected path
            final_path = actual_output_path if actual_output_path else (self.output_path + '.mp4')
            self.download_completed.emit(final_path)
            
        except Exception as e:
            self.download_error.emit(str(e))
        
        finally:
            # Cleanup cookie file
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
        cookies: str = ""
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
        
        Returns:
            download_id
        """
        download_id = str(uuid.uuid4())
        
        # Sanitize filename and add quality
        safe_title = self._sanitize_filename(title)
        filename = f"{safe_title}_{quality}"
        output_path = str(output_dir / filename)
        
        # Create worker
        worker = DownloadWorker(url, output_path, cookies)
        self.active_downloads[download_id] = worker
        worker.finished.connect(lambda did=download_id: self._cleanup_download(did))
        
        # Start download
        worker.start()
        
        return download_id
    
    def cancel_download(self, download_id: str):
        """Cancel a download without blocking UI."""
        if download_id in self.active_downloads:
            worker = self.active_downloads[download_id]
            worker.stop()
            del self.active_downloads[download_id]
    
    def get_worker(self, download_id: str) -> Optional[DownloadWorker]:
        """Get download worker by ID"""
        return self.active_downloads.get(download_id)

    def _cleanup_download(self, download_id: str):
        """Remove worker from active map when thread finishes."""
        if download_id in self.active_downloads:
            del self.active_downloads[download_id]
    
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
