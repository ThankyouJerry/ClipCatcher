"""Local, bounded failure reports without access-bearing URLs or credentials."""
from datetime import datetime, timezone
import os
import re
from core.app_tools import get_app_support_dir


def sanitize_error(text):
    text = str(text)
    text = re.sub(r'https?://[^\s<>"\']+', '[URL removed]', text, flags=re.I)
    text = re.sub(r'(?im)\b(cookie|authorization|proxy-authorization)\s*[:=][^\r\n]*', r'\1: [removed]', text)
    text = re.sub(r'(?i)\b(NID_AUT|NID_SES|access_token|refresh_token|password|token|signature|key)\s*[:=]\s*[^\s;,]+', r'\1=[removed]', text)
    return text[-12000:]


def save_error_report(text):
    """Return a new local report path, or None without hiding the original error."""
    safe = sanitize_error(text)
    try:
        directory = get_app_support_dir() / 'logs'
        directory.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc)
        path = directory / ('download-error-' + stamp.strftime('%Y%m%dT%H%M%S%fZ') + '.txt')
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(stamp.isoformat() + '\n' + safe + '\n')
        return str(path)
    except OSError:
        return None
