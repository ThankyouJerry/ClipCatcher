## ClipCatcher v2.0.12

### 주요 변경 사항

- Linux/클라우드에서 화면 없이 실행하는 CLI(`check`, `info`, `download`)를 추가했습니다.
- 다운로드 핵심 로직을 GUI와 분리하고 취소·자식 프로세스 정리·파일명 처리를 보완했습니다.
- 상단 도움말 메뉴에서 yt-dlp 상태를 확인할 수 있습니다.
- Windows GUI, macOS Apple Silicon 앱, Linux x86_64 CLI를 각각 빌드하고 패키지 시작 검사를 수행하는 배포 절차를 추가했습니다.

### 다운로드

- Windows x64: `ClipCatcher-Windows.zip`을 풀고 `ClipCatcher.exe` 실행
- macOS Apple Silicon: `ClipCatcher-macOS.zip`을 풀고 앱을 응용 프로그램 폴더로 이동 (Intel Mac 전용 빌드 없음)
- Linux x86_64 (glibc 2.35 이상): `ClipCatcher-Linux-x86_64.tar.gz`를 풀고 `./clipcatcher --cli check` 실행. GUI 앱이 아닌 명령줄 패키지입니다.
- 파일 무결성 확인: `SHA256SUMS`

Windows 앱은 코드 서명되지 않았으며 macOS 앱은 ad-hoc 서명만 되어 있습니다. Apple 공증은 포함하지 않습니다.
패키지 검사 통과가 모든 영상·네트워크 환경에서의 다운로드 성공을 보장하지는 않습니다.
치지직 접속 제한이나 DNS 오류가 있는 환경에서는 서비스 접근이 가능한 네트워크가 필요합니다.

다운로드한 콘텐츠의 저작권은 원 저작권자에게 있습니다. 플랫폼 이용약관과 저작권자의 허락 범위를 확인해 주세요.

### 검증 범위와 포함 도구

- 패키지 검사는 Windows/macOS의 실제 Qt 창 생성·종료와 Linux의 로컬 시험 영상 다운로드·변환을 포함합니다.
- Linux FFmpeg는 imageio-ffmpeg 0.6.0이 제공하는 7.0.2-static입니다. 각 플랫폼의 정확한 버전·빌드 정보와 라이선스는 패키지 내부 `third-party-notices`에 기록됩니다. FFprobe는 포함하지 않습니다.
- 이 환경의 치지직 장시간 VOD 후반 구간 다운로드는 완료를 확인하지 못했습니다. 모든 치지직 영상·구간의 클라우드 다운로드가 검증된 것으로 보아서는 안 됩니다.
