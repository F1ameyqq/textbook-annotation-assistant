"""Read-only A01 R3 archive preflight; prints JSON, runs no project code."""
import hashlib
import json
from pathlib import Path
import subprocess
from datetime import datetime, timezone

ROOT = Path('D:/1800')
EVIDENCE = ROOT / 'docs/evidence/A01/review-R3'
WORKTREE = Path('C:/Users/ASUS/.codex/worktrees/a01-source-geometry/1800')
TARGET = '180bb1e86fb2a7eb1546be85af70f466f069daf5'
REPORT = 'docs/tasks/A01-review-R3-report.md'
MANIFEST = 'docs/evidence/A01/review-R3/sha256-manifest.json'
EXPECTED_REPORT = '5fa9bb4d4cd4743fd1dfe632f73423e9d9734e5931c2b8f9fcd0f95ed2f362b1'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(*args, cwd=ROOT):
    return subprocess.check_output(['git', *args], cwd=str(cwd))


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


failures = []


def check(name, actual, expected):
    if actual != expected:
        failures.append({'check': name, 'actual': actual, 'expected': expected})


def check_records(name, records, base):
    seen = set()
    for row in records:
        rel = row['path']
        p = (base / rel).resolve()
        if not p.is_relative_to(base.resolve()):
            failures.append({'check': name + ' path escape', 'path': rel})
            continue
        check(name + ' unique ' + rel, rel not in seen, True)
        seen.add(rel)
        if not p.is_file():
            failures.append({'check': name + ' missing', 'path': rel})
            continue
        data = p.read_bytes()
        if 'bytes' in row:
            check(name + ' length ' + rel, len(data), row['bytes'])
        check(name + ' hash ' + rel, sha(data), row['sha256'])
    return len(records)


manifest = read_json(ROOT / MANIFEST)
boot = read_json(EVIDENCE / 'bootstrap.json')
inventory = read_json(EVIDENCE / 'resume-inventory.json')
closeout = read_json(EVIDENCE / 'resume-closeout-audit.json')
check('target', manifest['target_commit'], TARGET)
check('report expected hash', sha((ROOT / REPORT).read_bytes()), EXPECTED_REPORT)
manifest_count = check_records('review manifest', manifest['records'], ROOT)
check('manifest count', manifest_count, 536)
check('self exclusion', manifest['excluded_self'], MANIFEST)
check('other exclusions', manifest['other_exclusions'], [])
listed = {row['path'] for row in manifest['records']}
actual = {p.relative_to(ROOT).as_posix() for p in EVIDENCE.rglob('*') if p.is_file()}
expected = (actual - {MANIFEST}) | {REPORT}
check('coverage missing', sorted(expected - listed), [])
check('coverage excess', sorted(listed - expected), [])
ignored_run = subprocess.run(['git', 'check-ignore', '--no-index', '--stdin'],
                            input=('\n'.join(sorted(listed)) + '\n').encode(),
                            cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
check('check-ignore exit', ignored_run.returncode in (0, 1), True)
ignored = set(ignored_run.stdout.decode().splitlines())
check('ignored declaration', sorted(ignored), sorted(manifest['git_ignored_paths_still_included']))
logs = {p for p in actual if p.endswith(('.log', '.stdout.txt', '.stderr.txt', '/stdout.txt', '/stderr.txt'))}
check('logs absent from manifest', sorted(logs - listed), [])
initial_count = check_records('resume initial', inventory['records'], EVIDENCE)
old_count = check_records('older review', boot['old_review_records'], ROOT)
main_count = check_records('main readonly input', closeout['main_inputs'], ROOT)

snapshot = Path(boot['snapshot'])
snapshot_count = check_records('frozen snapshot', boot['verified_blobs'], snapshot)
tree = {}
for row in git('ls-tree', '-r', '-z', TARGET).split(b'\0'):
    if row:
        meta, path = row.split(b'\t', 1)
        mode, kind, oid = meta.split()
        check('git entry is blob ' + path.decode(), kind.decode(), 'blob')
        tree[path.decode()] = oid.decode()
check('snapshot record coverage', sorted(row['path'] for row in boot['verified_blobs']), sorted(tree))
snapshot_files = {p.relative_to(snapshot).as_posix() for p in snapshot.rglob('*') if p.is_file()}
check('snapshot disk coverage', sorted(snapshot_files), sorted(tree))
objects = sorted(set(tree.values()))
packed = git('cat-file', '--batch', cwd=ROOT) if not objects else subprocess.check_output(
    ['git', 'cat-file', '--batch'], input=('\n'.join(objects) + '\n').encode(), cwd=str(ROOT))
offset = 0
blob_hashes = {}
for expected_oid in objects:
    end = packed.index(b'\n', offset)
    oid, kind, size = packed[offset:end].decode().split()
    size = int(size)
    data = packed[end + 1:end + 1 + size]
    offset = end + 1 + size + 1
    check('batch oid ' + expected_oid, oid, expected_oid)
    check('batch type ' + oid, kind, 'blob')
    blob_hashes[oid] = (len(data), sha(data))
for row in boot['verified_blobs']:
    oid = tree[row['path']]
    check('fixed git oid ' + row['path'], row['git_blob_oid'], oid)
    check('raw git byte length/hash ' + row['path'], blob_hashes[oid], (row['bytes'], row['sha256']))

archive_path = 'docs/evidence/A01/execution/R3/archive-manifest.json'
archive = read_json(snapshot / archive_path)
execution_count = check_records('execution archive', archive['files'], snapshot)
execution_report = 'docs/tasks/A01-rework-R3-report.md'
check('execution report', sha((snapshot / execution_report).read_bytes()), boot['execution_report_sha256'])
check('execution archive sha', sha((snapshot / archive_path).read_bytes()), boot['archive_manifest_sha256'])
check('geometry', sha((snapshot / 'src/annotation/geometry/__init__.py').read_bytes()), boot['geometry_sha256'])
check('handoff', sha((ROOT / 'docs/tasks/A01-review-R3-handoff.md').read_bytes()), boot['handoff_sha256'])
check('worktree HEAD', git('rev-parse', 'HEAD', cwd=WORKTREE).decode().strip(), TARGET)
check('worktree status', git('status', '--porcelain=v1', cwd=WORKTREE).decode(), '')

original_checks = [row for row in closeout['checks'] if row['name'].startswith('original input ')]
check('original input count', len(original_checks), 31)
for row in original_checks:
    rel = row['name'][len('original input '):]
    p = snapshot / rel
    if p.is_file():
        expected_pair = row['expected']
        check('original input expected pair ' + rel, isinstance(expected_pair, list) and len(expected_pair) == 2, True)
        check('original input current ' + rel, [sha(p.read_bytes())] * 2, expected_pair)
    else:
        failures.append({'check': 'original input path unresolved', 'path': rel})

integrity = read_json(EVIDENCE / 'final-integrity.json')
report_links = integrity['report_links']
for row in report_links:
    link = row['target']
    link_path = (ROOT / REPORT).parent / link
    check('report link exists ' + link, link_path.exists(), True)

tracked = set(git('ls-files', '-z').decode().split('\0'))
output = {
    'audit_kind': 'COORDINATOR_ARCHIVE_PREFLIGHT_ONLY',
    'observed_utc': datetime.now(timezone.utc).isoformat(),
    'target_commit': TARGET,
    'root_head_observed': git('rev-parse', 'HEAD').decode().strip(),
    'report_path': REPORT,
    'report_sha256': sha((ROOT / REPORT).read_bytes()),
    'manifest_path': MANIFEST,
    'manifest_sha256': sha((ROOT / MANIFEST).read_bytes()),
    'manifest_entries': manifest_count,
    'review_evidence_files_including_manifest': len(actual),
    'manifest_tracked_paths': len(listed & tracked),
    'manifest_untracked_paths': len(listed - tracked),
    'ignored_logs_included': sorted(ignored),
    'all_logs_included_count': len(logs),
    'initial_review_files_preserved': initial_count,
    'older_review_files_preserved': old_count,
    'main_readonly_inputs_preserved': main_count,
    'frozen_files_disk_and_raw_git_exact': snapshot_count,
    'distinct_raw_git_blobs': len(objects),
    'execution_archive_entries': execution_count,
    'original_input_checks_resolved': len(original_checks),
    'report_links_checked': len(report_links),
    'worktree_head': git('rev-parse', 'HEAD', cwd=WORKTREE).decode().strip(),
    'worktree_status': git('status', '--porcelain=v1', cwd=WORKTREE).decode(),
    'failed_checks': failures,
    'functional_tests_run': 0,
    'limitations': [
        'No acceptance or integration decision is made by this preflight.',
        'Reviewer completed status is supplied by parent; process claim is documentary, not rescanned.',
        'Source/preservation historical outer launcher exit codes are absent as explicitly disclosed.',
        'New formal review files need explicit archival; ignore status is not Git persistence.'
    ]
}
print(json.dumps(output, ensure_ascii=True, indent=2))
