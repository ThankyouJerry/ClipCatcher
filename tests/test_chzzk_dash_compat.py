import xml.etree.ElementTree as ET
from unittest.mock import patch
import pytest
from yt_dlp import YoutubeDL
from yt_dlp.extractor.chzzk import CHZZKVideoIE
from yt_dlp.extractor.common import InfoExtractor
from core.chzzk_dash_compat import install_chzzk_dash_compat

MPD='''<MPD xmlns="urn:mpeg:dash:schema:mpd:2011" mediaPresentationDuration="PT4S"><Period><AdaptationSet mimeType="video/mp4" codecs="avc1.64001e"><Representation id="v0" bandwidth="1000000" width="1280" height="720"><BaseURL>video.mp4</BaseURL><SegmentList duration="2"><Initialization range="0-999"/><SegmentURL mediaRange="1000-1999"/><SegmentURL mediaRange="2000-2999"/></SegmentList></Representation></AdaptationSet></Period></MPD>'''


def test_upstream_parser_reproduces_observed_sourceurl_keyerror():
    ie=InfoExtractor(YoutubeDL({'quiet':True}))
    with pytest.raises(KeyError,match='sourceURL'):
        list(ie._parse_mpd_periods(ET.fromstring(MPD),mpd_url='https://offline.invalid/manifest.mpd',mpd_base_url='https://offline.invalid/'))


def test_compat_preserves_original_manifest_and_selected_quality():
    install_chzzk_dash_compat()
    doc=ET.fromstring(MPD);before=ET.tostring(doc)
    ie=CHZZKVideoIE(YoutubeDL({'quiet':True,'external_downloader':{'dash':'ffmpeg'}}))
    periods=list(ie._parse_mpd_periods(doc,mpd_url='https://offline.invalid/manifest.mpd',mpd_base_url='https://offline.invalid/'))
    fmt=periods[0]['formats'][0]
    assert fmt['url']=='https://offline.invalid/video.mp4'
    assert not fmt.get('fragments')
    assert fmt['height']==720
    assert fmt['manifest_stream_number']==0
    assert ET.tostring(doc)==before


def test_compat_leaves_unsupported_multifile_form_unmodified():
    install_chzzk_dash_compat()
    doc=ET.fromstring(MPD.replace('mediaRange="1000-1999"','media="other.mp4" mediaRange="1000-1999"'))
    before=ET.tostring(doc)
    ie=CHZZKVideoIE(YoutubeDL({'quiet':True}))
    with pytest.raises(KeyError,match='sourceURL'):
        list(ie._parse_mpd_periods(doc,mpd_url='https://offline.invalid/manifest.mpd'))
    assert ET.tostring(doc)==before


def test_existing_sourceurl_manifest_unchanged():
    install_chzzk_dash_compat()
    doc=ET.fromstring(MPD.replace('<Initialization range="0-999"/>','<Initialization sourceURL="init.mp4"/>').replace('<SegmentURL mediaRange=', '<SegmentURL media="video.mp4" mediaRange='))
    before=ET.tostring(doc)
    ie=CHZZKVideoIE(YoutubeDL({'quiet':True}))
    assert list(ie._parse_mpd_periods(doc,mpd_url='https://offline.invalid/manifest.mpd'))
    assert ET.tostring(doc)==before


def test_chzzk_vod_binary_requests_ffmpeg_for_dash():
    from core.download_job import DownloadJob
    job=DownloadJob('https://chzzk.naver.com/video/1234567','/tmp/test',start_time=22978,end_time=23005)
    class Proc:
        stdout=iter([]);returncode=1
        def wait(self):return 1
    with patch('core.download_job.get_ffmpeg_binary',return_value='/fake/ffmpeg'),patch('core.download_job.subprocess.Popen',return_value=Proc()) as popen:
        with pytest.raises(Exception):job._run_ytdlp_binary_download(['/fake/app','--run-yt-dlp'])
    cmd=popen.call_args.args[0]
    assert cmd[cmd.index('--downloader')+1]=='dash:ffmpeg'
    assert cmd[cmd.index('--download-sections')+1]=='*22978-23005'


def test_compat_preserves_drm_marker():
    install_chzzk_dash_compat()
    doc=ET.fromstring(MPD.replace('<Representation id=', '<ContentProtection schemeIdUri="urn:mpeg:dash:mp4protection:2011" value="cenc"/><Representation id='))
    ie=CHZZKVideoIE(YoutubeDL({'quiet':True}))
    periods=list(ie._parse_mpd_periods(doc,mpd_url='https://offline.invalid/manifest.mpd',mpd_base_url='https://offline.invalid/'))
    assert periods[0]['formats'][0]['has_drm'] is True


def test_source_cli_keeps_chzzk_download_in_cancellable_subprocess():
    import sys
    from pathlib import Path
    from core.download_job import DownloadJob
    job=DownloadJob('https://chzzk.naver.com/video/1234567','/tmp/test',use_subprocess=True)
    with patch('core.download_job.sys.frozen',False,create=True),patch.object(job,'_refresh_clip_stream_url'),patch.object(job,'_run_ytdlp_binary_download') as run:
        job._run_ytdlp_download()
    prefix=run.call_args.args[0]
    assert prefix[0]==sys.executable
    assert Path(prefix[1]).name=='main.py'
    assert prefix[2]=='--run-yt-dlp'
