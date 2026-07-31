#!/bin/bash
sudo apt update && sudo apt install -y ffmpeg curl git
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
git clone https://github.com/drelshater-svg/Shater-Youtube-downloader.git
cd Shater-Youtube-downloader
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt
uv run yotube_downloader.py
