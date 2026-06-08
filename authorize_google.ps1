# Refresh local ADC for AutoBrief's real delivery (keyless domain-wide delegation).
#
# DWD does NOT use a browser consent for the delivery scopes — those are granted
# once in the Workspace Admin console. This script only refreshes plain ADC
# (cloud-platform scope), which the org policy does NOT block, so the local
# process can impersonate the delivery service account.
#
# PREREQUISITE (one-time, Workspace admin):
#   Admin console -> Security -> Access and data control -> API controls ->
#   Domain-wide delegation -> Add new:
#     Client ID: 110521031441107066209
#     Scopes:    https://www.googleapis.com/auth/gmail.compose,
#                https://www.googleapis.com/auth/calendar.events,
#                https://www.googleapis.com/auth/drive.file
#
# Usage:   powershell -ExecutionPolicy Bypass -File .\authorize_google.ps1

$ErrorActionPreference = 'Stop'

Write-Host "Refreshing local ADC (plain cloud-platform login -- not blocked)..." -ForegroundColor Cyan
Write-Host "Sign in as support@lightonpluslab.com and click Allow." -ForegroundColor Cyan

# Plain login: no sensitive Gmail/Drive scopes here -> the org block does not apply.
gcloud auth application-default login

if ($LASTEXITCODE -eq 0) {
  Write-Host ""
  Write-Host "ADC refreshed. Verifying DWD delivery..." -ForegroundColor Green
  $env:AUTOBRIEF_ENABLE_GOOGLE = '1'
  python -m autobrief.mcp_server.verify_google
} else {
  Write-Host "gcloud login did not complete (exit $LASTEXITCODE)." -ForegroundColor Red
}
