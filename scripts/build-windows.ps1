param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$Root = Split-Path $PSScriptRoot -Parent
Push-Location $Root
try {
    & $Python -c "import sys,struct; assert sys.platform == 'win32' and struct.calcsize('P') == 8, 'Requires 64-bit Python on Windows'"
    if ($LASTEXITCODE -ne 0) { throw 'Windows x64 Python required' }
    $env:PYTHONPATH = Join-Path $Root 'windows'
    & $Python -m unittest discover -s windows/tests -v
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
    & $Python windows/main.py --smoke-test
    if ($LASTEXITCODE -ne 0) { throw 'UI smoke test failed' }
    & $Python -m PyInstaller --noconfirm --clean --windowed --onedir --name LoLPing `
        --manifest windows/LoLPing.manifest --paths windows `
        --add-data 'Resources;Resources' windows/main.py
    if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
    $Process = Start-Process -FilePath (Join-Path $Root 'dist/LoLPing/LoLPing.exe') -ArgumentList '--smoke-test' -Wait -PassThru
    if ($Process.ExitCode -ne 0) { throw 'Packaged app smoke test failed' }
    Copy-Item windows/README.md dist/LoLPing/README-Windows.md
    Compress-Archive -Path dist/LoLPing -DestinationPath dist/LoLPing-Windows-x64.zip -Force
    Write-Host 'Built dist/LoLPing-Windows-x64.zip. Extract the entire folder before running LoLPing.exe.'
} finally {
    Pop-Location
}
