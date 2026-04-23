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
        
        # YouTube URL
        yt_match = re.search(
            r'(?:youtube\.com/watch\?.*v=|youtu\.be/|youtube\.com/shorts/)([a-zA-Z0-9_-]{11})',
            url
        )
        if yt_match:
            return {'type': 'youtube', 'id': yt_match.group(1), 'url': url}
        
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
                vod_status = video.get('vodStatus', 'UNKNOWN')
                in_key   = video.get('inKey', '')
                vid_id   = video.get('videoId', '')
                page_url = f"https://chzzk.naver.com/video/{video_id}"
                
                # Try liveRewindPlaybackJson first (VOD_ON_AIR / 빠른다시보기)
                resolutions = self._parse_resolutions(video)
                
                # For ABR_HLS: fetch resolutions from DASH media API
                if not resolutions and vod_status == 'ABR_HLS' and in_key and vid_id:
                    resolutions = await self._fetch_abr_resolutions(
                        vid_id, in_key, page_url, headers
                    )
                
                return {
                    'id': video.get('videoNo'),
                    'type': 'vod',
                    'title': video.get('videoTitle', 'Untitled'),
                    'thumbnail': video.get('thumbnailImageUrl', ''),
                    'duration': video.get('duration', 0),
                    'channel_name': video.get('channel', {}).get('channelName', 'Unknown'),
                    'publish_date': video.get('publishDate', ''),
                    'resolutions': resolutions,
                    'vod_status': vod_status,
                    'is_downloadable': vod_status == 'ABR_HLS',
                    'liveRewindPlaybackJson': video.get('liveRewindPlaybackJson'),
                    'url': page_url,
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
                    'vod_status': 'ABR_HLS',  # Clips are always ready
                    'is_downloadable': True,
                }
    
    async def _fetch_abr_resolutions(
        self, video_id: str, in_key: str, page_url: str, headers: dict
    ) -> List[Dict]:
        """ABR_HLS 영상의 화질 목록을 DASH 미디어 API에서 가져옵니다."""
        resolutions = []
        try:
            media_url = (
                f"https://apis.naver.com/neonplayer/vodplay/v2/playback/{video_id}"
                f"?key={in_key}&cc=KR&tz=Asia%2FSeoul&lc=ko_KR&cpl=ko_KR"
                f"&service=chzzk&mediaProtocol=hls&application=PC_WEB"
            )
            async with aiohttp.ClientSession() as session:
                async with session.get(media_url, headers=headers) as resp:
                    if resp.status != 200:
                        return resolutions
                    dash = await resp.json()
            
            # DASH MPD JSON → period → adaptationSet → representation
            periods = dash.get('period', [])
            seen_heights = set()
            for period in periods:
                for adapt in period.get('adaptationSet', []):
                    if adapt.get('mimeType', '').startswith('video'):
                        for rep in adapt.get('representation', []):
                            h = rep.get('height')
                            if not h or h in seen_heights:
                                continue
                            seen_heights.add(h)
                            # Try to extract qualityId from 'any' field
                            quality_id = ''
                            for item in rep.get('any', []):
                                if item.get('kind') == 'qualityId':
                                    quality_id = item.get('value', '')
                                    break
                            tbr = rep.get('bandwidth', 0)
                            resolutions.append({
                                'quality':  quality_id or f'{h}p',
                                'label':    f'{h}p',
                                'url':      page_url,  # yt-dlp uses page URL
                                'height':   h,
                                'width':    rep.get('width', 0),
                                'bitrate':  tbr,
                            })
            
            resolutions.sort(key=lambda x: x['height'], reverse=True)
        except Exception as e:
            print(f"[ABR] 화질 목록 가져오기 실패: {e}")
        return resolutions

    def _parse_resolutions(self, video: Dict) -> List[Dict]:
        """Parse available resolutions from liveRewindPlaybackJson (VOD_ON_AIR)"""
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
                    'label':   f"{track.get('videoHeight', 0)}p",
                    'url':     master_url,
                    'width':   track.get('videoWidth', 0),
                    'height':  track.get('videoHeight', 0),
                    'bitrate': track.get('videoBitRate', 0),
                })
            
            resolutions.sort(key=lambda x: x['height'], reverse=True)
            
        except Exception as e:
            print(f"Error parsing resolutions: {e}")
        
        return resolutions
    
    @staticmethod
    def get_master_playlist_url(video_data: dict) -> Optional[str]:
        """
        Get the original Master Playlist URL from metadata
        
        Args:
            video_data: Video metadata dictionary
        
        Returns:
            Master Playlist URL or None
        """
        raw_json_str = video_data.get('liveRewindPlaybackJson')
        if not raw_json_str:
            return None
            
        try:
            playback_data = json.loads(raw_json_str)
            media_list = playback_data.get('media', [])
            
            for media in media_list:
                if media.get('path'):
                    return media.get('path')
                    
        except Exception:
            pass
            
        return None

    @staticmethod
    def get_m3u8_url(video_data: dict, quality: str = '1080p') -> Optional[str]:
        """
        Extract m3u8 URL for a specific quality from liveRewindPlaybackJson
        
        Args:
            video_data: Video metadata dict (from fetch_vod_metadata)
            quality: Quality to extract (e.g., '1080p', '720p')
        
        Returns:
            m3u8 URL for specified quality, or None if not found
        """
        try:
            # Get raw video content if passed from API response
            if 'content' in video_data:
                video_data = video_data['content']
            
            playback_json_str = video_data.get('liveRewindPlaybackJson')
            if not playback_json_str:
                return None
            
            playback_data = json.loads(playback_json_str)
            
            if not playback_data.get('media') or len(playback_data['media']) == 0:
                return None
            
            media = playback_data['media'][0]
            master_url = media.get('path', '')
            
            if not master_url:
                return None
            
            # Replace vod_playlist.m3u8 with specific quality chunklist
            # e.g., https://.../vod_playlist.m3u8 -> https://.../1080p/vod_chunklist.m3u8
            base_url = master_url.rsplit('/', 1)[0]
            quality_number = quality.replace('p', '')  # '1080p' -> '1080'
            
            # Construct variant playlist URL
            variant_url = f"{base_url}/{quality_number}p/vod_chunklist.m3u8"
            
            # Preserve query parameters from master URL
            if '?' in master_url:
                query_params = master_url.split('?', 1)[1]
                variant_url = f"{variant_url}?{query_params}"
            
            return variant_url
            
        except Exception as e:
            print(f"Error extracting m3u8 URL: {e}")
            return None
