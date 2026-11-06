# local-render: renders "Orbit" on this computer.
# Usage:  powershell -ExecutionPolicy Bypass -File run.ps1 [--check | --preview]
# All the work happens in runtime/lr_render.py (plain Python, standard library only).
$ErrorActionPreference = "Continue"
Set-Location -Path $PSScriptRoot
$candidates = @(@("py", "-3"), @("python"), @("python3"))
foreach ($c in $candidates) {
  $exe = $c[0]
  $pre = @($c | Select-Object -Skip 1)
  if (Get-Command $exe -ErrorAction SilentlyContinue) {
    & $exe @pre -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" *> $null
    if ($LASTEXITCODE -eq 0) {
      & $exe @pre -I runtime/lr_render.py @args
      exit $LASTEXITCODE
    }
  }
}
Write-Host "Python 3.8 or newer is needed to render this video."
Write-Host "  Install it with:  winget install --id Python.Python.3.12 -e"
Write-Host "  or download it from https://www.python.org/downloads/"
exit 1
