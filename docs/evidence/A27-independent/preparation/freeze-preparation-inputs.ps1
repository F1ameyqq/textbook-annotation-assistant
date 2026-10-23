$ErrorActionPreference = 'Stop'
$taskRoot = 'D:/1800'
$reviewRoot = 'D:/1800/docs/evidence/A27-independent/preparation'
$frozenRoot = 'D:/1800/.local/stages/a27-independent-20261023/preparation-inputs'
$utf8 = New-Object System.Text.UTF8Encoding($false)
$pairs = @(
    @('created-zone-reconciliation-review', 'a25-created-zone-reconciliation-closure'),
    @('remaining-two-actual-review', 'a25-remaining-two-actual-closure'),
    @('final-recovery-preparation-review', 'a25-final-recovery-preparation-closure'),
    @('final-recovery-actual-review', 'a25-final-five-save-readback-closure')
)
$sources = @(
    'docs/tasks/A27-stability-independent-20261023.md',
    'docs/tasks/A27-batch-stability-20261023.md'
)
$checks = @()
foreach ($pair in $pairs) {
    $reviewRelative = 'docs/evidence/A25-independent/' + $pair[0]
    $receiptRelative = 'docs/evidence/coordinator/' + $pair[1] + '/receipt.json'
    $receipt = [IO.File]::ReadAllText((Join-Path $taskRoot $receiptRelative), $utf8) | ConvertFrom-Json
    $selfPath = Join-Path $taskRoot ($reviewRelative + '/review-files.sha256')
    $selfHash = (Get-FileHash -LiteralPath $selfPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($selfHash -cne $receipt.review_manifest_sha256) { throw ('REVIEW_MANIFEST_MISMATCH: ' + $pair[0]) }
    $entries = @{}
    foreach ($line in [IO.File]::ReadAllLines($selfPath, $utf8)) {
        if ($line -match '^([a-f0-9]{64})  (.+)$') { $entries[$Matches[2]] = $Matches[1] }
    }
    foreach ($leaf in @('report.md', 'result.json', 'raw-manifest.json')) {
        $relative = $reviewRelative + '/' + $leaf
        $hash = (Get-FileHash -LiteralPath (Join-Path $taskRoot $relative) -Algorithm SHA256).Hash.ToLowerInvariant()
        if (-not $entries.ContainsKey($leaf) -or $hash -cne $entries[$leaf]) { throw ('FIXED_MEMBER_MISMATCH: ' + $relative) }
        if ($leaf -eq 'result.json' -and $hash -cne $receipt.machine_result.sha256) { throw ('ROOT_RESULT_MISMATCH: ' + $relative) }
        if ($leaf -eq 'raw-manifest.json' -and $hash -cne $receipt.raw_manifest_sha256) { throw ('ROOT_RAW_MANIFEST_MISMATCH: ' + $relative) }
        $checks += [pscustomobject]@{ relative_path=$relative; sha256=$hash; fixed_review_manifest_match=$true }
        $sources += $relative
    }
    $sources += $reviewRelative + '/review-files.sha256'
    $sources += $receiptRelative
}
if (Test-Path -LiteralPath $frozenRoot) { throw 'FROZEN_DESTINATION_EXISTS_NO_OVERWRITE' }
[IO.Directory]::CreateDirectory($frozenRoot) | Out-Null
$members = @()
foreach ($relative in $sources) {
    $source = Join-Path $taskRoot $relative
    $destination = Join-Path $frozenRoot $relative
    [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($destination)) | Out-Null
    $before = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant()
    [IO.File]::Copy($source, $destination, $false)
    $after = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant()
    $copy = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($before -cne $after -or $before -cne $copy) { throw ('COPY_OR_SOURCE_CHANGED: ' + $relative) }
    $members += [pscustomobject]@{ source=$source; copy=$destination; bytes=(Get-Item -LiteralPath $source).Length; sha256=$before }
}
$manifest = [ordered]@{
    schema='A27IndependentPreparationInputManifest/v1'
    at_utc=[DateTimeOffset]::UtcNow.ToString('o')
    status='PUBLIC_FIXED_REFERENCE_INPUTS_VERIFIED'
    members=$members
    reference_member_checks=$checks
    root_review_manifest_checks=$pairs.Count
    source_copy_checks=$members.Count
    underlying_a25_private_raw_reverified=$false
    a27_candidate_received=$false
    real_profile_or_ledger_read=$false
}
[IO.File]::WriteAllText((Join-Path $reviewRoot 'input-manifest.json'), (($manifest | ConvertTo-Json -Depth 10) + "`n"), $utf8)
[ordered]@{ status=$manifest.status; copied=$members.Count; report_result_raw_manifest_checks=$checks.Count; root_review_manifest_checks=$pairs.Count; candidate_received=$false; product_tests_run=0 } | ConvertTo-Json -Compress
