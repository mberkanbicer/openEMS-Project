<#
.SYNOPSIS
Build the Rust-native Windows package for this fork and smoke-test it.

.DESCRIPTION
Produces a self-contained Windows x64 zip with

  bin\      openems-cli, nf2ff-cli, sar-cli, ctb, hyp2mat, appcsxcad
            plus every non-system DLL they import (HDF5 and friends, MSVC CRT)
  python\   CSXCAD and openEMS PyO3 wheels for the chosen interpreter
  README.txt, VERSION.txt

and then verifies the artifact: the CLI parses and steps a small model, and the
wheels import and write a CSXCAD XML from a clean virtual environment.

The same script is what .github/workflows/windows-rust-package.yml runs, so a
local run and a CI run build the same layout.

.PARAMETER Python
Python interpreter used for the maturin wheels and the venv smoke test. It must
have numpy available (or a venv can see it); HDF5 must be discoverable through
HDF5_LIB_DIR / HDF5_INCLUDE_DIR / PATH, exactly like the test suite.

.PARAMETER OutDir
Directory for the zip (default: <repo>/dist).

.PARAMETER SkipBuild
Reuse the existing release binaries and wheels instead of rebuilding.

.EXAMPLE
pwsh scripts/ci/build_windows_package.ps1 -Python C:\conda\envs\openems\python.exe
#>
[CmdletBinding()]
param(
    [string]$Python = "",
    [string]$OutDir = "",
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
if (-not $OutDir) { $OutDir = Join-Path $repo "dist" }
$OutDir = [IO.Path]::GetFullPath($OutDir)

if (-not $Python) {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $cmd) { throw "no python on PATH; pass -Python <interpreter>" }
    $Python = $cmd.Source
}
if (-not (Test-Path $Python)) { throw "python not found: $Python" }
$Python = (Resolve-Path $Python).Path

function Step([string]$name, [scriptblock]$body) {
    Write-Host "== $name" -ForegroundColor Cyan
    & $body
    if ($LASTEXITCODE -ne 0) { throw "$name failed (exit $LASTEXITCODE)" }
}

function Git([string]$repoPath, [string[]]$gitArguments) {
    $out = & git.exe -C $repoPath @gitArguments 2>$null
    if ($LASTEXITCODE -ne 0) { throw "git $($gitArguments -join ' ') failed in $repoPath" }
    return ($out | Out-String).Trim()
}

# ---------------------------------------------------------------- metadata --
$rootSha = Git $repo @("rev-parse", "--short", "HEAD")
$openemsDescribe = Git (Join-Path $repo "openEMS") @("describe", "--tags", "--always")
$rustc = (& rustc --version | Out-String).Trim()
$version = "0.1.0-$rootSha"
$stem = "openEMS-rust_${openemsDescribe}_win64"
$stage = Join-Path $OutDir $stem
$wheelDir = Join-Path $stage "python"
$binDir = Join-Path $stage "bin"

Write-Host "repo      $repo"
Write-Host "revision  $rootSha / openEMS $openemsDescribe"
Write-Host "python    $Python"
Write-Host "stage     $stage"

# ------------------------------------------------------------------ builds --
$packages = @(
    "openems-cli",
    "nf2ff-cli",
    "sar-cli",
    "ctb-rs",
    "hyp2mat-rs",
    "appcsxcad"
)

if (-not $SkipBuild) {
    Step "cargo build --release" {
        Push-Location $repo
        try {
            & cargo build --release @($packages | ForEach-Object { "-p"; $_ })
        } finally { Pop-Location }
    }
}

if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }
New-Item -ItemType Directory -Force $binDir, $wheelDir | Out-Null

$binaries = @(
    "openems-cli",
    "nf2ff-cli",
    "sar-cli",
    "ctb",
    "hyp2mat",
    "appcsxcad"
)
foreach ($name in $binaries) {
    $exe = Join-Path $repo "target\release\$name.exe"
    if (-not (Test-Path $exe)) { throw "missing release binary: $exe" }
    Copy-Item $exe $binDir -Force
}

if (-not $SkipBuild) {
    $maturin = Get-Command maturin -ErrorAction SilentlyContinue
    if (-not $maturin) { throw "maturin not found; pip install maturin" }
    foreach ($crate in @("CSXCAD\rust-py", "openEMS\rust-py")) {
        Step "maturin build $crate" {
            Push-Location (Join-Path $repo $crate)
            try {
                & maturin build --release --out $wheelDir --interpreter $Python
            } finally { Pop-Location }
        }
    }
}
$wheels = @(Get-ChildItem $wheelDir -Filter *.whl)
if ($wheels.Count -eq 0) { throw "no wheels in $wheelDir" }

# ------------------------------------------------------- runtime DLL closure --
# Windows resolves DLLs from the executable directory first, so every
# non-system dependency is staged next to the binaries. dumpbin gives the
# import table; the walk is recursive because hdf5.dll pulls in curl/zlib/etc.
function Find-Dumpbin {
    $vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
    if (Test-Path $vswhere) {
        $vs = & $vswhere -latest -products * -property installationPath
        if ($vs) {
            $candidate = Get-ChildItem (Join-Path $vs "VC\Tools\MSVC") -Recurse -Filter dumpbin.exe -ErrorAction SilentlyContinue |
                Where-Object { $_.FullName -match 'Hostx64\\x64' } |
                Select-Object -First 1 -ExpandProperty FullName
            if ($candidate) { return $candidate }
        }
    }
    $cmd = Get-Command dumpbin.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return $null
}

$dumpbin = Find-Dumpbin
Write-Host "dumpbin   $dumpbin"

$searchDirs = @()
if ($env:HDF5_LIB_DIR) { $searchDirs += $env:HDF5_LIB_DIR }
if ($env:HDF5_LIB_DIR) { $searchDirs += (Join-Path (Split-Path $env:HDF5_LIB_DIR) "bin") }
if ($env:EXTRA_DLL_DIRS) { $searchDirs += ($env:EXTRA_DLL_DIRS -split ";") }
# Deliberately not PATH: copying DLLs from System32 or unrelated toolchains
# bloated the first attempt to 160 files and would ship OS components.
$searchDirs = $searchDirs | Where-Object { $_ -and (Test-Path $_) } | Select-Object -Unique

$systemPattern = '^(kernel32|user32|advapi32|ole32|oleaut32|shell32|shlwapi|gdi32|ws2_32|bcrypt|crypt32|ntdll|msvcrt|ucrtbase|api-ms-win-|winmm|iphlpapi|psapi|dbghelp|secur32|wldap32|version|imm32|comdlg32|comctl32|setupapi|userenv|dwmapi|d3d|dxgi|opengl32|glu32|vulkan-1|nvapi|dinput|xinput|winhttp|wininet|netapi32|mpr|authz|rpcrt4|cabinet|msi|oleacc|uxtheme|powrprof|pdh|wevtapi|normaliz|wintrust|wtsapi32|cfgmgr32|devobj)'

if ($dumpbin) {
    $staged = @{}
    $queue = [System.Collections.Generic.Queue[string]]::new()
    Get-ChildItem $binDir -Filter *.exe | ForEach-Object { $queue.Enqueue($_.FullName) }
    $missing = @{}
    while ($queue.Count -gt 0) {
        $binary = $queue.Dequeue()
        $imports = & $dumpbin /nologo /dependents $binary 2>$null |
            Select-String -Pattern '^\s+([A-Za-z0-9_.\-]+\.dll)\s*$' |
            ForEach-Object { $_.Matches[0].Groups[1].Value }
        foreach ($dll in $imports) {
            if ($dll -match $systemPattern) { continue }
            $key = $dll.ToLowerInvariant()
            if ($staged.ContainsKey($key)) { continue }
            $source = $null
            foreach ($dir in $searchDirs) {
                $candidate = Join-Path $dir $dll
                if (Test-Path $candidate) { $source = $candidate; break }
            }
            if (-not $source) {
                if (-not $missing.ContainsKey($dll)) {
                    $missing[$dll] = $binary
                    Write-Warning "unresolved import $dll (from $(Split-Path $binary -Leaf))"
                }
                continue
            }
            Copy-Item $source $binDir -Force
            $staged[$key] = $true
            $queue.Enqueue((Join-Path $binDir $dll))
        }
    }
    Write-Host "staged $($staged.Count) non-system DLL(s)"
} else {
    Write-Warning "dumpbin not found; the package may miss runtime DLLs"
}

# MSVC runtime: Rust links the dynamic CRT. Python brings vcruntime140 but not
# msvcp140, so ship both next to the binaries.
$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
if (Test-Path $vswhere) {
    $vs = & $vswhere -latest -products * -property installationPath
    if ($vs) {
        $crt = Get-ChildItem (Join-Path $vs "VC\Redist\MSVC") -Recurse -Directory -Filter "Microsoft.VC*.CRT" -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -match '\\x64\\Microsoft\.VC' -and $_.FullName -notmatch 'onecore' } |
            Sort-Object FullName | Select-Object -Last 1
        if ($crt) {
            Copy-Item (Join-Path $crt.FullName "*.dll") $binDir -Force
            Write-Host "copied MSVC CRT from $($crt.FullName)"
        }
    }
}

# --------------------------------------------------------------- metadata --
$readme = @"
openEMS Rust migration - Windows x64 package
============================================

Build
  repository revision : $rootSha
  openEMS describe    : $openemsDescribe
  compiler            : $rustc
  Python wheel tag    : $($wheels[0].Name)

Contents
  bin\openems-cli.exe   FDTD solver (same CLI as the native openEMS)
  bin\nf2ff-cli.exe     near-to-far-field post-processing
  bin\sar-cli.exe       SAR post-processing
  bin\ctb.exe           circuit/RF network tool
  bin\hyp2mat.exe       HyperLynx PCB converter
  bin\appcsxcad.exe     geometry editor (egui/wgpu)
  python\*.whl          CSXCAD and openEMS Python extensions

Usage
  bin\openems-cli.exe model.xml
  python -m pip install python\*.whl
  The Python extensions link the HDF5 DLL shipped in bin\; add that directory
  to PATH before importing them (the smoke test does the same).

Scope
  This is the Rust migration artifact, not the native C++ installer. Builds are
  reproducible with scripts\ci\build_windows_package.ps1; the workflow
  .github\workflows\windows-rust-package.yml runs the same script.
"@
Set-Content (Join-Path $stage "README.txt") $readme -Encoding UTF8

$versionText = @(
    "repository=$rootSha",
    "openEMS=$openemsDescribe",
    "rustc=$rustc",
    "python=$(& $Python -c 'import sys; print(sys.version.split()[0])')",
    "wheel=$($wheels[0].Name)"
) -join "`n"
Set-Content (Join-Path $stage "VERSION.txt") $versionText -Encoding UTF8

# ------------------------------------------------------------------- smoke --
Step "smoke: CLI help" {
    $help = & (Join-Path $binDir "openems-cli.exe") -h 2>&1
    $code = $LASTEXITCODE
    if ($code -ne 0) { throw "openems-cli -h exited $code" }
    $helpText = ($help | Out-String)
    if ($helpText -notmatch "Version:") { throw "openems-cli -h has no version banner" }
    Write-Host (($helpText -split "`n" | Where-Object { $_ -match "Version:" }) -join "`n")
}

Step "smoke: CLI solves a tiny model" {
    $fixture = Join-Path $repo "CSXCAD\rust\tests\fixtures\xml\10_openems_wrapper.xml"
    $model = Join-Path $OutDir "smoke-model.xml"
    $text = (Get-Content $fixture -Raw) `
        -replace 'NumberOfTimesteps="100"', 'NumberOfTimesteps="20"' `
        -replace 'PML_8', 'PEC'
    # No BOM: the CSXCAD reader rejects a byte-order mark.
    [IO.File]::WriteAllText($model, $text, (New-Object System.Text.UTF8Encoding($false)))
    Push-Location $OutDir
    try {
        $runLog = & (Join-Path $binDir "openems-cli.exe") $model 2>&1
        $code = $LASTEXITCODE
    } finally { Pop-Location }
    if ($code -ne 0) { throw "openems-cli failed on the smoke model (exit $code)" }
    $runText = ($runLog | Out-String)
    if ($runText -notmatch "simulation completed: (\d+) timesteps") {
        throw "openems-cli did not report a completed simulation"
    }
    Remove-Item $model -Force
    Write-Host (($runText -split "`n" | Where-Object { $_ -match "simulation completed" }) -join "`n")
}

Step "smoke: Python wheels" {
    $venv = Join-Path $OutDir "smoke-venv"
    if (Test-Path $venv) { Remove-Item $venv -Recurse -Force }
    & $Python -m venv --system-site-packages $venv
    if ($LASTEXITCODE -ne 0) { throw "venv creation failed" }
    $venvPython = Join-Path $venv "Scripts\python.exe"
    & $venvPython -m pip install --quiet --no-deps --force-reinstall @($wheels | ForEach-Object { $_.FullName })
    if ($LASTEXITCODE -ne 0) { throw "wheel install failed" }
    $env:PATH = "$binDir;$env:PATH"
    $probe = Join-Path $OutDir "smoke-python.py"
    @"
import tempfile, os
from CSXCAD import ContinuousStructure
from openEMS import openEMS, _openems
import csxcad_py

csx = ContinuousStructure()
mesh = csx.GetGrid()
mesh.SetDeltaUnit(1e-3)
for axis in ("x", "y", "z"):
    mesh.AddLine(axis, [0.0, 1.0, 2.0])
mat = csx.AddMaterial("smoke", epsilon=4.0)
mat.AddBox([0, 0, 0], [1, 1, 1])
fdtd = openEMS(NrTS=10)
fdtd.SetCSX(csx)
path = os.path.join(tempfile.mkdtemp(), "smoke.xml")
csx.Write2XML(path)
assert os.path.getsize(path) > 0
print("wheel smoke ok:", csxcad_py.__name__, _openems.__name__, os.path.getsize(path))
"@ | Set-Content $probe -Encoding UTF8
    & $venvPython $probe
    if ($LASTEXITCODE -ne 0) { throw "wheel smoke failed" }
    Remove-Item $probe, $venv -Recurse -Force
}

# ------------------------------------------------------------------ archive --
$zip = Join-Path $OutDir "$stem.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path $stage -DestinationPath $zip -CompressionLevel Optimal

$hash = (Get-FileHash $zip -Algorithm SHA256).Hash.ToLowerInvariant()
$size = (Get-Item $zip).Length
Write-Host ""
Write-Host "package : $zip"
Write-Host "size    : $size bytes"
Write-Host "sha256  : $hash"
Set-Content (Join-Path $OutDir "$stem.sha256") "$hash  $stem.zip" -Encoding ASCII
