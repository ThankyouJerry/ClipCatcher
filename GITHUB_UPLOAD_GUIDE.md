# ClipCatcher GitHub Release Guide

Use [docs/RELEASING.md](docs/RELEASING.md) as the current release procedure. The previous Windows-only automation and manual macOS upload instructions are obsolete.

- [Repository](https://github.com/ThankyouJerry/ClipCatcher)
- [Published releases](https://github.com/ThankyouJerry/ClipCatcher/releases)
- [Current build status](BUILD_STATUS.md)

Windows x64 GUI, macOS Apple Silicon GUI, and Linux x86_64 CLI packages are built and smoke-tested by GitHub Actions. A new version tag or `release/vX.Y.Z` branch produces a draft after native checks pass; the workflow then verifies the uploaded asset manifest and publishes automatically. Manual workflow runs build and verify only. Review assets, SHA256SUMS, platform limits, release notes, README screenshots, and site documentation before starting a publishing workflow. Never overwrite an existing published release to hide a correction; use a new version.
