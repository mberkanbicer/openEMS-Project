#Requires -Version 5.1
<#
.SYNOPSIS
    Open, run and plot the openEMS Rust tutorial projects.

.DESCRIPTION
    Three self-contained openEMS/CSXCAD XML projects live next to this script.
    This helper opens them in AppCSXCAD, runs them with the Rust solver and
    plots the results, so a fresh checkout can be exercised end to end without
    remembering the individual command lines.

    Tool resolution (first match wins):
      solver : -Solver, $env:OPENEMS_BIN, target\release\openems-cli.exe, PATH
      GUI    : -Gui,    $env:APPCXCAD_BIN, target\release\appcsxcad.exe, PATH
      python : -Python, $env:OPENEMS_PYTHON, $env:CONDA_PREFIX, conda env
               'openems', PATH

.PARAMETER Tutorial
    Which tutorial to act on: 01, 02, 03 or all (default).

.PARAMETER Mode
    gui  - open the project in AppCSXCAD and leave the window open
    run  - run the solver, writing results\<tutorial>\
    plot - run plot_tutorials.py over existing results
    all  - gui, then run, then plot (default)

.PARAMETER Solver
    Path to openems-cli.exe (or another openEMS-compatible solver).

.PARAMETER Gui
    Path to appcsxcad.exe.

.PARAMETER Python
    Python interpreter with numpy, h5py and matplotlib.

.PARAMETER Gpu
    Pass --gpu to the solver (requires a build with the 'gpu' feature).

.PARAMETER Show
    Let the plotting script open the figures instead of only saving them.

.EXAMPLE
    .\run_tutorial.ps1

.EXAMPLE
    .\run_tutorial.ps1 -Tutorial 03 -Mode run

.EXAMPLE
    .\run_tutorial.ps1 -Tutorial 02 -Mode plot -Show

.NOTES
    The solver writes into results\<tutorial>\ so the repository stays clean;
    results/ is ignored by git.
#>
[CmdletBinding()]
param(
    [ValidateSet('01', '02', '03', 'all')]
    [string]$Tutorial = 'all',

    [ValidateSet('gui', 'run', 'plot', 'all')]
    [string]$Mode = 'all',

    [string]$Solver,
    [string]$Gui,
    [string]$Python,

    [switch]$Gpu,
    [switch]$Show
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $here
$resultsRoot = Join-Path $here 'results'
$plotScript = Join-Path $here 'plot_tutorials.py'

# Tutorial id -> project base name.
$tutorials = [ordered]@{
    '01' = '01_free_space_pulse'
    '02' = '02_dielectric_interface'
    '03' = '03_rectangular_cavity'
}

function Write-Step {
    param([string]$Text)
    Write-Host ''
    Write-Host "==> $Text" -ForegroundColor Cyan
}

function Resolve-Tool {
    <#
        Resolve an executable from an explicit path, an environment variable,
        a list of candidate paths and finally the PATH lookup.
    #>
    param(
        [string]$Explicit,
        [string]$EnvName,
        [string[]]$Candidates,
        [string]$CommandName,
        [string]$Description
    )

    if ($Explicit) {
        if (Test-Path -LiteralPath $Explicit) {
            return (Resolve-Path -LiteralPath $Explicit).Path
        }
        $command = Get-Command $Explicit -ErrorAction SilentlyContinue
        if ($command) { return $command.Source }
        throw "$Description not found: '$Explicit'"
    }

    if ($EnvName) {
        $fromEnv = [Environment]::GetEnvironmentVariable($EnvName)
        if ($fromEnv) {
            if (Test-Path -LiteralPath $fromEnv) {
                return (Resolve-Path -LiteralPath $fromEnv).Path
            }
            $command = Get-Command $fromEnv -ErrorAction SilentlyContinue
            if ($command) { return $command.Source }
            throw "$Description from $EnvName not found: '$fromEnv'"
        }
    }

    foreach ($candidate in $Candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate)) {
            return $candidate
        }
    }

    $command = Get-Command $CommandName -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    return $null
}

function Get-SolverPath {
    $candidates = @(
        (Join-Path $repoRoot 'target\release\openems-cli.exe'),
        (Join-Path $repoRoot 'target\debug\openems-cli.exe'),
        (Join-Path $repoRoot 'bin\openems-cli.exe'),
        (Join-Path $repoRoot 'bin\openEMS.exe')
    )
    $path = Resolve-Tool -Explicit $Solver -EnvName 'OPENEMS_BIN' `
        -Candidates $candidates -CommandName 'openems-cli' `
        -Description 'openEMS solver'
    if (-not $path) {
        throw @'
openEMS solver not found.

Build it first:
    cargo build --release -p openems-cli --features gpu

or pass -Solver <path> / set $env:OPENEMS_BIN.
'@
    }
    return $path
}

function Get-GuiPath {
    $candidates = @(
        (Join-Path $repoRoot 'target\release\appcsxcad.exe'),
        (Join-Path $repoRoot 'target\debug\appcsxcad.exe'),
        (Join-Path $repoRoot 'bin\appcsxcad.exe')
    )
    $path = Resolve-Tool -Explicit $Gui -EnvName 'APPCXCAD_BIN' `
        -Candidates $candidates -CommandName 'appcsxcad' `
        -Description 'AppCSXCAD'
    if (-not $path) {
        throw @'
AppCSXCAD not found.

Build it first:
    cargo build --release -p appcsxcad

or pass -Gui <path> / set $env:APPCXCAD_BIN.
'@
    }
    return $path
}

function Test-PythonModules {
    <#
        True when the interpreter can import everything plot_tutorials.py
        needs.  Probing beats guessing between the base conda environment and
        the 'openems' environment that actually carries numpy/h5py/matplotlib.
    #>
    param([string]$Path)

    & $Path -c 'import numpy, h5py, matplotlib' 2>&1 | Out-Null
    return ($LASTEXITCODE -eq 0)
}

function Get-PythonPath {
    $candidates = @()
    if ($env:USERPROFILE) {
        $candidates += (Join-Path $env:USERPROFILE 'miniconda3\envs\openems\python.exe')
        $candidates += (Join-Path $env:USERPROFILE 'anaconda3\envs\openems\python.exe')
    }
    if ($env:CONDA_PREFIX) {
        $candidates += (Join-Path $env:CONDA_PREFIX 'python.exe')
    }
    $command = Get-Command 'python' -ErrorAction SilentlyContinue
    if ($command) { $candidates += $command.Source }

    $explicit = Resolve-Tool -Explicit $Python -EnvName 'OPENEMS_PYTHON' `
        -Candidates @() -CommandName 'python' -Description 'Python interpreter'

    # An explicitly chosen interpreter wins; report clearly if it is missing
    # the modules instead of silently falling back.
    if ($Python -or $env:OPENEMS_PYTHON) {
        if (-not $explicit) {
            throw 'Python interpreter not found (-Python / $env:OPENEMS_PYTHON).'
        }
        if (-not (Test-PythonModules -Path $explicit)) {
            throw @"
'$explicit' cannot import numpy, h5py and matplotlib.

Install them or point -Python / `$env:OPENEMS_PYTHON at the openEMS conda
environment, for example:
    `$env:USERPROFILE\miniconda3\envs\openems\python.exe
"@
        }
        return $explicit
    }

    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate)) {
            if (Test-PythonModules -Path $candidate) { return $candidate }
        }
    }

    throw @'
No Python interpreter with numpy, h5py and matplotlib was found.

Activate the openEMS conda environment first, or pass -Python <path> / set
$env:OPENEMS_PYTHON.  Candidates tried:
  - %USERPROFILE%\miniconda3\envs\openems\python.exe
  - %USERPROFILE%\anaconda3\envs\openems\python.exe
  - $env:CONDA_PREFIX\python.exe
  - python on PATH
'@
}

function Get-SelectedIds {
    if ($Tutorial -eq 'all') {
        return @($tutorials.Keys)
    }
    return @($Tutorial)
}

function Open-TutorialInGui {
    param([string]$Id)

    $project = Join-Path $here ($tutorials[$Id] + '.xml')
    if (-not (Test-Path -LiteralPath $project)) {
        throw "Missing tutorial project: '$project'"
    }
    $guiPath = Get-GuiPath
    Write-Step "AppCSXCAD: $($tutorials[$Id])"
    $process = Start-Process -FilePath $guiPath -ArgumentList ('"' + $project + '"') -PassThru
    Write-Host "  launched $([IO.Path]::GetFileName($guiPath)) (PID $($process.Id))"
    Write-Host "  project: $project"
}

function Invoke-TutorialSolver {
    param([string]$Id)

    $project = Join-Path $here ($tutorials[$Id] + '.xml')
    if (-not (Test-Path -LiteralPath $project)) {
        throw "Missing tutorial project: '$project'"
    }
    $solverPath = Get-SolverPath
    $outputDir = Join-Path $resultsRoot $tutorials[$Id]
    New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

    $arguments = @($project)
    if ($Gpu) { $arguments += '--gpu' }

    Write-Step "run $($tutorials[$Id])"
    Write-Host "  solver : $solverPath"
    Write-Host "  output : $outputDir"

    $watch = [Diagnostics.Stopwatch]::StartNew()
    Push-Location $outputDir
    try {
        & $solverPath @arguments
        $exitCode = $LASTEXITCODE
    }
    finally {
        Pop-Location
    }
    $watch.Stop()

    if ($exitCode -ne 0) {
        throw "solver exited with code $exitCode for '$($tutorials[$Id])'"
    }
    Write-Host ("  completed in {0:N2} s" -f $watch.Elapsed.TotalSeconds)
}

function Invoke-TutorialPlots {
    $pythonPath = Get-PythonPath
    if (-not (Test-Path -LiteralPath $plotScript)) {
        throw "Missing plotting script: '$plotScript'"
    }

    $arguments = @($plotScript, '--results', $resultsRoot)
    if ($Tutorial -ne 'all') {
        $arguments += @('--only', $Tutorial)
    }
    if ($Show) { $arguments += '--show' }

    Write-Step 'plot'
    Write-Host "  python : $pythonPath"
    & $pythonPath @arguments
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        throw "plot_tutorials.py exited with code $exitCode"
    }
}

# ---------------------------------------------------------------------- main
$selected = Get-SelectedIds
$failure = $null

try {
    if ($Mode -eq 'gui' -or $Mode -eq 'all') {
        foreach ($id in $selected) { Open-TutorialInGui -Id $id }
    }
    if ($Mode -eq 'run' -or $Mode -eq 'all') {
        foreach ($id in $selected) { Invoke-TutorialSolver -Id $id }
    }
    if ($Mode -eq 'plot' -or $Mode -eq 'all') {
        Invoke-TutorialPlots
    }
}
catch {
    $failure = $_
    Write-Host ''
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ''
if ($failure) {
    Write-Host 'Tutorial run failed.' -ForegroundColor Red
    exit 1
}
Write-Host 'Tutorial run finished.' -ForegroundColor Green
exit 0
