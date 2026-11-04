@echo off
setlocal
cd /d "%~dp0"
if exist "dist\WRLD.exe" (
  start "" "dist\WRLD.exe"
  exit /b 0
)
echo WRLD.exe is not built yet.
echo First double-click BUILD_WRLD_EXE.cmd and complete the build.
pause
