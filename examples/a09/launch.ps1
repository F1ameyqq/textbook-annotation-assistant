param(
    [Parameter(Mandatory=$true)][string]$ExpectedHead,
    [Parameter(Mandatory=$true)][string]$Inputs,
    [Parameter(Mandatory=$true)][string]$Output,
    [Parameter(Mandatory=$true)][string]$BudgetDir,
    [Parameter(Mandatory=$true)][string]$LaunchRecord
)
$ErrorActionPreference = 'Stop'
$env:GIT_NO_LAZY_FETCH = '1'
$taskRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$recordPath = [IO.Path]::GetFullPath($LaunchRecord)
if (Test-Path -LiteralPath $recordPath) { throw 'Launch record already exists; no repeat' }
$null = New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($recordPath)) -Force
$pythonPath = (Get-Command python).Source
$argValues = @('-B', (Join-Path $PSScriptRoot 'bounded.py'), '--expected-head', $ExpectedHead, '--inputs', $Inputs, '--output', $Output, '--budget-dir', $BudgetDir)
$quotedArgs = $argValues | ForEach-Object { '"' + $_.Replace('"', '\"') + '"' }
$proc = Start-Process -FilePath $pythonPath -ArgumentList $quotedArgs -WorkingDirectory $taskRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput ($recordPath + '.stdout.txt') -RedirectStandardError ($recordPath + '.stderr.txt')
$startTime = $proc.StartTime.ToUniversalTime().ToString('o')
$startedAt = [DateTime]::UtcNow.ToString('o')
$within = $proc.WaitForExit(240000)
if (-not $within) {
    # Original System.Diagnostics.Process handle; do not enumerate unrelated PIDs.
    $proc.Kill()
    $null = $proc.WaitForExit(5000)
}
$proc.Refresh()
$record = [ordered]@{
    frozen_head = $ExpectedHead
    supervisor_pid = $proc.Id
    supervisor_kernel_creation_time = $startTime
    launch_observed_at = $startedAt
    supervisor_end_time = $proc.ExitTime.ToUniversalTime().ToString('o')
    supervisor_exit_code = $proc.ExitCode
    supervisor_released = $proc.HasExited
    original_process_handle_waited = $true
    within_240_seconds = $within
    child_release_record = (Join-Path $Output 'release.json')
}
[IO.File]::WriteAllText($recordPath, ($record | ConvertTo-Json -Depth 6), [Text.UTF8Encoding]::new($false))
if (-not $within -or $proc.ExitCode -ne 0) { exit 1 }
