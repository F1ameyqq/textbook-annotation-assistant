"""Independent static preparation. No product import, SQL, or business execution."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

SOURCE = Path('D:/1800-worktrees/i01-a')
ROOT = Path('D:/1800-i01-review-01a14e1c')
OUT = Path('D:/1800/docs/evidence/I01-A/review')
BASE = 'a1c3c3b2d452ecbdf5c57a8b7372e7d53de0f8d8'
CANDIDATE = 'be68b8d7c645de556d601458d1d493258f063721'
DELIVERY = '3fdc5d37e221fc73410f197605f5d7b8878182d5'
PRODUCT = '6097a06de937fee8876feccedf46920510850b83'
os.environ['GIT_NO_LAZY_FETCH'] = '1'

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def save(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = data if isinstance(data, bytes) else (json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode('utf8')
    with path.open('xb') as f:
        f.write(raw)

def git(*args, repo=SOURCE, data=None):
    return subprocess.check_output(['git', '-c', 'core.longpaths=true', '-C', str(repo), *args], input=data, env=os.environ)

def raw(commit, path):
    return git('show', commit + ':' + path)

def batch(commit, paths):
    packed = git('cat-file', '--batch', data=''.join(commit + ':' + p + '\n' for p in paths).encode())
    offset = 0
    for path in paths:
        end = packed.index(b'\n', offset)
        blob, kind, size = packed[offset:end].decode().split()
        assert kind == 'blob', (path, kind)
        size = int(size)
        data = packed[end + 1:end + 1 + size]
        offset = end + 2 + size
        yield path, data, blob
    assert offset == len(packed)

def main():
    assert not ROOT.exists(), 'Existing run view must never be reused'
    index = Path(git('rev-parse', '--path-format=absolute', '--git-path', 'index', repo=Path('D:/1800')).decode().strip())
    save(OUT/'main-index-before.json', dict(path=str(index), bytes=index.stat().st_size, sha256=sha(index.read_bytes())))
    manifest_raw = raw(DELIVERY, 'docs/evidence/I01-A/execution/manifest.json')
    manifest = json.loads(manifest_raw)
    fixed = {
        'docs/tasks/I01-A-execution-report.md': '59a3d4990162ba4ea798cafb2989e2df2714a757a637eb3d7bc2192f0569b3d9',
        'docs/evidence/I01-A/execution/manifest.json': 'e55f241b6e1c85eec5ed4c09d50361ef7a9a4f1db8aa7bed9045f87d67a187aa',
        'docs/evidence/I01-A/execution/release.json': 'cdb007faa3653719ec058c41a7d209fe98b3437f9d8b52b762841667d4eb685e',
    }
    for path, expected in fixed.items():
        data = raw(DELIVERY, path)
        assert sha(data) == expected, path
        save(OUT/'author-fixed'/path, data)
    entries = manifest['files']
    assert len(entries) == 665 and len({r['path'] for r in entries}) == 665
    audited = []
    selected = []
    for row, (path, data, blob) in zip(entries, batch(DELIVERY, [x['path'] for x in entries])):
        assert len(data) == row['bytes'] and sha(data) == row['sha256'], path
        audited.append(dict(path=path, bytes=len(data), sha256=sha(data), git_blob=blob))
        # Author SQL is never opened. Only fixed JSON and process records are retained.
        if path.endswith('.json') and (path.endswith('/result.json') or path.endswith('/audit.json') or '/static-closure/' in path or path.endswith('/worker-ended.json') or path.endswith('/worker-started.json') or path.endswith('/completed.json') or path.endswith('/old-candidate-refusal.json') or 'freeze-byte' in path or 'staging-check' in path):
            save(OUT/'author-fixed'/path, data)
            selected.append(path)
    changes = git('diff', '--name-status', BASE, DELIVERY).decode().splitlines()
    allowed = ('examples/i01/', 'tests/fixtures/i01/', 'docs/evidence/I01-A/execution/')
    for change in changes:
        status, path = change.split('\t')
        assert status == 'A' and (path.startswith(allowed) or path == 'docs/tasks/I01-A-execution-report.md' or (path.startswith('tests/test_i01') and path.endswith('.py'))), change
    assert not git('diff', '--name-only', BASE, DELIVERY, '--', 'src', 'pyproject.toml', 'requirements.txt', 'examples/a01', 'examples/a02')
    product = git('ls-tree', '-r', PRODUCT, 'src/annotation/runtime', 'src/annotation/contracts/a03_native', 'src/annotation/delivery', 'src/annotation/quality')
    assert product == git('ls-tree', '-r', BASE, 'src/annotation/runtime', 'src/annotation/contracts/a03_native', 'src/annotation/delivery', 'src/annotation/quality')
    ROOT.mkdir()
    git('init', '--quiet', repo=ROOT)
    object_dir = git('rev-parse', '--path-format=absolute', '--git-path', 'objects').decode().strip()
    save(ROOT/'.git/objects/info/alternates', (object_dir+'\n').encode())
    git('update-ref', '--no-deref', 'HEAD', CANDIDATE, repo=ROOT)
    assert git('rev-parse', 'HEAD', repo=ROOT).decode().strip() == CANDIDATE
    prefixes = ['examples/i01', 'tests/fixtures/i01', 'tests/test_i01_preflight.py', 'docs/evidence/I01-A/execution/preparation']
    paths = git('ls-tree', '-r', '--name-only', CANDIDATE, *prefixes).decode().splitlines()
    exported = []
    for path, data, blob in batch(CANDIDATE, paths):
        save(ROOT/path, data)
        exported.append(dict(path=path, bytes=len(data), sha256=sha(data), git_blob=blob, commit=CANDIDATE))
    identity = json.loads((ROOT/'docs/evidence/I01-A/execution/preparation/identity.json').read_bytes())
    view = ROOT/'docs/evidence/I01-A/execution/preparation/raw-view'
    for item in identity['files']:
        p = item['path'].replace('\\','/')
        data = (view/p).read_bytes()
        assert data == raw(BASE, p) and sha(data) == item['sha256'], p
    for item in identity['inputs']:
        p = item['path'].replace('\\','/')
        assert sha((ROOT/p).read_bytes()) == item['sha256'], p
    pins = view/'src/annotation/contracts/a03_native/data/profile.json'
    profile = json.loads(pins.read_bytes())
    for name, expected in profile['implementation_pins']:
        p = view/('src/'+name[1:]) if name.startswith('@') else pins.parent.parent/name
        assert sha(p.read_bytes()) == expected, name
    for name, expected in profile['schema_pins']:
        assert sha((pins.parent/name).read_bytes()) == expected
    for key, name in [('api_sha256','api.json'),('interface_sha256','interface-source.json'),('oracle_sha256','oracle.json')]:
        assert sha((pins.parent/name).read_bytes()) == profile[key]
    assert json.loads((pins.parent/'adoption.json').read_bytes())['profile_sha256'] == sha(pins.read_bytes())
    save(OUT/'static-preparation.json', dict(status='STATIC_READY_NO_BUSINESS_RUN', base=BASE, candidate=CANDIDATE, delivery=DELIVERY, product=PRODUCT, review_root=str(ROOT), raw_manifest_members=audited, changed_paths=changes, allowed_changes=True, product_unchanged=True, author_json_saved=selected, candidate_export=exported, baseline_raw_verified=len(identity['files']), implementation_pins_verified=len(profile['implementation_pins']), author_primary_sql_opened=False, targets=0, dispatches=0, python=sys.executable, python_version=sys.version, at_ns=time.time_ns()))
    print(json.dumps(dict(status='STATIC_READY', members=len(audited), exported=len(exported), base_originals=len(identity['files']), pins=len(profile['implementation_pins']), root=str(ROOT), targets=0, dispatches=0)))

if __name__ == '__main__':
    main()
