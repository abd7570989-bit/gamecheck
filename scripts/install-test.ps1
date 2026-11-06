# Installs the NSIS installer silently for the current user (no admin), smoke-tests
# the installed copy, then uninstalls it and checks that the files are gone.
# Problems are reported as GitHub annotations so they are visible on the run page.
param([Parameter(Mandatory = $true)][string]$InstallerGlob)
$ErrorActionPreference = "Stop"

function Fail($msg) { Write-Host "::error title=Install test::$msg"; exit 1 }
function Note($msg) { Write-Host "::notice title=Install test::$msg"; Write-Host $msg }

trap {
  Write-Host "::error title=Install test exception::$($_.Exception.Message) (line $($_.InvocationInfo.ScriptLineNumber))"
  exit 1
}

$installer = Get-ChildItem $InstallerGlob | Select-Object -First 1
if (-not $installer) { Fail "No installer matches $InstallerGlob" }
Note "Installer: $($installer.Name), $([math]::Round($installer.Length / 1MB, 1)) MB"

$p = Start-Process -FilePath $installer.FullName -ArgumentList "/S" -PassThru
if (-not $p.WaitForExit(300000)) { Fail "Installer did not finish within 5 minutes" }
Note "Installer exit code: $($p.ExitCode)"
if ($p.ExitCode -ne 0) { Fail "Installer exit code $($p.ExitCode)" }

# Where did it install? Ask the uninstall entry the installer wrote for the current user.
$key = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\GameCheck"
if (-not (Test-Path $key)) { Fail "No per-user uninstall entry at $key (was it installed per-machine?)" }
$entry = Get-ItemProperty $key
$dir = $entry.InstallLocation.Trim('"')
$exeName = if ($entry.MainBinaryName) { $entry.MainBinaryName } else { "gamecheck.exe" }
$exe = Join-Path $dir $exeName
Note "Installed to $dir ($exeName). Display name: $($entry.DisplayName) $($entry.DisplayVersion)"
if (-not (Test-Path $exe)) { Fail "Installed executable not found: $exe. Files: $((Get-ChildItem $dir -Name) -join ', ')" }

# The installer must not leave the app running: a running copy would swallow the
# smoke-test launch through the single-instance plugin.
$running = Get-Process | Where-Object { $_.Path -eq $exe }
if ($running) { Note "Stopping $($running.Count) copy(ies) started by the installer"; $running | Stop-Process -Force; Start-Sleep 2 }

& "$PSScriptRoot/smoke-test.ps1" -Exe $exe
if ($LASTEXITCODE -ne 0) { Fail "Smoke test of the installed copy failed" }

$uninstaller = Join-Path $dir "uninstall.exe"
if (-not (Test-Path $uninstaller)) { Fail "uninstall.exe not found in $dir" }
Start-Process -FilePath $uninstaller -ArgumentList "/S" -Wait
# NSIS uninstallers re-launch themselves from %TEMP%, so wait for the files to go.
$deadline = (Get-Date).AddSeconds(60)
while ((Test-Path $exe) -and (Get-Date) -lt $deadline) { Start-Sleep 2 }
if (Test-Path $exe) { Fail "Uninstall left $exe behind" }
if (Test-Path $key) { Fail "Uninstall left the registry entry $key behind" }
Note "Install, smoke test and uninstall without admin: passed"
