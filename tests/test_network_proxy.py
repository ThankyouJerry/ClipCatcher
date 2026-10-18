"""Use existing runtime proxies without enabling implicit .netrc authentication."""
from unittest.mock import patch
import pytest
from core.network_proxy import https_proxy_for


def test_honors_existing_https_proxy_without_printing_it():
    with patch('core.network_proxy.getproxies', return_value={'https': 'http://proxy.internal:8080'}), patch('core.network_proxy.proxy_bypass', return_value=False):
        assert https_proxy_for('https://api.chzzk.naver.com/video') == 'http://proxy.internal:8080'


def test_no_proxy_preserves_direct_route():
    with patch('core.network_proxy.getproxies') as lookup, patch('core.network_proxy.proxy_bypass', return_value=True):
        assert https_proxy_for('https://api.chzzk.naver.com/video') is None
        lookup.assert_not_called()


def test_absent_proxy_preserves_direct_route():
    with patch('core.network_proxy.getproxies', return_value={}), patch('core.network_proxy.proxy_bypass', return_value=False):
        assert https_proxy_for('https://api.chzzk.naver.com/video') is None


@pytest.mark.parametrize('proxy', ['socks5://proxy.internal:1080', 'http://', 'proxy.internal:8080'])
def test_unsupported_configured_proxy_does_not_silently_bypass(proxy):
    with patch('core.network_proxy.getproxies', return_value={'https': proxy}), patch('core.network_proxy.proxy_bypass', return_value=False):
        with pytest.raises(RuntimeError, match='Configured HTTPS proxy'):
            https_proxy_for('https://api.chzzk.naver.com/video')


def test_non_https_input_never_uses_proxy():
    with patch('core.network_proxy.getproxies') as lookup:
        assert https_proxy_for('http://example.com') is None
        lookup.assert_not_called()


@pytest.mark.parametrize('operation', ['api', 'playlist', 'segment'])
def test_requests_forward_proxy_without_enabling_netrc_or_cdn_cookies(operation, tmp_path):
    import asyncio
    from unittest.mock import MagicMock
    from core.chzzk_api import ChzzkAPI
    from core.segment_downloader import SegmentDownloader

    class Content:
        sent = False

        async def read(self, size):
            if self.sent:
                return b''
            self.sent = True
            return b'{}'

        async def iter_chunked(self, size):
            yield b'{}'

    class Response:
        status = 200
        charset = 'utf-8'
        content = Content()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

    class Session:
        get = MagicMock(return_value=Response())

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

    session = Session()
    url = 'https://vod.pstatic.net/fixture'
    proxy = 'http://proxy.internal:8080'
    if operation == 'api':
        with patch('core.chzzk_api.https_proxy_for', return_value=proxy), patch(
            'core.chzzk_api.aiohttp.ClientSession', return_value=session
        ) as constructor:
            asyncio.run(ChzzkAPI()._request_json(url, {}))
        assert not constructor.call_args.kwargs.get('trust_env', False)
    else:
        downloader = SegmentDownloader()
        downloader.session = session
        downloader.cookies = {'NID_AUT': 'test-only-secret'}
        with patch('core.segment_downloader.https_proxy_for', return_value=proxy):
            if operation == 'playlist':
                asyncio.run(downloader._fetch_text(url))
            else:
                asyncio.run(downloader._download_file(url, str(tmp_path / 'segment')))
        assert session.get.call_args.kwargs['cookies'] == {}
    assert session.get.call_args.kwargs['proxy'] == proxy
    assert session.get.call_args.kwargs['allow_redirects'] is False
