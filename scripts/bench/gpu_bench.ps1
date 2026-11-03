# GPU/CPU benchmark harness for the Rust openEMS CLI.
#
# Usage:
#   pwsh -File scripts/bench/gpu_bench.ps1 -Models "a.xml","b.xml" -Repeat 3
#   pwsh -File scripts/bench/gpu_bench.ps1 -Models "a.xml" -Gpu -Repeat 5
#
# Prints the best and average wall time per model and engine. The harness is
# deliberately dependency-free: it only runs the CLI and times it, so the same
# numbers can be reproduced on any machine with a built `openems-cli`.

param(
    [Parameter(Mandatory = $true)][string[]]$Models,
    [int]$Repeat = 3,
    [switch]$Gpu,
    [string]$Cli = "",
    [string]$WorkDir = ""
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrEmpty($Cli)) {
    $root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
    $Cli = Join-Path $root "target\release\openems-cli.exe"
}
if (-not (Test-Path $Cli)) {
    throw "openems-cli not found at '$Cli'; build it with: cargo build --release -p openems-cli --features gpu"
}

if ([string]::IsNullOrEmpty($WorkDir)) {
    $WorkDir = Join-Path ([System.IO.Path]::GetTempPath()) "openems-bench"
}
New-Item -ItemType Directory -Force $WorkDir | Out-Null

$rows = @()
foreach ($model in $Models) {
    $name = Split-Path -Leaf $model
    $cliArgs = @($model)
    if ($Gpu) { $cliArgs += "--gpu" }
    $times = @()
    for ($i = 0; $i -lt $Repeat; $i++) {
        Push-Location $WorkDir
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        & $Cli @cliArgs | Out-Null
        $code = $LASTEXITCODE
        $sw.Stop()
        Pop-Location
        if ($code -ne 0) { throw "$name exited with $code" }
        $times += $sw.Elapsed.TotalSeconds
    }
    $min = ($times | Measure-Object -Minimum).Minimum
    $avg = ($times | Measure-Object -Average).Average
    $rows += [pscustomobject]@{
        Model = $name
        Engine = if ($Gpu) { "gpu" } else { "cpu" }
        Best = [math]::Round($min, 3)
        Average = [math]::Round($avg, 3)
        Runs = $Repeat
    }
}

$rows | Format-Table -AutoSize
