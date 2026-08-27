$ErrorActionPreference = "Stop"
$project = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $project

& ".\.venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean ".\zhumi_memo.spec"
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed." }

$compiler = Join-Path $project "build_tools\InnoSetup7\ISCC.exe"
if (-not (Test-Path -LiteralPath $compiler)) {
    throw "Inno Setup compiler not found at $compiler"
}
& $compiler ".\installer\zhumi_memo.iss"
if ($LASTEXITCODE -ne 0) { throw "Installer build failed." }

Write-Host "Installer created in release\"
