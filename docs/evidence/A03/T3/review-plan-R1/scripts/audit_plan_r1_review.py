"""Independent C1-C4 document-delta review; no product import or SQL."""
import ast
import difflib
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

REPO = Path('D:/1800')
ROOT = REPO / '.local/A03-T3-independent-review/plan-R1'
OUT = REPO / 'docs/evidence/A03/T3/review-plan-R1'
T = '765aef597a93fe36060fce65e17b22fe1c3408b8'
D = '3fcdb73416142a0a85dfb951a7f839849871c549'
P = '1330047dd29890dea0e433ff01b991f615bf78f4'
W = '0beba0d0c82376b119c46b1d35a137fde541113c'
PREFIX = 'docs/evidence/A03/T3/execution/plan-R1/'
MATRIX = 'docs/tasks/A03-T3-remaining-matrix.md'
PLAN = 'docs/tasks/A03-T3-integration-plan.md'
commands = []
cache = {}

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def git(*args):
    argv = ['git', '-c', 'core.longpaths=true', *args]
    process = subprocess.Popen(argv, cwd=str(REPO), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=45)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill()
        stdout, stderr = process.communicate()
    commands.append({'argv': argv, 'cwd': str(REPO), 'pid': process.pid,
                     'exit_code': process.returncode, 'timeout': timed_out,
                     'waited_and_reaped': True, 'stdout_bytes': len(stdout),
                     'stdout_sha256': sha(stdout), 'stderr': stderr.decode('utf-8', 'replace')})
    if timed_out or process.returncode:
        raise RuntimeError(repr(argv))
    return stdout

def raw(commit, path):
    if (commit, path) not in cache:
        cache[commit, path] = git('show', commit + ':' + path)
    return cache[commit, path]

def write(name, obj):
    (OUT / name).write_bytes((json.dumps(obj, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))

def old_review_hashes():
    manifest_path = REPO / 'docs/evidence/A03/T3/review/manifest.json'
    data = manifest_path.read_bytes()
    result = {manifest_path.relative_to(REPO).as_posix(): sha(data)}
    for item in json.loads(data)['members']:
        current = (REPO / item['path']).read_bytes()
        assert len(current) == item['bytes'] and sha(current) == item['sha256'], item['path']
        result[item['path']] = sha(current)
    return result

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    before = old_review_hashes()
    changed = git('diff', '--name-status', D, T, '--').decode('utf-8').splitlines()
    additions = [PREFIX + name for name in [
        'adoption-and-count-register.json', 'audit_plan_revision.py',
        'first-static-failure/audit_plan_revision.attempt-01.py',
        'first-static-failure/observed-tool-return.json', 'manifest.json',
        'reference-index.json', 'revision-checks.json']]
    expected = {'M\t' + MATRIX, 'M\t' + PLAN} | {'A\t' + name for name in additions}
    assert set(changed) == expected, changed
    assert git('diff', '--name-only', D, T, '--', 'src', 'examples', 'tests') == b''
    for path in [MATRIX, PLAN] + additions:
        dest = ROOT / 'frozen-target' / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw(T, path))
    manifest_raw = raw(T, PREFIX + 'manifest.json')
    assert sha(manifest_raw) == '02b80200878ddf09a08c603dc2a2c45bef4917764d978fc0019d58655f8b7937'
    manifest = json.loads(manifest_raw)
    members = []
    for item in manifest['members']:
        data = raw(T, item['path'])
        assert len(data) == item['bytes'] and sha(data) == item['sha256'], item['path']
        members.append({'path': item['path'], 'raw_bytes': len(data), 'raw_sha256': sha(data), 'matches': True})
    assert {item['path'] for item in members} == {MATRIX, PLAN} | (set(additions) - {PREFIX + 'manifest.json'})
    old_execution = []
    old_paths = git('ls-tree', '-r', '--name-only', D, 'docs/evidence/A03/T3/execution').decode('utf-8').splitlines()
    assert len(old_paths) == 4
    for path in old_paths:
        assert raw(D, path) == raw(T, path)
        old_execution.append({'path': path, 'raw_sha256': sha(raw(D, path)), 'unchanged': True})
    row_re = rb'^\| (?:V\d\d|R\d\d) \|.*$'
    old_rows = re.findall(row_re, raw(D, MATRIX), flags=re.M)
    new_rows = re.findall(row_re, raw(T, MATRIX), flags=re.M)
    assert len(new_rows) == 28 and new_rows == old_rows
    index = json.loads(raw(T, PREFIX + 'reference-index.json'))
    checked = []
    for item in index['references']:
        data = raw(item['commit'], item['path'])
        assert len(data) == item['raw_bytes'] and sha(data) == item['raw_sha256']
        if 'blob_sha1' in item:
            assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == item['blob_sha1']
        lines = data.decode('utf-8').splitlines()
        for excerpt in item.get('excerpts', []):
            assert 1 <= excerpt['start'] <= excerpt['end'] <= len(lines)
            assert excerpt['lines'] == [{'line': i, 'text': lines[i-1]} for i in range(excerpt['start'], excerpt['end'] + 1)]
        checked.append({'commit': item['commit'], 'path': item['path'], 'raw_bytes': len(data),
                        'raw_sha256': sha(data), 'excerpt_ranges': [[e['start'], e['end']] for e in item.get('excerpts', [])],
                        'matches': True, 'product_or_helper_executed': False})
    assert len(checked) == 17
    author_checks = json.loads(raw(T, PREFIX + 'revision-checks.json'))
    assert len(author_checks['commands']) == 29
    assert all(c['waited_and_reaped'] and c['exit_code'] == 0 for c in author_checks['commands'])
    first = raw(T, PREFIX + 'first-static-failure/audit_plan_revision.attempt-01.py')
    corrected = raw(T, PREFIX + 'audit_plan_revision.py')
    delta = list(difflib.unified_diff(first.decode().splitlines(), corrected.decode().splitlines(), lineterm=''))
    changes = [line for line in delta if line.startswith(('+', '-')) and not line.startswith(('+++', '---'))]
    assert len(changes) == 2 and '(145, 150)' in changes[0] and '(145, 149)' in changes[1]
    ast.parse(corrected.decode('utf-8'))
    failure = json.loads(raw(T, PREFIX + 'first-static-failure/observed-tool-return.json'))
    assert failure['exit_code'] == 1 and failure['pid'] is None
    handoff = raw(W, 'docs/tasks/A03-T3-plan-R1-review-handoff.md')
    dispatch = raw(W, 'docs/tasks/A03-T3-plan-revision-handoff.md')
    register = json.loads(raw(T, PREFIX + 'adoption-and-count-register.json'))
    assert register['adoption_seams']['D-M']['product_changes_authorized_this_turn'] is False
    assert register['adoption_seams']['D-CONV']['database_migration'] == 'NOT_AUTHORIZED'
    assert register['adoption_seams']['K']['combination_commit'] is None
    counts = register['bounded_counts']
    assert counts['M']['native_starts_upper'] == 1 + 2 + 2
    assert counts['M']['dispatch_upper'] == 3 + 2*2 + 2*2
    assert counts['L_preferred']['all_business_starts_upper'] == 3 + 2
    assert counts['L_preferred']['all_dispatch_upper'] == 1 + 1 + 2 + 2
    assert counts['L_preferred']['A_pending_sequence'] == [1, 2, 3, 2]
    assert counts['L_optional_not_dispatched']['all_dispatch_upper'] == counts['L_preferred']['all_dispatch_upper'] + 1
    assert counts['F']['dispatch_upper'] == 3 + 2 + 1
    assert old_review_hashes() == before
    write('static-delta-audit.json', {'scope': 'C1_C4_REVISION_ONLY_NO_FULL_28_REVIEW',
        'target': T, 'previous_document_target': D, 'product_base': P, 'review_workflow': W,
        'handoff_raw_sha256': sha(handoff), 'revision_dispatch_raw_sha256': sha(dispatch),
        'changed_paths': changed, 'product_examples_tests_diff': [],
        'target_manifest_sha256': sha(manifest_raw), 'manifest_members': members,
        'preserved_old_execution': old_execution,
        'accepted_28_rows_byte_equal': True, 'accepted_28_rows_semantically_re_reviewed': False,
        'affected_references': checked,
        'author_first_failure': {'exit_code': 1, 'kind': failure['evidence_kind'], 'original_pid_claimed': False,
                                  'correction_diff': delta, 'business_rerun': False},
        'author_corrected_static_commands': 29,
        'old_independent_review_files_unchanged': before,
        'bounded_count_arithmetic_matches': True,
        'author_auditor_executed': False,
        'product_imports': 0, 'business_runs': 0, 'sqlite_connections': 0,
        'new_T2_results_used_to_rewrite_old_plan': False,
        'review_commands': commands,
        'release': 'All recorded read-only Git subprocesses communicated/waited/reaped. No business process or background session created.'})
    print(json.dumps({'target': T, 'manifest_members': len(members), 'affected_references': len(checked),
                      'old_execution_preserved': len(old_execution), 'rows_preserved_not_re_reviewed': 28,
                      'old_independent_review_files_preserved': len(before),
                      'static_git_commands_reaped': len(commands), 'business_runs': 0,
                      'sqlite_connections': 0}, ensure_ascii=False))

if __name__ == '__main__':
    main()
