#!/bin/bash
# Build script for macOS

echo "🔨 Building ClipCatcher for macOS..."

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf build dist

# Build with PyInstaller
echo "📦 Building application..."
python3 -m PyInstaller build.spec

if [ $? -eq 0 ]; then
    echo "✅ Build successful!"
    echo "📁 Application location: dist/ClipCatcher.app"
    echo ""
    echo "To create DMG (requires create-dmg):"
    echo "  brew install create-dmg"
    echo "  create-dmg --volname 'ClipCatcher' --window-size 600 400 --icon-size 100 --app-drop-link 450 150 ClipCatcher.dmg dist/ClipCatcher.app"
else
    echo "❌ Build failed!"
    exit 1
fi
