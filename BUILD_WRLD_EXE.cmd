@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title WRLD - Build Desktop EXE

echo ============================================================
echo                WRLD - BUILD WINDOWS EXE
echo ============================================================
echo.
echo This prepares WRLD v1.8.1 on your Windows PC.
echo It downloads build tools. The finished WRLD.exe runs without Python.
echo.
echo Build directory: %CD%
echo.

if not exist "native.py" (
  echo ERROR: native.py is missing. Fully extract the ZIP first.
  goto failed
)
if not exist "web\index.html" (
  echo ERROR: web\index.html is missing. Fully extract the ZIP first.
  goto failed
)

if not exist ".wrld-build-venv\Scripts\python.exe" (
  echo [1/4] Creating isolated Python build environment...
  where py >nul 2>nul
  if not errorlevel 1 (
    py -3 -m venv ".wrld-build-venv"
  ) else (
    python -m venv ".wrld-build-venv"
  )
  if errorlevel 1 (
    echo.
    echo ERROR: Could not create the build environment.
    echo Make sure Python is installed and accessible in Command Prompt.
    goto failed
  )
) else (
  echo [1/4] Reusing Python build environment...
)

set "PY=.wrld-build-venv\Scripts\python.exe"
echo.
echo [2/4] Installing/updating WebView2 wrapper and EXE packager...
"%PY%" -m pip install --disable-pip-version-check --upgrade pip
if errorlevel 1 goto failed
"%PY%" -m pip install --disable-pip-version-check --upgrade "pyinstaller>=6.21" "pywebview>=6.1,<7"
if errorlevel 1 goto failed

echo.
echo [3/4] Building WRLD.exe with custom 999 icon...
"%PY%" -m PyInstaller --noconfirm --clean --onefile --windowed --name WRLD --icon "web\favicon.ico" --add-data "web;web" --collect-all webview --hidden-import clr --hidden-import webview.platforms.edgechromium "native.py"
if errorlevel 1 goto failed

if not exist "dist\WRLD.exe" (
  echo ERROR: The build did not produce dist\WRLD.exe.
  goto failed
)

echo.
echo [4/4] Build complete!
echo.
echo YOUR WINDOWS APP:
echo    %CD%\dist\WRLD.exe
echo.
echo After this build, you can run WRLD.exe without installing Python.
echo It uses the Microsoft Edge WebView2 runtime built into most
echo Windows installations.
echo.
echo Double-click dist\WRLD.exe to launch WRLD.
echo Your music and playlists remain in their current locations.
echo.
explorer "dist"
pause
exit /b 0

:failed
echo.
echo BUILD FAILED. No music files have been modified.
echo If the error was about missing packages, check your internet connection.
echo You can send the error text or screenshot for troubleshooting.
echo.
pause
exit /b 1
