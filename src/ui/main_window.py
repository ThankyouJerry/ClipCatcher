"""
Main Window for ClipCatcher
"""
import asyncio
import subprocess
import platform
import os
from pathlib import Path
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QComboBox,
    QListWidget, QListWidgetItem, QMessageBox,
    QGroupBox, QSizePolicy, QTabWidget
)
from PyQt6.QtGui import QAction, QPixmap
from qasync import asyncSlot

from ui.download_item import DownloadItemWidget
from ui.settings_dialog import SettingsDialog
from ui.time_range_widget import TimeRangeWidget
from core.chzzk_api import ChzzkAPI
from core.youtube_api import YouTubeAPI
from core.downloader import DownloadManager
from core.config import Config
from core.dependency_check import get_missing_dependencies


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.api = ChzzkAPI()
        self.youtube_api = YouTubeAPI()
        self.download_manager = DownloadManager()
        self.current_metadata = None
        self.download_widgets = {}  # download_id -> {item, widget, bucket}
        self.pending_download_ids = []
        self.running_download_ids = set()
        self.max_concurrent_downloads = max(1, int(self.config.get("concurrent_downloads", 1)))
        
        # Load download path from config or default
        default_path = os.path.join(os.getcwd(), "downloads")
        self.download_path = self.config.get("download_path", default_path)
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path, exist_ok=True)
        
        self.setWindowTitle("ClipCatcher")
        self.setMinimumSize(1000, 750)
        self.resize(1100, 820)
        
        self._init_ui()
        self._create_menu_bar()
        QTimer.singleShot(300, self._show_dependency_guide_if_needed)
    
    def _init_ui(self):
        """Initialize the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout()
        main_layout.setSpacing(14)
        main_layout.setContentsMargins(24, 16, 24, 16)

        left_layout = QVBoxLayout()
        left_layout.setSpacing(14)
        
        # Header
        header_label = QLabel("🎬 ClipCatcher")
        header_label.setStyleSheet("""
            QLabel {
                font-size: 22px;
                font-weight: 700;
                color: #00FFA3;
                padding: 6px 0;
            }
        """)
        left_layout.addWidget(header_label)
        
        # URL Input Section
        url_group = self._create_url_input_section()
        left_layout.addWidget(url_group)
        
        # Video Info Section (hidden until URL fetched)
        self.info_group = self._create_video_info_section()
        self.info_group.setVisible(False)
        left_layout.addWidget(self.info_group)
        
        # Time Range Widget (independent section, hidden until URL fetched)
        self.time_range_widget = TimeRangeWidget()
        self.time_range_widget.setVisible(False)
        left_layout.addWidget(self.time_range_widget)
        left_layout.addStretch()

        main_layout.addLayout(left_layout, stretch=3)
        download_center = self._create_download_center_section()
        main_layout.addWidget(download_center, stretch=2)

        central_widget.setLayout(main_layout)
    
    def _create_url_input_section(self) -> QGroupBox:
        """Create URL input section"""
        group = QGroupBox("URL 입력")
        layout = QVBoxLayout()
        layout.setSpacing(12)
        
        # URL input
        input_layout = QHBoxLayout()
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("치지직 또는 YouTube URL을 입력하세요 (예: https://chzzk.naver.com/video/12345 또는 https://youtu.be/xxxxx)")
        self.url_input.returnPressed.connect(self._fetch_metadata)
        input_layout.addWidget(self.url_input)
        
        # Status indicator
        self.status_indicator = QLabel("⚪")
        self.status_indicator.setStyleSheet("""
            QLabel {
                font-size: 24px;
                padding: 0 8px;
            }
        """)
        self.status_indicator.setToolTip("URL 입력 후 정보를 가져오면 다운로드 가능 여부가 표시됩니다")
        input_layout.addWidget(self.status_indicator)
        
        self.fetch_button = QPushButton("정보 가져오기")
        self.fetch_button.clicked.connect(self._fetch_metadata)
        input_layout.addWidget(self.fetch_button)
        
        layout.addLayout(input_layout)
        
        # Status message label (hidden by default)
        self.status_message_label = QLabel()
        self.status_message_label.setWordWrap(True)
        self.status_message_label.setVisible(False)
        layout.addWidget(self.status_message_label)
        
        group.setLayout(layout)
        return group
    
    def _create_video_info_section(self) -> QGroupBox:
        """Create video info display section"""
        group = QGroupBox("영상 정보")
        layout = QVBoxLayout()
        layout.setSpacing(14)
        layout.setContentsMargins(14, 14, 14, 14)
        
        # ── Row 1: Thumbnail + Title/Channel/Quality ──────────────────
        top_row = QHBoxLayout()
        top_row.setSpacing(16)

        # Thumbnail: 16:9
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(240, 135)
        self.thumbnail_label.setStyleSheet("""
            QLabel {
                background-color: #363650;
                border-radius: 8px;
                font-size: 36px;
            }
        """)
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail_label.setText("📹")
        top_row.addWidget(self.thumbnail_label)

        # 썸네일 오른쪽 컬럼: 제목/채널/날짜 + 화질/다운로드
        text_col = QVBoxLayout()
        text_col.setSpacing(6)
        text_col.setContentsMargins(0, 4, 0, 4)

        self.title_label = QLabel()
        self.title_label.setObjectName("titleLabel")
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet("font-size: 15px; font-weight: 700; color: #eee;")
        text_col.addWidget(self.title_label)

        self.channel_name = QLabel()
        self.channel_name.setStyleSheet("font-size: 13px; color: #aaa;")
        text_col.addWidget(self.channel_name)

        self.video_date = QLabel()
        self.video_date.setStyleSheet("font-size: 12px; color: #777;")
        text_col.addWidget(self.video_date)

        text_col.addStretch()

        # 화질 + 다운로드 버튼 — 썸네일 오른쪽 컬럼 안에 배치
        quality_row = QHBoxLayout()
        quality_row.setSpacing(8)

        quality_label = QLabel("화질:")
        quality_label.setFixedWidth(36)
        quality_label.setStyleSheet("color: #aaa; font-size: 13px;")
        quality_row.addWidget(quality_label)

        self.quality_combo = QComboBox()
        self.quality_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.quality_combo.setMinimumHeight(36)
        quality_row.addWidget(self.quality_combo)

        self.download_button = QPushButton("다운로드")
        self.download_button.setFixedWidth(120)
        self.download_button.setMinimumHeight(36)
        self.download_button.clicked.connect(self._start_download)
        quality_row.addWidget(self.download_button)

        text_col.addLayout(quality_row)

        top_row.addLayout(text_col, stretch=1)
        layout.addLayout(top_row)

        group.setLayout(layout)
        return group
    
    def _create_download_center_section(self) -> QGroupBox:
        """Create right-side download center with tab views."""
        group = QGroupBox("다운로드 센터")
        layout = QVBoxLayout()
        layout.setSpacing(8)

        self.download_center_label = QLabel()
        self.download_center_label.setObjectName("subtitleLabel")
        layout.addWidget(self.download_center_label)

        self.download_tabs = QTabWidget()

        self.active_list = QListWidget()
        self.active_list.setSpacing(8)
        self.active_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.active_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.completed_list = QListWidget()
        self.completed_list.setSpacing(8)
        self.completed_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.completed_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.failed_list = QListWidget()
        self.failed_list.setSpacing(8)
        self.failed_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.failed_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.download_tabs.addTab(self.active_list, "진행중")
        self.download_tabs.addTab(self.completed_list, "완료")
        self.download_tabs.addTab(self.failed_list, "실패")
        layout.addWidget(self.download_tabs, stretch=1)

        group.setLayout(layout)
        self._refresh_download_center()
        return group
    
    def _create_menu_bar(self):
        """Create menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("파일")
        
        settings_action = QAction("설정", self)
        settings_action.triggered.connect(self._open_settings)
        file_menu.addAction(settings_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("종료", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Help menu
        help_menu = menubar.addMenu("도움말")
        
        about_action = QAction("정보", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    @asyncSlot()
    async def _fetch_metadata(self):
        """Fetch video metadata from URL"""
        url = self.url_input.text().strip()
        
        # Reset status indicator
        self.status_indicator.setText("⚪")
        self.status_indicator.setToolTip("확인 중...")
        self.status_message_label.setVisible(False)
        
        # Hide info sections
        self.info_group.setVisible(False)
        self.time_range_widget.setVisible(False)
        self.download_button.setEnabled(False)
        
        if not url:
            self.status_indicator.setText("🔴")
            self.status_indicator.setToolTip("URL을 입력해주세요")
            QMessageBox.warning(self, "오류", "URL을 입력해주세요.")
            return
        
        # Parse URL (Chzzk or YouTube)
        parsed = self.api.parse_url(url)
        if not parsed:
            self.status_indicator.setText("🔴")
            self.status_indicator.setToolTip("지원하지 않는 URL입니다")
            QMessageBox.warning(self, "오류", "올바른 치지직 또는 YouTube URL을 입력해주세요.")
            return
        
        # Disable button
        self.fetch_button.setEnabled(False)
        self.fetch_button.setText("가져오는 중...")
        self.status_indicator.setText("🟡")
        self.status_indicator.setToolTip("정보를 가져오는 중...")
        
        try:
            # Get cookies (Chzzk only)
            cookies_dict = self.config.get("cookies", {})
            cookie_str = ""
            if cookies_dict.get("NID_AUT") and cookies_dict.get("NID_SES"):
                cookie_str = f"NID_AUT={cookies_dict['NID_AUT']}; NID_SES={cookies_dict['NID_SES']}"
            
            # Fetch metadata
            if parsed['type'] == 'youtube':
                # yt-dlp is synchronous → run in thread pool
                loop = asyncio.get_event_loop()
                metadata = await loop.run_in_executor(
                    None, self.youtube_api.fetch_metadata, url
                )
            elif parsed['type'] == 'vod':
                metadata = await self.api.fetch_vod_metadata(parsed['id'], cookie_str)
            else:
                metadata = await self.api.fetch_clip_metadata(parsed['id'], cookie_str)
            
            self.current_metadata = metadata
            self._display_metadata(metadata)
            
        except Exception as e:
            self.status_indicator.setText("🔴")
            self.status_indicator.setToolTip(f"오류: {str(e)}")
            QMessageBox.critical(self, "오류", f"메타데이터를 가져오는데 실패했습니다:\n{str(e)}")
        
        finally:
            self.fetch_button.setEnabled(True)
            self.fetch_button.setText("정보 가져오기")
    
    def _display_metadata(self, metadata: dict):
        """Display fetched metadata"""
        self.current_metadata = metadata
        
        # Show info sections
        self.info_group.setVisible(True)
        
        # Update text info
        self.title_label.setText(metadata['title'])
        self.channel_name.setText(metadata.get('channel_name', ''))
        
        # Format publish date if available
        publish_date = metadata.get('publish_date', '')
        self.video_date.setText(publish_date)
        
        # Update Time Range Widget with duration, and show it
        duration = metadata.get('duration', 0)
        self.time_range_widget.set_duration(duration)
        self.time_range_widget.setVisible(True)
        
        # Update status indicator
        is_downloadable = metadata.get('is_downloadable', False)
        vod_status = metadata.get('vod_status', 'UNKNOWN')
        
        if is_downloadable:
            self.status_indicator.setText("🟢")
            self.status_indicator.setToolTip("다운로드 가능")
            self.status_message_label.setVisible(False)
            self.download_button.setEnabled(True)
            self.download_button.setText("다운로드")
        else:
            # Fast replay / upload state - Manual download available
            self.status_indicator.setText("🟠")
            self.status_indicator.setToolTip("수동 다운로드 (느릴 수 있음)")
            self.status_message_label.setVisible(True)
            self.status_message_label.setStyleSheet("""
                QLabel {
                    color: #FF9F43;
                    background-color: rgba(255, 159, 67, 0.1);
                    padding: 10px;
                    border-radius: 8px;
                    font-size: 13px;
                }
            """)
            self.status_message_label.setText(
                f"⚠️ 빠른 다시보기 상태 (vodStatus: {vod_status})\n"
                f"수동 다운로드 모드로 진행됩니다.\n"
                f"속도가 느릴 수 있으며, 완료까지 시간이 걸립니다."
            )
            self.download_button.setEnabled(True)
            self.download_button.setText("다운로드")
        
        # Load thumbnail
        thumbnail_url = metadata.get('thumbnail', '')
        if thumbnail_url:
            import urllib.request
            try:
                data = urllib.request.urlopen(thumbnail_url).read()
                pixmap = QPixmap()
                if pixmap.loadFromData(data):
                    self.thumbnail_label.setPixmap(pixmap.scaled(self.thumbnail_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            except Exception as e:
                self.thumbnail_label.setText("No Thumbnail")
        else:
            self.thumbnail_label.setText("No Thumbnail")
        
        # Update quality combo
        self.quality_combo.clear()
        for res in metadata['resolutions']:
            self.quality_combo.addItem(
                f"{res['label']} ({res.get('bitrate', 0) // 1000} kbps)",
                res # Store the full resolution dict as data
            )
    
    def _start_download(self):
        """Start the download process"""
        if not self.current_metadata:
            return
            
        # Get selected quality
        selected_res = self.quality_combo.currentData()
        if not selected_res:
            QMessageBox.warning(self, "오류", "화질을 선택해주세요.")
            return
        
        url = selected_res['url'] # Use the URL from the selected resolution
        quality_label = selected_res['label'] # Use the label for display
        title = self.current_metadata['title']
        video_id = self.current_metadata['id']
        
        # Check if manual download is needed
        # YouTube/Chzzk ABR_HLS: use yt-dlp
        # Chzzk VOD_ON_AIR (fast replay): manual segment download
        content_type = self.current_metadata.get('type', 'vod')
        vod_status    = self.current_metadata.get('vod_status', '')
        use_manual_download = (
            content_type == 'vod'
            and vod_status != 'ABR_HLS'
        )
        
        # Build yt-dlp format_selector for quality selection
        # Applies to both YouTube and Chzzk ABR_HLS (yt-dlp handles both)
        format_selector = None
        height = selected_res.get('height', 0)
        if content_type == 'youtube' or (content_type == 'vod' and vod_status == 'ABR_HLS'):
            if height:
                format_selector = f'bestvideo[height<={height}]+bestaudio/best[height<={height}]'
            else:
                format_selector = 'bestvideo+bestaudio/best'
            # Use page URL (yt-dlp resolves actual stream URL from it)
            url = self.current_metadata.get('url', url)

        
        # Check split download
        try:
            time_range = self.time_range_widget.get_time_range()
            print(f"DEBUG time_range: {time_range}")
            print(f"DEBUG radio_partial checked: {self.time_range_widget.radio_partial.isChecked()}")
            print(f"DEBUG start_input: '{self.time_range_widget.start_input.text()}'")
            print(f"DEBUG end_input:   '{self.time_range_widget.end_input.text()}'")
        except ValueError as e:
            QMessageBox.warning(self, "입력 오류", str(e))
            return
            
        if not time_range:
            # Download full video
            self._initiate_download(video_id, url, title, quality_label, use_manual_download,
                                    format_selector=format_selector)
        else:
            # Download selected part
            part_title = f"{title} ({time_range['start']}초~)"
            if time_range['end']:
                part_title = f"{title} ({time_range['start']}초~{time_range['end']}초)"
            
            print(f"DEBUG: starting partial download start={time_range['start']} end={time_range['end']}")
            self._initiate_download(
                video_id, url, part_title, quality_label, use_manual_download,
                start_time=time_range['start'],
                end_time=time_range['end'],
                format_selector=format_selector,
            )

        
        # Show confirmation
        QMessageBox.information(
            self,
            "다운로드 시작",
            f"다운로드가 시작되었습니다!\n저장 위치: {self.download_path}"
        )
        
    def _initiate_download(
        self, 
        video_id, 
        url, 
        title, 
        quality, 
        use_manual, 
        start_time=None, 
        end_time=None,
        format_selector=None,
    ):
        """Helper to start a single download task"""
        from datetime import date
        today = date.today().strftime("%Y-%m-%d")
        output_dir = Path(self.download_path) / today
        output_dir.mkdir(parents=True, exist_ok=True)
        
        cookies_header = self.config.get_cookie_header()
        cookies_netscape = self.config.get_cookies_netscape()
        
        download_id = self.download_manager.start_download(
            video_id=video_id,
            url=url,
            title=title,
            quality=quality,
            output_dir=str(output_dir),
            cookies_header=cookies_header,
            cookies_netscape=cookies_netscape,
            use_manual_download=use_manual,
            start_time=start_time,
            end_time=end_time,
            format_selector=format_selector,
        )
        
        # Create UI item
        widget = DownloadItemWidget(
            download_id=download_id,
            title=title,
            thumbnail_url=self.current_metadata.get('thumbnail', '') # Use current metadata thumbnail
        )
        
        # Connect signals
        worker = self.download_manager.get_worker(download_id)
        if worker:
            worker.progress_updated.connect(widget.update_progress)
            worker.status_changed.connect(widget.update_status)
            worker.download_completed.connect(widget.set_completed)
            worker.download_error.connect(widget.set_error)
            worker.download_completed.connect(
                lambda output_path, did=download_id: self._on_download_completed(did, output_path)
            )
            worker.download_error.connect(
                lambda error_message, did=download_id: self._on_download_failed(did, error_message)
            )
        
        widget.cancel_requested.connect(self._cancel_download)
        widget.open_file_requested.connect(self._open_file)
        
        # Add to active tab first (queued / running state)
        item = QListWidgetItem(self.active_list)
        item.setSizeHint(widget.sizeHint())
        self.active_list.addItem(item)
        self.active_list.setItemWidget(item, widget)

        self.download_widgets[download_id] = {
            "item": item,
            "widget": widget,
            "bucket": "active",
            "title": title,
            "thumbnail_url": self.current_metadata.get('thumbnail', ''),
        }
        self.pending_download_ids.append(download_id)
        widget.update_status("대기열에 추가됨")
        self._refresh_download_center()
        self._pump_download_queue()
        
    def _cancel_download(self, download_id: str):
        """Cancel a download"""
        if download_id in self.pending_download_ids:
            self.pending_download_ids.remove(download_id)

        if download_id in self.running_download_ids:
            self.running_download_ids.remove(download_id)
            self.download_manager.cancel_download(download_id)
        else:
            self.download_manager.remove_download(download_id)

        self._remove_download_widget(download_id)
        self._refresh_download_center()
        self._pump_download_queue()

    def _pump_download_queue(self):
        """Start queued downloads up to concurrent limit."""
        while self.pending_download_ids and len(self.running_download_ids) < self.max_concurrent_downloads:
            download_id = self.pending_download_ids.pop(0)
            worker = self.download_manager.get_worker(download_id)
            if not worker or download_id not in self.download_widgets:
                continue
            self.running_download_ids.add(download_id)
            widget = self.download_widgets[download_id]["widget"]
            widget.update_status("다운로드 시작 중...")
            worker.start()
        self._refresh_download_center()

    def _on_download_completed(self, download_id: str, _output_path: str):
        """Handle completion: cleanup, move tab, then schedule next."""
        if download_id in self.running_download_ids:
            self.running_download_ids.remove(download_id)
        self.download_manager.remove_download(download_id)
        self._archive_download_widget(
            download_id,
            "completed",
            output_path=_output_path,
        )
        self._refresh_download_center()
        self._pump_download_queue()

    def _on_download_failed(self, download_id: str, _error_message: str):
        """Handle failure: cleanup, move tab, then schedule next."""
        if download_id in self.running_download_ids:
            self.running_download_ids.remove(download_id)
        self.download_manager.remove_download(download_id)
        self._archive_download_widget(
            download_id,
            "failed",
            error_message=_error_message,
        )
        self._refresh_download_center()
        self._pump_download_queue()

    def _archive_download_widget(
        self,
        download_id: str,
        target_bucket: str,
        output_path: str = "",
        error_message: str = "",
    ):
        """Replace active widget with a fresh widget in target tab (safer than reparent move)."""
        if download_id not in self.download_widgets:
            return
        entry = self.download_widgets[download_id]
        old_list = self._list_by_bucket(entry["bucket"])
        new_list = self._list_by_bucket(target_bucket)
        if old_list is None or new_list is None:
            return

        old_item = entry["item"]
        old_row = old_list.row(old_item)
        if old_row >= 0:
            taken = old_list.takeItem(old_row)
            del taken
        old_widget = entry["widget"]
        old_widget.deleteLater()

        new_widget = DownloadItemWidget(
            download_id=download_id,
            title=entry.get("title", ""),
            thumbnail_url=entry.get("thumbnail_url", ""),
        )
        new_widget.cancel_requested.connect(self._cancel_download)
        new_widget.open_file_requested.connect(self._open_file)

        if target_bucket == "completed":
            new_widget.set_completed(output_path)
        elif target_bucket == "failed":
            new_widget.set_error(error_message)
        else:
            new_widget.update_status("대기열에 추가됨")

        new_item = QListWidgetItem(new_list)
        new_item.setSizeHint(new_widget.sizeHint())
        new_list.addItem(new_item)
        new_list.setItemWidget(new_item, new_widget)

        entry["item"] = new_item
        entry["widget"] = new_widget
        entry["bucket"] = target_bucket

    def _remove_download_widget(self, download_id: str):
        """Remove download widget row from current tab list."""
        if download_id not in self.download_widgets:
            return
        entry = self.download_widgets[download_id]
        list_widget = self._list_by_bucket(entry["bucket"])
        if list_widget is not None:
            row = list_widget.row(entry["item"])
            if row >= 0:
                list_widget.takeItem(row)
        entry["widget"].deleteLater()
        del self.download_widgets[download_id]

    def _list_by_bucket(self, bucket: str):
        if bucket == "active":
            return self.active_list
        if bucket == "completed":
            return self.completed_list
        if bucket == "failed":
            return self.failed_list
        return None

    def _refresh_download_center(self):
        """Refresh center label and tab titles."""
        active_count = self.active_list.count()
        completed_count = self.completed_list.count()
        failed_count = self.failed_list.count()
        queued_count = len(self.pending_download_ids)
        running_count = len(self.running_download_ids)

        self.download_center_label.setText(
            f"실행 {running_count}/{self.max_concurrent_downloads} | 대기 {queued_count} | 전체 {active_count + completed_count + failed_count}"
        )
        self.download_tabs.setTabText(0, f"진행중 ({active_count})")
        self.download_tabs.setTabText(1, f"완료 ({completed_count})")
        self.download_tabs.setTabText(2, f"실패 ({failed_count})")
    
    def _open_file(self, file_path: str):
        """Open downloaded file"""
        try:
            if platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', file_path])
            elif platform.system() == 'Windows':
                os.startfile(file_path)
            else:  # Linux
                subprocess.run(['xdg-open', file_path])
        except Exception as e:
            QMessageBox.warning(self, "오류", f"파일을 열 수 없습니다:\n{str(e)}")
    
    def _open_settings(self):
        """Open settings dialog"""
        dialog = SettingsDialog(self.config, self)
        if dialog.exec():
            self.download_path = self.config.get(
                "download_path",
                os.path.join(os.getcwd(), "downloads")
            )
            self.max_concurrent_downloads = max(
                1, int(self.config.get("concurrent_downloads", 1))
            )
            os.makedirs(self.download_path, exist_ok=True)
            self._refresh_download_center()
            self._pump_download_queue()
    
    def _show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "ClipCatcher 정보",
            "<h3>ClipCatcher</h3>"
            "<p>네이버 치지직 VOD 및 클립 다운로더</p>"
            "<p>Version 1.0.0</p>"
            "<p>PyQt6 기반 데스크톱 애플리케이션</p>"
        )

    def _show_dependency_guide_if_needed(self):
        """Show external tool setup guide when required dependencies are missing."""
        missing = get_missing_dependencies()
        if not missing:
            return

        missing_names = ", ".join(item.name for item in missing)
        system_name = platform.system()

        if system_name == "Darwin":
            cli_guide = (
                "brew install ffmpeg yt-dlp\n"
                "또는\n"
                "python3 -m pip install -U yt-dlp imageio-ffmpeg"
            )
            links = (
                "• yt-dlp: https://github.com/yt-dlp/yt-dlp#installation\n"
                "• ffmpeg: https://ffmpeg.org/download.html"
            )
        elif system_name == "Windows":
            cli_guide = (
                "winget install yt-dlp.yt-dlp\n"
                "winget install Gyan.FFmpeg"
            )
            links = (
                "• yt-dlp: https://github.com/yt-dlp/yt-dlp#installation\n"
                "• ffmpeg: https://ffmpeg.org/download.html"
            )
        else:
            cli_guide = (
                "sudo apt install ffmpeg\n"
                "python3 -m pip install -U yt-dlp imageio-ffmpeg"
            )
            links = (
                "• yt-dlp: https://github.com/yt-dlp/yt-dlp#installation\n"
                "• ffmpeg: https://ffmpeg.org/download.html"
            )

        QMessageBox.warning(
            self,
            "외부 도구 설치 안내",
            f"다음 도구를 찾지 못했습니다: {missing_names}\n\n"
            "1) 다운로드 링크\n"
            f"{links}\n\n"
            "2) CLI 설치 방법\n"
            f"{cli_guide}\n\n"
            "설치 후 앱을 다시 실행하면 자동으로 인식됩니다."
        )
