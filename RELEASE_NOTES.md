## ClipCatcher v2.0.15

### 수정 사항
- 구간 다운로드가 진행되는데도 0%와 ‘다운로드 시작 중’에 머물던 진행률 표시를 수정했습니다.
- FFmpeg 전용 진행 스트림으로 실제 처리 시간을 읽어 선택 구간 대비 진행률을 표시합니다. 저장 완료 전에는 최대 99%까지 표시합니다.
- 기존 설정·쿠키·저장 경로·다운로드 파일은 유지됩니다.

### 검증
- macOS 설치 앱에서 치지직과 YouTube 각각 20초·1080p 구간 다운로드, 중간 진행률 갱신, 완료를 확인했습니다.
- 두 출력 모두 H.264/AAC이며 정확히 20초, 전체 디코딩 검사에서 오류가 없었습니다.
- 진행률 회귀 테스트와 Windows/macOS/Linux 패키지 검사를 포함합니다. 모든 영상·네트워크 환경의 성공을 보장하지는 않습니다.

### 다운로드
- Windows x64: `ClipCatcher-Windows.zip`
- macOS Apple Silicon: `ClipCatcher-macOS.zip` (Intel 전용 빌드 없음)
- Linux x86_64: `ClipCatcher-Linux-x86_64.tar.gz` (glibc 2.35 이상, 명령줄 패키지)
- 무결성 확인: `SHA256SUMS`

Windows는 미서명, macOS는 ad-hoc 서명이며 Apple 공증은 포함하지 않습니다.
다운로드한 콘텐츠의 저작권과 플랫폼 이용약관을 준수해 주세요.
