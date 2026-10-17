"""Read-only integrity check for the integration-R1 REWORK review archive."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import re
import subprocess

ROOT = Path('D:/1800')
PREFIX = 'docs/evidence/A01/review-integration-R1/'
E = ROOT / PREFIX
REPORT = 'docs/tasks/A01-integration-R1-review-report.md'
MANIFEST = PREFIX + 'sha256-manifest.json'
EXPECTED_REPORT = '2aaed84505799509319cab8e99a94eba818b69fd301caf4d3be89fe48c6a3caf'
EXPECTED_MANIFEST = 'a331ad8a039408f2225f9e9842cc0a4d0860af7a0ece67f3fafa527f0c6600ad'
TARGET = '5f872150a237b195f73c78e02e13a91d2f4f46a7'
failures = []

def sha(b):
    return hashlib.sha256(b).hexdigest()

def load(rel):
    return json.loads((E / rel).read_text(encoding='utf-8-sig'))

def check(name, actual, expected):
    if actual != expected:
        failures.append({'check': name, 'actual': actual, 'expected': expected})

def safe_path(rel, root=ROOT):
    path = root / rel
    if Path(rel).is_absolute() or not path.resolve().is_relative_to(root.resolve()):
        failures.append({'check': 'unsafe path', 'path': rel})
        return None
    return path

def check_records(label, records):
    seen = set()
    for row in records:
        path = safe_path(row['path'])
        check(label + ' unique ' + row['path'], row['path'].casefold() not in seen, True)
        seen.add(row['path'].casefold())
        if path is None:
            continue
        if not path.is_file():
            failures.append({'check': label + ' file missing', 'path': row['path']})
            continue
        data = path.read_bytes()
        check(label + ' bytes ' + row['path'], len(data), row['bytes'])
        check(label + ' hash ' + row['path'], sha(data), row['sha256'])

report_data = (ROOT / REPORT).read_bytes()
manifest_data = (ROOT / MANIFEST).read_bytes()
check('report identity', sha(report_data), EXPECTED_REPORT)
check('manifest identity', sha(manifest_data), EXPECTED_MANIFEST)
m = json.loads(manifest_data)
check('target commit', m['final_commit'], TARGET)
check('outcome', m['outcome'], 'REWORK')
check('self excluded', m['self_excluded'], MANIFEST)
check('other exclusions', m['other_exclusions'], [])
check_records('archive', m['files'])
listed = {x['path'] for x in m['files']}
disk_files = {p.relative_to(ROOT).as_posix() for p in E.rglob('*') if p.is_file()}
expected = (disk_files - {MANIFEST}) | {REPORT}
check('coverage missing', sorted(expected - listed), [])
check('coverage excess', sorted(listed - expected), [])
check('archive count', len(m['files']), 226)
check('archive allowed paths', sorted(p for p in listed if p != REPORT and not p.startswith(PREFIX)), [])
ignored_process = subprocess.run(['git', 'check-ignore', '--no-index', '-z', '--stdin'], cwd=str(ROOT),
    input=('\0'.join(sorted(listed)) + '\0').encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
check('ignore query exit', ignored_process.returncode in (0, 1), True)
ignored = set(ignored_process.stdout.decode().split('\0')) - {''}
declared_ignored = {x['path'] for x in m['files'] if x['git_ignored']}
check('ignored flags match', sorted(ignored), sorted(declared_ignored))
check('ignored inventory', sorted(ignored), sorted(load('git-ignored-paths.json')['ignored_paths']))
historical = load('historical-before.json')['files']
excluded_shared = {'docs/coordination.md', 'docs/coordination-state.json'}
protected = [x for x in historical if x['path'] not in excluded_shared]
check_records('historical', protected)

links = re.findall(r'\]\(([^)]+)\)', report_data.decode('utf-8-sig'))
for link in links:
    if '://' not in link and not link.startswith('#'):
        check('report link ' + link, ((ROOT / REPORT).parent / link.split('#', 1)[0]).exists(), True)
integrity = load('final-integrity.json')
check('final integrity target report', integrity['report_sha256'], EXPECTED_REPORT)
check('final integrity outcome', integrity['outcome'], 'REWORK')
check('mandatory failure', integrity['mandatory_failure'], 'I1-GIT-01')
check('release statement', integrity['owned_sessions_to_release'], 0)
process = load('process-check.json')
check('saved process matches', process['matched_count'], 0)
check('saved owned sessions', process['owned_tool_sessions_still_running'], [])

no_git = load('git-availability/minimal-without-git/command.json')
with_git = load('git-availability/minimal-with-git/command.json')
full_git = load('git-availability/raw-full-with-git/command.json')
for key in ('argv', 'cwd', 'PYTHONPATH', 'has_dot_git', 'observer'):
    check('minimal controlled comparison ' + key, no_git[key], with_git[key])
check('minimal no Git exit', no_git['exit_code'], 1)
check('minimal with Git exit', with_git['exit_code'], 0)
check('no Git executable', no_git['git_executable'], None)
check('with Git executable', bool(with_git['git_executable']), True)
check('no repository metadata', no_git['has_dot_git'], False)
check('limited PATH', no_git['PATH'], 'C:\\Windows\\System32;C:\\Windows')
error_bytes = (E / 'git-availability/minimal-without-git/stderr.txt').read_bytes()
error = error_bytes.decode('gbk')
for marker in ('FileNotFoundError', 'WinError 2', 'identity.py', 'test_export_subdirectory_cannot_borrow_enclosing_git_head'):
    check('failure log marker ' + marker, marker in error, True)
check('full raw with Git exit', full_git['exit_code'], 0)
check('entry exits agree', integrity['entry_exits'], {'checkout_with_git': 0, 'raw_without_git': 1, 'raw_with_git': 0})
minimal_inputs = load('minimal-reproducer-inputs.json')
for row in minimal_inputs:
    p = safe_path(row['path'], E)
    if p is None:
        continue
    raw = subprocess.check_output(['git', 'cat-file', 'blob',
        '2078731114ad3a07368ca46a2f34c3544af64e2b:' + row['source']], cwd=str(ROOT))
    check('minimal input disk hash ' + row['source'], sha(p.read_bytes()), row['sha256'])
    check('minimal input Git hash ' + row['source'], sha(raw), row['sha256'])

print(json.dumps({
    'audit_kind': 'BOUNDED_REWORK_ARCHIVE_PREFLIGHT',
    'checked_at_utc': datetime.now(timezone.utc).isoformat(),
    'target_commit': TARGET,
    'report_path': REPORT, 'report_sha256': sha(report_data),
    'manifest_path': MANIFEST, 'manifest_sha256': sha(manifest_data),
    'manifest_entries': len(m['files']),
    'evidence_files_including_manifest': len(disk_files),
    'report_in_manifest': REPORT in listed,
    'ignored_files_actual': sorted(ignored),
    'protected_historical_files_checked': len(protected),
    'shared_coordination_excluded_from_global_unchanged_claim': sorted(excluded_shared),
    'report_links_checked': len(links),
    'I1_GIT_01': {'minimal_no_git_exit': no_git['exit_code'], 'minimal_with_git_exit': with_git['exit_code'],
        'full_raw_with_git_exit': full_git['exit_code'], 'same_argv_cwd_pythonpath': True,
        'minimal_inputs_bound_to_git': len(minimal_inputs), 'stderr_encoding': 'gbk',
        'stderr_original_bytes': len(error_bytes), 'stderr_original_sha256': sha(error_bytes)},
    'release_check_saved_at': process['checked_at'],
    'saved_task_path_matches': process['matched_count'],
    'failed_checks': failures,
    'functional_tests_or_reproductions_run': 0,
    'limits': ['No acceptance, repair, staging, commit or integration decision.',
        'Saved OS task-path check is time-scoped; this preflight did not rescan processes.',
        'Other tasks and live shared coordination files are outside the unchanged claim.',
        'Negative collector outer exit 0 is not listed in collection-receipts.json; requires its separate tool receipt.',
        'I04 nonblocking redundant reference label omission and collection stdout limitation remain disclosed.']
}, ensure_ascii=True, indent=2))
