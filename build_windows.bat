@echo off
REM Build script for Windows

echo Building Chzzk Downloader for Windows...

REM Clean previous builds
echo Cleaning previous builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM Build with PyInstaller
echo Building application...
pyinstaller build.spec

if %ERRORLEVEL% EQU 0 (
    echo Build successful!
    echo Application location: dist\ChzzkDownloader.exe
    echo.
    echo To create installer, use Inno Setup or NSIS
) else (
    echo Build failed!
    exit /b 1
)
