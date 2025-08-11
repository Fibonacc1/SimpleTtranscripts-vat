@echo off
REM Change to directory of this script
cd /d %~dp0

REM Launch the audio processor GUI
python scripts\run_whisper.py

pause
