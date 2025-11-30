"""
Chzzk API Client
Handles fetching metadata from Chzzk API
"""
import aiohttp
import re
import json
from typing import Dict, Optional, List

class ChzzkAPI:
    """Client for Chzzk API"""
    
    BASE_URL = "https://api.chzzk.naver.com"
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
    
    @staticmethod
    def parse_url(url: str) -> Optional[Dict[str, str]]:
        """
        Parse Chzzk URL to extract type and ID
        
        Returns:
            dict with 'type' and 'id' keys, or None if invalid
        """
        # VOD URL: https://chzzk.naver.com/video/[videoNo]
        vod_match = re.search(r'chzzk\.naver\.com/video/(\d+)', url)
        if vod_match:
            return {'type': 'vod', 'id': vod_match.group(1)}
        
        # Clip URL: https://chzzk.naver.com/clips/[clipNo]
        clip_match = re.search(r'chzzk\.naver\.com/clips/([a-zA-Z0-9]+)', url)
        if clip_match:
            return {'type': 'clip', 'id': clip_match.group(1)}
        
        return None
    
    async def fetch_vod_metadata(self, video_id: str, cookies: str = "") -> Dict:
        """
        Fetch VOD metadata from Chzzk API v3
        
        Args:
            video_id: Video ID
            cookies: Cookie string (NID_AUT and NID_SES)
        
        Returns:
            Dictionary with video metadata
        """
        headers = self.headers.copy()
        if cookies:
            headers['Cookie'] = cookies
        
        url = f"{self.BASE_URL}/service/v3/videos/{video_id}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    raise Exception(f"Failed to fetch metadata: HTTP {response.status}")
                
                data = await response.json()
                
                if not data.get('content'):
                    raise Exception("Video not found")
                
                video = data['content']
                
                # Extract resolutions
                resolutions = self._parse_resolutions(video)
                
                return {
                    'id': video.get('videoNo'),
                    'type': 'vod',
                    'title': video.get('videoTitle', 'Untitled'),
                    'thumbnail': video.get('thumbnailImageUrl', ''),
                    'duration': video.get('duration', 0),
                    'channel_name': video.get('channel', {}).get('channelName', 'Unknown'),
                    'publish_date': video.get('publishDate', ''),
                    'resolutions': resolutions,
                }
    
    async def fetch_clip_metadata(self, clip_id: str, cookies: str = "") -> Dict:
        """
        Fetch clip metadata from Chzzk API v1
        
        Args:
            clip_id: Clip ID
            cookies: Cookie string
        
        Returns:
            Dictionary with clip metadata
        """
        headers = self.headers.copy()
        if cookies:
            headers['Cookie'] = cookies
        
        url = f"{self.BASE_URL}/service/v1/clips/{clip_id}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    raise Exception(f"Failed to fetch metadata: HTTP {response.status}")
                
                data = await response.json()
                
                if not data.get('content'):
                    raise Exception("Clip not found")
                
                clip = data['content']
                
                return {
                    'id': clip.get('clipUID'),
                    'type': 'clip',
                    'title': clip.get('clipTitle', 'Untitled'),
                    'thumbnail': clip.get('thumbnailImageUrl', ''),
                    'duration': clip.get('duration', 0),
                    'channel_name': clip.get('ownerChannel', {}).get('channelName', 'Unknown'),
                    'publish_date': clip.get('readablePublishDate', ''),
                    'resolutions': [{
                        'quality': 'original',
                        'label': 'Original',
                        'url': clip.get('videoUrl', ''),
                    }],
                }
    
    def _parse_resolutions(self, video: Dict) -> List[Dict]:
        """Parse available resolutions from liveRewindPlaybackJson"""
        resolutions = []
        
        try:
            playback_json = video.get('liveRewindPlaybackJson')
            if not playback_json:
                return resolutions
            
            playback_data = json.loads(playback_json)
            
            if not playback_data.get('media') or len(playback_data['media']) == 0:
                return resolutions
            
            media = playback_data['media'][0]
            master_url = media.get('path', '')
            
            if not master_url:
                return resolutions
            
            encoding_tracks = media.get('encodingTrack', [])
            
            for track in encoding_tracks:
                resolutions.append({
                    'quality': track.get('encodingTrackId', ''),
                    'label': f"{track.get('videoHeight', 0)}p",
                    'url': master_url,
                    'width': track.get('videoWidth', 0),
                    'height': track.get('videoHeight', 0),
                    'bitrate': track.get('videoBitRate', 0),
                })
            
            # Sort by height (descending)
            resolutions.sort(key=lambda x: x['height'], reverse=True)
            
        except Exception as e:
            print(f"Error parsing resolutions: {e}")
        
        return resolutions
