# ClipCatcher

치지직 VOD와 클립을 다운로드할 수 있는 데스크톱 애플리케이션입니다.

ClipCatcher는 기존 `chzzkdownloader`를 발전시킨 후속작으로, 더 나은 UI, 더 안정적인 다운로드 경험, 그리고 확장 가능한 구조를 목표로 만들었습니다.
이 계정에서는 ClipCatcher를 대표 프로젝트로 운영합니다.

## Why ClipCatcher

- 치지직 VOD와 클립을 더 편하게 다운로드
- GUI 기반으로 누구나 쉽게 사용 가능
- Windows / macOS에서 바로 실행 가능한 배포본 제공
- 이후 채팅/분석 도구와 연결 가능한 메인 앱

## Main Features

- 치지직 VOD 다운로드
- 치지직 클립 다운로드
- 해상도 선택 및 다운로드 품질 제어
- 여러 영상 링크를 한 줄씩 붙여넣어 기본 순차 대기열에 추가
- 순차 다운로드 큐와 진행중/완료/실패 상태 관리
- 완료 파일 및 다운로드 저장 폴더 바로 열기
- YouTube 다운로드의 Final Cut Pro 호환 코덱 우선 선택
- 치지직 빠른 다시보기의 실제 HLS 길이 기반 시간 범위 검증
- 직관적인 GUI 제공
- 크로스 플랫폼 배포 지원

## Latest Update

개발 브랜치에는 `도움말 → yt-dlp 상태 확인` 메뉴를 추가했습니다. 현재 사용 가능한 yt-dlp의 버전과 경로를 확인하고 재검사할 수 있습니다. 설치나 업데이트를 자동으로 수행하지 않습니다. 이 기능은 아래 `v2.0.11` 배포본에는 아직 포함되지 않았으며, 최신 Windows 빌드는 [GitHub Actions](https://github.com/ThankyouJerry/ClipCatcher/actions/workflows/build.yml)의 성공한 실행에서 `ClipCatcher-Windows` 아티팩트로 받을 수 있습니다(GitHub 로그인 필요).

`v2.0.11`에서는 `단일 파일`·`여러 파일` 입력 모드, 이미 사용 가능한 `yt-dlp`의 재설치 안내 생략, 다운로드 작업 스레드 수명 관리, 비표준 해상도 표시와 저장 파일명 충돌 방지를 반영했습니다. 업데이트하려면 [최신 배포본](https://github.com/ThankyouJerry/ClipCatcher/releases/latest)을 받아 기존 앱을 교체해주세요. 기존 설정과 다운로드한 영상은 유지됩니다.

`v2.0.10`에서는 변경된 치지직 클립 API에 맞춰 클립 정보·화질 조회와 다운로드를 복구했습니다. 다운로드 시작 직전에 NAVER 재생 API에서 만료되지 않은 클립 주소를 다시 받아 대기열에서도 안정적으로 처리합니다. 치지직 VOD/클립과 YouTube 링크를 실제 호스트 기준으로 검증하고, 메타데이터 요청에 시간 제한·재시도·응답 크기 제한을 적용했습니다. 앱에서 설치하는 `yt-dlp`는 공식 SHA-256 체크섬과 실행 가능 여부를 확인한 뒤에만 기존 파일을 교체합니다.

다운로드 안정성도 함께 강화했습니다. YouTube 재생목록 링크는 선택한 영상 한 개만 처리하며, 취소할 때 `yt-dlp`와 수동 HLS 병합에 사용되는 FFmpeg 프로세스까지 함께 종료합니다. 빠른 다시보기용 HLS 쿠키는 NAVER 도메인에만 전송하고, 재생목록/세그먼트 다운로드에는 제한 시간·재시도·크기 제한을 적용합니다. 앱 전용 `yt-dlp` 설치·업데이트는 백그라운드에서 진행되어 설치 중에도 화면이 멈추지 않습니다.

버전별 변경 내용은 [CHANGELOG.md](CHANGELOG.md)에서 확인할 수 있습니다.

## 사용 방식

- 개발 버전: 상단 메뉴바의 `도움말 → yt-dlp 상태 확인`에서 사용 가능 여부·버전·경로를 확인하고 `다시 확인`으로 재검사할 수 있습니다. 설치 파일을 변경하지 않으며, 최신 버전 조회는 아닙니다. 업데이트는 별도의 `yt-dlp 설치/업데이트` 메뉴를 사용합니다.

- `단일 파일`: 링크 하나의 정보를 가져온 뒤 화질과 시작·종료 시간을 선택해 다운로드합니다.
- `여러 파일`: 링크를 한 줄에 하나씩 입력하고 `대기열에 추가`를 누릅니다. 각 영상은 전체 길이와 확인 가능한 최고 화질로 추가되며, 기본 설정에서는 한 개씩 순서대로 다운로드합니다. 추가 중에는 버튼을 다시 눌러 남은 링크 조회를 중단할 수 있습니다.

## Screenshots

![ClipCatcher main screen](assets/screenshots/01-main.png)

| 진행중 | 완료 |
| --- | --- |
| ![ClipCatcher active downloads tab](assets/screenshots/02-active-tab.png) | ![ClipCatcher completed downloads tab](assets/screenshots/03-completed-tab.png) |

| 실패 |
| --- |
| ![ClipCatcher failed downloads tab](assets/screenshots/04-failed-tab.png) |

### 실제 링크 정보 조회 예시

아래 화면은 예시 치지직 VOD 링크를 앱에 입력한 뒤 `정보 가져오기`로 영상 정보와 화질 목록을 불러온 상태입니다.

| https://chzzk.naver.com/video/14046440 | https://chzzk.naver.com/video/14056205 |
| --- | --- |
| ![ClipCatcher demo for CHZZK video 14046440](assets/screenshots/demo-14046440.png) | ![ClipCatcher demo for CHZZK video 14056205](assets/screenshots/demo-14056205.png) |

## Project Position

ClipCatcher는 이 계정의 대표 프로젝트입니다.

관련 보조 도구:
- [chzzk-chat-exporter](https://github.com/ThankyouJerry/chzzk-chat-exporter): 치지직 채팅을 CSV로 내보내는 크롬 확장 프로그램
- [streamstamp](https://github.com/ThankyouJerry/streamstamp): 유튜브 타임스탬프 관리 도구

## Download

최신 실행 파일은 [Releases](https://github.com/ThankyouJerry/ClipCatcher/releases) 페이지에서 받을 수 있습니다.

- Windows: `ClipCatcher-Windows.zip`
- macOS: `ClipCatcher-macOS.zip`

## Website

ClipCatcher 소개, 사용사례, 사용법은 GitHub Pages에서 볼 수 있습니다.

- [ClipCatcher Website](https://thankyoujerry.github.io/ClipCatcher/)

## Runtime Dependency

실행/병합 과정에서 아래 도구가 필요합니다.

- `ffmpeg`
- `ffprobe`
- `yt-dlp` (소스 실행 기준)

이미 실행 가능한 `yt-dlp`가 앱 전용 폴더, 시스템 경로 또는 Python 패키지에 있다면 다시 설치하지 않아도 됩니다. 비트레이트 정보가 없으면 `kbps` 수치만 생략합니다. `자동 선택 (다운로드 시 화질 결정)`은 해상도 목록을 확보하지 못해 다운로드 시 사용 가능한 포맷을 고른다는 뜻입니다. YouTube는 Final Cut 호환 H.264 화질을 표시하며, 2:1·세로 영상 등은 `960p (1920×960)`처럼 실제 크기를 표시합니다.

## Run From Source

```bash
git clone https://github.com/ThankyouJerry/ClipCatcher.git
cd ClipCatcher
pip install -r requirements.txt
python src/main.py
```

## Recommended For

- 치지직 다시보기를 자주 저장하는 사용자
- 클립과 VOD를 한 앱에서 관리하고 싶은 사용자
- GUI 기반 다운로드 도구를 선호하는 사용자

## Copyright Notice

ClipCatcher는 사용자가 접근 가능한 영상의 저장을 돕는 도구입니다.
프로그램 사용과 다운로드는 자유롭게 할 수 있지만, 영상과 음성 등 콘텐츠의 저작권은 원 저작권자에게 있습니다.
개인 보관 범위를 넘어 재업로드, 공유, 편집물 공개, 상업적 이용을 할 때는 각 플랫폼의 이용약관과 원 저작권자의 허락 범위를 반드시 확인해주세요.

## Roadmap

- 다운로드 안정성 개선
- UI/UX 개선
- 채팅/분석 도구와의 워크플로우 연결 강화

## License

MIT License

## Cross-platform CLI / Linux Cloud (개발 버전)

Windows·macOS·Linux에서 같은 다운로드 코어를 사용합니다. GUI에도 동일한 파일명 처리·최종 파일 경로 추적·POSIX 프로세스 정리 개선이 적용됩니다. CLI는 디스플레이나 PyQt6 없이 치지직 공개 VOD/클립과 YouTube 영상을 처리합니다.
Python 3.10 이상과 시스템 FFmpeg/FFprobe가 필요합니다. 현재 Linux 실행 파일 배포는 없으며 소스로 실행합니다.

```bash
# Ubuntu / Debian (관리자 권한이 있는 환경)
sudo apt-get update && sudo apt-get install -y python3-venv ffmpeg
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-headless.txt
python src/main.py --cli check
python src/main.py --cli info 'https://chzzk.naver.com/video/14046440'
# 명시적으로 구간을 지정하면 전체 VOD 다운로드를 피할 수 있습니다.
python src/main.py --cli download 'https://chzzk.naver.com/video/14046440' \
  --start 00:01:00 --end 00:01:10 --quality 720p --output-dir ./downloads
```

- `python src/cli.py ...`로도 같은 명령을 사용할 수 있습니다.
- `check`: 로컬 yt-dlp/FFmpeg 상태를 JSON으로 출력합니다. 설치/업데이트나 영상 서비스 요청을 하지 않습니다.
- `info`: 공개 메타데이터를 조회하고 제목, 길이, 화질을 JSON으로 출력합니다. 미디어를 저장하지 않습니다.
- `download`: 영상 하나를 저장합니다. 시간 옵션을 생략하면 전체 영상을 다운로드합니다. `--start`만 지정하면 끝까지 다운로드합니다.
- 시간은 초, `MM:SS`, `HH:MM:SS` 형식이며 소수 초도 지원합니다. 종료 시각은 시작 시각보다 커야 합니다.
- `--quality 720p`는 최대 높이입니다. 해당 높이 이하의 확인 가능한 화질이 없으면 오류로 종료합니다. 생략하면 확인된 최고 화질을 선택합니다. YouTube는 기존 앱과 같은 H.264/AAC 호환 형식을 사용합니다.
- 기본 저장 위치는 실행한 디렉터리의 `downloads/`입니다. `--output-dir`로 쓰기 가능한 절대/상대 경로를 선택하세요. 파일명에 고유 접미사를 붙여 같은 영상의 반복 작업을 구분합니다.
- 성공 시 표준 출력은 최종 파일 경로, 진행/진단 메시지는 표준 오류입니다. 종료 코드는 성공 `0`, 실행 실패 `1`, 잘못된 인수 `2`, 중단 `130`입니다. Ctrl+C와 SIGTERM은 다운로드 및 자식 프로세스 정리를 요청합니다.
- CLI는 GUI의 저장된 설정/쿠키를 읽지 않습니다. 로그인, 성인 인증, 회원 전용 콘텐츠는 지원 범위 밖입니다. 서비스 차단/네트워크 제한/접근 권한 문제를 우회하지 않습니다.
- 일반 VOD·클립·YouTube는 기존 yt-dlp 경로, 변환 전 CHZZK VOD는 기존 수동 HLS 다운로드 경로를 공유합니다. 원본의 키프레임/서버/형식에 따라 구간 요청에도 추가 미디어 전송 및 재인코딩이 필요할 수 있습니다.
- GUI는 기존 `requirements.txt` 설치와 `python src/main.py` 실행 방식을 유지합니다. Linux 앱 전용 도구 폴더는 절대 경로인 `$XDG_DATA_HOME/ClipCatcher/bin`, 미설정 시 `~/.local/share/ClipCatcher/bin`입니다.

### 테스트

```bash
# Qt 없는 환경에서 실행 가능한 오프라인 테스트
python -m pip install pytest
python -m pytest -q tests/test_cli.py tests/test_headless_regressions.py tests/test_headless_integration.py \
  tests/test_url_utils.py tests/test_segment_downloader.py \
  tests/test_app_tools.py tests/test_dependency_check.py

# GUI 의존성이 설치된 개발 환경: 기존 UI 회귀 테스트도 포함
QT_QPA_PLATFORM=offscreen python -m pytest -q
```

테스트는 실제 외부 영상 다운로드 성공을 보증하지 않습니다. 사이트별 접근과 포맷은 변경될 수 있습니다.

### Windows / macOS CLI

macOS는 `brew install ffmpeg`, Windows는 FFmpeg/FFprobe를 설치하고 PATH에 등록한 뒤 가상 환경을 만드세요. Windows PowerShell에서는 다음처럼 활성화 없이 실행할 수 있습니다.

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-headless.txt
.\.venv\Scripts\python.exe src/main.py --cli check
.\.venv\Scripts\python.exe src/main.py --cli info 'https://chzzk.naver.com/video/14046440'
```

macOS/Linux는 위 POSIX 명령을 사용합니다. 가상 환경을 활성화하지 않아도 CLI는 필요 시 현재 Python의 `-m yt_dlp`를 별도 프로세스로 실행하여 중단 처리를 유지합니다. GUI 실행 방식과 기존 설정 위치는 변경하지 않습니다.

### 검증 범위

- Linux Python 3.12: 전체 회귀 테스트, Qt 미설치 환경의 CLI 테스트, `check`/`--smoke` 실행을 확인했습니다.
- 실제 FFmpeg로 만든 1초짜리 로컬 테스트 영상을 yt-dlp로 저장하고 FFprobe로 길이와 최종 경로를 검증합니다. 외부 VOD 다운로드 검증과는 별개입니다.
- Windows·macOS·Linux의 Python 3.10/3.12 headless 테스트와 세 운영체제의 GUI 회귀 테스트를 GitHub Actions 매트릭스로 구성했습니다. 각 실행의 성공 여부는 [Actions](https://github.com/ThankyouJerry/ClipCatcher/actions/workflows/headless-tests.yml)에서 확인하세요. CI 구성 자체가 실행 성공을 의미하지는 않습니다.
- 개발 클라우드에서 공개 CHZZK API 조회는 DNS 이름 해석 실패로 완료하지 못했습니다. 실제 CHZZK/YouTube 미디어 다운로드, 플랫폼별 설치 파일 및 배포 검증은 아직 완료하지 않았습니다.
