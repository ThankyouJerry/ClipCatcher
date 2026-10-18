# Native release verification

Run **Build native release packages** manually for build-only verification.
The workflow builds Windows x64 GUI, macOS Apple Silicon GUI, and Linux x86_64
headless CLI independently on native runners, tests source code, and smoke-tests
the packaged binaries. Linux additionally downloads a generated local fixture
through the bundled yt-dlp helper with no system Python/yt-dlp on PATH.

Update APP_VERSION in src/main.py, build.spec bundle version and release notes
before tagging. Push a new `release/vX.Y.Z` branch at the reviewed commit to
build and create its new tag and **draft**. A new `v*` tag also triggers the same
gated draft flow. Only after all three jobs pass, the workflow
checks the tag matches APP_VERSION, verifies the three expected archives, and
includes SHA256SUMS. Existing releases are never overwritten; the branch flow also refuses an existing tag. After creating the draft, the workflow checks uploaded asset names/sizes
against the local manifest and only then publishes it. Manual workflow runs never
publish or create releases. A failure before publication leaves the release unpublished.

macOS uses ad-hoc signing, not Developer ID signing/notarization. Windows is
unsigned. Do not describe these packages as notarized or signed by a trusted
publisher. Linux is CLI-only; Linux GUI compatibility is not claimed.
Real public-service downloads and interactive GUI testing are separate from
these deterministic build smoke tests. Consult BUILD_REPORT.md for their scope.
