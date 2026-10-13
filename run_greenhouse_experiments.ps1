# ======================================================================
#         AGRIVOLTAIC GREENHOUSE DIGITAL TWIN - EXPERIMENT RUNNER
# ======================================================================

param (
    [string]$Choice = ""
)

$ErrorActionPreference = "Continue"

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "        AGRIVOLTAIC GREENHOUSE DIGITAL TWIN - EXPERIMENT RUNNER       " -ForegroundColor Magenta
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

# Check if uv is installed
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] 'uv' package manager could not be found." -ForegroundColor Red
    Write-Host "Please install 'uv' before running experiments: https://docs.astral.sh/uv/"
    exit 1
}

$Script:Status1 = "SKIPPED"
$Script:Status2 = "SKIPPED"
$Script:Status3 = "SKIPPED"

function Run-Exp {
    param (
        [string]$ExpNum,
        [string]$ExpName,
        [string]$ExpScript,
        [string[]]$ExtraArgs = @()
    )

    Write-Host "[RUNNING] Experiment ${ExpNum}: ${ExpName}" -ForegroundColor Blue
    Write-Host "Command: uv run python $ExpScript $($ExtraArgs -join ' ')"
    Write-Host "----------------------------------------------------------------------" -ForegroundColor Cyan

    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $cmdArgs = @("run", "python", $ExpScript) + $ExtraArgs
    & uv @cmdArgs
    $exitCode = $LASTEXITCODE
    $sw.Stop()
    $duration = [math]::Round($sw.Elapsed.TotalSeconds, 1)

    Write-Host "----------------------------------------------------------------------" -ForegroundColor Cyan
    if ($exitCode -eq 0) {
        Write-Host "[SUCCESS] Experiment ${ExpNum} completed in ${duration}s." -ForegroundColor Green
        Set-Variable -Name "Status${ExpNum}" -Value "PASSED (${duration}s)" -Scope Script
    } else {
        Write-Host "[FAILED] Experiment ${ExpNum} failed with exit code ${exitCode} after ${duration}s." -ForegroundColor Red
        Set-Variable -Name "Status${ExpNum}" -Value "FAILED (${duration}s)" -Scope Script
    }
    Write-Host ""
}

function Show-Menu {
    Write-Host "Select Benchmark Experiment:" -ForegroundColor White
    Write-Host "  1) Exp 1: Initial Calibration Benchmark (Model A vs Baseline vs Calibrated Model B & Speedup)"
    Write-Host "  2) Exp 2: Multi-Scenario Cross-Validation (Multi-Scenario Model A vs Model B)"
    Write-Host "  3) Exp 3: Physical Degradation Tracking Benchmark (Recalibration under Model A Degradation)"
    Write-Host "  5) Run ALL Experiments Sequentially"
    Write-Host "  q) Quit"
    Write-Host ""
    $resp = Read-Host "Enter your choice [1, 2, 3, 5 or q]"
    Write-Host ""
    return $resp
}

if ([string]::IsNullOrWhiteSpace($Choice)) {
    $Choice = Show-Menu
}

switch ($Choice) {
    "1" {
        Run-Exp -ExpNum "1" -ExpName "Initial Calibration Benchmark" -ExpScript "cases/greenhouse/exp1_initial_calibration.py"
    }
    "2" {
        Run-Exp -ExpNum "2" -ExpName "Scenario Simulation Benchmark" -ExpScript "cases/greenhouse/exp2_scenario_simulation.py"
    }
    "3" {
        Run-Exp -ExpNum "3" -ExpName "Periodic Recalibration Benchmark" -ExpScript "cases/greenhouse/exp3_recalibration.py"
    }
    { $_ -in "5", "all" } {
        Write-Host "[INFO] Running all benchmark experiments sequentially...`n" -ForegroundColor Yellow
        Run-Exp -ExpNum "1" -ExpName "Initial Calibration Benchmark" -ExpScript "cases/greenhouse/exp1_initial_calibration.py" -ExtraArgs @("--force-model-a")
        Run-Exp -ExpNum "2" -ExpName "Scenario Simulation Benchmark" -ExpScript "cases/greenhouse/exp2_scenario_simulation.py"
        Run-Exp -ExpNum "3" -ExpName "Periodic Recalibration Benchmark" -ExpScript "cases/greenhouse/exp3_recalibration.py"
    }
    { $_ -in "q", "Q" } {
        Write-Host "Exited." -ForegroundColor Yellow
        exit 0
    }
    default {
        Write-Host "[ERROR] Invalid choice." -ForegroundColor Red
        exit 1
    }
}

# Print Summary Table
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "                     EXPERIMENT RUN SUMMARY                          " -ForegroundColor Magenta
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ("{0,-40} | {1,-20}" -f "Experiment Name", "Status") -ForegroundColor White
Write-Host "------------------------------------------------------------"
Write-Host ("{0,-40} | {1}" -f "Exp 1: Initial Calibration Benchmark", $Script:Status1)
Write-Host ("{0,-40} | {1}" -f "Exp 2: Multi-Scenario Cross-Validation", $Script:Status2)
Write-Host ("{0,-40} | {1}" -f "Exp 3: Recalibration Capability", $Script:Status3)
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "Completed! Results, plots, and metrics are saved in 'results/greenhouse/'." -ForegroundColor Green
