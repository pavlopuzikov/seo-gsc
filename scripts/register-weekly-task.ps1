<#
.SYNOPSIS
    Register the weekly SEO report as a Windows Scheduled Task (Monday 08:00).
    Mirrors the infra/multi-agent setup_scheduler.ps1 pattern.

.PARAMETER AtTime
    Time to run on Monday. Default: 08:00.

.PARAMETER Unregister
    Remove the task instead of creating it.

.EXAMPLE
    .\register-weekly-task.ps1
    .\register-weekly-task.ps1 -AtTime "09:00"
    .\register-weekly-task.ps1 -Unregister
#>

param(
    [string]$AtTime = "08:00",
    [switch]$Unregister
)

$ErrorActionPreference = "Stop"
$TaskName = "SeoWeeklyReport"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Runner = Join-Path $ScriptDir "run-weekly-report.ps1"

if ($Unregister) {
    try {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "[seo-weekly] Removed scheduled task: $TaskName"
    } catch {
        Write-Host "[seo-weekly] Task '$TaskName' not found or already removed."
    }
    exit 0
}

if (-not (Test-Path $Runner)) {
    Write-Host "[seo-weekly] ERROR: run-weekly-report.ps1 not found at $Runner"
    exit 1
}

$actionArgs = '-ExecutionPolicy Bypass -WindowStyle Hidden -File "{0}"' -f $Runner
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $actionArgs -WorkingDirectory $ScriptDir
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At $AtTime
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -RestartCount 2 `
    -RestartInterval (New-TimeSpan -Minutes 10)

try {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
} catch {}

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Weekly SEO report (seo-gsc) for configured properties." `
    -RunLevel Highest

Write-Host ""
Write-Host "============================================="
Write-Host "  SeoWeeklyReport scheduled task registered"
Write-Host "============================================="
Write-Host "  Task name:  $TaskName"
Write-Host "  Schedule:   every Monday at $AtTime"
Write-Host "  Runner:     $Runner"
Write-Host "  To run now:  Start-ScheduledTask -TaskName $TaskName"
Write-Host "  To remove:   .\register-weekly-task.ps1 -Unregister"
Write-Host "============================================="
