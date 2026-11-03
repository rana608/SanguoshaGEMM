$ErrorActionPreference = 'Stop'
$workspace = Split-Path $PSScriptRoot -Parent
New-Item -ItemType Directory -Force -Path "$workspace/.tools" | Out-Null
# Dependencies remain under this workspace. Requires Python 3.11+ and 7-Zip.
python "$workspace/scripts/download_tools.py"
if ($LASTEXITCODE -ne 0) { throw 'Tool download/hash verification failed' }
if (-not (Test-Path "$workspace/.tools/qt/5.5/mingw492_32/bin/qmake.exe")) {
    python "$workspace/scripts/extract_qt.py"
    if ($LASTEXITCODE -ne 0) { throw 'Qt extraction failed' }
}
$swigLink = "$workspace/upstream/tools/swig"
$swigTarget = "$workspace/.tools/swigwin-3.0.12"
if (-not (Test-Path -LiteralPath $swigLink)) {
    New-Item -ItemType Junction -Path $swigLink -Target $swigTarget | Out-Null
}
if (-not (Test-Path "$swigLink/swig.exe")) { throw 'SWIG path is occupied by an unexpected directory' }
python "$workspace/scripts/fetch_licenses.py"
if ($LASTEXITCODE -ne 0) { throw 'License download failed' }
Write-Output 'Local toolchain is ready. Run scripts/build.ps1, then scripts/package.ps1.'
