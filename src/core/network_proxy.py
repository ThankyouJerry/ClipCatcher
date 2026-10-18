"""Honor existing HTTPS proxy configuration without consulting .netrc."""
from urllib.parse import urlsplit
from urllib.request import getproxies, proxy_bypass


def https_proxy_for(url: str):
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.hostname or proxy_bypass(parts.hostname):
        return None
    proxy = getproxies().get("https")
    if not proxy:
        return None
    # aiohttp supports HTTP(S) proxies. Do not invent a route or silently bypass
    # an explicitly configured unsupported proxy.
    if urlsplit(proxy).scheme not in {"http", "https"} or not urlsplit(proxy).hostname:
        raise RuntimeError("Configured HTTPS proxy must use HTTP or HTTPS")
    return proxy
