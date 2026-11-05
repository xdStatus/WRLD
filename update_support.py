"""GitHub Release based updates for the portable Windows WRLD.exe.

Requires a public GitHub repository with latest release assets WRLD.exe and
WRLD.exe.sha256.  This app never downloads music or uploads the library.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import ssl
import subprocess
import sys
import threading
from pathlib import Path
from urllib.request import Request, build_opener, HTTPSHandler

from app_version import APP_VERSION
from player import CONFIG_DIR

REPO_FILE = CONFIG_DIR / 'update-channel.json'
REPO_RE = re.compile(r'^[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}$')
VERSION_RE = re.compile(r'^v?(\d+)\.(\d+)\.(\d+)$')
MAX_EXE = 350 * 1024 * 1024
_user_agent = {'User-Agent': f'WRLD/{APP_VERSION}', 'Accept': 'application/vnd.github+json'}
_lock = threading.RLock()

def _build_https_opener():
    # Use Windows' native certificate store, preserving full TLS verification.
    # This also supports trusted enterprise/campus intermediate certificates.
    if os.name == 'nt':
        import truststore
        return build_opener(HTTPSHandler(context=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)))
    return build_opener()

_https_opener = _build_https_opener()

def _open_https(request, timeout):
    try:
        return _https_opener.open(request, timeout=timeout)
    except ssl.SSLCertVerificationError as exc:
        raise ValueError(
            'Unable to verify GitHub HTTPS using trusted certificates. '
            'Check Windows date/time and trusted network certificates. '
            'Certificate verification was not disabled.'
        ) from exc



def current_repo():
    try:
        value = json.loads(REPO_FILE.read_text(encoding='utf-8')).get('repository', '')
    except (OSError, ValueError, TypeError):
        value = ''
    return value if isinstance(value, str) and REPO_RE.fullmatch(value) else ''


def configure_repo(value):
    if not isinstance(value, str) or (value and not REPO_RE.fullmatch(value)):
        raise ValueError('Enter a public GitHub repository as owner/repository.')
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    temp = REPO_FILE.with_suffix('.tmp')
    temp.write_text(json.dumps({'repository': value}, indent=2), encoding='utf-8')
    os.replace(temp, REPO_FILE)
    return {'repository': value, 'version': APP_VERSION}


def _json(url):
    with _open_https(Request(url, headers=_user_agent), timeout=12) as response:
        if response.status != 200: raise ValueError('Could not read release information.')
        return json.load(response)


def _version(tag):
    match = VERSION_RE.fullmatch(tag or '')
    if not match: raise ValueError('Release tag must be vMAJOR.MINOR.PATCH (example: v1.8.1).')
    return tuple(map(int, match.groups()))


def check_update():
    repo = current_repo()
    if not repo:
        return {'configured': False, 'repository': '', 'version': APP_VERSION, 'available': False,
                'message': 'Set a public GitHub release repository to enable updates.'}
    info = _json(f'https://api.github.com/repos/{repo}/releases/latest')
    latest = str(info.get('tag_name', ''))
    version = _version(latest)
    available = version > _version(APP_VERSION)
    assets = {a.get('name'): a for a in info.get('assets', []) if isinstance(a, dict)}
    if available and ('WRLD.exe' not in assets or 'WRLD.exe.sha256' not in assets):
        raise ValueError('Latest release is missing WRLD.exe or WRLD.exe.sha256.')
    return {'configured': True, 'repository': repo, 'version': APP_VERSION,
            'latest': '.'.join(map(str, version)), 'tag': latest,
            'available': available,
            'message': 'Update available.' if available else 'WRLD is up to date.'}


def _release_asset_url(repo, tag, filename):
    # GitHub tag and filename are validated; no arbitrary download locations.
    if not VERSION_RE.fullmatch(tag): raise ValueError('Invalid release version.')
    return f'https://github.com/{repo}/releases/download/{tag}/{filename}'


def _sha_file(contents):
    text = contents.decode('utf-8').strip()
    match = re.match(r'^([a-fA-F0-9]{64})(?:\s+\*?WRLD\.exe)?\s*$', text)
    if not match: raise ValueError('Release checksum has an invalid format.')
    return match.group(1).lower()


def _download_verified(url, expected, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = destination.with_suffix('.download')
    try:
        digest = hashlib.sha256()
        total = 0
        with _open_https(Request(url, headers=_user_agent), timeout=40) as response, temp.open('wb') as handle:
            while True:
                chunk = response.read(1024 * 512)
                if not chunk: break
                total += len(chunk)
                if total > MAX_EXE: raise ValueError('Update exceeds size limit.')
                digest.update(chunk)
                handle.write(chunk)
        if digest.hexdigest() != expected: raise ValueError('SHA-256 verification failed. Update was not installed.')
        with temp.open('rb') as handle:
            if handle.read(2) != b'MZ': raise ValueError('Downloaded update is not a Windows executable.')
        os.replace(temp, destination)
    finally:
        try: temp.unlink(missing_ok=True)
        except OSError: pass


def _probe_executable(exe: Path):
    """Never shut down the working player for a release whose Python cannot launch."""
    try:
        test = subprocess.run(
            [str(exe), '--startup-probe'], timeout=30, check=False,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError(
            'The downloaded WRLD.exe could not start on this PC. '
            'Your installed version was kept. Check Windows Security Protection history '
            'for blocked or quarantined files.'
        ) from exc
    if test.returncode != 0:
        raise ValueError(
            'The downloaded WRLD.exe failed its Windows startup check '
            f'(exit code {test.returncode}). Your installed version was kept.'
        )


# This helper runs OUTSIDE WRLD.exe, waits for it to close, and replaces the portable EXE.
# It keeps a one-version backup and restores it on failure.
PS_HELPER = r"""
param(
 [Parameter(Mandatory=$true)][int]$WaitProcessId,
 [Parameter(Mandatory=$true)][string]$TargetExe,
 [Parameter(Mandatory=$true)][string]$NewExe,
 [Parameter(Mandatory=$true)][string]$ExpectedSha256
)
$ErrorActionPreference = 'Stop'
function Test-WRLDExe([string]$Executable) {
  $process = $null
  try {
    $start = [System.Diagnostics.ProcessStartInfo]::new()
    $start.FileName = $Executable
    $start.Arguments = '--startup-probe'
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $process = [System.Diagnostics.Process]::Start($start)
    if (-not $process) { return $false }
    if (-not $process.WaitForExit(30000)) {
      $process.Kill()
      return $false
    }
    return ($process.ExitCode -eq 0)
  } catch {
    return $false
  } finally {
    if ($process) { $process.Dispose() }
  }
}
try {
 for ($i=0; $i -lt 160; $i++) {
   if (-not (Get-Process -Id $WaitProcessId -ErrorAction SilentlyContinue)) { break }
   Start-Sleep -Milliseconds 500
 }
 if (Get-Process -Id $WaitProcessId -ErrorAction SilentlyContinue) {
    throw 'WRLD did not close before the update timeout.'
 }
 if ([IO.Path]::GetFileName($TargetExe) -ine 'WRLD.exe') { throw 'Unexpected target executable.' }
 $computed = (Get-FileHash -LiteralPath $NewExe -Algorithm SHA256).Hash
 if ($computed -ine $ExpectedSha256) { throw 'Downloaded file checksum changed.' }
 $backup = Join-Path ([IO.Path]::GetDirectoryName($TargetExe)) 'WRLD.previous.exe'
 if (Test-Path -LiteralPath $backup) { Remove-Item -LiteralPath $backup -Force }
 if (Test-Path -LiteralPath $TargetExe) { Move-Item -LiteralPath $TargetExe -Destination $backup -Force }
 try {
   Move-Item -LiteralPath $NewExe -Destination $TargetExe -Force
 } catch {
   if (Test-Path -LiteralPath $backup) { Move-Item -LiteralPath $backup -Destination $TargetExe -Force }
   throw
 }
 # Retry startup verification after replacement: one-file extraction may fail
 # transiently on Windows even if the downloaded executable passed its first probe.
 $probePassed = $false
 for ($attempt = 0; $attempt -lt 3; $attempt++) {
   if (Test-WRLDExe $TargetExe) { $probePassed = $true; break }
   Start-Sleep -Seconds 2
 }
 if (-not $probePassed) {
   # Restore the previous version instead of leaving a failed update installed.
   $failed = Join-Path ([IO.Path]::GetDirectoryName($TargetExe)) 'WRLD.failed.exe'
   if (Test-Path -LiteralPath $failed) { Remove-Item -LiteralPath $failed -Force }
   Move-Item -LiteralPath $TargetExe -Destination $failed -Force
   if (Test-Path -LiteralPath $backup) {
     Move-Item -LiteralPath $backup -Destination $TargetExe -Force
     Start-Process -FilePath $TargetExe -WorkingDirectory ([IO.Path]::GetDirectoryName($TargetExe))
   }
   throw 'The updated WRLD.exe failed its launch test. The previous version was restored and reopened.'
 }
 # Give the probe's temporary one-file extraction time to close before launch.
 Start-Sleep -Seconds 2
 $launched = Start-Process -FilePath $TargetExe -WorkingDirectory ([IO.Path]::GetDirectoryName($TargetExe)) -PassThru
 if (-not $launched) { throw 'WRLD did not start after the update was installed.' }
} catch {
  $log = Join-Path $env:APPDATA 'WRLDPlayer\update-error.txt'
  $_ | Out-String | Set-Content -LiteralPath $log -Encoding UTF8
  Add-Type -AssemblyName System.Windows.Forms
  [System.Windows.Forms.MessageBox]::Show("WRLD update failed. Your old app may still be available as WRLD.previous.exe. Details: $log", 'WRLD update') | Out-Null
}
"""


def download_and_stage_update():
    # The bundled app can replace ONLY itself, with the user's explicit approval.
    if not getattr(sys, 'frozen', False) or not sys.executable.lower().endswith('wrld.exe'):
        raise ValueError('Install updates from the compiled WRLD.exe, not the source build.')
    with _lock:
        status = check_update()
        if not status.get('available'): raise ValueError('No newer release is available.')
        repo = status['repository']; tag = status['tag']
        url = _release_asset_url(repo, tag, 'WRLD.exe')
        checksum_url = _release_asset_url(repo, tag, 'WRLD.exe.sha256')
        with _open_https(Request(checksum_url, headers=_user_agent), timeout=20) as response:
            contents = response.read(512)
        expected = _sha_file(contents)
        root = Path(os.environ.get('LOCALAPPDATA', str(CONFIG_DIR))) / 'WRLDPlayer' / 'updates' / status['latest']
        exe = root / 'WRLD.exe'
        _download_verified(url, expected, exe)
        # Verify that the bundled Python runtime and WebView imports work.
        # This protects against missing python313.dll and security-software blocking.
        _probe_executable(exe)
        helper = root / 'apply-update.ps1'
        helper.write_text(PS_HELPER, encoding='utf-8-sig')
        target = Path(sys.executable).resolve()
        if target.name.lower() != 'wrld.exe': raise ValueError('Unexpected installed file name.')
        # Confirm folder is writable before closing the existing player.
        test = target.parent / '.wrld-update-write-test'
        try:
            test.write_bytes(b'WRLD')
        except OSError as exc:
            raise ValueError('WRLD.exe is in a protected folder. Move it to your Documents or Apps folder and try again.') from exc
        finally:
            test.unlink(missing_ok=True)
        params = ['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass',
                  '-File',str(helper),'-WaitProcessId',str(os.getpid()),
                  '-TargetExe',str(target),'-NewExe',str(exe),'-ExpectedSha256',expected]
        subprocess.Popen(params, cwd=str(root), creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        return {'ready': True, 'version': status['latest'], 'message': 'Update verified. WRLD will close and restart.'}
