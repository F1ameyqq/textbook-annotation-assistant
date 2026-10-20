"""Read fixed Git objects and parse source only. Never import/run candidate or E1-E4."""
import ast
import difflib
import hashlib
import json
import os
from pathlib import Path
import subprocess
from datetime import datetime, timezone

ROOT = Path('D:/1800-worktrees/a15-independent-fixed')
OUT = ROOT / 'docs/evidence/A15/independent-preflight-static'
EVIDENCE = ROOT / 'docs/evidence/A15/certificate-exception'
BASE = '81fab23e3e7e9e32a36d3857a253afc69b5bd3e1'
PRODUCT = 'bef0204541eedd86e1fab849e8002a83f432cd7b'
FINAL = '25f9083b2c8183196a7b2d7671efd40d2ef78713'
WORKFLOW = 'ec69a4bfd72b64e3bd6c6435ef0ec780fd109249'
EXPECTED_CANDIDATE = '78382e0b484ad46ab497217683fa3022440a1f570589f538c3d355670d552652'
EXPECTED_DELIVERY = '835cdcb94e25bf5d3d1ae91a99a268f4e52035ab9b88e53439f9ea6bd311ba19'
commands = []

def sha(data):
    return hashlib.sha256(data).hexdigest()

def git(*args):
    command = ['git', '-c', 'core.longpaths=true', '-C', 'D:/1800', *args]
    completed = subprocess.run(command, env={**os.environ, 'GIT_NO_LAZY_FETCH': '1'},
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    commands.append({'argv': command, 'GIT_NO_LAZY_FETCH': '1',
                     'exit_code': completed.returncode,
                     'stdout_bytes': len(completed.stdout),
                     'stderr_bytes': len(completed.stderr)})
    if completed.returncode:
        raise RuntimeError('STATIC_GIT_READ_FAILED')
    return completed.stdout

def tree(raw):
    result = {}
    for entry in raw.split(b'\0'):
        if entry:
            identity, path = entry.split(b'\t', 1)
            result[path.decode('utf-8')] = identity.decode('ascii')
    return result

def write_new(name, value):
    with (OUT / name).open('xb') as stream:
        stream.write((json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)
                      + '\n').encode('utf-8'))

candidate_raw = (EVIDENCE / 'candidate-manifest.json').read_bytes()
delivery_raw = (EVIDENCE / 'delivery-raw-manifest.json').read_bytes()
assert sha(candidate_raw) == EXPECTED_CANDIDATE
assert sha(delivery_raw) == EXPECTED_DELIVERY
candidate = json.loads(candidate_raw)
delivery = json.loads(delivery_raw)
raw_trees = {label: git('ls-tree', '-r', '-z', commit)
             for label, commit in [('base', BASE), ('product', PRODUCT), ('final', FINAL)]}
trees = {label: tree(raw) for label, raw in raw_trees.items()}
assert raw_trees['base'] == (EVIDENCE / 'base-tree.bin').read_bytes()
preserved = {}
for label in ('product', 'final'):
    differences = [path for path, identity in trees['base'].items()
                   if trees[label].get(path) != identity]
    assert not differences
    new_paths = sorted(set(trees[label]) - set(trees['base']))
    assert all(path in ('tools/headless_cert_exception_reuse_probe.py',
                        'tools/a15_cert_exception_gate_delta.py',
                        'tools/a15_observation_launcher.py')
               or path.startswith('docs/evidence/A15/certificate-exception/')
               for path in new_paths)
    preserved[label] = {'old_members': len(trees['base']), 'old_changes': differences,
                        'new_members': len(new_paths), 'new_paths': new_paths,
                        'tree_raw_sha256': sha(raw_trees[label])}
verified = []
for item in delivery['members']:
    relative = Path(item['path'])
    assert not relative.is_absolute() and '..' not in relative.parts
    raw = (ROOT / relative).read_bytes()
    blob = hashlib.sha1(b'blob ' + str(len(raw)).encode('ascii') + b'\0' + raw).hexdigest()
    assert (len(raw), sha(raw), blob) == (item['size'], item['sha256'], item['git_blob_expected'])
    assert trees['final'][item['path']] == '100644 blob ' + blob
    verified.append({'path': item['path'], 'size': len(raw), 'sha256': sha(raw), 'git_blob': blob})
manifest_rel = 'docs/evidence/A15/certificate-exception/delivery-raw-manifest.json'
assert git('cat-file', 'blob', FINAL + ':' + manifest_rel) == delivery_raw
for item in candidate['members']:
    assert any(row['path'] == item['path'] and row['sha256'] == item['sha256']
               for row in verified)
    assert trees['product'][item['path']] == trees['final'][item['path']]
assert git('cat-file', 'blob', PRODUCT + ':docs/evidence/A15/certificate-exception/candidate-manifest.json') == candidate_raw
source_rel = 'tools/headless_native_reuse_probe_r1.py'
old_raw = (ROOT / 'r1-reference.py').read_bytes()
assert sha(old_raw) == '3f1e4a425e18ed0e2a28893989f31677ba6b9b7f4b9c3da2800bc925443999c9'
assert git('cat-file', 'blob', BASE + ':' + source_rel) == old_raw
native_equal = []
for name in ('native_windows.py', 'process_check.py'):
    original_path = 'docs/evidence/A12/native-reuse-probe/reviewed-native/' + name
    copied = (EVIDENCE / 'reviewed-native' / name).read_bytes()
    assert git('cat-file', 'blob', BASE + ':' + original_path) == copied
    native_equal.append({'name': name, 'sha256': sha(copied), 'raw_equal': True})
authority = []
provenance = json.loads((EVIDENCE / 'authority-provenance.json').read_bytes())
authority_names = {'AGENTS.md': 'AGENTS.md', 'docs/coordination.md': 'coordination.md',
 'docs/tasks/A15-certificate-exception-reuse.md': 'execution-task.md',
 'docs/tasks/A15-independent-certificate-exception-review.md': 'review-task.md',
 'docs/tasks/A15-certificate-exception-observation-proposal.md': 'proposal.md',
 'docs/approvals/A15-certificate-exception-user-decision.json': 'user-decision.json'}
for item in provenance['authority']:
    if item.get('git_commit') == WORKFLOW:
        copied = (EVIDENCE / 'authority' / authority_names[item['source']]).read_bytes()
        assert sha(copied) == item['sha256']
        assert git('cat-file', 'blob', WORKFLOW + ':' + item['source']) == copied
        authority.append({'source': item['source'], 'sha256': sha(copied), 'raw_equal': True})
old = old_raw.decode('utf-8')
new = (ROOT / 'tools/headless_cert_exception_reuse_probe.py').read_bytes().decode('utf-8')
derived = ''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                    fromfile=BASE + ':' + source_rel,
                    tofile='tools/headless_cert_exception_reuse_probe.py')).encode('utf-8')
assert derived == (EVIDENCE / 'r1-derived-raw.diff').read_bytes()
failure = json.loads((EVIDENCE / 'packaging-first-failure.json').read_bytes())
diagnostic_lines = [{'line': line, 'hex': derived.splitlines(True)[line - 1].hex()}
                    for line in failure['trailing_whitespace_lines']]
assert len(diagnostic_lines) == 17 and all(item['hex'] == '200a' for item in diagnostic_lines)
assert failure['individual_check_exit_code'] is None
assert failure['suite_started'] is False
old_tree = ast.parse(old)
new_tree = ast.parse(new)
old_nodes = {node.name: node for node in old_tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
new_nodes = {node.name: node for node in new_tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
invariants = ['utc', 'digest', 'save_new', 'StopProbe', 'safe_error', 'NativePolicy', 'NativeGuard',
 'close_owned', 'initial_release', 'load_native', 'profile_binding', 'emit_occupancy_count',
 'accept_occupancy_zero', 'initial_observation', 'guard_snapshot', 'require_running_guard',
 'apply_terminal_guard', 'record_observation_error', 'OwnedJob']
raw_bodies = []
for name in invariants + ['observe_page', 'finalize_observation']:
    prior = ast.get_source_segment(old, old_nodes[name])
    current = ast.get_source_segment(new, new_nodes[name])
    normalized = prior.replace('AUTHENTICATED_VIEWER_OBSERVED', 'AUTHENTICATED_VIEWER') if name in ('observe_page', 'finalize_observation') else prior
    assert normalized == current
    raw_bodies.append({'name': name, 'old_lines': [old_nodes[name].lineno, old_nodes[name].end_lineno],
                      'new_lines': [new_nodes[name].lineno, new_nodes[name].end_lineno],
                      'raw_equal_except_enum': True, 'new_source_sha256': sha(current.encode('utf-8'))})
changed = sorted(name for name in old_nodes if name in new_nodes and
                 ast.get_source_segment(old, old_nodes[name]) != ast.get_source_segment(new, new_nodes[name]))
syntax = []
for relative in ('tools/headless_cert_exception_reuse_probe.py',
                 'tools/a15_observation_launcher.py', 'tools/a15_cert_exception_gate_delta.py'):
    parsed = ast.parse((ROOT / relative).read_bytes())
    syntax.append({'path': relative, 'ast_parse_only': True, 'import_or_execution': False})
calls = [{'function': node.func.attr, 'line': node.lineno} for node in ast.walk(new_tree)
         if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
         and node.func.attr in ('goto', 'launch_persistent_context')]
assert [item['function'] for item in calls].count('goto') == 1
assert [item['function'] for item in calls].count('launch_persistent_context') == 1
report = {'task': 'A15', 'phase': 'STATIC_ONLY_WAITING_NEW_AUTHOR_DELIVERY',
 'at': datetime.now(timezone.utc).isoformat(), 'base': BASE, 'product': PRODUCT, 'failed_final': FINAL,
 'candidate_manifest_sha256': EXPECTED_CANDIDATE, 'delivery_manifest_sha256': EXPECTED_DELIVERY,
 'fixed_raw_members_including_manifest': len(verified) + 1, 'candidate_members': len(candidate['members']),
 'raw_members': verified, 'preservation': preserved, 'authoritative_raw': authority,
 'native_dependencies': native_equal, 'r1_reference_sha256': sha(old_raw),
 'raw_diff': {'sha256': sha(derived), 'size': len(derived), 'exact_recomputed': True,
              'original_diagnostic_lines': diagnostic_lines, 'original_check_exit_code': None,
              'original_check_rerun': False, 'failed_stop_and_not_run_preserved': True},
 'invariant_bodies': raw_bodies, 'changed_r1_top_level_bodies': changed,
 'added_top_level_bodies': sorted(set(new_nodes) - set(old_nodes)), 'syntax': syntax,
 'context_navigation_calls': calls, 'independent_E1_E4_executions': 0,
 'candidate_modules_imported': 0, 'product_subprocesses_created': 0,
 'static_git_processes_only': commands, 'browser_network_profile_native_occupancy_actions': 0,
 'live_activated_by_reviewer': False, 'first_save_readback': 'NOT_RUN'}
write_new('raw-and-source-audit.json', report)
print(json.dumps({'raw_members': len(verified) + 1, 'candidate_members': len(candidate['members']),
 'old_members_preserved': len(trees['base']), 'new_product': preserved['product']['new_members'],
 'new_final': preserved['final']['new_members'], 'invariant_bodies': len(raw_bodies),
 'raw_diff_bytes': len(derived), 'static_git_reads': len(commands), 'E1_E4_executions': 0}))
