@echo off
echo Normalizing level10.mp3 with ffmpeg...
echo.

REM Check if ffmpeg is available
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo Error: ffmpeg not found!
    echo Please install ffmpeg first.
    pause
    exit /b 1
)

REM Create backup
if not exist "sound\level10_backup.mp3" (
    copy "sound\level10.mp3" "sound\level10_backup.mp3"
    echo Backup created: sound\level10_backup.mp3
)

REM Normalize the audio
echo Normalizing audio...
ffmpeg -i "sound\level10.mp3" -af "loudnorm=I=-20:LRA=7:TP=-1" -y "sound\level10.mp3"

if errorlevel 1 (
    echo Normalization failed!
    echo Restoring backup...
    copy "sound\level10_backup.mp3" "sound\level10.mp3"
) else (
    echo Normalization completed successfully!
)

echo.
pause
