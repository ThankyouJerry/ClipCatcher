"""
Settings Dialog
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QFileDialog, QTabWidget,
    QWidget, QGroupBox
)
from PyQt6.QtCore import Qt
from pathlib import Path

class SettingsDialog(QDialog):
    """Settings configuration dialog"""
    
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("설정")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        self._init_ui()
        self._load_settings()
    
    def _init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout()
        layout.setSpacing(20)
        
        # Tab widget
        tabs = QTabWidget()
        
        # General tab
        general_tab = self._create_general_tab()
        tabs.addTab(general_tab, "일반")
        
        # Authentication tab
        auth_tab = self._create_auth_tab()
        tabs.addTab(auth_tab, "인증")
        
        layout.addWidget(tabs)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_button = QPushButton("취소")
        cancel_button.setObjectName("secondaryButton")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        save_button = QPushButton("저장")
        save_button.clicked.connect(self._save_settings)
        button_layout.addWidget(save_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def _create_general_tab(self) -> QWidget:
        """Create general settings tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(16)
        
        # Download path
        path_group = QGroupBox("다운로드 경로")
        path_layout = QVBoxLayout()
        
        path_input_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        path_input_layout.addWidget(self.path_input)
        
        browse_button = QPushButton("찾아보기")
        browse_button.setObjectName("secondaryButton")
        browse_button.clicked.connect(self._browse_path)
        path_input_layout.addWidget(browse_button)
        
        path_layout.addLayout(path_input_layout)
        path_group.setLayout(path_layout)
        layout.addWidget(path_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _create_auth_tab(self) -> QWidget:
        """Create authentication settings tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(16)
        
        # Cookies group
        cookies_group = QGroupBox("네이버 쿠키 (연령 제한 컨텐츠)")
        cookies_layout = QVBoxLayout()
        cookies_layout.setSpacing(12)
        
        # Info label
        info_label = QLabel(
            "연령 제한이 걸린 영상을 다운로드하려면 네이버 로그인 쿠키가 필요합니다.\n"
            "브라우저 개발자 도구(F12) → Application → Cookies에서 값을 복사하세요."
        )
        info_label.setWordWrap(True)
        info_label.setObjectName("subtitleLabel")
        cookies_layout.addWidget(info_label)
        
        # NID_AUT
        aut_label = QLabel("NID_AUT:")
        cookies_layout.addWidget(aut_label)
        self.nid_aut_input = QLineEdit()
        self.nid_aut_input.setPlaceholderText("NID_AUT 쿠키 값을 입력하세요")
        cookies_layout.addWidget(self.nid_aut_input)
        
        # NID_SES
        ses_label = QLabel("NID_SES:")
        cookies_layout.addWidget(ses_label)
        self.nid_ses_input = QLineEdit()
        self.nid_ses_input.setPlaceholderText("NID_SES 쿠키 값을 입력하세요")
        cookies_layout.addWidget(self.nid_ses_input)
        
        cookies_group.setLayout(cookies_layout)
        layout.addWidget(cookies_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _browse_path(self):
        """Browse for download directory"""
        current_path = self.path_input.text()
        path = QFileDialog.getExistingDirectory(
            self,
            "다운로드 폴더 선택",
            current_path
        )
        if path:
            self.path_input.setText(path)
    
    def _load_settings(self):
        """Load current settings into UI"""
        self.path_input.setText(self.config.get("download_path", ""))
        
        cookies = self.config.get("cookies", {})
        self.nid_aut_input.setText(cookies.get("NID_AUT", ""))
        self.nid_ses_input.setText(cookies.get("NID_SES", ""))
    
    def _save_settings(self):
        """Save settings and close dialog"""
        # Update config
        self.config.set("download_path", self.path_input.text())
        self.config.set("cookies", {
            "NID_AUT": self.nid_aut_input.text().strip(),
            "NID_SES": self.nid_ses_input.text().strip()
        })
        
        # Save to file
        self.config.save()
        
        self.accept()
