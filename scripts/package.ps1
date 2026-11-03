param([ValidateSet('all','baseline','optimized')][string]$Edition = 'all')
$ErrorActionPreference = 'Stop'
$workspace = Split-Path $PSScriptRoot -Parent
$qt = Join-Path $workspace '.tools/qt/5.5/mingw492_32'
$editions = if ($Edition -eq 'all') { @('baseline','optimized') } else { @($Edition) }
foreach ($variant in $editions) {
$label = if ($variant -eq 'baseline') { 'Baseline' } else { 'Optimized' }
$dest = Join-Path $workspace "dist/SanguoshaGEMM-$label"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
foreach ($name in @('audio','etc','font','image','lang','lua','qss','skins','ui-script','scenarios')) {
    Copy-Item -LiteralPath (Join-Path "$workspace/upstream" $name) -Destination $dest -Recurse -Force
}
foreach ($name in @('LICENSE','GPLv3','MCFR','qt_zh_CN.qm','sanguosha.qm')) {
    Copy-Item -LiteralPath (Join-Path "$workspace/upstream" $name) -Destination $dest -Force
}
Copy-Item -LiteralPath "$workspace/build/SanguoshaGEMM-$label.exe" -Destination "$dest/SanguoshaGEMM-$label.exe" -Force
$env:PATH = "$qt/bin;$workspace/.tools/qt/Tools/mingw492_32/bin;$env:PATH"
python "$workspace/scripts/deploy_qt.py" --edition $variant
if ($LASTEXITCODE -ne 0) { throw "Runtime packaging failed" }
Copy-Item -LiteralPath "$workspace/licenses" -Destination $dest -Recurse -Force
Copy-Item -LiteralPath "$workspace/examples" -Destination $dest -Recurse -Force
Copy-Item -LiteralPath "$workspace/scripts/compare.py" -Destination "$dest/compare.py" -Force
Copy-Item -LiteralPath "$workspace/scripts/benchmark_suite.py" -Destination "$dest/benchmark_suite.py" -Force
if (Test-Path "$workspace/evidence/versions/suite-v1/report.html") {
    python "$workspace/scripts/export_suite_report.py" "$workspace/evidence/versions/suite-v1" "$dest/test-suite-report" --historical
    if ($LASTEXITCODE -ne 0) { throw 'Suite report export failed' }
}
if (Test-Path "$workspace/evidence/expanded/suite-v1/report.html") {
    python "$workspace/scripts/export_suite_report.py" "$workspace/evidence/expanded/suite-v1" "$dest/expanded-report" --historical
    if ($LASTEXITCODE -ne 0) { throw 'Expanded report export failed' }
}
if (Test-Path "$workspace/evidence/versions/benchmark/report.html") {
    python "$workspace/scripts/export_suite_report.py" "$workspace/evidence/versions/benchmark" "$dest/comparison-example" --historical
    if ($LASTEXITCODE -ne 0) { throw 'Comparison example export failed' }
}
if (Test-Path "$workspace/docs") { Copy-Item -LiteralPath "$workspace/docs" -Destination $dest -Recurse -Force }
if (Test-Path "$workspace/README.md") { Copy-Item -LiteralPath "$workspace/README.md" -Destination "$dest/README.md" -Force }
Write-Output $dest
}
