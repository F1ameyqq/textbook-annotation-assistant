"""Read-only frozen-delivery integrity preflight. No project code is executed."""
from pathlib import Path
from datetime import datetime, timezone
import base64
import hashlib
import json
import subprocess

ROOT = Path('D:/1800')
WT = Path('C:/Users/ASUS/.codex/worktrees/a01-source-geometry/1800')
BASE = '180bb1e86fb2a7eb1546be85af70f466f069daf5'
PATCH = 'f8f2981a815f96147144d3747d26752b564cc9f7'
FINAL = '5f872150a237b195f73c78e02e13a91d2f4f46a7'
EVIDENCE = 'docs/evidence/A01/execution/integration-R1/'
MANIFEST = EVIDENCE + 'archive-manifest.json'
REPORT = 'docs/tasks/A01-integration-R1-execution-report.md'
MUTABLE = 'tests/test_a01_rework_r3.py'
failures = []

def sha(data):
    return hashlib.sha256(data).hexdigest()

def git(*args):
    return subprocess.check_output(['git', *args], cwd=str(WT))

def check(label, actual, expected):
    if actual != expected:
        failures.append({'check': label, 'actual': actual, 'expected': expected})

def load(path):
    return json.loads((WT / path).read_text(encoding='utf-8-sig'))

def tree(commit):
    result = {}
    for row in git('ls-tree', '-r', '-z', commit).split(b'\0'):
        if row:
            meta, path = row.split(b'\t', 1)
            result[path.decode()] = meta.decode().split()[2]
    return result

def blob(commit, path):
    return git('cat-file', 'blob', commit + ':' + path)

check('HEAD', git('rev-parse', 'HEAD').decode().strip(), FINAL)
check('worktree clean', git('status', '--porcelain=v1').decode(), '')
for parent, child in [(BASE, PATCH), (PATCH, FINAL)]:
    rc = subprocess.run(['git', 'merge-base', '--is-ancestor', parent, child], cwd=str(WT)).returncode
    check('ancestor ' + parent + ' of ' + child, rc, 0)
old_tree, new_tree = tree(BASE), tree(FINAL)
changes = git('diff', '--name-status', BASE, FINAL).decode().splitlines()
changed = {line.split('\t', 1)[1] for line in changes}
allowed_exact = {MUTABLE, 'tests/test_a01_integration_r1.py', REPORT}
allowed_prefix = (EVIDENCE, 'examples/a01/integration-R1/', 'tests/fixtures/a01/integration-R1/')
check('out of scope', sorted(p for p in changed if p not in allowed_exact and not p.startswith(allowed_prefix)), [])
check('modified old paths', sorted(p for p in old_tree if old_tree[p] != new_tree.get(p)), [MUTABLE])
check('attribute mutations', sorted(p for p in changed if p.endswith('.gitattributes')), [])
package = git('diff', '--name-status', PATCH, FINAL).decode().splitlines()
check('packaging only adds report/evidence', all(line.startswith('A\t') and
      (line[2:] == REPORT or line[2:].startswith(EVIDENCE)) for line in package), True)
manifest = load(MANIFEST)
check('manifest base', manifest['base_commit'], BASE)
check('manifest patch', manifest['patch_commit'], PATCH)
check('manifest main', manifest['main_parent'], '4946b8ab307f88bdc25c14ace5ead774e3119fc5')
listed = set()
for row in manifest['files']:
    path = row['path']
    check('unique manifest ' + path, path not in listed, True)
    listed.add(path)
    if path not in new_tree:
        failures.append({'check': 'manifest missing Git path', 'path': path})
        continue
    disk, raw = (WT / path).read_bytes(), blob(FINAL, path)
    check('manifest disk sha ' + path, sha(disk), row['sha256'])
    check('manifest Git sha ' + path, sha(raw), row['sha256'])
    check('manifest exact bytes ' + path, disk == raw, True)
check('manifest full coverage', sorted(listed), sorted(changed - {MANIFEST}))
check('manifest own exact bytes', (WT / MANIFEST).read_bytes() == blob(FINAL, MANIFEST), True)
check('report SHA', sha((WT / REPORT).read_bytes()), manifest['report_sha256'])
baseline = load(EVIDENCE + 'baseline.json')
preserved = baseline['preserved_files']
check('preserved list coverage', sorted(r['path'] for r in preserved), sorted(set(old_tree) - {MUTABLE}))
for row in preserved:
    path = row['path']
    check('old disk ' + path, sha((WT / path).read_bytes()), row['disk_sha256'])
    check('old Git ' + path, new_tree.get(path), old_tree[path])
for row in baseline['read_only_evidence']:
    check('root readonly ' + row['path'], sha((ROOT / row['path']).read_bytes()), row['sha256'])
ref_path = 'tests/fixtures/a01/R3/preservation-manifest.json'
ref = load(ref_path)
check('historical manifest SHA', sha((WT / ref_path).read_bytes()),
      '9ea7a71204c0417b16b232511010a781ad5a9c001287cc89c059b87a2b6ec795')
check('historical manifest count', len(ref['files']), 971)
check('historical manifest variants', sum(len(r['representations']) > 1 for r in ref['files']), 25)
selected = load('tests/fixtures/a01/integration-R1/reference.json')
check('selected reference commit', selected['reference_commit'], ref['reference_commit'])
check('selected manifest SHA', selected['source_manifest_sha256'], sha((WT / ref_path).read_bytes()))
ref_rows = {row['path']: row for row in ref['files']}
for row in selected['files']:
    encoded = row['git_original_base64']
    metadata = {k: v for k, v in row.items() if k != 'git_original_base64'}
    check('selected original metadata ' + row['path'], metadata, ref_rows[row['path']])
    original = base64.b64decode(encoded, validate=True)
    check('selected original bytes ' + row['path'], original == blob(ref['reference_commit'], row['path']), True)
    check('selected original hash ' + row['path'], sha(original), row['git_sha256'])

preservation = load(EVIDENCE + 'preservation.json')
after = load(EVIDENCE + 'after/results.json')
snapshots = load(EVIDENCE + 'after/snapshots.json')
check('preservation patch', preservation['implementation_commit'], PATCH)
check('two form identity', after['identity'], snapshots['identity'])
identity = snapshots['identity']
check('integration main', identity['main_parent'], manifest['main_parent'])
check('integration base', identity['A01_base'], BASE)
check('integration patch', identity['patch_parent'], PATCH)
parents = git('show', '-s', '--format=%P', identity['temporary_commit']).decode().strip().split()
check('actual integration parents', parents, [identity['main_parent'], PATCH])
check('actual integration tree', git('rev-parse', identity['temporary_commit'] + '^{tree}').decode().strip(), identity['tree'])
check('zero owned sessions declaration', after['sessions_to_release'], 0)
check('zero external calls declaration', after['network_browser_platform_model_calls'], 0)
check('temporary checkout removal declaration', after['normal_worktree_removed'], True)

print(json.dumps({
    'kind': 'DELIVERY_PREFLIGHT_ONLY', 'checked_at_utc': datetime.now(timezone.utc).isoformat(),
    'target_commit': FINAL, 'patch_commit': PATCH, 'baseline_commit': BASE,
    'worktree_head': git('rev-parse', 'HEAD').decode().strip(),
    'worktree_status': git('status', '--porcelain=v1').decode(),
    'changed_paths': len(changes), 'patch_to_delivery_packaging_paths': len(package),
    'manifest_entries': len(manifest['files']), 'manifest_path': MANIFEST,
    'manifest_sha256': sha((WT / MANIFEST).read_bytes()),
    'report_path': REPORT, 'report_sha256': sha((WT / REPORT).read_bytes()),
    'preserved_old_files': len(preserved), 'preserved_production_files': sum(p.startswith('src/') for p in old_tree),
    'root_readonly_files': len(baseline['read_only_evidence']),
    'historical_manifest_entries': len(ref['files']), 'historical_variant_paths': 25,
    'selected_fixed_git_originals': len(selected['files']),
    'integration_identity': identity, 'failed_checks': failures,
    'functional_tests_run': 0,
    'limits': ['Preflight is not functional acceptance or integration.',
               'Session release is documentary; no OS process scan.',
               'Temporary two-form runtime semantics remain for independent review.']
}, ensure_ascii=True, indent=2))
