<#
.SYNOPSIS
    Generate the weekly SEO report(s) for one or more configured properties.
    Run by the SeoWeeklyReport scheduled task, or manually.

.PARAMETER Properties
    Property keys from config.yaml. Default: portfolio, shop.

.PARAMETER Days
    Lookback window for the "current" week (the previous week is auto-derived).

.EXAMPLE
    .\run-weekly-report.ps1
    .\run-weekly-report.ps1 -Properties portfolio -Days 7
#>

param(
    [string[]]$Properties = @("portfolio", "shop"),
    [int]$Days = 7
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ToolDir = Split-Path -Parent $ScriptDir
# Prefer a virtualenv inside the repo; fall back to whatever python is on PATH,
# because the scheduled task runs with no shell profile and no activated env.
$Python = Join-Path $ToolDir ".venv/Scripts/python.exe"
if (-not (Test-Path $Python)) {
    $onPath = Get-Command python -ErrorAction SilentlyContinue
    if ($onPath) { $Python = $onPath.Source }
}
$ReportsDir = Join-Path $ToolDir "reports"
$ConfigPath = Join-Path $ToolDir "config.yaml"

if (-not (Test-Path $Python)) {
    Write-Host "[seo-weekly] ERROR: Python not found at $Python"
    exit 1
}
if (-not (Test-Path $ReportsDir)) {
    New-Item -ItemType Directory -Path $ReportsDir | Out-Null
}

$Stamp = Get-Date -Format "yyyy-MM-dd"
$failures = 0

Push-Location $ToolDir
try {
    foreach ($prop in $Properties) {
        $out = Join-Path $ReportsDir ("{0}-{1}.md" -f $prop, $Stamp)
        Write-Host "[seo-weekly] $prop -> $out"
        try {
            & $Python -m seo_gsc.cli weekly --source api --property $prop --days $Days --config $ConfigPath --output $out
        } catch {
            Write-Host "[seo-weekly] FAILED for $prop : $($_.Exception.Message)"
            $failures++
        }
    }
} finally {
    Pop-Location
}

if ($failures -gt 0) {
    Write-Host "[seo-weekly] Completed with $failures failure(s)."
    exit 1
}
Write-Host "[seo-weekly] All reports written to $ReportsDir"
