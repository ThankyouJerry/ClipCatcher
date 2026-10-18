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
        self._recovery_source = None
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default (with legacy migration)"""
        for path in (self.config_file, self.legacy_config_file):
            if not path.exists():
                continue
            loaded_config = self._load_json(path)
            if loaded_config is not None:
                config = self._merge_with_defaults(loaded_config)
                if any(type(config.get(key)) is not type(value) or config.get(key) != value
                       for key, value in loaded_config.items()):
                    self._recovery_source = path
                return config
            # An invalid current file must not silently resurrect legacy cookies.
            return deepcopy(self.DEFAULT_CONFIG)
        return deepcopy(self.DEFAULT_CONFIG)

    def _load_json(self, path: Path) -> Optional[Dict[str, Any]]:
        """Read an object without logging configuration values or credentials."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
            self._restrict_permissions(path)
            if not isinstance(loaded, dict):
                raise ValueError("Configuration must be an object")
            return loaded
        except (OSError, ValueError, UnicodeError, RecursionError):
            self._recovery_source = path
            print("Invalid or unreadable configuration; using safe defaults.")
            return None

    def _merge_with_defaults(self, loaded_config: Dict[str, Any]) -> Dict[str, Any]:
        """Keep valid preferences and unknown keys, replacing unsafe known values."""
        config = deepcopy(self.DEFAULT_CONFIG)
        config.update(loaded_config)
        for key in ("download_path", "default_quality", "theme"):
            value = config[key]
            if (not isinstance(value, str) or not value.strip()
                    or any(ord(char) < 32 for char in value)):
                config[key] = self.DEFAULT_CONFIG[key]
        count = config["concurrent_downloads"]
        if type(count) is not int or not 1 <= count <= 5:
            config["concurrent_downloads"] = self.DEFAULT_CONFIG["concurrent_downloads"]
        cookies = loaded_config.get("cookies", {})
        config["cookies"] = {
            key: cookies.get(key, "") if isinstance(cookies, dict)
            and isinstance(cookies.get(key, ""), str)
            and not any(ord(char) < 32 for char in cookies.get(key, "")) else ""
            for key in self.DEFAULT_CONFIG["cookies"]
        }
        return config

    def _preserve_recovery_source(self):
        """Keep original bytes before the first save replaces a recovered file."""
        source = getattr(self, "_recovery_source", None)
        if source is None:
            return
        # mkstemp is exclusive and owner-only; never overwrite an older backup.
        fd, name = tempfile.mkstemp(prefix="config.recovery.", suffix=".json",
                                    dir=self.config_dir)
        backup = Path(name)
        try:
            with os.fdopen(fd, "wb") as target, source.open("rb") as original:
                import shutil
                shutil.copyfileobj(original, target)
                target.flush()
                os.fsync(target.fileno())
        except Exception:
            backup.unlink(missing_ok=True)
            raise
        self._recovery_source = None

    def save(self):
        """Atomically save configuration with owner-only permissions."""
        temp_path = None
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            self._preserve_recovery_source()

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
