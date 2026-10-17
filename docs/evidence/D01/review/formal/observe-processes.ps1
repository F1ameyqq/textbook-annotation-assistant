$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$workspace = [System.IO.Path]::GetFullPath((Join-Path $root '../../../../../'))
$receipt = Get-Content -LiteralPath (Join-Path $root 'receipt.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$records = @(Get-Content -LiteralPath (Join-Path $root 'commands.json') -Raw -Encoding UTF8 | ConvertFrom-Json)
$records += @(Get-Content -LiteralPath (Join-Path $root 'resume01/commands.json') -Raw -Encoding UTF8 | ConvertFrom-Json)
$outers = @(
    (Get-Content -LiteralPath (Join-Path $root 'collector-run01/command.json') -Raw -Encoding UTF8 | ConvertFrom-Json),
    (Get-Content -LiteralPath (Join-Path $root 'collector-resume01/command.json') -Raw -Encoding UTF8 | ConvertFrom-Json)
)
$known = @{}
foreach($record in $records) { $known[[int]$record.pid] = [double]$record.finished_unix }
foreach($outer in $outers) {
    $known[[int]$outer.pid] = [double]$outer.finished_unix
    $known[[int]$outer.collector_pid] = [double]$outer.finished_unix
}
$paths = @($receipt.exclusive_stage, $receipt.outside_root, $root)
$observed = @()
$reused = @()
foreach($process in (Get-CimInstance Win32_Process)) {
    if ($process.ProcessId -eq $PID) { continue }
    $knownPid = $known.ContainsKey([int]$process.ProcessId)
    $pathMatch = $false
    if($process.CommandLine) {
        foreach($path in $paths) {
            if($process.CommandLine.IndexOf($path,[System.StringComparison]::OrdinalIgnoreCase) -ge 0 -or
               $process.CommandLine.IndexOf($path.Replace('/','\'),[System.StringComparison]::OrdinalIgnoreCase) -ge 0) { $pathMatch=$true }
        }
    }
    if(-not ($knownPid -or $pathMatch)) { continue }
    $created = if($process.CreationDate) { ([DateTimeOffset]$process.CreationDate).ToUnixTimeMilliseconds()/1000.0 } else { $null }
    $item = [ordered]@{ pid=$process.ProcessId; name=$process.Name; parent_pid=$process.ParentProcessId; task_path_match=$pathMatch; known_pid=$knownPid; creation_unix=$created }
    if($knownPid -and -not $pathMatch -and $null -ne $created -and $created -gt $known[[int]$process.ProcessId]) { $reused += $item }
    else { $observed += $item }
}
$result = [ordered]@{
    observed_at_utc = [DateTimeOffset]::UtcNow.ToString('o'); current_shell_pid_excluded=$PID
    known_synchronous_pid_count=$known.Count; all_recorded_commands_returned=@($records | Where-Object { -not $_.synchronous_return }).Count -eq 0
    outer_receipts=@($outers | Select-Object pid,collector_pid,synchronous_return,exit_code)
    observed_remaining=$observed; known_pid_reused=$reused; command_lines_exported=$false
    scope='Known synchronous child/runner PIDs and exact unique runtime/collector paths; point-in-time observation only.'
}
$utf8=[System.Text.UTF8Encoding]::new($false)
[System.IO.File]::WriteAllText((Join-Path $root 'process-observation.json'),(ConvertTo-Json -InputObject $result -Depth 15)+"`n",$utf8)
$result | ConvertTo-Json -Depth 15
if($observed.Count -ne 0) { throw 'Potential remaining task process; reconcile before final conclusion.' }
