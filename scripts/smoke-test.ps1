# Starts a GameCheck executable in smoke-test mode and checks that its interface
# loaded in WebView2 and reached Rust over IPC. Exit code 0 = passed.
param(
  [Parameter(Mandatory = $true)][string]$Exe,
  [int]$TimeoutSeconds = 120
)
$ErrorActionPreference = "Stop"
if (-not (Test-Path $Exe)) { Write-Host "::error::Executable not found: $Exe"; exit 1 }

$out = Join-Path $env:RUNNER_TEMP ("smoke-" + [guid]::NewGuid() + ".json")
$env:GAMECHECK_SMOKE_TEST = "1"
$env:GAMECHECK_SMOKE_OUT = $out

Write-Host "Starting $Exe"
$proc = Start-Process -FilePath $Exe -PassThru
if (-not $proc.WaitForExit($TimeoutSeconds * 1000)) {
  $proc.Kill()
  Write-Host "::error::GameCheck did not exit within $TimeoutSeconds s"
  exit 1
}
Write-Host "Exit code: $($proc.ExitCode)"
if ($proc.ExitCode -ne 0) { Write-Host "::error::Smoke test failed with exit code $($proc.ExitCode)"; exit 1 }
if (-not (Test-Path $out)) { Write-Host "::error::Frontend report was not written"; exit 1 }

$report = Get-Content $out -Raw | ConvertFrom-Json
Write-Host ($report | ConvertTo-Json)
if ($report.navItems -ne 7) { Write-Host "::error::Expected 7 navigation items, got $($report.navItems)"; exit 1 }
if ($report.route -ne "/") { Write-Host "::error::Unexpected start route $($report.route)"; exit 1 }
Write-Host "Smoke test passed"
