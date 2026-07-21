#!/bin/bash
# Build script for macOS

set -euo pipefail

echo "🔨 Building ClipCatcher for macOS..."

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf build dist

# Build with PyInstaller
echo "📦 Building application..."
python3 -m PyInstaller build.spec

# Desktop folders can reapply Finder metadata that invalidates code signing.
# Stage the release bundle outside File Provider before signing and archiving.
STAGING_DIR="$(mktemp -d)"
trap 'rm -rf "$STAGING_DIR"' EXIT
STAGED_APP="$STAGING_DIR/ClipCatcher.app"

echo "🔏 Preparing and verifying release bundle..."
ditto --noextattr --noacl --norsrc dist/ClipCatcher.app "$STAGED_APP"
xattr -cr "$STAGED_APP"
find "$STAGED_APP" -type l -exec xattr -cs {} +
codesign --force --deep --sign - "$STAGED_APP"
codesign --verify --deep --strict --verbose=1 "$STAGED_APP"

echo "🧪 Running packaged smoke test..."
"$STAGED_APP/Contents/MacOS/ClipCatcher" --smoke

echo "🗜️ Creating release archive..."
ditto -c -k --sequesterRsrc --keepParent \
    "$STAGED_APP" dist/ClipCatcher-macOS.zip

# The Desktop can reattach Finder metadata and invalidate a raw app bundle.
# Keep only the verified archive as the release artifact.
rm -rf dist/ClipCatcher.app dist/ClipCatcher

echo "✅ Build successful!"
echo "📦 Release archive: dist/ClipCatcher-macOS.zip"
shasum -a 256 dist/ClipCatcher-macOS.zip
