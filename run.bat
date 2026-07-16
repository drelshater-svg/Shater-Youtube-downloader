@echo off
echo ===================================================
echo   Starting Studio Video Customization Suite
echo ===================================================

:: Check if uv is installed, if not, install it via standalone installer
where uv >nul 2>nul
if %errorlevel% neq 0 (
    echo [INFO] uv manager not found. Installing uv...
    powershell -ExecutionPolicy Bypass -Command "irm https://astral.sh | iex"
    set "PATH=%USERPROFILE%\.local\bin;%PATH%"
)

echo [INFO] Synchronizing dependencies and running project...
:: uv run will automatically grab Python 3.11 and launch app.py securely
uv run --python 3.12 yotube_downloader.py

pause

