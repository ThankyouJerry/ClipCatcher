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
