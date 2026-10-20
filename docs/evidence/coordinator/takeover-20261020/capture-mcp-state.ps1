param([Parameter(Mandatory=$true)][string]$OutputName)
$ErrorActionPreference = 'Stop'
$evidenceRoot = 'D:\1800\docs\evidence\coordinator\takeover-20261020'
if ($OutputName -notmatch '^[a-z0-9-]+\.json$') { throw 'Invalid output name' }
$allProcesses = @(Get-CimInstance Win32_Process)
$mcpProcesses = @($allProcesses | Where-Object { $_.Name -eq 'node.exe' -and $_.CommandLine -match 'playwright' })
$ids = @($mcpProcesses | ForEach-Object { $_.ProcessId })
$connections = @(Get-NetTCPConnection -ErrorAction SilentlyContinue | Where-Object { $_.OwningProcess -in $ids } | ForEach-Object {
  [ordered]@{ pid=$_.OwningProcess; state=$_.State.ToString(); local_address=$_.LocalAddress; local_port=$_.LocalPort; remote_address=$_.RemoteAddress; remote_port=$_.RemotePort }
})
$mcp = @($mcpProcesses | ForEach-Object {
  $p = $_
  $chain = @()
  $walk = $p
  for($depth=0; $depth -lt 5 -and $null -ne $walk; $depth++) {
    $chain += [ordered]@{ pid=$walk.ProcessId; parent=$walk.ParentProcessId; name=$walk.Name; creation_time=$walk.CreationDate.ToString('o') }
    $parentId = $walk.ParentProcessId
    $walk = $allProcesses | Where-Object { $_.ProcessId -eq $parentId } | Select-Object -First 1
  }
  [ordered]@{ pid=$p.ProcessId; parent=$p.ParentProcessId; creation_time=$p.CreationDate.ToString('o'); extension_mode=($p.CommandLine -match '--extension'); is_cli=($p.CommandLine -match '[\\/]cli\.js'); ancestors=$chain }
})
$edgeRoots = @($allProcesses | Where-Object { $_.Name -eq 'msedge.exe' -and $_.CommandLine -notmatch '--type=' } | ForEach-Object {
  [ordered]@{pid=$_.ProcessId; parent=$_.ParentProcessId; creation_time=$_.CreationDate.ToString('o')}
})
$record = [ordered]@{ at=(Get-Date -Format o); coordinator_thread_id='01a15768-1e2d-7781-b29f-1f7376270216'; mcp_processes=$mcp; mcp_tcp_connections=$connections; edge_roots=$edgeRoots; pid_to_thread_mapping='NOT_PROVEN'; process_changes_by_this_script=0; scope='Instantaneous sanitized metadata only; no command-line URLs, tokens, credentials or browser state' }
$json = $record | ConvertTo-Json -Depth 15
[System.IO.File]::WriteAllText((Join-Path $evidenceRoot $OutputName), $json + "`n", [System.Text.UTF8Encoding]::new($false))
[ordered]@{output=$OutputName; mcp_process_count=$mcp.Count; mcp_tcp_connection_count=$connections.Count; edge_root_count=$edgeRoots.Count} | ConvertTo-Json -Compress
