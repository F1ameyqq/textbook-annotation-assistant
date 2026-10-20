"""Independent read-only raw identity, preservation and AST comparison. No imports of product."""
import ast
import difflib
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

os.environ['GIT_NO_LAZY_FETCH'] = '1'
sys.stdout.reconfigure(encoding='utf-8')
REPO = Path('D:/1800')
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'review-output'
BASE = '0c30b365ed18b006bcab32bed4acb60869ff9f92'
ORIGINAL_BASE = '5e31abf791a69333384b0154c02a77da557e7a63'
PRODUCT = 'd45ed25a98361002ddb28985c1d27687c4421a17'
FINAL = '81fab23e3e7e9e32a36d3857a253afc69b5bd3e1'
WORKFLOW = '4e300c8d7c544a0f802425827906783efb1344e8'
OLD = 'tools/headless_native_reuse_probe.py'
NEW = 'tools/headless_native_reuse_probe_r1.py'
DELTA = 'docs/evidence/A12/review-delta/'
EXPECTED_CANDIDATE = '38eb3f836f14b44db77ce516f461bd4f3934df71807c1fac962560603a210920'
EXPECTED_DELIVERY = 'b615681648be2ce5c35c5e7e6502733b135c26be4d0e070b5c6838eb4094ded7'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def git(*args):
    return subprocess.check_output(['git', '-c', 'core.longpaths=true', *args], cwd=str(REPO))

def tree(commit):
    raw = git('ls-tree', '-rz', '--full-tree', commit)
    found = {}
    for record in raw.split(b'\0'):
        if record:
            left, path = record.split(b'\t', 1)
            found[path.decode('utf-8')] = tuple(left.decode('ascii').split())
    return raw, found

def write_new(name, obj):
    with (OUT / name).open('xb') as f:
        f.write((json.dumps(obj, ensure_ascii=True, indent=2, sort_keys=True) + '\n').encode('utf-8'))

def require(ok, text):
    if not ok:
        raise AssertionError(text)

def body_map(source):
    module = ast.parse(source)
    result = {}
    for node in module.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            result[node.name] = ast.dump(node, include_attributes=False)
            if isinstance(node, ast.ClassDef):
                for member in node.body:
                    if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        result[node.name + '.' + member.name] = ast.dump(member, include_attributes=False)
    return result

raw_base, base = tree(BASE)
raw_original, original = tree(ORIGINAL_BASE)
raw_product, product = tree(PRODUCT)
raw_final, final = tree(FINAL)
require(git('rev-parse', FINAL + '^').decode().strip() == PRODUCT, 'FINAL_PARENT')
require(git('rev-parse', PRODUCT + '^').decode().strip() == BASE, 'PRODUCT_PARENT')
changed = [p for p in base if final.get(p) != base[p] or product.get(p) != base[p]]
require(not changed, 'OLD_PATH_CHANGED')
require(len(base) == 31181 and len(original) == 31159, 'BASE_MEMBER_COUNTS')
original_added = sorted(set(base) - set(original))
new_added = sorted(set(final) - set(base))
require(len(original_added) == 22 and len(new_added) == 31, 'ADDED_COUNTS')
require(all(p == NEW or p.startswith(DELTA) or p == 'docs/tasks/A12-review-delta-author-report.md'
            for p in new_added), 'ADDED_ALLOWLIST')
expected_inputs = sorted(original_added + new_added)
local_files = sorted(p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*')
                     if p.is_file() and 'review-output' not in p.relative_to(ROOT).parts)
require(local_files == expected_inputs, 'INPUT_SET_NOT_EXACT_53')
inputs = []
for p in expected_inputs:
    local = ROOT / p
    require(not local.is_symlink(), 'INPUT_SYMLINK')
    blob = git('cat-file', 'blob', final[p][2])
    require(local.read_bytes() == blob, 'RAW_MISMATCH:' + p)
    mode, kind, oid = final[p]
    inputs.append({'path': p, 'mode': mode, 'type': kind, 'git_oid': oid,
                   'size': len(blob), 'sha256': sha(blob)})

candidate_raw = (ROOT / (DELTA + 'candidate-manifest.json')).read_bytes()
delivery_raw = (ROOT / (DELTA + 'delivery-raw-manifest.json')).read_bytes()
require(sha(candidate_raw) == EXPECTED_CANDIDATE, 'CANDIDATE_SHA')
require(sha(delivery_raw) == EXPECTED_DELIVERY, 'DELIVERY_SHA')
candidate = json.loads(candidate_raw)
delivery = json.loads(delivery_raw)
require(candidate['workflow_commit'] == WORKFLOW, 'WORKFLOW_BINDING')
for member in candidate['members']:
    p = member['path']
    data = (ROOT / p).read_bytes()
    require(sha(data) == member['sha256'] and len(data) == member['size'], 'CANDIDATE_MEMBER')
    require(product[p] == final[p], 'CANDIDATE_PRODUCT_FINAL_DIFFERENCE')
require(len(candidate['members']) == 21, 'CANDIDATE_COUNT')
for member in delivery['members_excluding_this_manifest']:
    p = member['path']
    data = (ROOT / p).read_bytes()
    require(sha(data) == member['sha256'] and len(data) == member['size'], 'DELIVERY_MEMBER')
    require(final[p] == (member['mode'], member['type'], member['raw_git_blob_expected']), 'DELIVERY_TREE_IDENTITY')
require(len(delivery['members_excluding_this_manifest']) == 30, 'DELIVERY_COUNT')
provenance = [
    ('authority/task.md', 'docs/tasks/A12-R1-review-findings-correction.md'),
    ('authority/independent-review.md', 'docs/tasks/A12-R1-independent-review.md'),
    ('authority/original-review.json', 'docs/evidence/coordinator/a12-formal-review/report.json'),
]
for copy, source in provenance:
    require((ROOT / (DELTA + copy)).read_bytes() == git('show', WORKFLOW + ':' + source), 'AUTHORITY_COPY')

old_source = (ROOT / OLD).read_bytes().decode('utf-8')
new_source = (ROOT / NEW).read_bytes().decode('utf-8')
old_ast, new_ast = body_map(old_source), body_map(new_source)
same = sorted(k for k in old_ast if old_ast[k] == new_ast.get(k))
different = sorted(k for k in old_ast if old_ast[k] != new_ast.get(k))
added = sorted(set(new_ast) - set(old_ast))
must_preserve = ['NativePolicy', 'open_owned', 'close_owned', 'initial_release', 'load_native',
                 'profile_binding', 'OwnedJob', 'supervise', 'worker_main', 'safe_error', 'save_new',
                 'NativeGuard.note', 'NativeGuard.paused', 'NativeGuard.child_target', 'NativeGuard.install']
require(all(k in same for k in must_preserve), 'PROTECTED_AST_CHANGED')
for p in [OLD, NEW, DELTA + 'delta_suite.py']:
    compile((ROOT / p).read_bytes(), p, 'exec')  # Syntax only; never exec/import here.
diff = ''.join(difflib.unified_diff(old_source.splitlines(True), new_source.splitlines(True),
                fromfile=OLD + '@' + BASE, tofile=NEW))
with (OUT / 'independent-product-delta.diff').open('xb') as f:
    f.write(diff.encode('utf-8'))

release = json.loads((ROOT / (DELTA + 'author-run/author-release.json')).read_bytes())
child = release['protocol_child']
require(release['further_action'] == 'STOPPED_NO_RETRY_NO_LIVE', 'AUTHOR_NOT_RELEASED')
require(child['state'] == 'RELEASED' and child['handle_closed'] and child['pipes_closed'], 'AUTHOR_CHILD_NOT_RELEASED')
require(child['before']['pid'] == child['after']['pid'] == 57848 and
        child['before']['created_filetime'] == child['after']['created_filetime'] and
        child['after']['exit_observed'] and child['after']['exit_code'] == 0, 'AUTHOR_CHILD_IDENTITY')
author_results = json.loads((ROOT / (DELTA + 'author-run/suite-result.json')).read_bytes())
require(all(author_results['cases']['D' + str(n)]['status'] == 'PASS' for n in range(1, 9)), 'AUTHOR_RECORDED_CASES')

report = {
    'at': datetime.now(timezone.utc).isoformat(), 'status': 'PASS_RAW_IDENTITY_AND_STATIC_SCOPE',
    'review_thread_id': '01a157a5-495a-7bf3-bc17-299ad85c48a7',
    'source_final_commit': BASE, 'workflow_commit': WORKFLOW,
    'product_driver_commit': PRODUCT, 'final_commit': FINAL,
    'raw_input_count': len(inputs), 'inputs': inputs,
    'candidate_manifest_sha256': EXPECTED_CANDIDATE, 'candidate_members': 21,
    'delivery_manifest_sha256': EXPECTED_DELIVERY, 'delivery_nonself_members': 30,
    'baseline_members': len(base), 'baseline_changed': changed,
    'original_A12_members': len(original_added), 'original_baseline_members': len(original),
    'added_paths': new_added, 'authority_raw_copies_checked': len(provenance),
    'tree_record_sha256': {'base': sha(raw_base), 'original_base': sha(raw_original),
                           'product': sha(raw_product), 'final': sha(raw_final)},
    'ast_same': same, 'ast_changed': different, 'ast_added': added,
    'protected_ast_all_equal': True, 'product_imports_or_runs': 0,
    'author_release_record_verified': True, 'author_case_results_are_independent_results': False,
    'git_mode': 'read-only; GIT_NO_LAZY_FETCH=1; every invocation core.longpaths=true',
}
write_new('raw-preflight.json', report)
print(json.dumps({k: v for k, v in report.items() if k not in ('inputs', 'ast_same', 'added_paths')}, indent=2))
