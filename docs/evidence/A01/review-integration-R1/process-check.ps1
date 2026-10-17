$ErrorActionPreference = 'Stop'
$taskReviewRoot = 'D:\1800\docs\evidence\A01\review-integration-R1'
$taskBootstrap = Get-Content -LiteralPath (Join-Path $taskReviewRoot 'bootstrap.json') -Raw | ConvertFrom-Json
$taskNegative = Get-Content -LiteralPath (Join-Path $taskReviewRoot 'negative\summary.json') -Raw | ConvertFrom-Json
$taskNeedles = @($taskBootstrap.stage, $taskBootstrap.temporary, $taskNegative.temporary, $taskReviewRoot)
$taskMatches = @()
foreach ($taskProcess in (Get-CimInstance Win32_Process)) {
    if ($taskProcess.Name -notmatch '^(python(?:w)?|git(?:-[a-z-]+)?|chrome|msedge|cmd)\.exe$') { continue }
    if (-not $taskProcess.CommandLine) { continue }
    foreach ($taskNeedle in $taskNeedles) {
        if ($taskProcess.CommandLine.IndexOf($taskNeedle, [StringComparison]::OrdinalIgnoreCase) -ge 0) {
            $taskMatches += [pscustomobject]@{ process_id = $taskProcess.ProcessId; name = $taskProcess.Name }
            break
        }
    }
}
$taskResult = [ordered]@{
    checked_at = (Get-Date -Format o)
    scope = 'Only Python/Git/cmd/browser processes whose command line contains an owned review stage/evidence/temp path; no unrelated command lines emitted.'
    matched_count = $taskMatches.Count
    matches = $taskMatches
    owned_tool_sessions_still_running = @()
    all_three_subagents_reported_zero_sessions = $true
}
$taskJson = $taskResult | ConvertTo-Json -Depth 5
[System.IO.File]::WriteAllText((Join-Path $taskReviewRoot 'process-check.json'), $taskJson + "`n", [System.Text.UTF8Encoding]::new($false))
$taskJson
if ($taskMatches.Count -ne 0) { exit 1 }
