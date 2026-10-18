"""One bounded static-auditor correction; preserves the original and all failures."""
from pathlib import Path
import hashlib
import json

root = Path(__file__).resolve().parent
source = (root / 'audit.py').read_text(encoding='utf-8')
replacements = [
    ('def map_path(text):', 'def map_path(text, relative_root=None):'),
    ("path = R / text[len(old):] if text.startswith(old) else Path(text)",
     "path = R / text[len(old):] if text.startswith(old) else Path(text)\n    if not path.is_absolute():\n        path = (relative_root or R) / path"),
    ("raw = map_path(item['path']).read_bytes()", "raw = map_path(item['path'], case / 'runtime').read_bytes()"),
    ("stream = b.proc('author-manifest-blobs', ['cat-file', '--batch'],\n                    data=''.join(b.TARGET + ':' + f['path'] + '\\n' for f in files).encode('utf-8'))",
     "stream = (H / 'static-processes/author-manifest-blobs/stdout.bin').read_bytes()"),
    ("b.write(H / 'author-manifest-check.json', {'target': b.TARGET, 'members': records, 'mismatches': [],\n             'manifest_sha256': sha((E / 'manifest.json').read_bytes()), 'history_reconstructed': False})",
     "check(load(H / 'author-manifest-check.json')['members'] == records, 'retained successful first-pass manifest check reused without rewriting')"),
    ("check(sha(path.read_bytes()) == end[stream + '_sha256'], 'raw subprocess stream exact: ' + str(path))",
     "if stream + '_sha256' in end:\n                check(sha(path.read_bytes()) == end[stream + '_sha256'], 'raw subprocess stream exact: ' + str(path))\n            else:\n                check('process-audit' in folder.parts, 'only the existing native observer uses completion without stream digests')"),
    ("elapsed = (end['ended_at_ns'] - start['started_at_ns']) / 1e9",
     "elapsed = (end['ended_at_ns'] - start['started_at_ns']) / 1e9 if 'ended_at_ns' in end else end['elapsed_seconds']"),
    ("H / 'audit-first-failure.json'", "H / 'audit-correction-failure.json'")
]
for before, after in replacements:
    assert source.count(before) == 1, before
    source = source.replace(before, after)
target = root / 'audit-r1.py'
with target.open('x', encoding='utf-8', newline='\n') as stream:
    stream.write(source)
with (root / 'static-audit-correction.json').open('x', encoding='utf-8', newline='\n') as stream:
    json.dump({'count': 1, 'original': 'audit.py', 'corrected': 'audit-r1.py',
       'original_sha256': hashlib.sha256((root / 'audit.py').read_bytes()).hexdigest(),
       'corrected_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
       'first_failure': 'audit-first-failure.json',
       'cause': 'files.path is runtime-relative; existing native observer completion records use elapsed_seconds and raw retained streams without timestamp/digest fields',
       'changes': ['Anchor files.path to its own case/runtime', 'Interpret existing native observer metadata without fabricating absent fields', 'Reuse retained successful raw-manifest Git check'],
       'business_calls': 0, 'business_reruns': 0, 'product_tool_inputs_expectations_changed': False}, stream, indent=2)
    stream.write('\n')
print(str(target))
