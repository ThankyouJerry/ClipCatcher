"""Qt adapters for the shared, headless download implementation."""
import re
import uuid
from pathlib import Path
from typing import Dict, Optional
from PyQt6.QtCore import QObject, pyqtSignal, QThread, QTimer

from core.download_job import (
    DownloadJob,
    build_final_cut_format_selector,
    select_download_format,
    is_youtube_url,
)


class DownloadWorker(DownloadJob, QThread):
    """Run the shared download job with the GUI's existing Qt signals."""

    progress_updated = pyqtSignal(int, float, int)
    status_changed = pyqtSignal(str)
    download_completed = pyqtSignal(str)
    download_error = pyqtSignal(str)

    def __init__(self, *args, **kwargs):
        QThread.__init__(self)
        DownloadJob.__init__(self, *args, **kwargs)

    def run(self):
        DownloadJob.run(self)


class DownloadManager(QObject):
    """Manages multiple downloads"""
    
    def __init__(self):
        super().__init__()
        self.active_downloads: Dict[str, DownloadWorker] = {}
        self._retired_downloads: Dict[str, DownloadWorker] = {}
    
    def start_download(
        self, 
        video_id: str,
        url: str,
        title: str,
        quality: str,
        output_dir: Path,
        cookies_header: str = "",
        cookies_netscape: str = "",
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
            cookies_header: Cookie header string (e.g. NID_AUT=...; NID_SES=...)
            cookies_netscape: Netscape cookie file content
            use_manual_download: Whether to use manual segment download
            start_time: Start time in seconds
            end_time: End time in seconds
            format_selector: yt-dlp format selector string (YouTube quality)
        
        Returns:
            download_id
        """
        download_id = str(uuid.uuid4())
        
        # Keep each queue entry distinct and leave room for yt-dlp suffixes.
        suffix = (
            f"_{self._sanitize_filename(quality, 48)}"
            f"_{self._sanitize_filename(video_id, 40)}_{download_id[:8]}"
        )
        safe_title = self._sanitize_filename(title, 220 - len(suffix.encode('utf-8')))
        filename = f"{safe_title}{suffix}"
        output_path = str(Path(output_dir) / filename)
        
        # Create worker
        worker = DownloadWorker(
            url, 
            output_path, 
            cookies_header=cookies_header,
            cookies_netscape=cookies_netscape,
            use_manual_download=use_manual_download,
            video_id=video_id,
            quality=quality,
            start_time=start_time,
            end_time=end_time,
            format_selector=format_selector,
        )
        self.active_downloads[download_id] = worker
        worker.finished.connect(
            lambda did=download_id: self._release_retired_download(did)
        )
        
        # NOTE: Worker is NOT started here. 
        # Caller must connect signals first and then call worker.start()
        
        return download_id
    
    def cancel_download(self, download_id: str):
        """Cancel a download and release it after its thread exits."""
        worker = self.active_downloads.get(download_id)
        if not worker:
            return

        worker.stop()
        self.remove_download(download_id)
    
    def get_worker(self, download_id: str) -> Optional[DownloadWorker]:
        """Get download worker by ID"""
        return self.active_downloads.get(download_id)

    def remove_download(self, download_id: str):
        """Hide a worker now, but keep its QThread alive until it exits."""
        worker = self.active_downloads.pop(download_id, None)
        if worker is not None and worker.isRunning():
            self._retired_downloads[download_id] = worker

    def _release_retired_download(self, download_id: str):
        worker = self._retired_downloads.get(download_id)
        if worker is None:
            return
        if worker.isRunning():
            QTimer.singleShot(10, lambda: self._release_retired_download(download_id))
        else:
            self._retired_downloads.pop(download_id, None)
    
    @staticmethod
    def _sanitize_filename(filename: str, max_bytes: int = 200) -> str:
        """Sanitize filename to remove invalid characters"""
        filename = re.sub(r'[\x00-\x1f<>:"/\\|?*]', '_', str(filename))
        filename = filename.encode('utf-8')[:max_bytes].decode('utf-8', errors='ignore')
        return filename.rstrip(' .') or 'video'
