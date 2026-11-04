@echo off
setlocal
cd /d "%~dp0"
echo WRLD Cloud - private Windows music server
echo.
echo Keep your PC on and connected to Tailscale.
echo Run once in an Administrator terminal:
echo    tailscale serve --bg 18766
echo.
echo This exposes the library ONLY within your private Tailscale network.
echo Do not use public port forwarding or Tailscale Funnel.
echo.
if exist "WRLD.exe" (
  "WRLD.exe" --cloud-server
) else (
  py -3 native.py --cloud-server
)
pause
