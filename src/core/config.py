"""
ClipCatcher Configuration Management
"""
import json
import os
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Dict, Any, Optional

class Config:
    """Application configuration manager"""
    
    DEFAULT_CONFIG = {
        "download_path": str(Path.home() / "Downloads" / "ClipCatcher"),
        "cookies": {
            "NID_AUT": "",
            "NID_SES": ""
        },
        "default_quality": "1080p",
        "concurrent_downloads": 1,
        "theme": "dark"
    }
    
    def __init__(self):
        self.config_dir = Path.home() / ".clipcatcher"
        self.config_file = self.config_dir / "config.json"
        self.legacy_config_file = Path.home() / ".chzzk-downloader" / "config.json"
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default (with legacy migration)"""
        if self.config_file.exists():
            loaded_config = self._load_json(self.config_file)
            if loaded_config is not None:
                return self._merge_with_defaults(loaded_config)

        if self.legacy_config_file.exists():
            loaded_config = self._load_json(self.legacy_config_file)
            if loaded_config is not None:
                return self._merge_with_defaults(loaded_config)

        return deepcopy(self.DEFAULT_CONFIG)

    def _load_json(self, path: Path) -> Optional[Dict[str, Any]]:
        """Load JSON config from a specific file path."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
            self._restrict_permissions(path)
            return loaded
        except Exception as e:
            print(f"Error loading config from {path}: {e}")
            return None

    def _merge_with_defaults(self, loaded_config: Dict[str, Any]) -> Dict[str, Any]:
        """Merge loaded config with defaults, including nested cookie values."""
        config = deepcopy(self.DEFAULT_CONFIG)
        config.update(loaded_config)

        default_cookies = self.DEFAULT_CONFIG.get("cookies", {}).copy()
        loaded_cookies = loaded_config.get("cookies", {})
        if isinstance(loaded_cookies, dict):
            default_cookies.update(loaded_cookies)
        config["cookies"] = default_cookies
        return config
    
    def save(self):
        """Atomically save configuration with owner-only permissions."""
        temp_path = None
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)

            fd, temp_name = tempfile.mkstemp(
                prefix="config.",
                suffix=".tmp",
                dir=self.config_dir,
            )
            temp_path = Path(temp_name)
            if os.name != "nt":
                os.fchmod(fd, 0o600)
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())

            os.replace(temp_path, self.config_file)
            temp_path = None
            self._restrict_permissions(self.config_file)
        except Exception as e:
            print(f"Error saving config: {e}")
        finally:
            if temp_path and temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass

    @staticmethod
    def _restrict_permissions(path: Path):
        """Limit cookie-bearing config files to the current user on POSIX."""
        if os.name == "nt":
            return
        try:
            path.chmod(0o600)
        except OSError as exc:
            print(f"Error securing config permissions for {path}: {exc}")
    
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
    
    def get_cookie_header(self) -> str:
        """Get cookies as HTTP Cookie header format."""
        cookies = self.config.get("cookies", {})
        nid_aut = cookies.get("NID_AUT", "")
        nid_ses = cookies.get("NID_SES", "")
        
        if not nid_aut or not nid_ses:
            return ""

        return f"NID_AUT={nid_aut}; NID_SES={nid_ses}"

    def get_cookies_netscape(self) -> str:
        """Get cookies in Netscape format for yt-dlp cookiefile."""
        cookies = self.config.get("cookies", {})
        nid_aut = cookies.get("NID_AUT", "")
        nid_ses = cookies.get("NID_SES", "")

        if not nid_aut or not nid_ses:
            return ""

        cookie_lines = [
            "# Netscape HTTP Cookie File",
            ".naver.com\tTRUE\t/\tTRUE\t0\tNID_AUT\t" + nid_aut,
            ".naver.com\tTRUE\t/\tTRUE\t0\tNID_SES\t" + nid_ses
        ]
        return "\n".join(cookie_lines)

    def get_cookies(self) -> str:
        """Backward-compatible alias for cookie header format."""
        return self.get_cookie_header()
