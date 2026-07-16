# 🎛️ Shater-Youtube-downloader
# 🎛️ A Studio Video Downloader ,Customization & Processing Suite
A local web-interface tool to download videos, stitch adaptive high-res channels, stamp custom text watermarks, mix background audio loops, and burn styled captions.


### 📋 Prerequisites (Mandatory)
This application uses **FFmpeg** for all underlying audio and video processing operations. It must be present on your computer system:
* **Windows**: Download the essentials compilation package and add its `/bin` directory folder to your system environment variables `Path`.
* **macOS**: Install via Homebrew: `brew install ffmpeg`
* **Linux**: Install via apt: `sudo apt install ffmpeg`

### 🚀 Quick Start Instructions

1. **Download the Repository**: Clone or download this project zip folder to your local drive.
2. **Ensure Assets Folders Exist**: Make sure two folders named `music` and `fonts` exist inside the project directory. Drop your custom `.mp3` or `.ttf` files inside them.
3. **Launch the Web Application**:
   * 🪟 **Windows**: Simply double-click the `run.bat` script file.
   * 🍏 **macOS** & 🐧 **Linux**: Open your terminal inside the project directory and execute:
     ```bash
     chmod +x run.sh
     ./run.sh
     ```

The script will automatically set up an isolated sandbox environment using the fast `uv` package manager, fetch the optimized Python 3.12 configuration layer, install your required packages, and open a private local browser dashboard instantly!

open your browser:
http://localhost:7861/

Enjoy , youtube downloader , downladed files should be on the "downlads" folder inside the project

Notes:
Music provided is a samples AI music , fonts is some sample opensourced fonts 
if you like to add more fonts , more music backgrounds just add them to the folders 

## ⚠️ Educational Purpose & Disclaimer

This project is created strictly for **educational and personal archival purposes**. It is designed as a localized experimentation utility to study video filter graphs, automated multimedia stitching via FFmpeg pipelines, and localized UI design implementations using Python and Gradio.

* **No Liability**: The author provides this software "as is" under the MIT License and assumes absolutely no responsibility or liability for how end-users interact with this code, any data loss, or system instability it might cause.
* **Terms of Service Compliance**: Downloading copyrighted media without the explicit permission of the owner or outside the parameters provided natively by streaming platforms is a direct violation of YouTube's Terms of Service. 
* **User Accountability**: The end-user is solely responsible for verifying the legal status, copyrights, and distribution permissions of any streaming URLs processed through this personal tool. Do not use this software for unauthorized media distribution or public commercial applications.
