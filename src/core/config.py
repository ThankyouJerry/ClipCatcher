"""
Chzzk Downloader Configuration Management
"""
import json
import os
from pathlib import Path
from typing import Dict, Any

class Config:
    """Application configuration manager"""
    
    DEFAULT_CONFIG = {
        "download_path": str(Path.home() / "Downloads" / "ChzzkDownloads"),
        "cookies": {
            "NID_AUT": "",
            "NID_SES": ""
        },
        "default_quality": "1080p",
        "concurrent_downloads": 3,
        "theme": "dark"
    }
    
    def __init__(self):
        self.config_dir = Path.home() / ".chzzk-downloader"
        self.config_file = self.config_dir / "config.json"
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    config = self.DEFAULT_CONFIG.copy()
                    config.update(loaded_config)
                    return config
            except Exception as e:
                print(f"Error loading config: {e}")
                return self.DEFAULT_CONFIG.copy()
        else:
            return self.DEFAULT_CONFIG.copy()
    
    def save(self):
        """Save configuration to file"""
        try:
            # Create config directory if it doesn't exist
            self.config_dir.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def get(self, key: str, default=None):
        """Get configuration value"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set configuration value"""
        self.config[key] = value
    
    def get_download_path(self) -> Path:
        """Get download path as Path object"""
        path = Path(self.config["download_path"])
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    def get_cookies(self) -> str:
        """Get cookies in Netscape format for yt-dlp"""
        cookies = self.config.get("cookies", {})
        nid_aut = cookies.get("NID_AUT", "")
        nid_ses = cookies.get("NID_SES", "")
        
        if not nid_aut or not nid_ses:
            return ""
        
        # Create Netscape cookie format
        cookie_lines = [
            "# Netscape HTTP Cookie File",
            ".naver.com\tTRUE\t/\tTRUE\t0\tNID_AUT\t" + nid_aut,
            ".naver.com\tTRUE\t/\tTRUE\t0\tNID_SES\t" + nid_ses
        ]
        return "\n".join(cookie_lines)
