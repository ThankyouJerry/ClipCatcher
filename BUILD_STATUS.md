# ClipCatcher Build Status

## Current release (2026-10-18)

- Version: `v2.0.13`, source `43f6006d3b959265297ed3c8747176ae13e7fe52`.
- [Published release](https://github.com/ThankyouJerry/ClipCatcher/releases/tag/v2.0.13).
- Windows x64 GUI: `ClipCatcher-Windows.zip` (unsigned).
- macOS Apple Silicon GUI: `ClipCatcher-macOS.zip` (ad-hoc signed; not notarized; no Intel build).
- Linux x86_64 CLI: `ClipCatcher-Linux-x86_64.tar.gz` (glibc 2.35+; no GUI).
- Integrity manifest: `SHA256SUMS`.

## Verification and release process

- [Native build/package checks](https://github.com/ThankyouJerry/ClipCatcher/actions/runs/39129088766): all four jobs passed.
- [Cross-platform regression checks](https://github.com/ThankyouJerry/ClipCatcher/actions/runs/39129088598): all nine jobs passed.
- Windows, macOS, and Linux packages are built by GitHub Actions. A new version tag or `release/vX.Y.Z` branch creates a draft only after the required package checks pass. The workflow verifies uploaded asset names and sizes against the manifest, then publishes automatically. Manual workflow runs build and verify only.
- Follow [the release procedure](docs/RELEASING.md); do not replace an already published version's assets.
- Package smoke checks and synthetic screenshots do not establish that every external video downloads successfully.
