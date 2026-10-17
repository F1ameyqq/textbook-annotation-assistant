# -*- coding: utf-8 -*-
"""Read frozen author records and original byte streams; never execute author code."""
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1]
PREFIX = 'docs/evidence/A03/execution/P2-R7-readonly-codec'
AUTHOR = OUT / 'input/checkout' / PREFIX

def load(path):
    return json.loads(path.read_text(encoding='utf8'))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

delivery = {row['path']: row for row in load(OUT / 'delivery-byte-index.json')['files']}
parent_release = load(AUTHOR / 'process-release.json')['runs']
child_release = load(AUTHOR / 'nested-process-release.json')['children']
assert len(parent_release) == 13 and len(child_release) == 10
parents, children = [], []
for row in parent_release:
    relative = PREFIX + '/runs/' + row['run']
    directory = OUT / 'input/checkout' / relative
    registration = load(directory / 'registration.json')
    exit_record = load(directory / 'exit.json')
    started = load(directory / 'started.json')
    assert registration['argv'] == exit_record['argv']
    assert registration['cwd'] == exit_record['cwd']
    assert 0 < registration['timeout_seconds'] <= 60
    assert exit_record['owned_pid'] == row['pid']
    assert row['pid'] in started.values()
    assert not exit_record['alive'] and not exit_record['timed_out']
    assert row['exit_code'] == exit_record['exit_code']
    for stream in ('stdout', 'stderr'):
        assert sha(directory / (stream + '.txt')) == row[stream + '_sha256']
    snapshot = delivery.get(relative + '/registered-script.py')
    assert snapshot is not None
    assert snapshot['sha256'] == registration['script_sha256']
    parents.append({'run': row['run'], 'pid': row['pid'], 'exit_code': row['exit_code'],
                    'alive': False, 'timed_out': False, 'raw_stream_hashes_verified': True,
                    'registered_script_raw_blob_sha256': snapshot['sha256']})
for row in child_release:
    directory = OUT / 'input/checkout' / row['record']
    registration = load(directory / 'registration.json')
    exit_record = load(directory / 'exit.json')
    assert registration['argv'] == exit_record['argv']
    assert registration['cwd'] == exit_record['cwd']
    assert 0 < registration['timeout_seconds'] <= 30
    assert row['pid'] == exit_record['pid']
    assert row['exit_code'] == exit_record['exit_code']
    assert not exit_record['alive'] and not exit_record['timed_out']
    for stream in ('stdout', 'stderr'):
        assert sha(directory / (stream + '.txt')) == row[stream + '_sha256']
    children.append({'record': row['record'], 'pid': row['pid'], 'exit_code': row['exit_code'],
                     'alive': False, 'timed_out': False, 'raw_stream_hashes_verified': True})

freeze = (AUTHOR / 'runs/freeze-01/stderr.txt').read_text(encoding='utf8')
prepare = (AUTHOR / 'runs/prepare-01/stderr.txt').read_text(encoding='utf8')
assert 'AssertionError: pyproject.toml' in freeze
assert 'TypeError: can only concatenate tuple (not "list") to tuple' in prepare
assert {r['run'] for r in parents if r['exit_code']} == {'freeze-01', 'prepare-01'}
product = load(AUTHOR / 'product-01-result.json')
assert product['tests_run'] == 13 and not product['failures'] and not product['errors']
assert len(product['skipped']) == 1 and '1314' in product['skipped'][0][1]
path = load(AUTHOR / 'path-01-result.json')
assert path['tests_run'] == 1 and not path['skipped'] and path['successful']
assert path['nested_children'] == 1
path_child = load(AUTHOR / 'nested-processes/path-01/child-01/exit.json')
assert 'mklink' in path_child['argv'] and '/J' in path_child['argv']
assert path_child['exit_code'] == 0
adjustment = load(AUTHOR / 'seal-adjustment.json')
assert not adjustment['log_bytes_changed'] and adjustment['test_or_codec_reruns'] == 0
provisional = load(AUTHOR / 'provisional/sha256-manifest.json')
# The final delivery retained the initial manifest and process release as raw blobs.
assert sha(AUTHOR / 'provisional/sha256-manifest.json') == adjustment['initial_manifest_sha256']
assert (AUTHOR / 'provisional/process-release.json').is_file()
assert '**/stderr.txt -whitespace' in (AUTHOR / '.gitattributes').read_text(encoding='utf8')
wheel_log = (AUTHOR / 'runs/wheel-01/stderr.txt').read_bytes()
assert wheel_log.endswith(b'\n\n')
result = {
    'status': 'AUTHOR_FROZEN_RECORDS_INDEPENDENTLY_CHECKED',
    'parent_count': len(parents), 'nested_count': len(children),
    'parents': parents, 'children': children,
    'failure_history': {
        'freeze-01': {'exit_code': 1, 'actual': 'raw Git bytes compared directly with CRLF checkout pyproject',
                      'stderr_sha256': sha(AUTHOR / 'runs/freeze-01/stderr.txt')},
        'prepare-01': {'exit_code': 1, 'actual': 'tuple/list concatenation in author preparation script',
                       'stderr_sha256': sha(AUTHOR / 'runs/prepare-01/stderr.txt')},
        'retained_original_script_snapshots': True, 'rerun_by_reviewer': False,
    },
    'author_symlink': {'initial': 'SKIPPED_WINDOWS_1314', 'initial_tests': 13,
                        'passed': 12, 'skipped': 1,
                        'supplement': 'ONE_DIRECTORY_JUNCTION_TEST_PASSED',
                        'supplement_child_exit': 0},
    'whitespace_adjustment': {'original_wheel_stderr_retained': True,
                              'stderr_sha256': sha(AUTHOR / 'runs/wheel-01/stderr.txt'),
                              'provisional_manifest_sha256': sha(AUTHOR / 'provisional/sha256-manifest.json'),
                              'attributes_only_for_raw_logs': True,
                              'reviewer_rebuild_install_or_author_test_rerun': False},
    'basis': 'Frozen records, raw log hashes and raw-Git delivery index; no OS/profile scan',
    'field_reset': 'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION',
}
with (OUT / 'author-evidence-audit.json').open('x', encoding='utf8', newline='\n') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
    f.write('\n')
print(json.dumps({'status': result['status'], 'parents': len(parents), 'children': len(children)}))
