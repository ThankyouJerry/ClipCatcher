"""
Main Window for ClipCatcher
"""
import asyncio
import json
import math
import subprocess
import platform
import os
from pathlib import Path
from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QComboBox,
    QListWidget, QListWidgetItem, QMessageBox,
    QGroupBox, QSizePolicy, QTabWidget, QFileDialog, QPlainTextEdit,
    QRadioButton
)
from PyQt6.QtGui import QAction, QPixmap
from qasync import asyncSlot

from ui.download_item import DownloadItemWidget, ThumbnailLoader
from ui.settings_dialog import SettingsDialog
from ui.time_range_widget import TimeRangeWidget
from core.chzzk_api import ChzzkAPI
from core.youtube_api import YouTubeAPI
from core.downloader import DownloadManager
from core.config import Config
from core.dependency_check import check_yt_dlp, get_missing_dependencies
from core.app_tools import find_app_tool, get_app_bin_dir, install_or_update_yt_dlp


class YtDlpStatusWorker(QThread):
    """Probe the local installation without blocking the GUI."""

    completed = pyqtSignal(object)

    def run(self):
        from core.dependency_check import ToolStatus
        try:
            status = check_yt_dlp()
        except Exception as exc:
            status = ToolStatus("yt-dlp", None, False, error=str(exc))
        self.completed.emit(status)


class YtDlpInstallWorker(QThread):
    """Install the app-owned yt-dlp without blocking the GUI event loop."""

    completed = pyqtSignal(str)
    failed = pyqtSignal(str)

    def run(self):
        try:
            self.completed.emit(install_or_update_yt_dlp())
        except Exception as exc:
            self.failed.emit(str(exc))


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
        self.thumbnail_loaders = []
        self.ytdlp_install_worker = None
        self.ytdlp_status_worker = None
        self._ytdlp_status_result = None
        self._closing = False
        self._allow_close = False
        self._batch_active = False
        self._batch_cancel_requested = False
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
        QTimer.singleShot(600, self._show_ytdlp_install_prompt_if_needed)
    
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
        group = QGroupBox("다운로드 입력")
        layout = QVBoxLayout()
        layout.setSpacing(12)

        mode_layout = QHBoxLayout()
        self.single_mode_radio = QRadioButton("단일 파일")
        self.single_mode_radio.setObjectName("inputMode")
        self.single_mode_radio.setChecked(True)
        self.batch_mode_radio = QRadioButton("여러 파일")
        self.batch_mode_radio.setObjectName("inputMode")
        self.batch_mode_radio.toggled.connect(self._set_input_mode)
        mode_layout.addWidget(self.single_mode_radio)
        mode_layout.addWidget(self.batch_mode_radio)
        mode_layout.addStretch()
        layout.addLayout(mode_layout)

        self.single_input_widget = QWidget()
        single_layout = QVBoxLayout(self.single_input_widget)
        single_layout.setContentsMargins(0, 0, 0, 0)
        input_layout = QHBoxLayout()

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("치지직 또는 YouTube URL을 입력하세요 (예: https://chzzk.naver.com/video/12345 또는 https://youtu.be/xxxxx)")
        self.url_input.returnPressed.connect(self._fetch_metadata)
        input_layout.addWidget(self.url_input)

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
        single_layout.addLayout(input_layout)

        self.status_message_label = QLabel()
        self.status_message_label.setWordWrap(True)
        self.status_message_label.setVisible(False)
        single_layout.addWidget(self.status_message_label)
        layout.addWidget(self.single_input_widget)

        self.batch_input_widget = QWidget()
        batch_layout = QVBoxLayout(self.batch_input_widget)
        batch_layout.setContentsMargins(0, 0, 0, 0)
        batch_hint = QLabel("영상 링크를 한 줄에 하나씩 입력하세요. 전체 영상을 확인 가능한 최고 화질로 대기열에 추가합니다.")
        batch_hint.setWordWrap(True)
        batch_layout.addWidget(batch_hint)
        self.batch_input = QPlainTextEdit()
        self.batch_input.setPlaceholderText("https://chzzk.naver.com/video/12345\nhttps://www.youtube.com/watch?v=...")
        self.batch_input.setMinimumHeight(160)
        batch_layout.addWidget(self.batch_input)
        batch_action_layout = QHBoxLayout()
        batch_action_layout.addStretch()
        self.batch_button = QPushButton("대기열에 추가")
        self.batch_button.clicked.connect(self._add_batch_downloads)
        batch_action_layout.addWidget(self.batch_button)
        batch_layout.addLayout(batch_action_layout)
        self.batch_input_widget.hide()
        layout.addWidget(self.batch_input_widget)

        group.setLayout(layout)
        return group

    def _set_input_mode(self, batch_mode: bool):
        self.single_input_widget.setVisible(not batch_mode)
        self.batch_input_widget.setVisible(batch_mode)
        self.info_group.setVisible(not batch_mode and self.current_metadata is not None)
        self.time_range_widget.setVisible(not batch_mode and self.current_metadata is not None)
    
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

        self.video_duration = QLabel()
        self.video_duration.setStyleSheet("font-size: 12px; color: #888;")
        text_col.addWidget(self.video_duration)

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

        center_header = QHBoxLayout()
        center_header.setSpacing(8)
        center_header.addWidget(self.download_center_label, stretch=1)

        self.open_download_folder_button = QPushButton("저장 폴더 열기")
        self.open_download_folder_button.setObjectName("secondaryButton")
        self.open_download_folder_button.setToolTip(
            "설정된 다운로드 저장 폴더를 엽니다"
        )
        self.open_download_folder_button.setMinimumWidth(112)
        self.open_download_folder_button.clicked.connect(
            self._open_download_folder
        )
        center_header.addWidget(self.open_download_folder_button)
        layout.addLayout(center_header)

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

        import_clipradar_action = QAction("ClipRadar JSON 가져오기", self)
        import_clipradar_action.triggered.connect(self._import_clipradar_json)
        file_menu.addAction(import_clipradar_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("종료", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Help menu
        help_menu = menubar.addMenu("도움말")
        
        about_action = QAction("정보", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

        self.ytdlp_status_action = QAction("yt-dlp 상태 확인", self)
        self.ytdlp_status_action.triggered.connect(self._check_ytdlp_status)
        help_menu.addAction(self.ytdlp_status_action)

        install_ytdlp_action = QAction("yt-dlp 설치/업데이트", self)
        install_ytdlp_action.triggered.connect(self._install_or_update_ytdlp)
        help_menu.addAction(install_ytdlp_action)
    
    @asyncSlot()
    async def _fetch_metadata(self):
        """Fetch video metadata from URL"""
        url = self.url_input.text().strip()
        
        # Reset status indicator
        self.status_indicator.setText("⚪")
        self.status_indicator.setToolTip("확인 중...")
        self.status_message_label.setVisible(False)
        
        # Hide info sections
        self.current_metadata = None
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
            
            metadata = await self._load_metadata(url, parsed, cookie_str)
            
            self.current_metadata = metadata
            self._display_metadata(metadata)
            
        except Exception as e:
            self.status_indicator.setText("🔴")
            self.status_indicator.setToolTip(f"오류: {str(e)}")
            QMessageBox.critical(self, "오류", f"메타데이터를 가져오는데 실패했습니다:\n{str(e)}")
        
        finally:
            self.fetch_button.setEnabled(True)
            self.fetch_button.setText("정보 가져오기")

    async def _load_metadata(self, url: str, parsed: dict, cookie_str: str) -> dict:
        if parsed['type'] == 'youtube':
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, self.youtube_api.fetch_metadata, url)
        if parsed['type'] == 'vod':
            return await self.api.fetch_vod_metadata(parsed['id'], cookie_str)
        return await self.api.fetch_clip_metadata(parsed['id'], cookie_str)

    @staticmethod
    def _batch_urls(text: str):
        urls = []
        seen = set()
        for line in text.splitlines():
            url = line.strip()
            if url and url not in seen:
                seen.add(url)
                urls.append(url)
        return urls

    @asyncSlot()
    async def _add_batch_downloads(self):
        if self._batch_active:
            self._batch_cancel_requested = True
            self.statusBar().showMessage("남은 링크 추가를 중단하는 중...")
            return
        urls = self._batch_urls(self.batch_input.toPlainText())
        if not urls:
            QMessageBox.warning(self, "입력 오류", "영상 링크를 한 줄에 하나씩 입력해주세요.")
            return
        if len(urls) > 100:
            QMessageBox.warning(self, "입력 오류", "한 번에 최대 100개 링크를 추가할 수 있습니다.")
            return

        self._batch_cancel_requested = False
        self._batch_active = True
        try:
            queued, failures = await self._enqueue_batch_urls(urls)
        finally:
            self._batch_active = False
            self.batch_button.setText("대기열에 추가")
            if not self._closing:
                self.statusBar().clearMessage()

        if self._closing:
            return

        message = f"{queued}개를 다운로드 대기열에 추가했습니다."
        if failures:
            message += f"\n\n추가하지 못한 링크 {len(failures)}개:\n" + "\n".join(failures[:10])
            if len(failures) > 10:
                message += f"\n외 {len(failures) - 10}개"
        QMessageBox.information(self, "여러 링크 추가 결과", message)

    async def _enqueue_batch_urls(self, urls):
        """Resolve each URL in order, then reuse the regular download queue."""
        queued = 0
        failures = []
        cookies = self.config.get("cookies", {})
        cookie_str = ""
        if cookies.get("NID_AUT") and cookies.get("NID_SES"):
            cookie_str = f"NID_AUT={cookies['NID_AUT']}; NID_SES={cookies['NID_SES']}"
        for index, url in enumerate(urls, 1):
            if self._closing or self._batch_cancel_requested:
                break
            self.batch_button.setText("추가 중단")
            self.statusBar().showMessage(f"영상 정보 확인 중: {index}/{len(urls)}")
            parsed = self.api.parse_url(url)
            if not parsed:
                failures.append(f"{index}번: 지원하지 않는 URL")
                continue
            try:
                metadata = await self._load_metadata(url, parsed, cookie_str)
                if self._closing or self._batch_cancel_requested:
                    break
                resolutions = metadata.get("resolutions") or []
                if not resolutions:
                    raise ValueError("사용 가능한 화질이 없습니다")
                self._queue_metadata_download(metadata, resolutions[0])
                queued += 1
            except Exception as exc:
                failures.append(f"{index}번: {str(exc)[:120]}")
        return queued, failures
    
    def _display_metadata(self, metadata: dict):
        """Display fetched metadata"""
        self.current_metadata = metadata
        
        show_details = self.single_mode_radio.isChecked()
        self.info_group.setVisible(show_details)
        
        # Update text info
        self.title_label.setText(metadata['title'])
        self.channel_name.setText(metadata.get('channel_name', ''))
        
        # Format publish date if available
        publish_date = metadata.get('publish_date', '')
        self.video_date.setText(publish_date)
        
        # Update Time Range Widget with duration, and show it
        duration = metadata.get('duration', 0)
        duration_is_reliable = metadata.get('duration_is_reliable', True)
        self.time_range_widget.set_duration(
            duration,
            enforce_limit=duration_is_reliable,
        )
        if duration > 0:
            duration_text = self.time_range_widget.format_time(duration)
            suffix = "" if duration_is_reliable else " (다운로드 시 재확인)"
            self.video_duration.setText(f"영상 길이: {duration_text}{suffix}")
        else:
            self.video_duration.setText("영상 길이: 확인 불가")
        self.time_range_widget.setVisible(show_details)
        
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
            self.thumbnail_label.setText("Loading...")
            loader = ThumbnailLoader(thumbnail_url)
            self.thumbnail_loaders.append(loader)
            loader.thumbnail_loaded.connect(self._set_main_thumbnail)
            loader.finished.connect(
                lambda current=loader: self._release_thumbnail_loader(current)
            )
            loader.start()
        else:
            self.thumbnail_label.setText("No Thumbnail")
        
        # Update quality combo; an unknown bitrate must not look like a 0 kbps stream.
        self.quality_combo.clear()
        for res in metadata['resolutions']:
            bitrate = res.get('bitrate')
            known_bitrate = (
                isinstance(bitrate, (int, float))
                and not isinstance(bitrate, bool)
                and math.isfinite(bitrate)
                and bitrate >= 1000
            )
            bitrate_text = f" ({int(bitrate // 1000)} kbps)" if known_bitrate else ""
            self.quality_combo.addItem(
                f"{res['label']}{bitrate_text}",
                res # Store the full resolution dict as data
            )
        self.quality_combo.setToolTip(
            "표시된 수치는 제공된 예상 비트레이트입니다. "
            "수치가 없어도 표시된 해상도를 선택할 수 있습니다. "
            "YouTube는 Final Cut 호환 H.264 화질을 표시합니다."
        )

    def _set_main_thumbnail(self, url: str, data: bytes):
        """Decode and display thumbnail data on the GUI thread."""
        if not self.current_metadata or self.current_metadata.get("thumbnail") != url:
            return
        pixmap = QPixmap()
        if not pixmap.loadFromData(data):
            self.thumbnail_label.setText("No Thumbnail")
            return
        self.thumbnail_label.setPixmap(
            pixmap.scaled(
                self.thumbnail_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        self.thumbnail_label.setText("")

    def _release_thumbnail_loader(self, loader: ThumbnailLoader):
        """Keep QThreads alive until their network request has finished."""
        if loader in self.thumbnail_loaders:
            self.thumbnail_loaders.remove(loader)
        loader.deleteLater()
    
    def _start_download(self):
        """Start the download process"""
        if not self.current_metadata:
            return
            
        # Get selected quality
        selected_res = self.quality_combo.currentData()
        if not selected_res:
            QMessageBox.warning(self, "오류", "화질을 선택해주세요.")
            return
        
        # Check split download
        try:
            time_range = self.time_range_widget.get_time_range()
        except ValueError as e:
            QMessageBox.warning(self, "입력 오류", str(e))
            return
        self._queue_metadata_download(self.current_metadata, selected_res, time_range)

        
        # Show confirmation
        QMessageBox.information(
            self,
            "다운로드 시작",
            f"다운로드가 시작되었습니다!\n저장 위치: {self.download_path}"
        )

    def _queue_metadata_download(self, metadata: dict, selected_res: dict, time_range=None):
        """Enqueue one item using the same format rules for single and batch input."""
        content_type = metadata.get('type', 'vod')
        vod_status = metadata.get('vod_status', '')
        use_manual = content_type == 'vod' and vod_status != 'ABR_HLS'
        url = selected_res['url']
        height = selected_res.get('height', 0)
        format_selector = None
        if content_type == 'clip':
            format_selector = 'best'
            url = metadata.get('url', url)
        elif content_type == 'youtube' or (content_type == 'vod' and not use_manual):
            if height:
                format_selector = f'bestvideo[height<={height}]+bestaudio/best[height<={height}]'
            else:
                format_selector = 'bestvideo+bestaudio/best'
            url = metadata.get('url', url)

        title = metadata['title']
        start_time = time_range['start'] if time_range else None
        end_time = time_range['end'] if time_range else None
        if time_range:
            title += f" ({start_time}초~{end_time}초)" if end_time else f" ({start_time}초~)"
        self._initiate_download(
            metadata['id'], url, title, selected_res['label'], use_manual,
            start_time=start_time, end_time=end_time,
            format_selector=format_selector, thumbnail_url=metadata.get('thumbnail', ''),
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
        thumbnail_url=None,
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
        if thumbnail_url is None:
            thumbnail_url = (self.current_metadata or {}).get('thumbnail', '')
        widget = DownloadItemWidget(
            download_id=download_id,
            title=title,
            thumbnail_url=thumbnail_url,
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
            "thumbnail_url": thumbnail_url,
        }
        self.pending_download_ids.append(download_id)
        widget.update_status("대기열에 추가됨")
        self._refresh_download_center()
        self._pump_download_queue()

    def _import_clipradar_json(self):
        """Import ClipRadar report JSON and enqueue highlight range downloads."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "ClipRadar JSON 가져오기",
            str(Path.home()),
            "ClipRadar JSON (*.json);;JSON Files (*.json);;All Files (*)",
        )
        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                report = json.load(f)
            if report.get("schemaVersion") != "clipradar.report.v1":
                raise ValueError("지원하지 않는 ClipRadar JSON 형식입니다.")

            video = report.get("video") or {}
            videos = report.get("videos") or []
            videos_by_id = {item.get("id"): item for item in videos if item.get("id")}
            videos_by_url = {item.get("url"): item for item in videos if item.get("url")}
            moments = report.get("moments") or []
            if not moments:
                raise ValueError("다운로드할 하이라이트 구간이 없습니다.")

            fallback_url = video.get("url") or ""

            queued = 0
            missing_url_count = 0
            invalid_url_count = 0
            invalid_range_count = 0
            for moment in moments:
                moment_url = moment.get("url") or moment.get("videoUrl") or fallback_url
                if not moment_url:
                    missing_url_count += 1
                    continue

                video_ref = (
                    videos_by_id.get(moment.get("videoId"))
                    or videos_by_url.get(moment_url)
                    or video
                )
                parsed = self.api.parse_url(moment_url)
                if not parsed:
                    invalid_url_count += 1
                    continue
                video_id = (
                    moment.get("videoId")
                    or video_ref.get("id")
                    or parsed.get("id")
                    or "clipradar"
                )
                content_type = parsed["type"]
                vod_title = (
                    moment.get("videoTitle")
                    or moment.get("vodTitle")
                    or video_ref.get("title")
                    or video.get("title")
                    or "ClipRadar Highlights"
                )

                self.current_metadata = {
                    "id": video_id,
                    "type": content_type,
                    "title": vod_title,
                    "thumbnail": moment.get("videoThumbnail") or video_ref.get("thumbnail", ""),
                    "url": moment_url,
                }

                start_time = self._clipradar_seconds(
                    moment.get(
                        "cutStartTimeSeconds",
                        moment.get("startTimeSeconds", moment.get("start")),
                    )
                )
                end_time = self._clipradar_seconds(
                    moment.get(
                        "cutEndTimeSeconds",
                        moment.get("endTimeSeconds", moment.get("end")),
                    )
                )
                if start_time is None and end_time is None:
                    invalid_range_count += 1
                    continue
                if end_time is not None and start_time is not None and end_time <= start_time:
                    invalid_range_count += 1
                    continue

                rank = moment.get("rank", queued + 1)
                title = moment.get("title") or f"ClipRadar 하이라이트 #{rank}"
                if len(videos) > 1:
                    download_title = f"[ClipRadar #{rank}] {vod_title} - {title}"
                else:
                    download_title = f"[ClipRadar #{rank}] {title}"
                self._initiate_download(
                    video_id=video_id,
                    url=moment_url,
                    title=download_title,
                    quality="ClipRadar",
                    use_manual=False,
                    start_time=start_time,
                    end_time=end_time,
                    format_selector="bestvideo+bestaudio/best",
                )
                queued += 1

            if queued == 0:
                if missing_url_count == len(moments):
                    raise ValueError(
                        "VOD URL이 JSON에 없습니다. report.video.url 또는 각 moment.url/videoUrl을 확인해주세요."
                    )
                if invalid_range_count == len(moments):
                    raise ValueError(
                        "유효한 시작/종료 시간이 있는 구간이 없습니다. cutStartTimeSeconds/cutEndTimeSeconds 값을 확인해주세요."
                    )
                if invalid_url_count:
                    raise ValueError(
                        "지원하지 않거나 안전하지 않은 VOD URL이 포함되어 있습니다. "
                        "CHZZK 또는 YouTube HTTPS 링크를 확인해주세요."
                    )
                raise ValueError("유효한 시작/종료 시간이 있는 구간이 없습니다.")

            QMessageBox.information(
                self,
                "ClipRadar 가져오기 완료",
                f"{queued}개 하이라이트를 다운로드 대기열에 추가했습니다.",
            )
        except Exception as e:
            QMessageBox.warning(
                self,
                "ClipRadar 가져오기 실패",
                f"JSON을 가져오지 못했습니다:\n{str(e)}",
            )

    @staticmethod
    def _clipradar_seconds(value):
        """Convert ClipRadar seconds or HH:MM:SS strings to seconds."""
        if value is None or value == "":
            return None
        if isinstance(value, (int, float)):
            return float(value)
        parts = str(value).split(":")
        try:
            total = 0
            for part in parts:
                total = total * 60 + float(part)
            return total
        except ValueError:
            return None
        
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
        if self._closing:
            return
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

    def _open_download_folder(self):
        """Open the configured root download folder."""
        folder_path = Path(self.download_path)
        try:
            folder_path.mkdir(parents=True, exist_ok=True)
            if platform.system() == "Darwin":
                subprocess.run(["open", str(folder_path)], check=True)
            elif platform.system() == "Windows":
                os.startfile(str(folder_path))
            else:
                subprocess.run(["xdg-open", str(folder_path)], check=True)
        except Exception as e:
            QMessageBox.warning(
                self,
                "오류",
                f"저장 폴더를 열 수 없습니다:\n{str(e)}",
            )
    
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
            "<p>Version 2.0.11</p>"
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

    def _show_ytdlp_install_prompt_if_needed(self):
        """Offer app-managed setup when yt-dlp is missing or cannot start."""
        if check_yt_dlp().available:
            return
        app_tool = find_app_tool("yt-dlp")

        reason = (
            "기존 앱 전용 yt-dlp가 실행되지 않아 복구가 필요합니다."
            if app_tool
            else "ClipCatcher 전용 yt-dlp가 아직 설치되지 않았습니다."
        )

        response = QMessageBox.question(
            self,
            "yt-dlp 앱 전용 설치",
            f"{reason}\n\n"
            "앱 전용 yt-dlp를 설치하면 Finder/Windows 실행 환경에서도 더 안정적으로 동작합니다.\n\n"
            f"설치 위치:\n{get_app_bin_dir(create=False)}\n\n"
            "지금 설치할까요?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if response == QMessageBox.StandardButton.Yes:
            self._install_or_update_ytdlp()

    def _check_ytdlp_status(self):
        if self.ytdlp_status_worker is not None:
            return
        if self.ytdlp_install_worker is not None:
            QMessageBox.information(self, "yt-dlp 상태 확인", "설치/업데이트가 끝난 뒤 다시 확인해주세요.")
            return
        worker = YtDlpStatusWorker(self)
        self.ytdlp_status_worker = worker
        self.ytdlp_status_action.setEnabled(False)
        worker.completed.connect(self._on_ytdlp_status_result)
        worker.finished.connect(self._on_ytdlp_status_finished)
        worker.start()

    def _on_ytdlp_status_result(self, status):
        self._ytdlp_status_result = status

    def _on_ytdlp_status_finished(self):
        worker = self.ytdlp_status_worker
        self.ytdlp_status_worker = None
        if worker:
            worker.deleteLater()
        self.ytdlp_status_action.setEnabled(True)
        status = self._ytdlp_status_result
        self._ytdlp_status_result = None
        if status is None or self._closing:
            return
        box = QMessageBox(self)
        box.setWindowTitle("yt-dlp 상태 확인")
        box.setTextFormat(Qt.TextFormat.PlainText)
        box.setText("사용 가능" if status.available else "사용 가능한 yt-dlp를 확인하지 못했습니다.")
        box.setInformativeText(
            f"버전: {status.version or '확인 불가'}\n"
            f"경로: {status.binary or '찾지 못함'}\n\n"
            "로컬 설치 상태 검사입니다. 최신 버전 여부나 특정 영상의 다운로드 가능 여부를 보장하지 않습니다.\n"
            "업데이트는 도움말의 'yt-dlp 설치/업데이트'를 이용해주세요."
        )
        if status.error:
            box.setDetailedText(status.error)
        retry = box.addButton("다시 확인", QMessageBox.ButtonRole.ActionRole)
        box.addButton(QMessageBox.StandardButton.Close)
        box.exec()
        if box.clickedButton() == retry:
            self._check_ytdlp_status()

    def _install_or_update_ytdlp(self):
        """Install or update yt-dlp in ClipCatcher's app-owned bin directory."""
        if self.ytdlp_status_worker is not None:
            QMessageBox.information(self, "yt-dlp 상태 확인 중", "상태 확인이 끝난 뒤 설치/업데이트해주세요.")
            return
        if self.ytdlp_install_worker and self.ytdlp_install_worker.isRunning():
            self.statusBar().showMessage("yt-dlp 설치/업데이트가 이미 진행 중입니다.", 3000)
            return

        worker = YtDlpInstallWorker(self)
        self.ytdlp_install_worker = worker
        worker.completed.connect(self._on_ytdlp_install_completed)
        worker.failed.connect(self._on_ytdlp_install_failed)
        worker.finished.connect(self._on_ytdlp_install_finished)
        self.statusBar().showMessage("yt-dlp 설치/업데이트 중...")
        worker.start()

    def _on_ytdlp_install_completed(self, path: str):
        QMessageBox.information(
            self,
            "yt-dlp 설치 완료",
            f"yt-dlp를 설치/업데이트했습니다.\n\n{path}",
        )

    def _on_ytdlp_install_failed(self, error: str):
        QMessageBox.warning(
            self,
            "yt-dlp 설치 실패",
            "yt-dlp 설치/업데이트에 실패했습니다.\n\n"
            f"{error}\n\n"
            "네트워크 연결을 확인하거나 CLI 설치 방법을 사용해주세요.",
        )

    def _on_ytdlp_install_finished(self):
        worker = self.ytdlp_install_worker
        self.ytdlp_install_worker = None
        self.statusBar().clearMessage()
        if worker:
            worker.deleteLater()

    def closeEvent(self, event):
        if self.ytdlp_status_worker is not None:
            QMessageBox.information(self, "yt-dlp 상태 확인 중", "상태 확인이 끝난 뒤 앱을 종료해주세요.")
            event.ignore()
            return
        if self._allow_close:
            super().closeEvent(event)
            return
        if self.ytdlp_install_worker and self.ytdlp_install_worker.isRunning():
            QMessageBox.information(
                self,
                "yt-dlp 설치 중",
                "안전한 설치를 위해 yt-dlp 업데이트가 끝난 뒤 앱을 종료해주세요.",
            )
            event.ignore()
            return
        if self._closing:
            event.ignore()
            return
        has_downloads = bool(
            self.pending_download_ids
            or self.running_download_ids
            or any(worker.isRunning() for worker in self.download_manager._retired_downloads.values())
            or self._batch_active
        )
        if has_downloads:
            answer = QMessageBox.question(
                self,
                "다운로드 중 종료",
                "진행 중인 다운로드와 링크 추가 작업을 취소하고 종료할까요?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self._closing = True
            self._batch_cancel_requested = True
            for download_id in list(self.pending_download_ids) + list(self.running_download_ids):
                self._cancel_download(download_id)
            self.statusBar().showMessage("작업 스레드가 종료되기를 기다리는 중...")
            QTimer.singleShot(50, self._finish_close_when_idle)
            event.ignore()
            return
        if any(loader.isRunning() for loader in self.thumbnail_loaders + list(ThumbnailLoader._running_loaders)):
            self._closing = True
            QTimer.singleShot(50, self._finish_close_when_idle)
            event.ignore()
            return
        super().closeEvent(event)

    def _finish_close_when_idle(self):
        workers = list(self.download_manager.active_downloads.values())
        workers += list(self.download_manager._retired_downloads.values())
        loaders = self.thumbnail_loaders + list(ThumbnailLoader._running_loaders)
        if self._batch_active or any(worker.isRunning() for worker in workers + loaders):
            QTimer.singleShot(50, self._finish_close_when_idle)
            return
        self._allow_close = True
        self.close()
