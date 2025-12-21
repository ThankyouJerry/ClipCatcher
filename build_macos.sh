#!/bin/bash
# Build script for macOS

echo "🔨 Building Chzzk Downloader for macOS..."

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf build dist

# Build with PyInstaller
# Build with PyInstaller
echo "📦 Building application..."
PY_BIN="../ytdlp-venv/bin/python3"

if [ ! -f "$PY_BIN" ]; then
    # Fallback to system python/pyinstaller if venv not found (or user running inside venv)
    pyinstaller build.spec
else
    "$PY_BIN" -m PyInstaller build.spec
fi

if [ $? -eq 0 ]; then
    echo "✅ Build successful!"
    echo "📁 Application location: dist/ChzzkDownloader.app"
    echo ""
    echo "To create DMG (requires create-dmg):"
    echo "  brew install create-dmg"
    echo "  create-dmg --volname 'Chzzk Downloader' --window-size 600 400 --icon-size 100 --app-drop-link 450 150 ChzzkDownloader.dmg dist/ChzzkDownloader.app"
else
    echo "❌ Build failed!"
    exit 1
fi
