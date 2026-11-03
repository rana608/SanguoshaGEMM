$ErrorActionPreference = 'Stop'
$workspace = Split-Path $PSScriptRoot -Parent
$aliasPath = Join-Path $env:USERPROFILE 'sgemm-work'
if (-not (Test-Path -LiteralPath $aliasPath)) { New-Item -ItemType Junction -Path $aliasPath -Target $workspace | Out-Null }
if ((Get-Item -LiteralPath $aliasPath).Target -ne $workspace) { throw 'sgemm-work points to another workspace' }
$qt = Join-Path $aliasPath '.tools/qt/5.5/mingw492_32'
$compiler = Join-Path $aliasPath '.tools/qt/Tools/mingw492_32/bin'
$env:PATH = "$qt/bin;$compiler;$env:PATH"
$build = Join-Path $aliasPath 'build/launcher'
New-Item -ItemType Directory -Force -Path $build | Out-Null
Push-Location $build
try {
    & "$qt/bin/qmake.exe" ../../launcher/launcher.pro
    if ($LASTEXITCODE -ne 0) { throw 'Launcher qmake failed' }
    & "$compiler/mingw32-make.exe" -j4
    if ($LASTEXITCODE -ne 0) { throw 'Launcher build failed' }
} finally { Pop-Location }
