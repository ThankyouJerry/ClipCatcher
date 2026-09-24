#!/bin/bash
# Build script for macOS

set -euo pipefail

echo "🔨 Building ClipCatcher for macOS..."

BUILD_ROOT="$(mktemp -d)"
trap 'rm -rf "$BUILD_ROOT"' EXIT

# Build with PyInstaller
echo "📦 Building application..."
python3 -m PyInstaller \
    --distpath "$BUILD_ROOT/dist" \
    --workpath "$BUILD_ROOT/build" \
    build.spec

# Desktop folders can reapply Finder metadata that invalidates code signing.
# Stage the release bundle outside File Provider before signing and archiving.
STAGED_APP="$BUILD_ROOT/ClipCatcher.app"

echo "🔏 Preparing and verifying release bundle..."
ditto --noextattr --noacl --norsrc "$BUILD_ROOT/dist/ClipCatcher.app" "$STAGED_APP"
xattr -cr "$STAGED_APP"
find "$STAGED_APP" -type l -exec xattr -cs {} +
codesign --force --deep --sign - "$STAGED_APP"
codesign --verify --deep --strict --verbose=1 "$STAGED_APP"

echo "🧪 Running packaged smoke test..."
"$STAGED_APP/Contents/MacOS/ClipCatcher" --smoke

echo "🗜️ Creating release archive..."
ditto -c -k --sequesterRsrc --keepParent \
    "$STAGED_APP" "$BUILD_ROOT/ClipCatcher-macOS.zip"

mkdir -p dist
mv "$BUILD_ROOT/ClipCatcher-macOS.zip" dist/ClipCatcher-macOS.zip

echo "✅ Build successful!"
echo "📦 Release archive: dist/ClipCatcher-macOS.zip"
shasum -a 256 dist/ClipCatcher-macOS.zip
