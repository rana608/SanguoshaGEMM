param([ValidateSet('all','baseline','optimized')][string]$Edition = 'all')
$ErrorActionPreference = 'Stop'
$workspace = Split-Path $PSScriptRoot -Parent
# A junction avoids legacy MinGW's non-ASCII path limitations; no global PATH change.
$aliasPath = Join-Path $env:USERPROFILE 'sgemm-work'
if (-not (Test-Path -LiteralPath $aliasPath)) {
    New-Item -ItemType Junction -Path $aliasPath -Target $workspace | Out-Null
}
if ((Get-Item -LiteralPath $aliasPath).Target -ne $workspace) {
    throw 'sgemm-work already points to another workspace.'
}
$qt = Join-Path $aliasPath '.tools/qt/5.5/mingw492_32'
$compiler = Join-Path $aliasPath '.tools/qt/Tools/mingw492_32/bin'
$env:PATH = "$qt/bin;$compiler;$env:PATH"
$build = Join-Path $aliasPath 'build'
New-Item -ItemType Directory -Force -Path $build | Out-Null
Set-Content -LiteralPath "$qt/bin/qt.conf" -Value "[Paths]`nPrefix=.." -Encoding Ascii
# Official open-source installer normally selects this edition during extraction.
$qconfig = Join-Path $qt "mkspecs/qconfig.pri"
(Get-Content -LiteralPath $qconfig -Raw).Replace("QT_EDITION = Enterprise", "QT_EDITION = OpenSource") | Set-Content -LiteralPath $qconfig -Encoding Ascii
Push-Location $build
try {
    $editions = if ($Edition -eq 'all') { @('baseline','optimized') } else { @($Edition) }
    foreach ($variant in $editions) {
        & "$qt/bin/qmake.exe" ../upstream/QSanguosha.pro 'CONFIG+=release' 'CONFIG-=debug' 'CONFIG-=debug_and_release' "GEMM_EDITION=$variant"
        if ($LASTEXITCODE -ne 0) { throw 'qmake failed' }
        # Variant objects may already exist on a repeated build: always relink the selected edition.
        if (Test-Path -LiteralPath "$build/QSanguosha.exe") { Remove-Item -LiteralPath "$build/QSanguosha.exe" -Force }
        & "$compiler/mingw32-make.exe" -j8
        if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
        $label = if ($variant -eq 'baseline') { 'Baseline' } else { 'Optimized' }
        Copy-Item -LiteralPath "$build/QSanguosha.exe" -Destination "$build/SanguoshaGEMM-$label.exe" -Force
    }
} finally { Pop-Location }
