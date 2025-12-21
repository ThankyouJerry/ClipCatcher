"""
Download Item Widget
Custom widget for displaying download progress
"""
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, 
    QProgressBar, QPushButton, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QPixmap
import os
import urllib.request

class ThumbnailLoader(QThread):
    """Thread for loading thumbnail images"""
    thumbnail_loaded = pyqtSignal(QPixmap)
    
    def __init__(self, url: str):
        super().__init__()
        self.url = url
    
    def run(self):
        """Download and load thumbnail"""
        try:
            if self.url:
                data = urllib.request.urlopen(self.url).read()
                pixmap = QPixmap()
                pixmap.loadFromData(data)
                if not pixmap.isNull():
                    # Scale to fit thumbnail size while maintaining aspect ratio
                    scaled = pixmap.scaled(160, 90, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                    self.thumbnail_loaded.emit(scaled)
        except Exception as e:
            print(f"Failed to load thumbnail: {e}")

class DownloadItemWidget(QWidget):
    """Widget for a single download item"""
    
    cancel_requested = pyqtSignal(str)  # download_id
    open_file_requested = pyqtSignal(str)  # file_path
    
    def __init__(self, download_id: str, title: str, thumbnail_url: str = ""):
        super().__init__()
        self.download_id = download_id
        self.title = title
        self.thumbnail_url = thumbnail_url
        self.output_path = ""
        
        self._init_ui()
        
        # Load thumbnail if URL provided
        if thumbnail_url:
            self._load_thumbnail()
    
    def _init_ui(self):
        """Initialize the UI"""
        # Main layout
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)
        
        # Thumbnail (placeholder for now)
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(160, 90)
        self.thumbnail_label.setStyleSheet("""
            QLabel {
                background-color: #363650;
                border-radius: 6px;
                font-size: 32px;
            }
        """)
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail_label.setText("📹")
        main_layout.addWidget(self.thumbnail_label)
        
        # Info section
        info_layout = QVBoxLayout()
        info_layout.setSpacing(6)
        
        # Title
        self.title_label = QLabel(self.title)
        self.title_label.setObjectName("titleLabel")
        self.title_label.setWordWrap(True)
        self.title_label.setMaximumWidth(400)
        info_layout.addWidget(self.title_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        info_layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("대기 중...")
        self.status_label.setObjectName("subtitleLabel")
        info_layout.addWidget(self.status_label)
        
        main_layout.addLayout(info_layout, 1)
        
        # Buttons
        button_layout = QVBoxLayout()
        button_layout.setSpacing(6)
        
        self.cancel_button = QPushButton("취소")
        self.cancel_button.setObjectName("dangerButton")
        self.cancel_button.setMaximumWidth(100)
        self.cancel_button.clicked.connect(self._on_cancel)
        button_layout.addWidget(self.cancel_button)
        
        self.open_button = QPushButton("파일 열기")
        self.open_button.setObjectName("secondaryButton")
        self.open_button.setMaximumWidth(100)
        self.open_button.setVisible(False)
        self.open_button.clicked.connect(self._on_open_file)
        button_layout.addWidget(self.open_button)
        
        button_layout.addStretch()
        
        main_layout.addLayout(button_layout)
        
        # Container frame
        container = QFrame()
        container.setLayout(main_layout)
        container.setStyleSheet("""
            QFrame {
                background-color: #2a2a3e;
                border-radius: 8px;
            }
        """)
        
        # Main widget layout
        widget_layout = QVBoxLayout()
        widget_layout.setContentsMargins(0, 0, 0, 0)
        widget_layout.addWidget(container)
        
        self.setLayout(widget_layout)
    

    
    def update_progress(self, progress: int, speed: float, eta: int):
        """Update download progress"""
        self.progress_bar.setValue(progress)
        
        # If speed/eta are 0 (e.g. manual download), don't overwrite status label
        # because update_status might be showing detailed info (e.g. segment count)
        if speed == 0 and eta == 0:
            return
            
        # Format speed
        if speed > 0:
            speed_mb = speed / (1024 * 1024)
            speed_text = f"{speed_mb:.1f} MB/s"
        else:
            speed_text = "계산 중..."
        
        # Format ETA
        if eta > 0:
            eta_min = eta // 60
            eta_sec = eta % 60
            eta_text = f"{eta_min}분 {eta_sec}초"
        else:
            eta_text = "계산 중..."
        
        self.status_label.setText(f"다운로드 중... | 속도: {speed_text} | 남은 시간: {eta_text}")
    
    def update_status(self, status: str):
        """Update status message"""
        self.status_label.setText(status)
    
    def set_completed(self, output_path: str):
        """Mark download as completed"""
        self.output_path = output_path
        self.progress_bar.setValue(100)
        self.status_label.setText("✅ 다운로드 완료!")
        self.status_label.setStyleSheet("color: #10b981; font-weight: 600;")
        
        self.cancel_button.setVisible(False)
        self.open_button.setVisible(True)
    
    def set_error(self, error_message: str):
        """Mark download as failed"""
        self.status_label.setText(f"❌ 오류: {error_message}")
        self.status_label.setStyleSheet("color: #ef4444; font-weight: 600;")
        self.cancel_button.setText("제거")
    
    def _on_cancel(self):
        """Handle cancel button click"""
        self.cancel_requested.emit(self.download_id)
    
    def _on_open_file(self):
        """Handle open file button click"""
        if self.output_path and os.path.exists(self.output_path):
            self.open_file_requested.emit(self.output_path)
    
    def _load_thumbnail(self):
        """Load thumbnail image from URL"""
        self.thumbnail_loader = ThumbnailLoader(self.thumbnail_url)
        self.thumbnail_loader.thumbnail_loaded.connect(self._set_thumbnail)
        self.thumbnail_loader.start()
    
    def _set_thumbnail(self, pixmap: QPixmap):
        """Set the loaded thumbnail image"""
        self.thumbnail_label.setPixmap(pixmap)
        self.thumbnail_label.setText("")  # Clear emoji text
"""
Download Item Widget
Custom widget for displaying download progress
"""
