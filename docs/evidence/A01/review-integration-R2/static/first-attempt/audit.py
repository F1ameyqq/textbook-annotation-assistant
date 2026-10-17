"""R2 independent read-only static audit; writes only this new evidence directory."""
import ast
import base64
import hashlib
import json
import subprocess
from pathlib import Path

REPO = Path('D:/1800')
OUT = Path(__file__).resolve().parent
WORKFLOW = 'fe91c27939d13f9be290f8274a0d46d90f4de2f0'
MAIN = '2d1dc8b97713ee06ec5bf35febe0b894ece584b2'
A01 = '5f872150a237b195f73c78e02e13a91d2f4f46a7'
A01_PATCH = 'f8f2981a815f96147144d3747d26752b564cc9f7'
FROZEN = '180bb1e86fb2a7eb1546be85af70f466f069daf5'
COMBO = '0645ac862f79fb4e232e4cfbd5f6bb5055a68d62'
OLD_COMBO = '2078731114ad3a07368ca46a2f34c3544af64e2b'
A02 = 'a1e5be00909172429d792b6c41bdaf384258694e'
A02_PATCH = 'ad71284f3b6ffc8454ee1d1e30933c8e39d7c1d8'
A02_BASE = '38aca9dcc8d027409b95193e9cc142c2336b76d3'
PRES = 'tests/fixtures/a01/R3/preservation-manifest.json'
CODE = 'tests/fixtures/a01/R3/code-reference.json'
FIXTURE = 'tests/fixtures/a01/integration-R1/reference.json'
INDEX = 'docs/evidence/A02/coordinator/portability-R2-integration/merge-index-check.json'
CHECKS = 'docs/evidence/A02/coordinator/portability-R2-integration/checks.json'
PREFLIGHT = 'docs/evidence/A01/coordinator/integration-R2-handoff/preflight.json'
R1REPORT = 'docs/tasks/A01-integration-R1-review-report.md'
R1MANIFEST = 'docs/evidence/A01/review-integration-R1/sha256-manifest.json'
R1NEGATIVE = 'docs/evidence/A01/review-integration-R1/negative/summary.json'
commands, checks, trees, cache, input_index = [], [], {}, {}, []


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


def tree(obj):
    if obj not in trees:
        rows = {}
        for row in git('ls-tree', '-rz', '--full-tree', obj).split(b'\0'):
            if row:
                header, name = row.split(b'\t', 1)
                mode, kind, oid = header.decode().split()
                rows[name.decode('utf-8')] = dict(mode=mode, kind=kind, oid=oid)
        trees[obj] = rows
    return trees[obj]


def blobs(oids):
    missing = sorted(set(oids) - set(cache))
    if not missing:
        return
    output = git('cat-file', '--batch', input=('\n'.join(missing) + '\n').encode())
    offset = 0
    for oid in missing:
        end = output.index(b'\n', offset)
        actual, kind, size = output[offset:end].decode().split()
        assert actual == oid and kind == 'blob'
        offset = end + 1
        cache[oid] = output[offset:offset + int(size)]
        offset += int(size) + 1
    assert offset == len(output)


def raw(obj, path):
    oid = tree(obj)[path]['oid']
    blobs([oid])
    return cache[oid]


def load(obj, path):
    return json.loads(raw(obj, path))


def check(label, passed, detail=None):
    checks.append(dict(label=label, passed=bool(passed), detail=detail))


def retain(obj, path):
    b = raw(obj, path)
    # Each input is a raw committed blob; tree OID ties it to the exact source.
    target = OUT / 'inputs' / obj[:12] / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b)
    input_index.append(dict(object=obj, path=path, blob_oid=tree(obj)[path]['oid'], sha256=sha(b), bytes=len(b)))


wf, main, combo, a01, old_combo = [tree(o) for o in (WORKFLOW, MAIN, COMBO, A01, OLD_COMBO)]
a02, a02_patch = tree(A02), tree(A02_PATCH)
git('merge-base', '--is-ancestor', A01_PATCH, A01)
git('merge-base', '--is-ancestor', A02_PATCH, A02)
git('merge-base', '--is-ancestor', A02, MAIN)
merge_base = git('merge-base', MAIN, A01).decode().strip()
ancestor = tree(merge_base)
delta = sorted(p for p in set(ancestor) | set(a01) if ancestor.get(p) != a01.get(p))
actual_delta = sorted(p for p in set(main) | set(combo) if main.get(p) != combo.get(p))
preflight = load(WORKFLOW, PREFLIGHT)
check('correct workflow main/delivery/tree preflight binding', preflight['main_parent'] == MAIN and preflight['delivery_parent'] == A01 and preflight['combined_tree'] == COMBO)
check('all 464 combined differences are exactly the frozen A01 delta', len(delta) == 464 and delta == actual_delta == sorted(preflight['combined_changed_paths']))
check('combined A01 delta uses A01 final identities', all(combo.get(p) == a01.get(p) for p in delta))
outside = [p for p in main if p not in delta]
check('all 11430 other main paths preserve exact mode/type/OID', len(outside) == 11430 and all(combo.get(p) == main[p] for p in outside))
policy = ['.gitattributes', 'pyproject.toml', 'docs/architecture.md', 'docs/contracts-v1.md', 'docs/coordination.md', 'docs/coordination-state.json']
check('root policy/contracts/dependency/state remain fixed main', all(combo[p] == main[p] for p in policy), policy)
relevant = sorted(p for p in a01 if p.startswith(('src/', 'examples/a01/', 'tests/fixtures/a01/')) or p.startswith('tests/test_a01'))
check('all A01 production/helpers/tests/fixtures retain final and old R1-combination OID', all(combo[p] == a01[p] == old_combo[p] for p in relevant), len(relevant))
check('11 A01 production modules unchanged', len([p for p in a01 if p.startswith('src/')]) == 11)
write('combination-identities.json', dict(workflow=WORKFLOW, main_parent=MAIN, delivery_parent=A01, combination_tree=COMBO,
      old_R1_combination_tree=OLD_COMBO, merge_base=merge_base, A01_delta_paths=delta,
      other_main_preserved=len(outside), A01_runtime_and_policy_identity_paths=[dict(path=p, oid=combo[p]['oid']) for p in relevant], root_paths=policy,
      limitation='Reads the frozen combination tree. Root reviewer separately reconstructs this tree in an independent object repository. No merge or commit is performed here.'))

identity = 'examples/a02/R1/identity.py'
check('new accepted A02 identity selected in main and combo', combo[identity] == main[identity] == a02[identity] == a02_patch[identity])
check('old failing A02 identity not selected', combo[identity] != old_combo[identity])
check('accepted A02 identity fixed expected OID/SHA', combo[identity]['oid'] == 'db0ca76a6a504ebd16e1b6731d104577c36bf0b0' and sha(raw(COMBO, identity)) == '02b51187b4b4f711f0df8ea501201cafe99c078c84351a376a66ae2f892af58e')
a02_runtime = ['examples/a02/R1/identity.py', 'examples/a02/portability-R2/probe.py', 'examples/a02/portability-R2/run_tests.py', 'examples/a02/portability-R2/verify.py', 'tests/test_a02_portability_r2.py', 'tests/test_a02_r1.py', 'tests/test_a02.py']
check('accepted A02 runtime/test identities survive combination unchanged', all(combo[p] == main[p] == a02[p] for p in a02_runtime))
def func(text, name):
    node = next(n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == name)
    return ast.get_source_segment(text, node)
check('A02 source_binding function exact source remains accepted unchanged', func(raw(A02_BASE, identity).decode(), 'source_binding') == func(raw(A02, identity).decode(), 'source_binding'))
write('A02-identity.json', dict(path=identity, selected_oid=combo[identity]['oid'], selected_sha256=sha(raw(COMBO, identity)),
      old_R1_oid=old_combo[identity]['oid'], runtime_and_tests=[dict(path=p, oid=combo[p]['oid']) for p in a02_runtime],
      accepted_final=A02, accepted_patch=A02_PATCH))

index = load(WORKFLOW, INDEX)
check('188 historical index rows and exact fixed A02 delivery', index['changed_paths'] == 188 and len(index['files']) == 188 and index['final_commit'] == A02 and index['raw_git_index_equal'] == 188 and index['raw_git_disk_equal'] == 183)
check('index tree is actual fixed main tree', git('rev-parse', MAIN + '^{tree}').decode().strip() == index['merged_index_tree'])
index_tree = tree(index['merged_index_tree'])
blobs(a02[e['path']]['oid'] for e in index['files'])
rows = []
for entry in index['files']:
    p = entry['path']
    b = raw(A02, p)
    same = entry['disk_equal']
    disk_rep = b if same else b.replace(b'\n', b'\r\n')
    ok = (a02[p] == main[p] == combo[p] == index_tree[p] and sha(b) == entry['sha256'] and len(b) == entry['bytes']
          and sha(disk_rep) == entry['disk_sha256'] and len(disk_rep) == entry['disk_bytes']
          and entry['exact_lf_to_crlf'] == (not same))
    if not same:
        ok = ok and p.endswith('.py') and b'\r' not in b
    check('A02 historical index/blob/disk representation: ' + p, ok)
    rows.append(dict(path=p, oid=a02[p]['oid'], git_sha256=sha(b), git_bytes=len(b), recorded_disk_sha256=entry['disk_sha256'], recorded_disk_bytes=entry['disk_bytes'], representation='GIT_BLOB' if same else 'EXACT_LF_TO_CRLF', passed=ok))
five = [r for r in rows if r['representation'] != 'GIT_BLOB']
check('exact five Python CRLF files; no additional tolerance', len(five) == 5 and {r['path'] for r in five} == set(index['exact_lf_to_crlf_paths']))
write('A02-188-file-representation-audit.json', dict(main_parent=MAIN, accepted_final=A02, source_workflow=WORKFLOW, files=rows,
      git_index_tree_matches=188, recorded_disk_raw_matches=183, strict_CRLF_files=five,
      evidence_level='Independent raw Git/OID/hash recomputation against the historical 188-row receipt. Not a re-observation of its past physical index or disk.'))

pres, code, fixture = [load(COMBO, p) for p in (PRES, CODE, FIXTURE)]
references = []
for path, manifest, n, candidates in ((PRES, pres, 971, 25), (CODE, code, 62, 3)):
    ref = tree(manifest['reference_commit'])
    blobs(e['git_blob_oid'] for e in manifest['files'])
    check(path + ' unchanged exact OID and fixed row policy', combo[path] == a01[path] == old_combo[path] and len(manifest['files']) == n == len({e['path'] for e in manifest['files']}) and sum(len(e['representations']) > 1 for e in manifest['files']) == candidates)
    entries = []
    for entry in manifest['files']:
        b = cache[entry['git_blob_oid']]
        wanted = [(sha(b), len(b))]
        if len(entry['representations']) == 2:
            crlf = b.replace(b'\n', b'\r\n')
            wanted.append((sha(crlf), len(crlf)))
        ok = ref[entry['path']]['oid'] == entry['git_blob_oid'] and sha(b) == entry['git_sha256'] and len(entry['representations']) in (1, 2) and wanted == [(v['sha256'], v['bytes']) for v in entry['representations']]
        check(path + ':' + entry['path'], ok)
        entries.append(dict(path=entry['path'], blob_oid=entry['git_blob_oid'], git_sha256=sha(b), git_bytes=len(b), representations=entry['representations'], passed=ok))
    references.append(dict(path=path, reference_commit=manifest['reference_commit'], manifest_blob_oid=combo[path]['oid'], manifest_sha256=sha(raw(COMBO, path)), files=entries))
check('preservation fixed SHA remains original', sha(raw(COMBO, PRES)) == '9ea7a71204c0417b16b232511010a781ad5a9c001287cc89c059b87a2b6ec795')
write('fixed-reference-audit.json', references)
original = {e['path']: e for e in pres['files']}
decoded = []
check('4 encoded originals correct top-level current frozen binding', len(fixture['files']) == 4 and fixture['reference_commit'] == pres['reference_commit'] and fixture['source_manifest_sha256'] == sha(raw(COMBO, PRES)))
for item in fixture['files']:
    b = base64.b64decode(item['git_original_base64'], validate=True)
    metadata = {k: v for k, v in item.items() if k != 'git_original_base64'}
    check('encoded original exact reference/Git content: ' + item['path'], metadata == original[item['path']] and b == cache[item['git_blob_oid']] and sha(b) == item['git_sha256'])
    decoded.append(dict(path=item['path'], blob_oid=item['git_blob_oid'], sha256=sha(b), bytes=len(b)))
write('encoded-originals.json', dict(reference_commit=fixture['reference_commit'], source_manifest_sha256=fixture['source_manifest_sha256'], files=decoded,
      limitation='Top-level reference_commit frozen value is correct; conventional regression still does not authenticate this redundant label (old I04).'))

archive_path = 'docs/evidence/A01/execution/integration-R1/archive-manifest.json'
archive = load(A01, archive_path)
blobs(a01[e['path']]['oid'] for e in archive['files'])
mismatches = [dict(path=e['path'], git_sha256=sha(raw(A01, e['path'])), git_bytes=len(raw(A01, e['path'])), archive_sha256=e['sha256']) for e in archive['files'] if sha(raw(A01, e['path'])) != e['sha256']]
new_fixture = raw(COMBO, FIXTURE)
new_fixture_crlf = new_fixture.replace(b'\n', b'\r\n')
check('A01 author archive remains 49/50 Git with same sole fixture mismatch', len(archive['files']) == 50 and len(mismatches) == 1 and mismatches[0]['path'] == FIXTURE)
check('A01 new fixture double SHA exactly unchanged', len(new_fixture) == 86374 and sha(new_fixture) == '51e2fd08803cfc918f62a23327da99993bf2a91363ef2ec3960f37765ee241db' and new_fixture.count(b'\n') == 64 and b'\r' not in new_fixture and len(new_fixture_crlf) == 86438 and sha(new_fixture_crlf) == '9b979d4b18ffe4db50ad5473c218ba28fdcbed0515d68ce324894be09cc2d0eb' == mismatches[0]['archive_sha256'])
write('A01-author-manifest-representation.json', dict(git_matches=49, author_recorded_disk_matches=50, mismatches=mismatches,
      strict_CRLF_candidate=dict(sha256=sha(new_fixture_crlf), bytes=len(new_fixture_crlf)),
      note='Retains old manifest discrepancy. No old reference candidate is added and past author disk is not re-observed.'))

check('R1 review report fixed SHA', sha(raw(WORKFLOW, R1REPORT)) == '2aaed84505799509319cab8e99a94eba818b69fd301caf4d3be89fe48c6a3caf')
check('R1 evidence manifest fixed SHA', sha(raw(WORKFLOW, R1MANIFEST)) == 'a331ad8a039408f2225f9e9842cc0a4d0860af7a0ece67f3fafa527f0c6600ad')
negative = load(WORKFLOW, R1NEGATIVE)
check('R1 negative provenance remains correct frozen A01 identity', negative['final'] == A01 and negative['integration_tree'] == OLD_COMBO and negative['base'] == FROZEN)
allowed_cases = []
for row in negative['focused']:
    label = row['label'].split('-')[0]
    if label in ('I01', 'I02', 'I03', 'I05'):
        check('R1 reusable negative ' + label, row['actual_exit_code'] == 1 and row['child_exit_code'] == 1 and row['expected_matched'])
        allowed_cases.append(row)
for row in negative['auxiliary']:
    check('R1 reusable fixed representation case ' + row['label'], row['expected_matched'])
    allowed_cases.append(row)
for row in negative['original_release']:
    check('R1 reusable original release case ' + row['label'], row['actual_exit_code'] == row['expected_exit_code'])
    allowed_cases.append(row)
old_i04 = next(r for r in negative['focused'] if r['label'].startswith('I04'))
check('I04 disclosed label limitation is retained, not rewritten pass', old_i04['actual_exit_code'] == 0 and not old_i04['expected_matched'])
entry = raw(COMBO, 'examples/a01/integration-R1/verify.py')
check('error propagation conventional entry byte-identical to prior tested entry', entry == raw(OLD_COMBO, 'examples/a01/integration-R1/verify.py'))
write('R1-reuse-scope.json', dict(related_A01_files_rechecked=len(relevant), reusable_cases=allowed_cases,
      reusable_error_propagation='Byte-identical complete entry accumulates child nonzero; historical failing raw command and negative nonzero receipts remain evidence of propagation.',
      limitation_I04=old_i04,
      not_reusable_as_R2_acceptance=['Old raw complete entry failed I1-GIT-01; must run the new fixed combined complete entry.', 'Old A02 count 52; new accepted suite is 62 and must be observed this round.', 'Old actual import paths/checkouts or noGit environment probes cannot prove this round imports or OS launch failure.', 'No new 630-case geometry run, platform acceptance, whole-book coverage, B confirmation or A04/D01 release is proved.'],
      functional_negatives_rerun=0))

a02_report = 'docs/tasks/A02-portability-R2-review-report.md'
check('A02 accepted report fixed SHA', sha(raw(WORKFLOW, a02_report)) == '92217848c055e133e2b79b4318027e1185105e8a75e5fc14531a7f1fda937d77')
integration = load(WORKFLOW, CHECKS)
check('A02 actual integration receipt binds M tree and 62 no-skip tests', integration['merge_commit'] == MAIN and integration['tree'] == index['merged_index_tree'] and integration['exit_code'] == 0 and integration['tests']['run'] == 62 and not any(integration['tests'][k] for k in ('failures', 'errors', 'skipped')))
coord_path = 'docs/evidence/A02/coordinator/portability-R2-acceptance/coordinator-check.json'
coord = load(WORKFLOW, coord_path)
check('A02 bounded coordinator reproduction 0/1/0 and accepted identity', coord['target_commit'] == A02 and [e['exit_code'] for e in coord['commands']] == [0, 1, 0] and coord['binding_without_git_rejected'] and coord['normal_identity_and_second_real_spawn_failure_verified'])
write('A02-prior-acceptance-scope.json', dict(accepted_final=A02, accepted_patch=A02_PATCH, review_report_sha256=sha(raw(WORKFLOW, a02_report)),
      integration_test_receipt=dict(merge_commit=MAIN, tree=integration['tree'], exit_code=integration['exit_code'], tests={k:v for k,v in integration['tests'].items() if k != 'imports'}),
      coordinator_reproduction_exit_codes=[e['exit_code'] for e in coord['commands']],
      scope='Prior accepted A02 binding/second-spawn independent negatives may be cited after identity checks. This is source/receipt audit, not a new functional execution.'))

workflow_inputs = ['docs/tasks/A01-integration-R2-review-handoff.md', 'docs/tasks/A02-portability-R2-coordinator-acceptance.md', a02_report, R1REPORT, R1NEGATIVE, INDEX, CHECKS, PREFLIGHT, coord_path]
for path in workflow_inputs:
    retain(WORKFLOW, path)
for path in (PRES, CODE, FIXTURE, 'examples/a01/integration-R1/verify.py', 'examples/a01/integration-R1/fixed_inputs.py', 'tests/test_a01_rework_r3.py', 'tests/test_a01_integration_r1.py', *a02_runtime):
    retain(COMBO, path)
retain(A01, archive_path)
write('input-index.json', input_index)
write('commands.json', commands)
write('checks.json', checks)
failures = [row for row in checks if not row['passed']]
result = dict(task='A01 integration-R2 independent static/reference audit', workflow=WORKFLOW, main_parent=MAIN, A01_final=A01,
              combination_tree=COMBO, A02_accepted_final=A02, check_count=len(checks), failures=failures,
              passed=not failures, read_commands=len(commands), all_read_commands_exit_zero=all(c['exit_code'] == 0 for c in commands),
              functional_regressions_run=0, functional_negative_controls_rerun=0, geometry_630_rerun=False,
              Git_mutations=0, network_browser_platform_credentials_model_calls=0, sessions_to_release=0,
              conclusion_scope='Static identities, fixed bytes and reuse admissibility only; root owns actual combination reconstruction, runtime imports, both full entries and original noGit singleton.')
write('summary.json', result)
print(json.dumps({k:v for k,v in result.items() if k != 'failures'}, ensure_ascii=False))
raise SystemExit(1 if failures else 0)
