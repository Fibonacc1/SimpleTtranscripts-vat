@echo off
REM Change to directory of this script
cd /d %~dp0
REM Launch the audio processor GUI without a console window
start "" /B pythonw scripts\run_whisper.py
exit