"""Complete only metadata intake after preserving the first schema-key error."""
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
AUTHOR = ROOT / 'docs/evidence/A24/first-save-wire'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def verify(rows, count):
    assert len(rows) == len({row['path'] for row in rows}) == count
    for row in rows:
        raw = (ROOT / row['path']).read_bytes()
        assert len(raw) == row.get('size', row.get('bytes')) and sha(raw) == row['sha256'], row['path']
        assert hashlib.sha1(b'blob ' + str(len(raw)).encode('ascii') + b'\0' + raw).hexdigest() == row.get('blob', row.get('git_blob')), row['path']
        assert row['mode'] == '100644' and row['type'] == 'blob'


inputs = (OUT / 'root-input-manifest.json').read_bytes()
assert sha(inputs) == '165b840054cc18ecaaa1cc89f17c3678c3450f26c842509351a4a78d2cba0326'
verify(json.loads(inputs)['members'], 225)
candidate = (AUTHOR / 'candidate-manifest.json').read_bytes()
delivery = (AUTHOR / 'delivery-final-manifest.json').read_bytes()
assert sha(candidate) == 'ac9573448692f313076a02489a9727cb9131040e22a6c55e5797c11a3e01cf19'
assert sha(delivery) == '03366e94a4b7d3672322839f5581a118c26190df3d5274b41bcd73fa0cb382d1'
verify(json.loads(candidate)['dependencies'], 92)
verify(json.loads(delivery)['members'], 144)
assert sha((AUTHOR / 'release.json').read_bytes()) == '178934cfb5a530623d77e39b3c276b0dbd70bf2372172f1177c60ec19f2ccd59'
result = {'result': 'PASS_RAW_INTAKE_ONLY', 'input_members': 225,
    'candidate_dependencies': 92, 'delivery_members': 144,
    'all_raw_size_sha256_git_blob_mode_type_checks': True,
    'older_failed_delivery_manifest_used_as_authority': False,
    'product_or_suite_runs_before_intake': 0, 'real_resources': 0,
    'metadata_errors_preserved': [
        {'tool_chunk': '0152fe', 'exit_code': 1, 'error': 'PowerShell brace-expansion ParserError; search never ran'},
        {'tool_chunk': '2d7f02', 'exit_code': 1, 'error': "KeyError: members at intake.py:47; 225 root input files already verified; candidate uses dependencies"},
        {'tool_chunk': None, 'exit_code': 'NOT_EXPOSED', 'error': 'Follow-up metadata probe indexed nonexistent files array; two null-array errors; no product action',
         'tool_chunk_identity': 'Only tool output text was forwarded; transcription only'}],
    'correction': 'Read exact schemas: candidate.dependencies, delivery.members and delivery.git_blob; originals left intact'}
with (OUT / 'intake-result.json').open('xb') as stream:
    stream.write((json.dumps(result, indent=2) + '\n').encode('utf-8'))
print(json.dumps({'result': result['result'], 'inputs': 225, 'candidate': 92, 'delivery': 144}))
