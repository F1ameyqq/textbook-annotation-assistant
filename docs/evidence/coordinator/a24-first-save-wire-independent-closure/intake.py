"""Fixed raw intake only; does not import or execute any product/helper."""
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
AUTHOR = ROOT / 'docs/evidence/A24/first-save-wire'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def new(name, value):
    raw = value if isinstance(value, bytes) else (json.dumps(value, indent=2) + '\n').encode('utf-8')
    with (OUT / name).open('xb') as stream:
        stream.write(raw)


def verify(rows, count):
    assert len(rows) == len({row['path'] for row in rows}) == count
    for row in rows:
        path = (ROOT / row['path']).resolve()
        assert ROOT.resolve() in path.parents
        raw = path.read_bytes()
        assert len(raw) == row.get('size', row.get('bytes')) and sha(raw) == row['sha256'], row['path']
        assert hashlib.sha1(b'blob ' + str(len(raw)).encode('ascii') + b'\0' + raw).hexdigest() == row['blob'], row['path']
        assert row['mode'] == '100644' and row['type'] == 'blob'


raw = Path('D:/1800/docs/evidence/coordinator/a24-first-save-wire-delivery/input-raw-manifest.json').read_bytes()
assert sha(raw) == '165b840054cc18ecaaa1cc89f17c3678c3450f26c842509351a4a78d2cba0326'
manifest = json.loads(raw)
assert manifest['product'] == '851cf6fce217df8f64a6f3bdeaa99b5e5e2c234d'
assert manifest['final'] == '680bd5f624659f1091db974d5ed30b332ff946dc'
verify(manifest['members'], 225)
new('root-input-manifest.json', raw)
raw = Path('D:/1800/docs/tasks/A24-first-save-wire-fixed-independent-review.md').read_bytes()
assert sha(raw) == '64ffaf55f42fb64e9fc9d0af66945fdddae071ebe09f082b5f83b60a622c8cdb'
new('fixed-review-task.md', raw)
for name, expected, count in (
    ('candidate-manifest.json', 'ac9573448692f313076a02489a9727cb9131040e22a6c55e5797c11a3e01cf19', 92),
    ('delivery-final-manifest.json', '03366e94a4b7d3672322839f5581a118c26190df3d5274b41bcd73fa0cb382d1', 144)):
    raw = (AUTHOR / name).read_bytes()
    assert sha(raw) == expected
    verify(json.loads(raw)['members'], count)
assert sha((AUTHOR / 'release.json').read_bytes()) == '178934cfb5a530623d77e39b3c276b0dbd70bf2372172f1177c60ec19f2ccd59'
new('intake-result.json', {'result': 'PASS_RAW_INTAKE_ONLY', 'input_members': 225,
    'candidate_dependencies': 92, 'delivery_members': 144, 'raw_size_sha256_git_blob_mode_type_verified': True,
    'older_failed_delivery_manifest_used_as_authority': False, 'product_imports_runs': 0, 'real_resources': 0,
    'metadata_search_error': {'tool_chunk': '0152fe', 'exit_code': 1,
        'error': 'PowerShell ParserError: Missing argument in parameter list (shell brace expansion syntax)',
        'effect': 'Search command did not run; no product or input write', 'correction': 'Explicit paths/directories',
        'source': 'Tool text transcription, not raw OS stderr bytes'}})
print(json.dumps({'result': 'PASS_RAW_INTAKE_ONLY', 'inputs': 225, 'candidate': 92, 'delivery': 144}))
