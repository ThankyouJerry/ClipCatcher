# 🎥 Chzzk Downloader

<div align="center">

**네이버 치지직(Chzzk) VOD/클립 + YouTube를 다운로드할 수 있는 데스크톱 애플리케이션**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.6+-green.svg)](https://www.riverbankcomputing.com/software/pyqt/)

[다운로드](#-다운로드-및-설치) • [기능](#-주요-기능) • [사용법](#-사용-방법) • [필수-도구-설치](#-필수-도구-설치-yt-dlp--ffmpeg) • [개발](#-개발자-가이드)

</div>

---

## ✨ 주요 기능

- 🎨 **모던 GUI** - PyQt6 기반의 다크 테마 인터페이스
- 🎥 **치지직(Chzzk) 지원** - VOD, 클립, 빠른다시보기 다운로드
- 📺 **YouTube 지원** - YouTube 영상 다운로드 (URL만 바꾸면 동일하게 사용)
- 🎞️ **고화질 선택** - 1080p / 720p / 480p / 360p 등 원하는 화질 선택
- ⏱️ **시간 범위 지정** - 영상의 특정 구간만 잘라서 다운로드
- 🚀 **고속 다운로드** - yt-dlp 기반 멀티스레드 다운로드
- 📦 **완벽한 재생** - ffmpeg으로 MP4 변환 (VLC, IINA, QuickTime 등 모든 플레이어 지원)
- 🍪 **연령 제한 컨텐츠** - 쿠키를 통한 성인 인증 영상 지원
- 📊 **실시간 진행률** - 다운로드 속도, 진행률, 남은 시간 표시
- 🖥️ **크로스 플랫폼** - macOS, Windows 지원

---

## 🔧 필수 도구 설치 (yt-dlp & ffmpeg)

> **이 프로그램은 `yt-dlp`와 `ffmpeg`가 시스템에 설치되어 있어야 합니다.**  
> 아래 공식 방법으로 설치해주세요.

---

### macOS

#### yt-dlp 설치
```bash
# Homebrew (권장)
brew install yt-dlp

# 또는 pip
pip3 install yt-dlp
```
공식 사이트: https://github.com/yt-dlp/yt-dlp

#### ffmpeg 설치
```bash
# Homebrew (권장)
brew install ffmpeg
```
공식 사이트: https://ffmpeg.org/download.html

---

### Windows

#### yt-dlp 설치

**방법 1 - winget (권장, Windows 10/11)**
```powershell
winget install yt-dlp
```

**방법 2 - 직접 다운로드**
1. https://github.com/yt-dlp/yt-dlp/releases/latest 접속
2. `yt-dlp.exe` 다운로드
3. `C:\Windows\System32\` 폴더에 복사 (또는 PATH에 추가된 폴더)

#### ffmpeg 설치

**방법 1 - winget (권장)**
```powershell
winget install Gyan.FFmpeg
```

**방법 2 - 공식 빌드 직접 다운로드**
1. https://www.gyan.dev/ffmpeg/builds/ 접속 (`ffmpeg-release-essentials.zip`)  
   또는 https://github.com/BtbN/FFmpeg-Builds/releases
2. ZIP 압축 해제
3. `bin` 폴더 안의 `ffmpeg.exe`, `ffprobe.exe`를 PATH에 추가된 폴더에 복사  
   (예: `C:\Windows\System32\` 또는 `C:\ffmpeg\bin\` 후 환경변수 PATH 추가)

#### 설치 확인
```powershell
yt-dlp --version
ffmpeg -version
```

---

## 📥 다운로드 및 설치

### 방법 1: Python으로 실행 (권장)

#### 1단계: 저장소 복제

```bash
git clone https://github.com/ThankyouJerry/chzzkdownloader-gui.git
cd chzzkdownloader-gui
```

또는 GitHub에서 ZIP 다운로드:
1. https://github.com/ThankyouJerry/chzzkdownloader-gui 접속
2. 녹색 **Code** 버튼 → **Download ZIP**
3. 압축 해제

#### 2단계: 의존성 설치

```bash
pip3 install -r requirements.txt
# Windows:
pip install -r requirements.txt
```

#### 3단계: 실행

```bash
python3 src/main.py
# Windows:
python src/main.py
```

---

### 방법 2: 실행 파일 사용

Python 없이 바로 실행하려면:

1. [Releases](https://github.com/ThankyouJerry/chzzkdownloader-gui/releases) 페이지에서 최신 버전 다운로드
   - **macOS**: `ChzzkDownloader-macOS.zip`
   - **Windows**: `ChzzkDownloader-Windows.zip`
2. 압축 해제 후 실행

> ⚠️ 실행 파일을 사용하더라도 **yt-dlp와 ffmpeg는 별도로 설치**해야 합니다. ([위 안내 참고](#-필수-도구-설치-yt-dlp--ffmpeg))

**macOS 보안 경고 해결:**
```bash
xattr -cr ChzzkDownloader.app
open ChzzkDownloader.app
```

---

## 🎯 사용 방법

### 기본 다운로드

1. **URL 입력**: 치지직 또는 YouTube URL을 입력창에 붙여넣기
   - 치지직 VOD: `https://chzzk.naver.com/video/12345`
   - 치지직 클립: `https://chzzk.naver.com/clips/abcde`
   - YouTube: `https://www.youtube.com/watch?v=VIDEO_ID`
   - YouTube Shorts: `https://www.youtube.com/shorts/VIDEO_ID`

2. **정보 가져오기**: "정보 가져오기" 버튼 클릭
   - 영상 제목, 채널, 날짜, 썸네일 표시
   - 사용 가능한 화질 목록 자동 표시

3. **화질 선택**: 드롭다운에서 원하는 해상도 선택

4. **시간 범위 선택** (선택 사항):
   - **전체 다운로드**: 기본값, 영상 전체 다운로드
   - **부분 다운로드**: 시작/종료 시간 입력 (`HH:MM:SS` 또는 초 단위)

5. **다운로드**: "다운로드" 버튼 클릭

6. **저장 위치**: `~/Downloads/chzzkdownloader/` 폴더에 저장됨

---

### 연령 제한 컨텐츠 다운로드 (치지직)

1. 브라우저에서 [네이버](https://www.naver.com) 로그인
2. `F12` → **Application** 탭 → **Cookies** → `naver.com`
3. `NID_AUT`, `NID_SES` 값 복사
4. 앱 메뉴 → **파일** → **설정** → 쿠키 입력

---

## 🛠️ 개발자 가이드

### 프로젝트 구조

```
chzzkdownloader-gui/
├── src/
│   ├── main.py                  # 진입점
│   ├── ui/
│   │   ├── main_window.py       # 메인 윈도우
│   │   ├── download_item.py     # 다운로드 항목 위젯
│   │   ├── time_range_widget.py # 시간 범위 선택 위젯
│   │   ├── settings_dialog.py   # 설정 다이얼로그
│   │   └── styles.py            # 스타일시트
│   └── core/
│       ├── chzzk_api.py         # Chzzk API 클라이언트
│       ├── youtube_api.py       # YouTube 메타데이터 (yt-dlp 바이너리)
│       ├── downloader.py        # 다운로드 매니저
│       ├── segment_downloader.py # HLS 세그먼트 다운로더
│       └── config.py            # 설정 관리
├── build.spec                   # PyInstaller 설정
├── build_macos.sh               # macOS 빌드 스크립트
├── build_windows.bat            # Windows 빌드 스크립트
└── requirements.txt
```

### 빌드

#### macOS
```bash
brew install yt-dlp ffmpeg   # 의존성 설치
pip3 install -r requirements.txt
python3 -m PyInstaller build.spec --clean
# 결과: dist/ChzzkDownloader.app
```

#### Windows
```powershell
winget install yt-dlp Gyan.FFmpeg
pip install -r requirements.txt
python -m PyInstaller build.spec --clean
# 결과: dist\ChzzkDownloader.exe
```

---

## 🐛 문제 해결

### `yt-dlp` 또는 `ffmpeg`를 찾을 수 없음
- 위의 [필수 도구 설치](#-필수-도구-설치-yt-dlp--ffmpeg) 안내를 따라 설치하세요
- 설치 후 터미널/PowerShell을 **재시작**하세요

### 다운로드가 멈추거나 실패
- 인터넷 연결 확인
- 연령 제한 영상: 쿠키 설정 필요
- YouTube 오류: `yt-dlp --update`로 최신 버전 업데이트

### macOS에서 "확인되지 않은 개발자" 경고
```bash
xattr -cr ChzzkDownloader.app
```

### Windows에서 바이러스 오탐지
- PyInstaller 빌드 파일의 정상적인 오탐지입니다
- Windows Defender 예외 추가 또는 소스 코드로 직접 실행하세요

---

## 📝 라이선스

MIT License — 자세한 내용은 [LICENSE](LICENSE) 참조

---

## ⚠️ 면책 조항

이 프로그램은 개인적인 용도로만 사용하세요. 다운로드한 콘텐츠를 무단으로 배포하거나 상업적으로 사용하는 것은 저작권법 위반입니다.

---

<div align="center">

**Made with ❤️ for Chzzk & YouTube users**

⭐ 이 프로젝트가 유용하다면 Star를 눌러주세요!

</div>
