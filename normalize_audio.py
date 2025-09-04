#!/usr/bin/env python3
"""
Temporary script to normalize level10.mp3 audio levels
This script provides multiple options for audio normalization
"""

import os
import shutil
import subprocess
import sys

def check_ffmpeg():
    """Check if ffmpeg is available"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False

def normalize_with_ffmpeg(input_file, output_file=None):
    """Normalize audio using ffmpeg"""
    if output_file is None:
        output_file = input_file
    
    print(f"Normalizing audio file: {input_file}")
    
    # Normalize the audio using loudnorm filter
    normalize_cmd = [
        'ffmpeg', '-i', input_file,
        '-af', 'loudnorm=I=-20:LRA=7:TP=-1',
        '-y',  # Overwrite output file
        output_file
    ]
    
    print("Running normalization with ffmpeg...")
    try:
        result = subprocess.run(normalize_cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print(f"Successfully normalized audio: {output_file}")
            return True
        else:
            print(f"FFmpeg error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("Normalization timed out!")
        return False

def install_ffmpeg_instructions():
    """Provide instructions for installing ffmpeg"""
    print("\n" + "="*60)
    print("FFMPEG INSTALLATION INSTRUCTIONS")
    print("="*60)
    print("\nTo normalize audio files, you need to install ffmpeg:")
    print("\n1. Download ffmpeg from: https://ffmpeg.org/download.html")
    print("2. Or use a package manager:")
    print("   - Windows (with Chocolatey): choco install ffmpeg")
    print("   - Windows (with Scoop): scoop install ffmpeg")
    print("   - Windows (with winget): winget install ffmpeg")
    print("   - macOS (with Homebrew): brew install ffmpeg")
    print("   - Linux (Ubuntu/Debian): sudo apt install ffmpeg")
    print("\n3. After installation, restart your terminal and run this script again.")
    print("\nAlternatively, you can manually normalize the audio using:")
    print("   - Audacity (free audio editor)")
    print("   - Online tools like CloudConvert")
    print("   - Any audio editing software")
    print("\nTarget settings for normalization:")
    print("   - Peak level: -1 dB")
    print("   - RMS level: -20 dB")
    print("   - Format: MP3, 192 kbps")

def create_manual_normalization_script():
    """Create a simple batch script for manual ffmpeg normalization"""
    batch_content = """@echo off
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
if not exist "sound\\level10_backup.mp3" (
    copy "sound\\level10.mp3" "sound\\level10_backup.mp3"
    echo Backup created: sound\\level10_backup.mp3
)

REM Normalize the audio
echo Normalizing audio...
ffmpeg -i "sound\\level10.mp3" -af "loudnorm=I=-20:LRA=7:TP=-1" -y "sound\\level10.mp3"

if errorlevel 1 (
    echo Normalization failed!
    echo Restoring backup...
    copy "sound\\level10_backup.mp3" "sound\\level10.mp3"
) else (
    echo Normalization completed successfully!
)

echo.
pause
"""
    
    with open("normalize_level10.bat", "w") as f:
        f.write(batch_content)
    
    print("Created normalize_level10.bat - you can run this if ffmpeg is installed")

def main():
    input_file = "sound/level10.mp3"
    
    if not os.path.exists(input_file):
        print(f"Error: File {input_file} not found!")
        return False
    
    print("Audio Normalization Script for level10.mp3")
    print("="*50)
    
    # Check if ffmpeg is available
    if check_ffmpeg():
        print("✓ ffmpeg found!")
        
        # Create backup
        backup_file = "sound/level10_backup.mp3"
        if not os.path.exists(backup_file):
            print(f"Creating backup: {backup_file}")
            shutil.copy2(input_file, backup_file)
        
        # Normalize the audio
        success = normalize_with_ffmpeg(input_file)
        
        if success:
            print("\n✓ Audio normalization completed successfully!")
            print(f"Original file backed up as: {backup_file}")
            print("The level10.mp3 file has been normalized to standard levels.")
        else:
            print("\n✗ Audio normalization failed!")
            print("Restoring from backup...")
            if os.path.exists(backup_file):
                shutil.copy2(backup_file, input_file)
                print("Original file restored from backup.")
        
        return success
    else:
        print("✗ ffmpeg not found!")
        install_ffmpeg_instructions()
        create_manual_normalization_script()
        
        print(f"\nCreated normalize_level10.bat for manual execution")
        print("You can also use any audio editor to normalize the file manually.")
        
        return False

if __name__ == "__main__":
    main()
