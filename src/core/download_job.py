"""
Download Manager with automatic method selection
"""
import os
import sys
import re
import signal
import subprocess
import threading
import tempfile
import asyncio
from pathlib import Path
from typing import Dict, Optional
import yt_dlp

from core.dependency_check import resolve_yt_dlp_binary
from core.segment_downloader import SegmentDownloader
from core.ffmpeg_utils import get_ffmpeg_binary
from core.url_utils import is_youtube_url, parse_media_url


def build_final_cut_format_selector(format_selector: Optional[str] = None) -> str:
    """Prefer H.264 video and AAC audio while preserving the quality limit."""
    height_match = re.search(r'height<=(\d+)', format_selector or '')
    height_filter = f'[height<={height_match.group(1)}]' if height_match else ''

    return '/'.join([
        f'bestvideo[vcodec^=avc1]{height_filter}+bestaudio[acodec^=mp4a]',
        f'bestvideo[vcodec^=avc1]{height_filter}+bestaudio[ext=m4a]',
        f'best[vcodec^=avc1][acodec^=mp4a]{height_filter}',
        f'best[vcodec^=avc1]{height_filter}',
    ])


def select_download_format(url: str, format_selector: Optional[str] = None) -> str:
    """Apply editor-compatible constraints only to YouTube downloads."""
    if is_youtube_url(url):
        return build_final_cut_format_selector(format_selector)
    return format_selector or 'bestvideo+bestaudio/best'


class DownloadEvent:
    """Small synchronous callback sink; GUI subclasses use native Qt signals."""

    def __init__(self):
        self._callbacks = []

    def connect(self, callback):
        self._callbacks.append(callback)

    def emit(self, *args):
        for callback in tuple(self._callbacks):
            callback(*args)


class DownloadJob:
    """Synchronous download job shared by CLI and the Qt worker."""
    
    
    def __init__(
        self, 
        url: str, 
        output_path: str, 
        cookies_header: str = "",
        cookies_netscape: str = "",
        use_manual_download: bool = False,
        video_id: Optional[str] = None,
        quality: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        format_selector: Optional[str] = None,  # yt-dlp format selector (YouTube quality)
        use_subprocess: bool = False,
    ):
        for name in ("progress_updated", "status_changed", "download_completed", "download_error"):
            if not hasattr(self, name):
                setattr(self, name, DownloadEvent())
        self.url = url
        self.output_path = output_path
        self.cookies_header = cookies_header
        self.cookies_netscape = cookies_netscape
        self.use_manual_download = use_manual_download
        self.video_id = video_id
        self.quality = quality
        self.start_time = start_time
        self.end_time = end_time
        self.use_subprocess = use_subprocess
        self.format_selector = format_selector
        self.should_stop = False
        self.cookie_file = None
        self.process: Optional[subprocess.Popen] = None
        self._stopping_process: Optional[subprocess.Popen] = None
    
    def run(self):
        """Run the download"""
        try:
            if self.use_manual_download:
                self._run_manual_download()
            else:
                self._run_ytdlp_download()
        except Exception as e:
            self.download_error.emit(str(e))
        finally:
            # A parser, stream, or callback failure must not leave yt-dlp alive.
            if self.process is not None and self.process.poll() is None:
                self.stop()
            self.process = None
            self._cleanup_cookie_file()
    
    def _run_manual_download(self):
        """Run manual segment download"""
        loop = asyncio.new_event_loop()
        try:
            self.status_changed.emit("수동 다운로드 시작 중...")
            asyncio.set_event_loop(loop)

            # Signed HLS URLs expire quickly, so refresh metadata immediately
            # before starting the fallback segment downloader.
            from core.chzzk_api import ChzzkAPI
            api = ChzzkAPI()
            fresh_metadata = loop.run_until_complete(
                api.fetch_vod_metadata(self.video_id, self.cookies_header)
            )

            if fresh_metadata.get("vod_status") == "ABR_HLS":
                self.url = fresh_metadata.get("url", self.url)
                self.status_changed.emit(
                    "VOD 변환 완료: yt-dlp 방식으로 전환합니다..."
                )
                self._run_ytdlp_download()
                return

            m3u8_url = api.get_master_playlist_url(fresh_metadata)
            if not m3u8_url:
                raise RuntimeError(
                    "현재 다운로드 가능한 서명된 HLS 재생목록을 찾지 못했습니다."
                )

            downloader = SegmentDownloader()

            def progress_callback(current, total):
                if self.should_stop:
                    raise RuntimeError("사용자가 다운로드를 취소했습니다.")
                progress = int((current / total) * 100) if total > 0 else 0
                self.progress_updated.emit(progress, 0, 0)
                self.status_changed.emit(f"다운로드 중... ({current}/{total} 세그먼트)")

            # Parse cookies
            cookies_dict = self._parse_cookie_header(self.cookies_header)

            # Use same headers as yt-dlp
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://chzzk.naver.com/',
                'Origin': 'https://chzzk.naver.com'
            }
            
            output_path = loop.run_until_complete(
                downloader.download_video(
                    m3u8_url,
                    self.output_path,
                    progress_callback,
                    headers=headers,
                    cookies=cookies_dict,
                    target_quality=self.quality,
                    start_time=self.start_time,
                    end_time=self.end_time,
                    cancel_callback=lambda: self.should_stop,
                    process_callback=self._set_active_process,
                )
            )

            self.status_changed.emit("완료")
            self.download_completed.emit(output_path)

        except Exception as exc:
            if not self.should_stop:
                self.download_error.emit(f"수동 다운로드 실패: {str(exc)}")
        finally:
            loop.close()
            asyncio.set_event_loop(None)

    def _run_ytdlp_download(self):
        """Run yt-dlp download.

        The app-owned or system yt-dlp binary is preferred for every supported
        service because the bundled Python package can lag behind site changes.
        """
        self._refresh_clip_stream_url()
        if resolve_yt_dlp_binary():
            self._run_ytdlp_binary_download()
        elif self.use_subprocess:
            # CLI cancellation must include package-backed FFmpeg subprocesses.
            self._run_ytdlp_binary_download([sys.executable, "-m", "yt_dlp"])
        else:
            self._run_ytdlp_package_download()

    def _refresh_clip_stream_url(self):
        """Resolve a fresh signed progressive URL for CHZZK clips."""
        parsed = parse_media_url(self.url)
        if not parsed or parsed.get("type") != "clip":
            return

        from core.chzzk_api import ChzzkAPI

        metadata = asyncio.run(
            ChzzkAPI().fetch_clip_metadata(parsed["id"], self.cookies_header)
        )
        resolutions = metadata.get("resolutions") or []
        selected = next(
            (item for item in resolutions if item.get("label") == self.quality),
            resolutions[0] if resolutions else None,
        )
        if not selected or selected.get("url") == metadata.get("url"):
            raise RuntimeError("치지직 클립의 다운로드 주소를 확인하지 못했습니다.")
        self.url = selected["url"]

    def _run_ytdlp_binary_download(self, command_prefix=None):
        """Download with the validated app-owned or system yt-dlp binary."""
        import re as _re
        import os

        ytdlp_bin = resolve_yt_dlp_binary() if command_prefix is None else None
        if command_prefix is None and not ytdlp_bin:
            raise Exception(
                "yt-dlp를 찾을 수 없습니다. 앱을 다시 실행해 설치 안내 팝업을 확인해주세요."
            )
        output_template = self.output_path.replace("%", "%%") + ".%(ext)s"

        # ── 명령어 구성 (URL은 반드시 마지막) ──────────────────
        cmd = list(command_prefix or [ytdlp_bin]) + [
            "--ignore-config",
            "--no-playlist",
            "--socket-timeout", "30",
            "--retries", "10",
            "--fragment-retries", "10",
            "--extractor-retries", "3",
        ]
        fmt = select_download_format(self.url, self.format_selector)
        cmd += ["-f", fmt]
        cmd += ["--merge-output-format", "mp4"]
        cmd += ["--print", "after_move:CLIPCATCHER_OUTPUT:%(filepath)s", "--progress"]
        cmd += ["--newline"]        # 진행률 한 줄씩 출력
        cmd += ["--no-warnings"]
        cmd += ["-o", output_template]

        if self.cookies_netscape:
            self.cookie_file = tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".txt",
                delete=False,
            )
            self.cookie_file.write(self.cookies_netscape)
            self.cookie_file.close()
            cmd += ["--cookies", self.cookie_file.name]

        # 시간 범위 (URL 앞에 추가)
        if self.start_time is not None or self.end_time is not None:
            start = self.start_time or 0
            end   = self.end_time
            if end is None:
                section = f"*{start}-inf"
            else:
                section = f"*{start}-{end}"
            cmd += ["--download-sections", section]
            cmd += ["--force-keyframes-at-cuts"]  # 정확한 컷팅을 위해

        # ffmpeg 경로 (URL 앞에 추가)
        ffmpeg_path = get_ffmpeg_binary()
        ffmpeg_dir = os.path.dirname(ffmpeg_path)
        env = os.environ.copy()
        extra_path_dirs = [ffmpeg_dir]
        if sys.platform == "darwin":
            extra_path_dirs.extend(["/opt/homebrew/bin", "/usr/local/bin"])
        extra_path_dirs = [path for path in extra_path_dirs if path]
        env["PATH"] = os.pathsep.join(extra_path_dirs + [env.get("PATH", "")])
        cmd += ["--ffmpeg-location", ffmpeg_path]

        # URL은 항상 마지막
        cmd += [self.url]

        # Do not log command lines: refreshed URLs may contain signed tokens.
        self.status_changed.emit("다운로드 시작 중...")

        popen_kwargs = {}
        if os.name == "nt":
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            popen_kwargs["start_new_session"] = True
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", bufsize=1, env=env,
            **popen_kwargs,
        )
        self.process = proc
        if self.should_stop:
            self.stop()
            return
        recent_lines = []

        # 진행률 파싱용 패턴
        pct_re    = _re.compile(r'\[download\]\s+([\d.]+)%')
        speed_re  = _re.compile(r'([\d.]+)([KMG]?)iB/s')
        eta_re    = _re.compile(r'ETA\s+([\d:]+)')
        # ffmpeg 재인코딩 진행률 (--force-keyframes-at-cuts 시 사용)
        ftime_re  = _re.compile(r'time=([\d:]+\.?\d*)')
        fspeed_re = _re.compile(r'speed=\s*([\d.]+)x')

        # 구간 다운로드 시 총 길이 계산 (진행률 계산용)
        section_duration = None
        if self.start_time is not None and self.end_time is not None:
            section_duration = self.end_time - self.start_time
        elif self.end_time is not None:
            section_duration = self.end_time

        def _parse_speed(m):
            val = float(m.group(1))
            unit = m.group(2)
            mul = {'K': 1024, 'M': 1024**2, 'G': 1024**3}.get(unit, 1)
            return int(val * mul)

        def _parse_eta(s):
            parts = s.split(':')
            try:
                if len(parts) == 3:
                    return int(parts[0])*3600 + int(parts[1])*60 + int(parts[2])
                elif len(parts) == 2:
                    return int(parts[0])*60 + int(parts[1])
                return int(parts[0])
            except Exception:
                return 0

        def _ftime_to_secs(t):
            """HH:MM:SS.xx → float seconds"""
            try:
                parts = t.split(':')
                if len(parts) == 3:
                    return int(parts[0])*3600 + int(parts[1])*60 + float(parts[2])
                elif len(parts) == 2:
                    return int(parts[0])*60 + float(parts[1])
                return float(parts[0])
            except Exception:
                return 0.0

        output_path = self.output_path + ".mp4"
        for line in proc.stdout:
            if self.should_stop:
                self._terminate_process_tree(proc)
                return

            line = line.strip()
            print(f"YTDLP OUT: {line}")
            if line:
                recent_lines.append(line)
                if len(recent_lines) > 20:
                    recent_lines.pop(0)

            # ── [download] X% 진행률 (일반 다운로드) ───────────
            pm = pct_re.search(line)
            if pm:
                pct   = int(float(pm.group(1)))
                speed = _parse_speed(speed_re.search(line)) if speed_re.search(line) else 0
                eta   = _parse_eta(eta_re.search(line).group(1)) if eta_re.search(line) else 0
                self.progress_updated.emit(pct, speed, eta)
                self.status_changed.emit(f"다운로드 중... {pm.group(1)}%")

            # ── ffmpeg frame= time= 진행률 (재인코딩) ──────────
            elif 'time=' in line and 'frame=' in line:
                ft = ftime_re.search(line)
                if ft and section_duration and section_duration > 0:
                    elapsed = _ftime_to_secs(ft.group(1))
                    pct = min(int(elapsed / section_duration * 100), 99)
                    sm = fspeed_re.search(line)
                    if sm:
                        spd = float(sm.group(1))
                        status = f"구간 인코딩 중... (인코딩 속도 {spd:.1f}배속)"
                    else:
                        status = "구간 인코딩 중..."
                    self.progress_updated.emit(pct, 0, 0)
                    self.status_changed.emit(status)
                elif ft:
                    self.status_changed.emit("구간 인코딩 중...")


            if line.startswith("CLIPCATCHER_OUTPUT:"):
                output_path = line.removeprefix("CLIPCATCHER_OUTPUT:")

            # ── 파일 경로 추적 ─────────────────────────────────
            dest_m = _re.search(r'\[download\] Destination: (.+)', line)
            if dest_m:
                output_path = dest_m.group(1).strip()
                self.status_changed.emit("파일 다운로드 중...")
            merge_m = _re.search(r'\[Merger\] Merging formats into "(.+)"', line)
            if merge_m:
                output_path = merge_m.group(1).strip()
                self.status_changed.emit("파일 병합 중...")

        try:
            proc.wait()
            if self.should_stop:
                return
            print(f"DEBUG: yt-dlp finished with code {proc.returncode}")
            if proc.returncode != 0:
                tail = "\n".join(recent_lines[-6:]) if recent_lines else ""
                detail = f"\n최근 로그:\n{tail}" if tail else ""
                raise Exception(f"yt-dlp 다운로드 실패 (코드 {proc.returncode}){detail}")

            self.status_changed.emit("완료")
            self.download_completed.emit(output_path)
        finally:
            if self.cookie_file and os.path.exists(self.cookie_file.name):
                try:
                    os.remove(self.cookie_file.name)
                except:
                    pass


    def _run_ytdlp_package_download(self):
        """Fallback download using the bundled Python yt_dlp package."""
        actual_output_path = None
        postprocessed_path = None

        def remember_output(event):
            nonlocal postprocessed_path
            if event.get("status") == "finished":
                postprocessed_path = (event.get("info_dict") or {}).get("filepath") or postprocessed_path
        
        try:
            # Create cookie file if cookies provided
            if self.cookies_netscape:
                self.cookie_file = tempfile.NamedTemporaryFile(
                    mode='w', 
                    suffix='.txt', 
                    delete=False
                )
                self.cookie_file.write(self.cookies_netscape)
                self.cookie_file.close()
            
            fmt = select_download_format(self.url, self.format_selector)
            ffmpeg_path = get_ffmpeg_binary()
            ydl_opts = {
                'format': fmt,
                'outtmpl': self.output_path.replace('%', '%%') + '.%(ext)s',
                'merge_output_format': 'mp4',
                'progress_hooks': [self._progress_hook],
                'postprocessor_hooks': [remember_output],
                'quiet': True,
                'no_warnings': True,
                'noplaylist': True,
                'socket_timeout': 30,
                'retries': 10,
                'fragment_retries': 10,
                'extractor_retries': 3,
                'ffmpeg_location': ffmpeg_path,
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }],
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                }
            }
            
            # Add range download support
            if self.start_time is not None or self.end_time is not None:
                def download_ranges_callback(info_dict, ydl):
                    return [{
                        'start_time': self.start_time if self.start_time is not None else 0,
                        'end_time': self.end_time if self.end_time is not None else float('inf')
                    }]
                ydl_opts['download_ranges'] = download_ranges_callback
                ydl_opts['force_keyframes_at_cuts'] = True
            
            if self.cookie_file:
                ydl_opts['cookiefile'] = self.cookie_file.name
            
            self.status_changed.emit("다운로드 시작 중...")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                if self.should_stop:
                    return
                info = ydl.extract_info(self.url, download=True)
                if info:
                    actual_output_path = ydl.prepare_filename(info)
            
            self.status_changed.emit("완료")
            final_path = postprocessed_path or actual_output_path or (self.output_path + '.mp4')
            self.download_completed.emit(final_path)
            
        except Exception as e:
            self.download_error.emit(str(e))
        
        finally:
            if self.cookie_file and os.path.exists(self.cookie_file.name):
                try:
                    os.remove(self.cookie_file.name)
                except:
                    pass
    
    def _progress_hook(self, d):
        """Progress hook for yt-dlp"""
        if self.should_stop:
            raise Exception("Download cancelled by user")
        
        if d['status'] == 'downloading':
            try:
                total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                downloaded_bytes = d.get('downloaded_bytes', 0)
                
                progress = 0
                if total_bytes > 0:
                    progress = int((downloaded_bytes / total_bytes) * 100)
                
                speed = d.get('speed', 0) or 0
                eta = d.get('eta', 0) or 0
                
                self.progress_updated.emit(progress, speed, eta)
                
                # Update status with fragment info if available
                fragment_index = d.get('fragment_index', 0)
                fragment_count = d.get('fragment_count', 0)
                if fragment_count > 0:
                    self.status_changed.emit(
                        f"다운로드 중... ({fragment_index}/{fragment_count} 조각)"
                    )
                else:
                    self.status_changed.emit("다운로드 중...")
                    
            except Exception:
                pass
        
        elif d['status'] == 'finished':
            self.status_changed.emit("병합 중...")
            self.progress_updated.emit(100, 0, 0)
    
    def stop(self):
        """Request cancellation without blocking the GUI thread."""
        self.should_stop = True
        process = self.process
        if not process or process.poll() is not None:
            return
        if self._stopping_process is process:
            return
        self._stopping_process = process

        if os.name == "nt":
            def terminate_windows():
                try:
                    self._terminate_process_tree(process, force=True)
                except (OSError, subprocess.TimeoutExpired):
                    if process.poll() is None:
                        process.kill()
                finally:
                    self._reap_process(process)
            # taskkill may be slow; never run it on the GUI or signal thread.
            threading.Thread(target=terminate_windows, daemon=False).start()
            return

        # Capture the session we created before its leader can exit. FFmpeg may
        # remain alive after yt-dlp handles SIGTERM and exits.
        process_group = None
        if os.name != "nt":
            try:
                candidate = os.getpgid(process.pid)
                if candidate == process.pid:
                    process_group = candidate
            except ProcessLookupError:
                pass
        self._terminate_process_tree(process)

        def force_kill_if_needed():
            try:
                threading.Event().wait(2)
                if process_group is not None:
                    try:
                        os.killpg(process_group, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                elif process.poll() is None:
                    try:
                        self._terminate_process_tree(process, force=True)
                    except OSError:
                        pass
            finally:
                self._reap_process(process)

        # Keep the CLI alive until its child-process cleanup has completed.
        threading.Thread(target=force_kill_if_needed, daemon=False).start()

    @staticmethod
    def _reap_process(process):
        """Reap a cancelled child off the GUI/signal thread."""
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)

    @staticmethod
    def _terminate_process_tree(process: subprocess.Popen, force: bool = False):
        """Terminate yt-dlp and any ffmpeg child processes it started."""
        if process.poll() is not None:
            return
        if os.name == "nt":
            command = ["taskkill", "/PID", str(process.pid), "/T"]
            if force:
                command.append("/F")
            subprocess.run(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=10,
            )
            return

        try:
            process_group = os.getpgid(process.pid)
            if process_group == process.pid:
                os.killpg(process_group, signal.SIGKILL if force else signal.SIGTERM)
            elif force:
                process.kill()
            else:
                process.terminate()
        except (OSError, ProcessLookupError):
            if force:
                process.kill()
            else:
                process.terminate()

    def _cleanup_cookie_file(self):
        """Remove a temporary cookie file once a worker exits."""
        if self.cookie_file and os.path.exists(self.cookie_file.name):
            try:
                os.remove(self.cookie_file.name)
            except OSError:
                pass

    def _set_active_process(self, process: Optional[subprocess.Popen]):
        """Expose manual FFmpeg to the existing non-blocking cancel path."""
        self.process = process

    @staticmethod
    def _parse_cookie_header(cookie_header: str) -> Dict[str, str]:
        cookies_dict: Dict[str, str] = {}
        if not cookie_header:
            return cookies_dict
        for cookie in cookie_header.split(';'):
            if '=' in cookie:
                key, value = cookie.strip().split('=', 1)
                cookies_dict[key.strip()] = value.strip()
        return cookies_dict
