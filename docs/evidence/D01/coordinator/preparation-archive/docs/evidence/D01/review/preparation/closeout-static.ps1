param([string]$Workspace = 'C:\Users\ASUS\.codex\worktrees\d01-review-preparation\1800')
$ErrorActionPreference = 'Stop'
$utf8 = [System.Text.UTF8Encoding]::new($false)
$preparation = Join-Path $Workspace 'docs/evidence/D01/review/preparation'
$reportRelative = 'docs/tasks/D01-review-preparation.md'
$report = Join-Path $Workspace $reportRelative
$closeout = Join-Path $preparation 'static-closeout.json'
$manifest = Join-Path $preparation 'sha256-manifest.json'
if ((Test-Path -LiteralPath $closeout) -or (Test-Path -LiteralPath $manifest)) { throw 'Closeout already exists; do not overwrite preparation evidence.' }
function Write-Json($Path, $Value) {
    [System.IO.File]::WriteAllText($Path, (ConvertTo-Json -InputObject $Value -Depth 50) + "`n", $utf8)
}
function Sha($Path) { return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() }
function Rel($Path) { return $Path.Substring($Workspace.Length + 1).Replace('\','/') }
function Git-Read([string[]]$GitArgs) {
    $output = & git -C $Workspace @GitArgs 2>&1
    $code = $LASTEXITCODE
    if ($code -ne 0) { throw ('Static Git scope read failed: ' + ($GitArgs -join ' ')) }
    return @($output | ForEach-Object { [string]$_ })
}
$indexPath = Join-Path $preparation 'input-index.json'
if ((Sha $indexPath) -ne '0ec3377b293c6ded8a7d339877e3842df5bd132e7a9a67d2dacde33f07b733e7') { throw 'Input index changed.' }
$index = Get-Content -LiteralPath $indexPath -Raw -Encoding UTF8 | ConvertFrom-Json
$matrix = Get-Content -LiteralPath (Join-Path $preparation 'verification-matrix.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if (@($matrix.results).Count -ne 16) { throw 'Unexpected matrix row count.' }
foreach ($row in $matrix.results) {
    if (($row.result -ne 'NOT_RUN') -or (@($row.evidence).Count -ne 0)) { throw ('Premature runtime result: ' + $row.id) }
}
if ($matrix.formal_dispatch_received -or $matrix.frozen_delivery_commit) { throw 'Preparation must not invent a frozen target.' }
$materialized = @()
foreach ($entry in $index.entries) {
    if ($entry.snapshot_path) {
        $path = Join-Path $preparation $entry.snapshot_path
        if ((Sha $path) -ne $entry.sha256) { throw ('Raw input copy changed: ' + $entry.snapshot_path) }
        if ((Get-Item -LiteralPath $path).Length -ne $entry.bytes) { throw 'Input copy length mismatch.' }
        $materialized += $entry.snapshot_path
    }
    if ($entry.functional_result -ne 'NOT_RUN') { throw 'Input identity is not functional evidence.' }
}
$bundleInputs = @($index.entries | Where-Object role -eq 'FROZEN_R3_FINITE_BUNDLE_PLANNED_INPUT')
$assets = @($bundleInputs | Where-Object repository_path -Match '/assets/')
if (($bundleInputs.Count -ne 29) -or ($assets.Count -ne 8)) { throw 'Unexpected fixed R3 inventory.' }
if (@($bundleInputs | Where-Object snapshot_path).Count -ne 0) { throw 'R3 bundles should remain index-only in preparation.' }
$gitCapture = Get-Content -LiteralPath (Join-Path $preparation 'static-git-commands.json') -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($command in $gitCapture.commands) {
    if (($command.exit_code -ne 0) -or (-not $command.synchronous_process_returned)) { throw 'Incomplete static capture process.' }
}
$head = (Git-Read @('rev-parse','HEAD')) -join ''
if ($head -ne 'f15f7bc03fac8994ade1642fa7547cbd823c6d43') { throw 'Review preparation worktree HEAD changed.' }
$branch = (Git-Read @('branch','--show-current')) -join ''
$tracked = Git-Read @('diff','--name-only','HEAD')
if ($tracked.Count -ne 0) { throw 'Tracked file changed in preparation worktree.' }
$untracked = Git-Read @('ls-files','--others','--exclude-standard')
foreach ($path in $untracked) {
    if (($path -ne $reportRelative) -and (-not $path.StartsWith('docs/evidence/D01/review/preparation/'))) { throw ('Out-of-scope new file: ' + $path) }
}
$text = Get-Content -LiteralPath $report -Raw -Encoding UTF8
$links = @()
foreach ($match in [regex]::Matches($text,'\[[^\]]+\]\(([^)]+)\)')) {
    $relative = $match.Groups[1].Value
    $absolute = [System.IO.Path]::GetFullPath((Join-Path ([System.IO.Path]::GetDirectoryName($report)) $relative))
    $pending = ($absolute -eq $closeout) -or ($absolute -eq $manifest)
    if ((-not (Test-Path -LiteralPath $absolute)) -and (-not $pending)) { throw ('Missing report link: ' + $relative) }
    $links += [ordered]@{ target = $relative; repository_path = Rel $absolute; exists_or_created_in_this_closeout = $true }
}
$ownFiles = @($report) + @(
    (Join-Path $preparation 'capture-static.ps1'), (Join-Path $preparation 'closeout-static.ps1'),
    (Join-Path $preparation 'verification-matrix.json')
)
foreach ($file in $ownFiles) {
    $content = [System.IO.File]::ReadAllText($file, $utf8)
    if ($content -match '(?m)[ \t]+\r?$') { throw ('Trailing whitespace: ' + (Rel $file)) }
    if (-not $content.EndsWith("`n")) { throw ('Missing final newline: ' + (Rel $file)) }
}
$processMatches = @(
    Get-CimInstance Win32_Process | Where-Object {
        $_.ProcessId -ne $PID -and
        $_.Name -in @('python.exe','pythonw.exe','git.exe','powershell.exe','pwsh.exe','cmd.exe','msedge.exe','chrome.exe') -and
        $_.CommandLine -and (
            $_.CommandLine.IndexOf($Workspace,[System.StringComparison]::OrdinalIgnoreCase) -ge 0 -or
            $_.CommandLine.IndexOf($Workspace.Replace('\','/'),[System.StringComparison]::OrdinalIgnoreCase) -ge 0
        )
    } | ForEach-Object { [ordered]@{ pid = $_.ProcessId; name = $_.Name; parent_pid = $_.ParentProcessId } }
)
Write-Json $closeout ([ordered]@{
    schema = 'D01-static-preparation-closeout-v1'; observed_at_utc = [DateTimeOffset]::UtcNow.ToString('o')
    status = 'PREPARED_WAITING_EXECUTION'; functional_result = 'NOT_RUN'
    workspace = $Workspace; worktree_head = $head; branch = $branch
    input_index_sha256 = Sha $indexPath; fixed_inputs = @($index.entries).Count
    verified_raw_document_copies = $materialized.Count; index_only_R3_files = $bundleInputs.Count
    indexed_R3_assets = $assets.Count; matrix_rows = @($matrix.results).Count; all_matrix_results_NOT_RUN = $true
    captured_git_commands = @($gitCapture.commands).Count; captured_git_processes_returned = $true
    tracked_changes = @($tracked); untracked_files_at_scope_check = @($untracked)
    allowed_new_paths = @($reportRelative,'docs/evidence/D01/review/preparation/**')
    report_links = $links; authored_document_whitespace_check = 'PASS_STATIC_ONLY'
    pending_created_links = @('static-closeout.json','sha256-manifest.json')
    process_observation = [ordered]@{
        current_shell_pid_excluded = $PID; task_path_matching_processes = $processMatches
        scope = 'Only selected executable names with this unique worktree path; no claim about other tasks or whole-machine state.'
        no_background_processes_started_by_this_preparation = $true
    }
    actual_functional_work = [ordered]@{
        venvs_created = 0; builds = 0; installs = 0; runtime_imports = 0; consumers = 0
        image_decodes = 0; negative_probes = 0; tests = 0; execution_thread_reads = 0
        execution_thread_messages = 0; execution_progress_polls = 0; platform_browser_credential_model_B_access = 0
    }
    commit_merge_push_performed = $false
    conclusion = 'Preparation only; end turn and await formal coordinator dispatch.'
})
$files = @((Get-Item -LiteralPath $report)) + @(Get-ChildItem -LiteralPath $preparation -Recurse -File -Force)
$fileEntries = @($files | Sort-Object FullName | ForEach-Object {
    [ordered]@{ path = Rel $_.FullName; bytes = $_.Length; sha256 = Sha $_.FullName }
})
Write-Json $manifest ([ordered]@{
    schema = 'D01-preparation-sha256-v1'; date = '2026-10-17'; timezone = 'Asia/Shanghai'
    status = 'PREPARED_WAITING_EXECUTION'; functional_result = 'NOT_RUN'
    workflow_commit = $index.workflow_commit; product_base_commit = $index.product_base_commit
    excludes = @('docs/evidence/D01/review/preparation/sha256-manifest.json')
    includes_ignored_files_by_filesystem_enumeration = $true
    entries = $fileEntries
})
foreach ($link in $links) {
    if (-not (Test-Path -LiteralPath (Join-Path $Workspace $link.repository_path))) { throw 'Final link target absent.' }
}
foreach ($entry in $fileEntries) {
    if ((Sha (Join-Path $Workspace $entry.path)) -ne $entry.sha256) { throw 'Manifest readback mismatch.' }
}
[pscustomobject]@{
    result = 'STATIC_PREPARATION_COMPLETE'; functional_result = 'NOT_RUN'
    report_sha256 = Sha $report; manifest_sha256 = Sha $manifest
    manifest_entries = $fileEntries.Count; report_links = $links.Count
    task_path_matching_processes = $processMatches.Count; branch = $branch
} | ConvertTo-Json
