# GitHub 업로드 가이드

## 1. Git 저장소 초기화

```bash
cd /Users/hvs/.gemini/antigravity/scratch/chzzk-downloader-gui
git init
git add .
git commit -m "Initial commit: Chzzk Downloader GUI v1.0.0"
```

## 2. GitHub 저장소 생성

1. [GitHub](https://github.com)에 로그인
2. 우측 상단 `+` 버튼 → `New repository` 클릭
3. Repository 정보 입력:
   - **Repository name**: `chzzk-downloader-gui`
   - **Description**: `네이버 치지직 VOD/클립 다운로더 - PyQt6 데스크톱 애플리케이션`
   - **Public** 또는 **Private** 선택
   - **Initialize this repository with** 옵션은 모두 체크 해제
4. `Create repository` 클릭

## 3. 로컬 저장소와 GitHub 연결

```bash
# GitHub 저장소 URL로 변경 (YOUR_USERNAME을 실제 사용자명으로 변경)
git remote add origin https://github.com/YOUR_USERNAME/chzzk-downloader-gui.git
git branch -M main
git push -u origin main
```

## 4. 첫 릴리즈 생성

### 방법 1: GitHub Actions 자동 빌드 (권장)

```bash
# 태그 생성 및 푸시
git tag v1.0.0
git push origin v1.0.0
```

GitHub Actions가 자동으로:
- Windows 실행 파일 빌드
- macOS 앱 빌드 및 DMG 생성
- Release 페이지에 자동 업로드

### 방법 2: 수동 빌드 및 업로드

#### macOS에서 빌드

```bash
./build_macos.sh
```

#### Windows에서 빌드

```cmd
build_windows.bat
```

#### GitHub Release 생성

1. GitHub 저장소 페이지에서 `Releases` 클릭
2. `Create a new release` 클릭
3. 태그 입력: `v1.0.0`
4. Release 제목: `Chzzk Downloader v1.0.0`
5. 설명 작성:

```markdown
## 🎉 첫 번째 릴리즈!

### 주요 기능
- 치지직 VOD/클립 다운로드
- 고화질 지원 (최대 1080p)
- 실시간 진행률 표시
- 썸네일 미리보기
- 연령 제한 콘텐츠 지원

### 다운로드
- **Windows**: ChzzkDownloader-Windows.zip
- **macOS**: ChzzkDownloader-macOS.dmg

### 설치 방법
자세한 내용은 [README](https://github.com/YOUR_USERNAME/chzzk-downloader-gui#readme) 참조
```

6. 빌드된 파일 드래그 앤 드롭:
   - `ChzzkDownloader-Windows.zip`
   - `ChzzkDownloader-macOS.dmg`
7. `Publish release` 클릭

## 5. README 업데이트

README.md의 다음 부분을 실제 GitHub 사용자명으로 변경:

```markdown
[Releases](https://github.com/YOUR_USERNAME/chzzk-downloader-gui/releases)
```

→

```markdown
[Releases](https://github.com/실제사용자명/chzzk-downloader-gui/releases)
```

## 6. 완료!

이제 사용자들이:
1. GitHub Releases 페이지에서 실행 파일 다운로드
2. Python 없이 바로 사용 가능
3. Windows/macOS 모두 지원

## 추가 팁

### 자동 빌드 확인

- GitHub 저장소 → `Actions` 탭에서 빌드 진행 상황 확인
- 빌드 실패 시 로그 확인 가능

### 업데이트 배포

```bash
# 코드 수정 후
git add .
git commit -m "Update: 기능 개선"
git push

# 새 버전 릴리즈
git tag v1.0.1
git push origin v1.0.1
```

### 이슈 및 기여

- Issues 탭에서 버그 리포트 및 기능 제안 받기
- Pull Request로 기여 받기
