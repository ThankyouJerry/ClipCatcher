# ClipCatcher GitHub Release Guide

## Repository

- GitHub: `https://github.com/ThankyouJerry/ClipCatcher`
- Releases: `https://github.com/ThankyouJerry/ClipCatcher/releases`
- Pages: `https://thankyoujerry.github.io/ClipCatcher/`

## Normal Release Flow

1. Commit all intended source and documentation changes.
2. Run local checks:

```bash
PYTHONPATH=src python3 -m py_compile $(find src -name '*.py' -print)
PYTHONPATH=src python3 src/main.py --smoke
```

3. Push `main`.
4. Create and push a new version tag:

```bash
git tag v2.0.8
git push origin v2.0.8
```

5. GitHub Actions builds `ClipCatcher-Windows.zip` automatically.
6. Build macOS locally and upload `ClipCatcher-macOS.zip` to the same release.

## Manual macOS Asset

```bash
./build_macos.sh
cd dist
zip -r ClipCatcher-macOS.zip ClipCatcher.app
```

Upload the zip from the GitHub Release page.

## Release Notes Template

```markdown
## ClipCatcher v2.0.8

### Changes
- Validate CHZZK fast-replay ranges against the actual HLS playlist duration.
- Show publish time and video duration as separate metadata fields.

### Downloads
- Windows: ClipCatcher-Windows.zip
- macOS: ClipCatcher-macOS.zip

### Notice
Downloaded videos remain subject to the original creator's copyright and platform terms.
```
