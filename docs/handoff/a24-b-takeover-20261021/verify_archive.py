"""Read-only handoff integrity check. No product imports, tests or platform calls."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--ref', default='HEAD')
parser.add_argument('--private', action='store_true', help='Also verify local private originals; unavailable on a different host until transferred')
args = parser.parse_args()
root = Path(__file__).resolve().parents[3]
env = dict(os.environ, GIT_NO_LAZY_FETCH='1')
def git(*parts, data=None):
    return subprocess.run(['git', '-c', 'core.longpaths=true', *parts], cwd=root, env=env,
                          input=data, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout
def safe(value):
    p = PurePosixPath(value)
    if p.is_absolute() or '..' in p.parts or '\\' in value or ':' in value:
        raise ValueError('Unsafe archive path')
    return p.as_posix()
prefix = 'docs/handoff/a24-b-takeover-20261021/'
manifest = json.loads(git('show', args.ref + ':' + prefix + 'manifest.json'))
paths = [safe(r['path']) for r in manifest['members']]
assert len(paths) == len({p.lower() for p in paths}) == manifest['member_count']
batch = git('cat-file', '--batch', data=b''.join((args.ref + ':' + p + '\n').encode() for p in paths))
pos = 0
blobs = {}
for row, path in zip(manifest['members'], paths):
    end = batch.index(b'\n', pos)
    header = batch[pos:end].split()
    assert header[1] == b'blob', path
    size = int(header[2]); raw = batch[end + 1:end + 1 + size]; pos = end + 2 + size
    assert len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256'], path
    assert header[0].decode() == row['blob'], path
    blobs[path] = raw
assert pos == len(batch)
src = {p.decode() for p in git('ls-tree', '-r', '--name-only', '-z', args.ref, '--', 'src/').split(b'\0') if p}
assert src == set(manifest['source_tree_paths'])
frozen_count = 0
for spec in manifest['frozen_manifests']:
    raw = blobs[spec['path']]
    assert hashlib.sha256(raw).hexdigest() == spec['sha256']
    frozen = json.loads(raw)
    for row in frozen['members']:
        path = safe(spec.get('member_base', '') + row['path'])
        data = blobs[path]
        assert len(data) == row['bytes'] and hashlib.sha256(data).hexdigest() == row['sha256'], path
        frozen_count += 1
private_count = 0
if args.private:
    index = json.loads(blobs[prefix + 'private-artifact-index.json'])
    for row in index['members']:
        raw = Path(row['path']).read_bytes()
        assert len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256'], row['kind']
        private_count += 1
print(json.dumps({'result': 'PASS_STATIC_ARCHIVE_INTEGRITY_ONLY', 'members': len(paths),
                  'frozen_member_checks': frozen_count, 'source_files': len(src),
                  'private_refs_checked': private_count, 'product_tests_or_platform_runs': 0}))
