import asyncio
import os
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from core.segment_downloader import SegmentDownloader

# Mock data
MOCK_M3U8_URL = "https://example.com/playlist.m3u8"
MOCK_INIT_URL = "https://example.com/init.m4s"
MOCK_SEGMENT_URL = "https://example.com/seg_000.m4v"
OUTPUT_PATH = "test_output.mp4"

MOCK_M3U8_CONTENT = """
#EXTM3U
#EXT-X-VERSION:7
#EXT-X-MAP:URI="init.m4s"
#EXTINF:2.0,
seg_000.m4v
#EXTINF:2.0,
seg_001.m4v
""".strip()

async def test_segment_downloader():
    print("Testing SegmentDownloader...")
    
    downloader = SegmentDownloader()
    
    # Mock aiohttp session and response
    with patch('aiohttp.ClientSession') as mock_session_cls:
        mock_session = MagicMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session
        
        # Mock responses
        mock_response_m3u8 = MagicMock()
        mock_response_m3u8.status = 200
        mock_response_m3u8.text = asyncio.Future()
        mock_response_m3u8.text.set_result(MOCK_M3U8_CONTENT)
        
        mock_response_segment = MagicMock()
        mock_response_segment.status = 200
        mock_response_segment.content.read = asyncio.Future()
        # Simulate small chunk
        mock_response_segment.content.read.side_effect = [b'datachunk', b'']
        
        # Configure get side effects based on URL
        def get_side_effect(url):
            mock_resp_ctx = MagicMock()
            if "playlist.m3u8" in url:
                mock_resp_ctx.__aenter__.return_value = mock_response_m3u8
            else:
                mock_resp_ctx.__aenter__.return_value = mock_response_segment
            return mock_resp_ctx
            
        mock_session.get.side_effect = get_side_effect
        
        # Mock combine_segments to avoid file IO
        with patch.object(downloader, '_combine_segments') as mock_combine:
            path = await downloader.download_video(
                MOCK_M3U8_URL,
                OUTPUT_PATH,
                lambda c, t: print(f"Progress: {c}/{t}")
            )
            
            print(f"Download completed: {path}")
            
            # Verify calls
            assert mock_session.get.call_count >= 3  # m3u8 + init + 2 segments
            mock_combine.assert_called_once()
            
            print("Test passed!")

if __name__ == "__main__":
    asyncio.run(test_segment_downloader())
