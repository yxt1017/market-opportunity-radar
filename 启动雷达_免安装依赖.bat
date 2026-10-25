@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 server.py
) else (
    python server.py
)
if errorlevel 1 (
    echo.
    echo 运行失败。请先安装 Python 3.10+，并勾选 Add Python to PATH。
    pause
)
