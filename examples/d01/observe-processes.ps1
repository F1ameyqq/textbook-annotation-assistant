param([Parameter(Mandatory = $true)][string]$OutputPath)
$ErrorActionPreference = 'Stop'
$taskRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
$taskEvidence = Join-Path $taskRoot 'docs/evidence/D01/execution'
$taskOutput = [IO.Path]::GetFullPath($OutputPath)
if (Test-Path -LiteralPath $taskOutput) { throw 'Preserve the previous process observation.' }
$taskLedgers = Get-ChildItem -LiteralPath $taskEvidence -Filter process-ledger.json -Recurse | ForEach-Object {
    Get-Content -LiteralPath $_.FullName -Raw | ConvertFrom-Json
}
$taskReceipts = Get-ChildItem -LiteralPath $taskEvidence -Filter command.json -Recurse |
    Where-Object { $_.Directory.Name -like 'collector-*' } | ForEach-Object {
        Get-Content -LiteralPath $_.FullName -Raw | ConvertFrom-Json
    }
$taskKnownPids = @($taskLedgers | ForEach-Object {
    $_.collector_pid
    $_.children | ForEach-Object { $_.pid }
}) + @($taskReceipts | ForEach-Object { $_.pid })
$taskObserved = @(Get-CimInstance Win32_Process | Where-Object {
    ($taskKnownPids -contains $_.ProcessId) -or
    ($_.CommandLine -and (
        $_.CommandLine.Contains((Join-Path $taskRoot '.local\d01\')) -or
        $_.CommandLine.Contains((Join-Path $taskRoot 'examples\d01\run.py')) -or
        $_.CommandLine.Contains((Join-Path $taskRoot 'examples\d01\collect.py'))
    ))
} | Select-Object ProcessId, ParentProcessId, Name, CreationDate)
$taskResult = [ordered]@{
    observed_at_utc = [DateTime]::UtcNow.ToString('o')
    script = $PSCommandPath
    cwd = (Get-Location).Path
    known_pids = @($taskKnownPids | Sort-Object -Unique)
    observed_remaining = $taskObserved
    command_lines_exported = $false
    scope = 'Known synchronous child/runner PIDs plus exact task runtime/runner paths; point-in-time observation'
}
$taskJson = $taskResult | ConvertTo-Json -Depth 7
[IO.File]::WriteAllText($taskOutput, $taskJson + [Environment]::NewLine, [Text.UTF8Encoding]::new($false))
$taskJson
if ($taskObserved.Count -ne 0) { throw 'A known PID or task path remains; inspect PID reuse before concluding.' }
