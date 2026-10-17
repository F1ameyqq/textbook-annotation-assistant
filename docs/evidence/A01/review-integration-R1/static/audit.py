"""Read-only Git/AST audit of the exact bounded A01 integration R1 delivery.

Run from any cwd: python -B <this absolute path>. Writes only its own directory.
No functional regression, Git mutation, network, browser, or installed-package import.
"""
import ast
import base64
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path('D:/1800')
OUT = Path(__file__).resolve().parent
FINAL = '5f872150a237b195f73c78e02e13a91d2f4f46a7'
PATCH = 'f8f2981a815f96147144d3747d26752b564cc9f7'
BASE = '180bb1e86fb2a7eb1546be85af70f466f069daf5'
MAIN = '4946b8ab307f88bdc25c14ace5ead774e3119fc5'
PREFIX = 'docs/evidence/A01/execution/integration-R1/'
FIXTURE = 'tests/fixtures/a01/integration-R1/reference.json'
PRES = 'tests/fixtures/a01/R3/preservation-manifest.json'
CODE = 'tests/fixtures/a01/R3/code-reference.json'
MUTABLE = 'tests/test_a01_rework_r3.py'
commands, checks, blob_cache = [], [], {}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(name, value):
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='\n') as handle:
        handle.write(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def git(*args, input=None):
    argv = ['git', *map(str, args)]
    p = subprocess.run(argv, cwd=REPO, input=input, capture_output=True)
    commands.append(dict(argv=argv, cwd=str(REPO), exit_code=p.returncode,
                         stdin_sha256=sha(input) if input else None,
                         stdout_bytes=len(p.stdout), stdout_sha256=sha(p.stdout),
                         stderr=p.stderr.decode('utf-8', errors='replace')))
    if p.returncode:
        raise RuntimeError('Git read failed: ' + repr(argv))
    return p.stdout


def check(label, passed, detail=None):
    checks.append(dict(label=label, passed=bool(passed), detail=detail))


def tree(commit):
    result = {}
    for row in git('ls-tree', '-rz', '--full-tree', commit).split(b'\0'):
        if row:
            header, path = row.split(b'\t', 1)
            mode, kind, oid = header.decode('ascii').split()
            result[path.decode('utf-8')] = dict(mode=mode, kind=kind, oid=oid)
    return result


def blobs(oids):
    missing = sorted(set(oids) - set(blob_cache))
    if not missing:
        return
    output = git('cat-file', '--batch', input=('\n'.join(missing) + '\n').encode())
    offset = 0
    for oid in missing:
        end = output.index(b'\n', offset)
        actual, kind, size = output[offset:end].decode('ascii').split()
        size = int(size)
        assert actual == oid and kind == 'blob'
        offset = end + 1
        blob_cache[oid] = output[offset:offset + size]
        offset += size + 1
    assert offset == len(output)


trees = {commit: tree(commit) for commit in (FINAL, PATCH, BASE, MAIN)}
for a, b in ((BASE, PATCH), (PATCH, FINAL)):
    git('merge-base', '--is-ancestor', a, b)
final, patch, base = trees[FINAL], trees[PATCH], trees[BASE]
changed = sorted(p for p in set(base) | set(final) if base.get(p) != final.get(p))
modified = [p for p in changed if p in base and p in final]
deleted = [p for p in changed if p not in final]
allowed = lambda p: p == MUTABLE or p == 'tests/test_a01_integration_r1.py' or p == 'docs/tasks/A01-integration-R1-execution-report.md' or p.startswith(('tests/fixtures/a01/integration-R1/', 'examples/a01/integration-R1/', PREFIX))
check('51 net changed paths are authorized', len(changed) == 51 and all(map(allowed, changed)), changed)
check('unique pre-existing modification', modified == [MUTABLE] and not deleted, modified)
preserved = [p for p in base if p != MUTABLE]
check('1143 old files preserve mode/type/blob identity', len(preserved) == 1143 and all(base[p] == final.get(p) for p in preserved))
production = [p for p in base if p.startswith('src/')]
check('all 11 production files unchanged', len(production) == 11 and all(base[p] == final.get(p) for p in production), production)
historical = [p for p in base if p.startswith(('examples/a01/R3/', 'tests/fixtures/a01/R3/'))]
check('all old R3 helpers/manifests/input packages unchanged', all(base[p] == final.get(p) for p in historical), len(historical))
check('root attributes/dependencies unchanged', all(base[p] == final[p] for p in ('.gitattributes', 'pyproject.toml')))
late = sorted(p for p in set(patch) | set(final) if patch.get(p) != final.get(p))
check('patch-to-final 36 paths are only new report/evidence', len(late) == 36 and all(p.startswith(PREFIX) or p == 'docs/tasks/A01-integration-R1-execution-report.md' for p in late), late)
code_paths = [p for p in changed if p.startswith(('tests/', 'examples/'))]
check('final tested code/input exactly equal patch', all(patch[p] == final[p] for p in code_paths), code_paths)
write('scope.json', dict(base=BASE, patch=PATCH, final=FINAL, main=MAIN, changed=changed, modified=modified,
                         preserved_count=len(preserved), production_files=production, unchanged_old_R3_count=len(historical), patch_to_final=late))

read_paths = [PRES, CODE, FIXTURE, MUTABLE, 'tests/test_a01_integration_r1.py', 'examples/a01/R3/preservation.py',
              *['examples/a01/integration-R1/' + p for p in ('fixed_inputs.py', 'verify.py', 'exercise.py', 'isolate.py', 'README.md')],
              PREFIX + 'archive-manifest.json', PREFIX + 'payload_control.initial.py', PREFIX + 'payload_control.py',
              PREFIX + 'payload-wrapper-correction.json', PREFIX + 'payload-damage/results.json', PREFIX + 'payload-damage/run/results.json',
              PREFIX + 'before/command.json', PREFIX + 'before/classification.json', PREFIX + 'baseline.json']
blobs(final[p]['oid'] for p in read_paths)
def raw(path):
    return blob_cache[final[path]['oid']]

pres, code, fixture = [json.loads(raw(p)) for p in (PRES, CODE, FIXTURE)]
ref_trees = {m['reference_commit']: tree(m['reference_commit']) for m in (pres, code)}
all_entries = [e for m in (pres, code) for e in m['files']]
blobs(e['git_blob_oid'] for e in all_entries)
references = []
for manifest_name, manifest, expected_count, expected_alternatives in ((PRES, pres, 971, 25), (CODE, code, 62, 3)):
    entries = manifest['files']
    check(manifest_name + ' exact count and unique paths', len(entries) == expected_count == len({e['path'] for e in entries}))
    check(manifest_name + ' exact finite alternative count', sum(len(e['representations']) > 1 for e in entries) == expected_alternatives)
    rows = []
    for entry in entries:
        b = blob_cache[entry['git_blob_oid']]
        ref = ref_trees[manifest['reference_commit']][entry['path']]
        expected = [dict(kind='GIT_BLOB', sha256=sha(b), bytes=len(b))]
        if len(entry['representations']) == 2:
            crlf = b.replace(b'\n', b'\r\n')
            expected.append(dict(kind='CHECKOUT_CRLF', sha256=sha(crlf), bytes=len(crlf)))
        # Compare each variant's bytes/hash; kind labels are separately retained.
        ok = (ref['oid'] == entry['git_blob_oid'] and entry['git_sha256'] == sha(b)
              and len(entry['representations']) in (1, 2)
              and [(x['sha256'], x['bytes']) for x in entry['representations']] == [(x['sha256'], x['bytes']) for x in expected])
        check(manifest_name + ':' + entry['path'], ok)
        rows.append(dict(path=entry['path'], git_blob_oid=ref['oid'], git_sha256=sha(b), git_bytes=len(b), representations=entry['representations'], passed=ok))
    references.append(dict(path=manifest_name, reference_commit=manifest['reference_commit'], manifest_git_sha256=sha(raw(manifest_name)), entries=rows))
check('preservation fixed manifest SHA unchanged', sha(raw(PRES)) == '9ea7a71204c0417b16b232511010a781ad5a9c001287cc89c059b87a2b6ec795')
write('references.json', references)

originals = {e['path']: e for e in pres['files']}
expected_paths = {'docs/coordination.md', 'examples/a01/build.py', 'tests/test_contracts.py', 'tests/fixtures/contracts/normal/assets/asset-page-a1.pgm'}
check('four encoded original identities are fixed and unique', len(fixture['files']) == 4 and {e['path'] for e in fixture['files']} == expected_paths)
check('fixture binds original reference commit and manifest', fixture['reference_commit'] == pres['reference_commit'] and fixture['source_manifest_sha256'] == sha(raw(PRES)))
decoded = []
for item in fixture['files']:
    b = base64.b64decode(item['git_original_base64'], validate=True)
    record = {k: v for k, v in item.items() if k != 'git_original_base64'}
    original = originals[item['path']]
    check('fixed original exact metadata: ' + item['path'], record == original)
    check('fixed original exact raw Git blob: ' + item['path'], b == blob_cache[original['git_blob_oid']] and sha(b) == item['git_sha256'])
    destination = OUT / 'decoded-Git-originals' / item['path']
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(b)
    decoded.append(dict(path=item['path'], git_blob_oid=item['git_blob_oid'], sha256=sha(b), bytes=len(b), metadata_equals_original_reference=record == original))
write('fixed-originals.json', dict(reference_commit=fixture['reference_commit'], source_manifest_sha256=fixture['source_manifest_sha256'], files=decoded))

archive = json.loads(raw(PREFIX + 'archive-manifest.json'))
check('author archive has exactly 50 changed paths excluding itself', len(archive['files']) == 50 and {e['path'] for e in archive['files']} == set(changed) - {PREFIX + 'archive-manifest.json'})
blobs(final[e['path']]['oid'] for e in archive['files'])
matches, mismatches = [], []
for entry in archive['files']:
    b = raw(entry['path'])
    row = dict(path=entry['path'], manifest_sha256=entry['sha256'], git_sha256=sha(b), git_bytes=len(b), git_blob_oid=final[entry['path']]['oid'])
    (matches if sha(b) == entry['sha256'] else mismatches).append(row)
check('author manifest Git match count is 49, not 50', len(matches) == 49 and len(mismatches) == 1 and mismatches[0]['path'] == FIXTURE, mismatches)
b = raw(FIXTURE)
crlf = b.replace(b'\n', b'\r\n')
check('sole new fixture CRLF is exactly 64 extra bytes', b'\r' not in b and b.count(b'\n') == 64 and len(b) == 86374 and len(crlf) == 86438)
check('sole fixture two fixed SHA bindings', sha(b) == '51e2fd08803cfc918f62a23327da99993bf2a91363ef2ec3960f37765ee241db' and sha(crlf) == '9b979d4b18ffe4db50ad5473c218ba28fdcbed0515d68ce324894be09cc2d0eb')
check('sole fixture exact CRLF matches author archive and JSON content', sha(crlf) == mismatches[0]['manifest_sha256'] and json.loads(b) == json.loads(crlf))
write('author-manifest-representation.json', dict(git_matches=matches, git_mismatches=mismatches, strict_CRLF_candidate=dict(sha256=sha(crlf), bytes=len(crlf), exact_lf_to_crlf=True), note='CRLF here is independently derived from Git bytes, not a generalized tolerance or observed test import.'))

source = raw(MUTABLE).decode('utf-8')
old = git('show', BASE + ':' + MUTABLE).decode('utf-8')
old_ast, new_ast = ast.parse(old), ast.parse(source)
def methods(module):
    return {node.name + '.' + method.name: ast.dump(method, include_attributes=False) for node in module.body if isinstance(node, ast.ClassDef) for method in node.body if isinstance(method, ast.FunctionDef)}
before, after = methods(old_ast), methods(new_ast)
method_changes = sorted(k for k in before if before[k] != after.get(k))
check('only targeted old test method body changes', set(before) == set(after) and method_changes == ['PreservationR3Tests.test_fixed_baseline_has_only_explicit_twenty_five_variants'], method_changes)
check('no old skip/assert wrapper was added', [s for s in source.splitlines() if 'skip' in s.lower()] == [s for s in old.splitlines() if 'skip' in s.lower()])
new_tests = ast.parse(raw('tests/test_a01_integration_r1.py').decode('utf-8'))
check('three new boundary tests; no skip/error swallowing', sum(k.split('.')[-1].startswith('test_') for k in methods(new_tests)) == 3 and not any(isinstance(n, (ast.ExceptHandler, ast.Try)) for n in ast.walk(new_tests)) and 'skip' not in raw('tests/test_a01_integration_r1.py').decode().lower())
verifier = ast.parse(raw('examples/a01/integration-R1/verify.py').decode())
check('new conventional verifier has no exception swallowing', not any(isinstance(n, ast.ExceptHandler) for n in ast.walk(verifier)))
fixed = raw('examples/a01/integration-R1/fixed_inputs.py').decode()
check('materializer validates base64/hash and does not normalize line endings', 'validate=True' in fixed and 'fixed Git original digest mismatch' in fixed and '.replace(' not in fixed and 'subprocess' not in fixed)
write('static-code-review.json', dict(changed_old_methods=method_changes,
    findings=[
      'verify.py records source_files from direct Path.read_bytes; this is not sys.modules/__file__ proof.',
      'Every command boolean is accumulated into all_ok; return is 0 iff all_ok, with focused scope explicitly documented.',
      'Original old method audit(ROOT,971-files) is removed only from conventional regression; full original R3 verify/manifests are byte-preserved.',
      '4 selected entries must equal original 971 reference entries including identity and representations; fixed manifest SHA freezes the remaining policy list.',
      'Helper itself validates encoded content SHA and path containment; original reference/identity cross-check is in the conventional test.',
      'Fixture top-level reference_commit is correct in the frozen delivery but is only echoed after materialization; it is not asserted against the original reference in the new conventional test. Entry identities and source_manifest_sha256 are asserted.',
      'No new skip, broad exception handler, or runtime Git expected-value regeneration found in conventional verifier/materializer/new tests.'
    ], limitation='Static review does not prove actual test subprocess imports or execute full regressions.'))

correction = json.loads(raw(PREFIX + 'payload-wrapper-correction.json'))
initial, corrected = [raw(PREFIX + p) for p in ('payload_control.initial.py', 'payload_control.py')]
check('original payload wrapper and correction both retained with exact SHA', sha(initial) == correction['original_wrapper_sha256'] and sha(corrected) == correction['corrected_wrapper_sha256'])
payload = json.loads(raw(PREFIX + 'payload-damage/results.json'))
nested = json.loads(raw(PREFIX + 'payload-damage/run/results.json'))
check('retained payload child rejects without re-run correction', payload['exit_code'] == 1 and not nested['passed'] and 'fixed Git original digest mismatch' in nested['commands'][0]['stderr'] and correction['original_wrapper_exit_code'] == 1 and correction['functional_replay_count'] == 1)
before_command = json.loads(raw(PREFIX + 'before/command.json'))
check('original failed author integration reproduction retained', before_command['exit_code'] == 1)
baseline = json.loads(raw(PREFIX + 'baseline.json'))
retained = []
for entry in baseline['read_only_evidence']:
    path = Path(entry['path'])
    actual = sha(path.read_bytes())
    retained.append(dict(path=entry['path'], expected_sha256=entry['sha256'], current_sha256=actual, passed=actual == entry['sha256']))
    check('original coordinator input/failure preserved: ' + entry['path'], actual == entry['sha256'])
write('retained-failures.json', dict(coordinator_inputs=retained, author_before_exit_code=before_command['exit_code'], payload_wrapper_original_exit_code=correction['original_wrapper_exit_code'], payload_child_exit_code=payload['exit_code'], functional_replay_count=correction['functional_replay_count']))

saved = []
for path in read_paths:
    if path.endswith('/baseline.json'):
        continue  # Large historical inventory is read by fixed Git ID, not blindly copied.
    dest = OUT / 'inputs' / path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(raw(path))
    saved.append(dict(path=path, git_blob_oid=final[path]['oid'], sha256=sha(raw(path)), bytes=len(raw(path))))
write('input-index.json', saved)
write('commands.json', commands)
write('checks.json', checks)
failed = [item for item in checks if not item['passed']]
summary = dict(task='A01-integration-R1 static independent subreview', final_commit=FINAL, patch_commit=PATCH,
               base_commit=BASE, main_parent=MAIN, checks=len(checks), failures=failed,
               passed=not failed, command_count=len(commands), all_recorded_read_commands_exit_zero=all(c['exit_code'] == 0 for c in commands),
               functional_regressions_run=0, Git_mutations=0, network_browser_platform_credentials_model_calls=0,
               subprocess_sessions_to_release=0,
               limitation='Root reviewer must independently obtain real imports and functional/negative-control results.')
write('summary.json', summary)
print(json.dumps({k: v for k, v in summary.items() if k not in ('failures',)}, ensure_ascii=False))
raise SystemExit(1 if failed else 0)
