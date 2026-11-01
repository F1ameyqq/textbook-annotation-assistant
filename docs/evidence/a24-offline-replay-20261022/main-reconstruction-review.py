"""One-shot local review of the fixed offline handoff, never a live launcher."""
from pathlib import Path, PurePosixPath
import argparse, datetime, hashlib, json, os, stat, subprocess, sys, unicodedata, zipfile

p = argparse.ArgumentParser()
p.add_argument('archive', type=Path)
p.add_argument('sha256')
p.add_argument('target', type=Path)
a = p.parse_args()
sha = lambda b: hashlib.sha256(b).hexdigest()
raw = a.archive.read_bytes()
assert sha(raw) == a.sha256, 'ARCHIVE_HASH_MISMATCH'
target = a.target.resolve()
assert not target.exists(), 'FRESH_REVIEW_ROOT_REQUIRED'
with zipfile.ZipFile(a.archive) as z:
    rows = z.infolist()
    assert len(rows) < 1000 and sum(r.file_size for r in rows) < 20_000_000
    keys = set()
    for r in rows:
        n = r.filename
        parts = n.split('/')
        assert not r.is_dir() and not r.flag_bits & 1
        assert not PurePosixPath(n).is_absolute() and '\\' not in n and ':' not in n
        assert all(c and c not in {'.', '..'} and c.rstrip('. ') == c for c in parts)
        for c in parts:
            stem = c.split('.')[0].upper()
            assert stem not in {'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(1,10)),*(f'LPT{i}' for i in range(1,10))}
            assert not any(ord(x) < 32 for x in c)
        mode = r.external_attr >> 16
        assert stat.S_IFMT(mode) in (0, stat.S_IFREG)
        key = unicodedata.normalize('NFC', n).casefold()
        assert key not in keys, 'DUPLICATE_ARCHIVE_PATH'
        keys.add(key)
    for key in keys:
        assert not any('/'.join(key.split('/')[:i]) in keys for i in range(1,len(key.split('/'))))
    target.mkdir(parents=True)
    extract = target / 'extracted'
    extract.mkdir()
    for r in rows:
        dest = extract.joinpath(*r.filename.split('/'))
        assert extract in dest.parents
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open('xb') as f:
            f.write(z.read(r))
package = extract / 'a24-offline-replay'
entry = package / 'offline_replay.py'
env = os.environ.copy()
env['PYTHONDONTWRITEBYTECODE'] = '1'
calls = []
def run(args, expected=0):
    cmd = [sys.executable, '-B', str(entry), *map(str,args)]
    r = subprocess.run(cmd, cwd=package, env=env, capture_output=True, text=True, timeout=45)
    calls.append({'argv':cmd,'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
    assert (r.returncode == 0) == (expected == 0), calls[-1]
    return r

run(['verify'])
tree = target / 'effective'
run(['rebuild','--target',tree])
effective = json.loads((package/'manifests/effective-manifest.json').read_bytes())
def verify_tree():
    files = {f.relative_to(tree).as_posix():f for f in tree.rglob('*') if f.is_file()}
    assert set(files) == {m['path'] for m in effective['members']}
    for m in effective['members']:
        b = files[m['path']].read_bytes()
        assert len(b) == m['bytes'] and sha(b) == m['sha256']
verify_tree()
run(['rebuild','--target',tree], expected=1)
verify_tree()
owner = tree/'src/annotation/runtime/live_pilot/owner.py'
good = owner.read_bytes()
owner.write_bytes(good+b'\n# main-review deliberate corruption\n')
bad_reports, bad_temp = target/'must-not-create-reports', target/'must-not-create-temp'
run(['test','--tree',tree,'--report-dir',bad_reports,'--temp-dir',bad_temp], expected=1)
assert not bad_reports.exists() and not bad_temp.exists(), 'TAMPER_IMPORT_OR_OUTPUT_NOT_REJECTED_EARLY'
owner.write_bytes(good)
verify_tree()
root_manifest = package/'root-manifest.json'
root_bytes = root_manifest.read_bytes()
root_manifest.rename(package/'root-manifest.withheld')
run(['verify'], expected=1)
(package/'root-manifest.withheld').rename(root_manifest)
assert root_manifest.read_bytes() == root_bytes
run(['verify'])
report = {'schema':'A24OfflinePackageMainReconstructionReview/v1',
          'recorded_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'archive_sha256':a.sha256,'archive_bytes':len(raw),'zip_members':len(rows),
          'reconstructed_members':len(effective['members']),
          'negative_cases':['existing target rejected without mutation','tampered source rejected before import or output','missing root manifest rejected'],
          'calls':calls,'decision':'PASS_RECONSTRUCTION_AND_THREE_NEGATIVES_ONLY_LIVE_HOLD',
          'synthetic_suites_delegated_to_independent_reviewer':True,
          'browser_or_platform_actions':0,'model_api_calls':0,'write_allowed':False}
with (target/'main-review.json').open('x',encoding='utf-8',newline='\n') as f:
    json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({k:report[k] for k in ['archive_sha256','zip_members','reconstructed_members','negative_cases','decision']}))
