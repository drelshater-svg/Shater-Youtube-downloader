#This script assumes you already have Git and FFmpeg installed on your Windows system path
@echo off
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh | iex"
set "PATH=%USERPROFILE%\.local\bin;%PATH%"
git clone https://github.com/drelshater-svg/Shater-Youtube-downloader.git
cd Shater-Youtube-downloader
uv venv
call .venv\Scripts\activate
uv pip install -r requirements.txt
uv run yotube_downloader.py
pause
