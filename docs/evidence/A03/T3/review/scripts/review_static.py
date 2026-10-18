"""Independent document/source audit. No product imports or database access."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

REPO = Path('D:/1800')
ROOT = Path('D:/1800/.local/A03-T3-independent-review')
OUT = REPO / 'docs/evidence/A03/T3/review'
TARGET = '3fcdb73416142a0a85dfb951a7f839849871c549'
BASE = '1330047dd29890dea0e433ff01b991f615bf78f4'
WORKFLOW = 'f7084b2e8f2e9a1fcf758f9cba56ec9c9fb1f304'
REVIEW_WORKFLOW = '69ef1b3456c7c44c463c4f4fb43b6064b8cf4e09'
COMMANDS = []
CACHE = {}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def git(*args):
    argv = ['git', '-c', 'core.longpaths=true', *args]
    result = subprocess.run(argv, cwd=str(REPO), stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=45, check=False)
    COMMANDS.append({'argv': argv, 'cwd': str(REPO), 'exit_code': result.returncode,
                     'stdout_bytes': len(result.stdout), 'stdout_sha256': sha(result.stdout),
                     'stderr': result.stderr.decode('utf-8', 'replace'),
                     'timeout_seconds': 45, 'completed_and_reaped': True})
    if result.returncode:
        raise RuntimeError('Static Git read failed: ' + repr(argv))
    return result.stdout

def raw(commit, path):
    key = (commit, path)
    if key not in CACHE:
        CACHE[key] = git('show', commit + ':' + path)
    return CACHE[key]

def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    changed = git('diff', '--name-status', BASE, TARGET, '--').decode('utf-8').splitlines()
    expected = {
        'docs/tasks/A03-T3-remaining-matrix.md',
        'docs/tasks/A03-T3-integration-plan.md',
        *('docs/evidence/A03/T3/execution/' + name for name in
          ['audit_references.py', 'manifest.json', 'reference-index.json', 'static-validation.json'])}
    assert set(changed) == {'A\t' + name for name in expected}, changed
    product_diff = git('diff', '--name-only', BASE, TARGET, '--', 'src', 'examples', 'tests')
    assert not product_diff
    for path in sorted(expected):
        dest = ROOT / 'frozen-target' / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw(TARGET, path))
    manifest_path = 'docs/evidence/A03/T3/execution/manifest.json'
    manifest_raw = raw(TARGET, manifest_path)
    assert sha(manifest_raw) == 'c5e801a381a04360ae223dd26ecf21fab9cd3db377985b7378ad0c8ebd998423'
    manifest = json.loads(manifest_raw)
    member_checks = []
    for item in manifest['members']:
        data = raw(TARGET, item['path'])
        assert len(data) == item['bytes'] and sha(data) == item['sha256'], item['path']
        member_checks.append({'path': item['path'], 'bytes': len(data), 'sha256': sha(data), 'matches': True})
    assert {item['path'] for item in member_checks} == expected - {manifest_path}

    index = json.loads(raw(TARGET, 'docs/evidence/A03/T3/execution/reference-index.json'))
    checks = []
    for item in index['references']:
        data = raw(item['commit'], item['path'])
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        assert len(data) == item['raw_bytes'] and sha(data) == item['raw_sha256'] and blob == item['blob_sha1'], item['path']
        lines = data.decode('utf-8-sig').splitlines()
        assert len(lines) == item['line_count']
        for anchor in item['selected_anchors']:
            assert lines[anchor['line'] - 1] == anchor['text']
        links = item.get('linked_manifest_release_indexes', [])
        for link in links:
            linked = raw(link['commit'], link['path'])
            assert len(linked) == link['raw_bytes'] and sha(linked) == link['raw_sha256']
            json.loads(linked)
        checks.append({'label': item['label'], 'commit': item['commit'], 'path': item['path'],
                       'raw_bytes': len(data), 'raw_sha256': sha(data), 'matches': True,
                       'linked_indexes_verified': len(links)})
        if item['label'] in {'STATIC', 'ENTRY'}:
            dest = ROOT / 'product-source' / item['path']
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)

    rows = {}
    matrix = raw(TARGET, 'docs/tasks/A03-T3-remaining-matrix.md').decode('utf-8')
    original_rows = {}
    for path in ['docs/tasks/A03-runtime-recovery.md', 'docs/tasks/A03-independent-review.md']:
        data = raw(WORKFLOW, path)
        for line in data.decode('utf-8').splitlines():
            match = re.match(r'^\| ([VR]\d{2}) \|', line)
            if match:
                original_rows[match.group(1)] = line
    for line in matrix.splitlines():
        match = re.match(r'^\| ([VR]\d{2}) \|', line)
        if match:
            assert match.group(1) not in rows
            rows[match.group(1)] = line
    ids = ['V%02d' % n for n in range(1, 11)] + ['R%02d' % n for n in range(1, 19)]
    assert list(rows) == ids and set(original_rows) == set(ids)
    indexed_map = {item['id']: item for item in index['original_28_requirements']}
    for key in ids:
        assert indexed_map[key]['original']['row'] == original_rows[key]
        assert indexed_map[key]['new_row'] == rows[key]
    handoff = raw(REVIEW_WORKFLOW, 'docs/tasks/A03-T3-review-handoff.md')
    preflight = json.loads(raw(REVIEW_WORKFLOW, 'docs/evidence/coordinator/heartbeat-20261018-0237/split-delivery-preflight.json'))['results']['A03-T3']
    assert preflight['target_commit'] == TARGET and preflight['members_raw_hash_verified'] == 5
    static = json.loads(raw(TARGET, 'docs/evidence/A03/T3/execution/static-validation.json'))
    author_release = all(item['completed_and_reaped'] and item['exit_code'] == 0 for item in static['commands'])
    save_json(OUT / 'identity-and-reference-audit.json', {
        'scope': 'INDEPENDENT_STATIC_DOCUMENT_SOURCE_REVIEW_ONLY', 'target': TARGET,
        'base': BASE, 'original_workflow': WORKFLOW, 'review_workflow': REVIEW_WORKFLOW,
        'review_handoff_raw_sha256': sha(handoff), 'changed_paths': changed,
        'product_examples_tests_diff': [], 'delivery_manifest_sha256': sha(manifest_raw),
        'manifest_members': member_checks, 'reference_checks': checks,
        'mapped_ids': ids, 'mapping_note': 'Identifier/text correspondence only; semantic findings are in review report.',
        'author_recorded_git_commands_completed': author_release,
        'author_command_count': len(static['commands']),
        'no_author_verifier_execution': 'Hardcoded ROOT/OUT would write author worktree. Independently checked raw references instead.',
        'product_imports': 0, 'business_runs': 0, 'database_connections': 0,
        't1_t2_new_results_used_to_update_frozen_matrix': False,
        'historical_full_corpus_copied': False,
        'review_commands': COMMANDS,
        'release': 'All synchronous static Git subprocesses completed and were reaped. No business or background process started.'})
    print(json.dumps({'manifest_members': len(member_checks), 'reference_entries': len(checks),
                      'linked_indexes': sum(x['linked_indexes_verified'] for x in checks),
                      'mapped_ids': len(ids), 'author_commands': len(static['commands']),
                      'review_git_commands': len(COMMANDS), 'status': 'STATIC_IDENTITY_REFERENCE_CHECKS_PASS'}, ensure_ascii=False))

if __name__ == '__main__':
    main()
