param(
    [string]$Repository = 'D:\1800',
    [string]$PreparationRoot = $PSScriptRoot
)
$ErrorActionPreference = 'Stop'
$workflow = 'f15f7bc03fac8994ade1642fa7547cbd823c6d43'
$productBase = 'c6bebdf43eb93f7a6ae21e96ec07ed155686777d'
$utf8 = [System.Text.UTF8Encoding]::new($false)
$records = [System.Collections.Generic.List[object]]::new()
$entries = [System.Collections.Generic.List[object]]::new()
$indexFile = Join-Path $PreparationRoot 'input-index.json'
if (Test-Path -LiteralPath $indexFile) { throw 'Refusing to overwrite an existing preparation capture.' }
[void][System.IO.Directory]::CreateDirectory($PreparationRoot)

function Hash-Bytes([byte[]]$Bytes) {
    $hasher = [System.Security.Cryptography.SHA256]::Create()
    try { return ([System.BitConverter]::ToString($hasher.ComputeHash($Bytes))).Replace('-', '').ToLowerInvariant() }
    finally { $hasher.Dispose() }
}
function Write-Json($Path, $Value) {
    [System.IO.File]::WriteAllText($Path, (ConvertTo-Json -InputObject $Value -Depth 50) + "`n", $utf8)
}
function Read-Git([string[]]$GitArgs) {
    foreach ($arg in $GitArgs) { if ($arg.Contains('"')) { throw 'Unexpected quotation mark in a Git argument.' } }
    $info = [System.Diagnostics.ProcessStartInfo]::new()
    $info.FileName = 'git'
    $info.Arguments = ($GitArgs | ForEach-Object { '"' + $_ + '"' }) -join ' '
    $info.WorkingDirectory = $Repository
    $info.UseShellExecute = $false
    $info.CreateNoWindow = $true
    $info.RedirectStandardOutput = $true
    $info.RedirectStandardError = $true
    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $info
    $start = [DateTimeOffset]::UtcNow.ToString('o')
    [void]$process.Start()
    $stderrTask = $process.StandardError.ReadToEndAsync()
    $stream = [System.IO.MemoryStream]::new()
    $process.StandardOutput.BaseStream.CopyTo($stream)
    $process.WaitForExit()
    $bytes = $stream.ToArray()
    $stderr = $stderrTask.GetAwaiter().GetResult()
    $record = [ordered]@{
        argv = @('git') + $GitArgs; cwd = $Repository; pid = $process.Id
        started_at_utc = $start; completed_at_utc = [DateTimeOffset]::UtcNow.ToString('o')
        exit_code = $process.ExitCode; stdout_bytes = $bytes.Length
        stdout_sha256 = Hash-Bytes $bytes; stderr = $stderr
        synchronous_process_returned = $true
        operation = 'STATIC_GIT_OBJECT_READ_ONLY'
    }
    if ($GitArgs[0] -ne 'cat-file') { $record.stdout_utf8 = $utf8.GetString($bytes) }
    $records.Add($record)
    $code = $process.ExitCode
    $process.Dispose()
    $stream.Dispose()
    if ($code -ne 0) { throw ('Git read failed: ' + ($GitArgs -join ' ')) }
    return [pscustomobject]@{ Bytes = $bytes; Text = $utf8.GetString($bytes) }
}
function Capture-Input([string]$Commit, [string]$Path, [string]$Role, [bool]$Materialize) {
    $identity = (Read-Git @('rev-parse', ($Commit + ':' + $Path))).Text.Trim()
    $blob = Read-Git @('cat-file', 'blob', $identity)
    $snapshot = $null
    if ($Materialize) {
        $group = if ($Commit -eq $workflow) { 'workflow' } else { 'product-base' }
        $snapshot = 'inputs/' + $group + '/' + $Path
        $target = Join-Path $PreparationRoot $snapshot
        [void][System.IO.Directory]::CreateDirectory([System.IO.Path]::GetDirectoryName($target))
        [System.IO.File]::WriteAllBytes($target, $blob.Bytes)
    }
    $entries.Add([ordered]@{
        source_commit = $Commit; repository_path = $Path; git_blob_oid = $identity
        sha256 = Hash-Bytes $blob.Bytes; bytes = $blob.Bytes.Length; role = $Role
        byte_representation = 'RAW_GIT_BLOB_NO_NEWLINE_TRANSFORMATION'
        snapshot_path = $snapshot
        materialization = $(if ($Materialize) { 'RAW_DOCUMENT_COPY' } else { 'INDEX_ONLY_NOT_CONSUMED' })
        functional_result = 'NOT_RUN'
    })
}

$workflowTree = (Read-Git @('rev-parse', ($workflow + '^{tree}'))).Text.Trim()
$baseTree = (Read-Git @('rev-parse', ($productBase + '^{tree}'))).Text.Trim()
$head = (Read-Git @('rev-parse', 'HEAD')).Text.Trim()
$workflowDocs = @(
    'AGENTS.md', 'docs/architecture.md', 'docs/contracts-v1.md', 'docs/coordination.md',
    'docs/tasks/D01-independent-review.md', 'docs/tasks/D01-dependency-implementation.md',
    'docs/tasks/D01-dependency-preparation.md', 'docs/tasks/A01-review-R3-report.md',
    'docs/tasks/A01-integration-R2-review-report.md',
    'docs/tasks/A01-integration-R2-coordinator-acceptance.md'
)
foreach ($path in $workflowDocs) { Capture-Input $workflow $path 'FIXED_WORKFLOW_OR_ACCEPTED_A01_DOCUMENT' $true }
$baseDocs = @(
    'pyproject.toml', 'examples/a01/consume.py', 'examples/a01/R3/README.md',
    'src/annotation/source/static/importer.py', 'src/annotation/source/static/consistency.py',
    'tests/test_contracts.py', 'tests/test_contracts_platform_refs.py', 'tests/test_a01_source.py'
)
foreach ($path in $baseDocs) { Capture-Input $productBase $path 'FIXED_PRODUCT_BASE_STATIC_REFERENCE' $true }
$bundlePaths = (Read-Git @('ls-tree', '-r', '--name-only', $productBase, 'examples/a01/R3/bundles')).Text.Trim() -split "`n"
foreach ($pathValue in $bundlePaths) {
    $path = $pathValue.TrimEnd("`r")
    Capture-Input $productBase $path 'FROZEN_R3_FINITE_BUNDLE_PLANNED_INPUT' $false
}
$sourceTree = Read-Git @('ls-tree', '-r', $productBase, 'src/annotation')
[System.IO.File]::WriteAllBytes((Join-Path $PreparationRoot 'base-source-tree.txt'), $sourceTree.Bytes)
Write-Json $indexFile ([ordered]@{
    schema = 'D01-static-preparation-inputs-v1'; date = '2026-10-17'; timezone = 'Asia/Shanghai'
    status = 'PREPARED_WAITING_EXECUTION'; functional_result = 'NOT_RUN'
    workflow_commit = $workflow; workflow_tree = $workflowTree
    product_base_commit = $productBase; product_base_tree = $baseTree
    observed_primary_head = $head; observed_primary_head_used_as_target = $false
    frozen_delivery_commit = $null; implementation_commit = $null
    execution_report_sha256 = $null; execution_manifest_sha256 = $null
    execution_session_release_evidence = $null
    byte_capture = 'Process.StandardOutput.BaseStream -> MemoryStream -> SHA256 / optional WriteAllBytes'
    entries = @($entries.ToArray())
})
Write-Json (Join-Path $PreparationRoot 'static-git-commands.json') ([ordered]@{
    operation = 'STATIC_PREPARATION_ONLY'; all_processes_synchronous = $true
    functional_commands = 0; installs = 0; venvs_created = 0; tests = 0
    commands = @($records.ToArray())
})
[pscustomobject]@{
    input_count = $entries.Count; bundle_file_count = $bundlePaths.Count
    git_commands = $records.Count; workflow_tree = $workflowTree; product_base_tree = $baseTree
    input_index_sha256 = (Get-FileHash -LiteralPath $indexFile -Algorithm SHA256).Hash.ToLowerInvariant()
    functional_result = 'NOT_RUN'
} | ConvertTo-Json
