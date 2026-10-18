# ClipCatcher Linux x86_64 CLI

This is a headless command-line application, not a Linux desktop app.
Requires x86_64 Linux with glibc 2.35 or newer (Ubuntu 22.04+). Python,
yt-dlp and FFmpeg are included in the package. Keep the executable and
`_internal` directory together. FFprobe is optional and not bundled.

```sh
tar -xzf ClipCatcher-Linux-x86_64.tar.gz
cd ClipCatcher-Linux-x86_64
./clipcatcher --cli check
./clipcatcher --cli info 'https://chzzk.naver.com/video/VIDEO_ID'
./clipcatcher --cli download 'https://chzzk.naver.com/video/VIDEO_ID' --start 00:10 --end 00:20 -o ./downloads
```

Use Ctrl+C to cancel. Internet access to the video service/CDN is required;
a successful dependency check does not verify access to a particular video.
Only download content you have permission to save. Cookies and login are not
imported by this CLI. See the repository README for supported sources/options.
