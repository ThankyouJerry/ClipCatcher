import asyncio
import sys
import os
import aiohttp

# Add src to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.chzzk_api import ChzzkAPI
from core.segment_downloader import SegmentDownloader

VIDEO_ID = "10819636"  # The fast replay video

async def test():
    print(f"Testing real download for {VIDEO_ID}...")
    api = ChzzkAPI()
    
    # Use full headers for API as well
    api.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': f'https://chzzk.naver.com/video/{VIDEO_ID}',
        'Origin': 'https://chzzk.naver.com',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
    })
    
    async with aiohttp.ClientSession(headers=api.headers) as session:
        try:
            # Fetch metadata
            print("Fetching metadata...")
            meta = await api.fetch_vod_metadata(VIDEO_ID)
            
            # Get Master Playlist URL
            m3u8_url = api.get_master_playlist_url(meta)
            
            if not m3u8_url:
                print("No Master Playlist URL found")
                return
            
            print(f"Master Playlist URL: {m3u8_url}")
            
            # Download 2 segments
            downloader = SegmentDownloader()
            
            def progress(c, t):
                print(f"Progress: {c}/{t}")
                
            print("Starting download (max 2 segments, quality=720p)...")
            
            # Use same headers as in downloader.py + enhanced
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': f'https://chzzk.naver.com/video/{VIDEO_ID}',
                'Origin': 'https://chzzk.naver.com',
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
            }
            
            path = await downloader.download_video(
                m3u8_url, 
                "test_real_output", 
                progress,
                headers=headers,
                max_segments=2,
                target_quality="720p"
            )
            print(f"Download success! Saved to {path}")
            
        except Exception as e:
            print(f"Download failed: {e}")
            import traceback
            traceback.print_exc()
                
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
