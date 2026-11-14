import io
from unittest.mock import patch, MagicMock
from core.download_job import DownloadJob


def test_quiet_ffmpeg_machine_progress():
    job = DownloadJob('https://example.com/video', '/tmp/clipcatcher-test', start_time=100, end_time=120)
    seen, statuses, completed = [], [], []
    job.progress_updated.connect(lambda pct, *_: seen.append(pct))
    job.status_changed.connect(statuses.append)
    job.download_completed.connect(completed.append)
    process = MagicMock()
    process.stdout = io.StringIO('out_time=00:00:02.000000\nprogress=continue\nout_time=00:00:10.000000\nprogress=continue\nout_time=00:00:20.000000\nprogress=end\nCLIPCATCHER_OUTPUT:/tmp/result.mp4\n')
    process.returncode = 0
    with patch('core.download_job.resolve_yt_dlp_binary', return_value='/bin/yt-dlp'), patch('core.download_job.get_ffmpeg_binary', return_value='/bin/ffmpeg'), patch('core.download_job.subprocess.Popen', return_value=process) as popen:
        job._run_ytdlp_binary_download()
    assert seen == [10, 50, 99]
    assert completed == ['/tmp/result.mp4']
    assert 'ffmpeg:-progress pipe:1 -nostats -stats_period 0.5' in popen.call_args.args[0]
    assert statuses[-1] == '완료'
