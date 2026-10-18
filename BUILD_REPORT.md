# Current release verification: v2.0.13 (2026-10-18)

Release source: `43f6006d3b959265297ed3c8747176ae13e7fe52`.

- [Native package workflow](https://github.com/ThankyouJerry/ClipCatcher/actions/runs/39129088766): all four jobs passed, including Windows/macOS/Linux package checks and release assembly.
- [Cross-platform regression workflow](https://github.com/ThankyouJerry/ClipCatcher/actions/runs/39129088598): all nine jobs passed.
- [Published v2.0.13 assets](https://github.com/ThankyouJerry/ClipCatcher/releases/tag/v2.0.13): Windows x64 GUI, macOS Apple Silicon GUI, Linux x86_64 CLI, and SHA256SUMS.
- README screenshots show the actual released Qt UI with explicitly synthetic sample data. They are not evidence of live downloads.
- Package checks do not guarantee downloads from every external video or network. Historical live CHZZK checks below retain their original scope.

## Historical build records

Everything below records the state at the time of each experiment. Statements about pending builds or unpublished packages are historical and are superseded by the current release verification above.

# v2.0.12 packaging validation (2026-10-18)

- Local Linux headless tests: 56 tests and 11 subtests passed.
- Full source suite with Qt offscreen: 100 tests and 11 subtests passed.
- Frozen Linux CLI built using PyInstaller 6.22.3; dependency check and bundled
  yt-dlp helper passed with no external Python/yt-dlp on PATH.
- Frozen helper downloaded a generated local MP4 byte-for-byte, then used its
  bundled FFmpeg 7.0.2-static to convert to AVI; system FFprobe verified 1s.
- Source GUI offscreen smoke constructs the real MainWindow with disposable
  config, suppresses dependency prompts, and exits cleanly without downloads.
- Windows and macOS native build/package checks have not run at the time this
  report was written. PR CI runs them before release; consult the exact commit's
  Actions results for passed/failed status, not this static report.
- Linux CHZZK long-VOD late-range cloud download is NOT verified. Imageio 7.0.2
  parses the stream but the bounded trial stalled; newer system builds failed
  the HLS extension check. No security checks were disabled.

See [release procedure](docs/RELEASING.md) and [Linux guide](docs/LINUX_PACKAGE.md).
The older build notes below are historical, not v2.0.12 validation evidence.

---

# ClipCatcher Build Report

## Local macOS Build

Use the macOS build script from the repository root:

```bash
./build_macos.sh
```

Expected output:

```text
dist/
├── ClipCatcher/
└── ClipCatcher.app/
```

To create a zip asset for GitHub Releases:

```bash
cd dist
zip -r ClipCatcher-macOS.zip ClipCatcher.app
```

## Windows Build

Windows builds are normally produced by GitHub Actions. To build manually on Windows:

```cmd
build_windows.bat
```

Expected executable path:

```text
dist\ClipCatcher\ClipCatcher.exe
```

## Release Assets

- `ClipCatcher-Windows.zip`
- `ClipCatcher-macOS.zip`

## Smoke Check

Before uploading a packaged build, run:

```bash
python src/main.py --smoke
```

For Windows GitHub Actions, the workflow runs:

```cmd
.\dist\ClipCatcher\ClipCatcher.exe --smoke
```

## macOS Security Note

Unsigned macOS apps can show an "unidentified developer" warning. For local testing:

```bash
xattr -cr dist/ClipCatcher.app
open dist/ClipCatcher.app
```

For public distribution, code signing and notarization should be considered separately.

## Local proxy compatibility follow-up (2026-10-18)

- Source commit: `9d63de9be4d2708ca2cff1b80dbdff403a56919b` (local, unpublished).
- Existing HTTPS proxy configuration is now forwarded explicitly to CHZZK API/HLS requests. No `.netrc` authentication, redirect allowance, CDN-cookie expansion, TLS relaxation or new proxy configuration was introduced.
- Full source suite: 110 passed, 11 subtests passed. Qt-free suite: 66 passed, 11 subtests passed. Independent review passed.
- Actual source CLI: public CHZZK VOD 15733051, 04:38:15–04:38:25, max 480p, no cookies; existing manual HLS route selected 7 overlapping segments. Exit 0 in about 30 seconds using system FFmpeg 7.1.5. FFprobe: 10.000 s, H.264 852×480, AAC, 2,031,644 bytes; complete decode passed.
- Rebuilt Linux frozen CLI passed dependency checks, bundled yt-dlp local HTTP fixture download, and bundled FFmpeg 1-second AVI transcode. Its external CHZZK download was not repeated.
- This follow-up and packaging changes remain unpublished. Existing merged-main CI does not validate these later local changes. Windows/macOS native release builds and public release remain pending.
