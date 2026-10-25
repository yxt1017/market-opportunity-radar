@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
    set "PYEXE=py"
) else (
    set "PYEXE=python"
)
if not exist ".venv\Scripts\python.exe" (
    %PYEXE% -m venv .venv
    if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
exit /b 0
:failed
echo.
echo 安装或启动失败。请确认已安装 Python 3.10+ 并可以访问 pip 软件源。
pause
exit /b 1
