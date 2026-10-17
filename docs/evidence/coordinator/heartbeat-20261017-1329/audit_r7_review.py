"""Coordinator read-only raw-byte/release audit. Does not rerun author checks."""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path('D:/1800')
OUT = Path(__file__).resolve().parent
E = ROOT / 'docs/evidence/A03/review/P2-R7-readonly-codec'
def sha(b): return hashlib.sha256(b).hexdigest()
def read(p): return json.loads(p.read_bytes())
def check_file(p, row):
    b = p.read_bytes()
    assert sha(b) == row['sha256'], str(p)
    assert len(b) == row['bytes'], str(p)
    return b

report = ROOT / 'docs/tasks/A03-P2-R7-readonly-codec-review-report.md'
assert sha(report.read_bytes()) == '5a49c435846423c131f489a67ee412f65c736a7153f80ceb7c0032f807dcfb0e'
manifest = E / 'sha256-manifest.json'
assert sha(manifest.read_bytes()) == '4c53d47a098a2cc3ef3f958322e91b2a57b28f6dfcca5375a9826f97d41f19c6'
m = read(manifest)
for row in m['files']: check_file(ROOT / row['path'], row)
actual = {p.relative_to(ROOT).as_posix() for p in E.rglob('*') if p.is_file()} | {report.relative_to(ROOT).as_posix()}
assert actual == {r['path'] for r in m['files']} | {manifest.relative_to(ROOT).as_posix()}

raw = read(E/'raw-source-index.json')['entries']
inputs = read(E/'input-index.json')['files'] + read(E/'compatibility-input-supplement.json')['files']
entries = inputs + raw
requests = [r['commit']+':'+r['path'] for r in entries]
proc = subprocess.run(['git','cat-file','--batch'], input=('\n'.join(requests)+'\n').encode(), cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
assert proc.returncode == 0
stream = io.BytesIO(proc.stdout)
for row in entries:
    header = stream.readline().decode().split()
    assert len(header) == 3 and header[1] == 'blob', row['path']
    b = stream.read(int(header[2])); assert stream.read(1) == b'\n'
    assert len(b) == row['bytes'] and sha(b) == row['sha256'], row['path']
    assert header[0] == row.get('raw_git_sha1',row.get('git_blob')), row['path']
    if 'file' in row: assert (E/row['file']).read_bytes() == b, row['file']
assert not stream.read()
old = read(E/'protected-old-files.json')['files']
for row in old: check_file(ROOT/row['path'],row)

release = read(E/'process-release.json')
for kind in ('parents','children'):
    for row in release[kind]:
        d = E/'runs'/row['run'] if kind == 'parents' else E/row['record']
        reg = read(d/'registration.json'); start = read(d/'started.json'); end = read(d/'completion.json')
        assert row['pid'] == start['pid'] == end['pid']
        assert row['exit_code'] == end['exit_code']
        assert not row['alive'] and not row['timed_out'] and not end['timed_out']
        assert end.get('alive_after_wait',end.get('alive')) is False
        assert reg['argv'] == end['argv'] and reg['cwd'] == end['cwd']
        for field, file in [('registration_sha256','registration.json'),('completion_sha256','completion.json'),('stdout_sha256','stdout.log'),('stderr_sha256','stderr.log')]:
            assert sha((d/file).read_bytes()) == row[field], str(d/file)
        if kind == 'parents': assert sha((d/'entry-source.py').read_bytes()) == row['script_sha256']

wheel = E/'input/checkout/docs/evidence/A03/execution/P2-R7-readonly-codec/distribution/annotation_contracts-0.1.0-py3-none-any.whl'
assert sha(wheel.read_bytes()) == 'c22c1bcae684d36bf0d39c1fd4c357409e093648157e8132f7b305245b7d02c7'
with zipfile.ZipFile(wheel) as z:
    names = [n for n in z.namelist() if n.startswith('annotation/contracts/a03_bridge/') and not n.endswith('/')]
    assert len(names) == 16
    for n in names: assert z.read(n) == (E/'input/checkout/src'/n).read_bytes()
result = dict(status='PASS', review_report_sha256=sha(report.read_bytes()), review_manifest_sha256=sha(manifest.read_bytes()), manifest_entries=len(m['files']), total_archive_files=len(actual), isolated_raw_copies=len(inputs), original_raw_pins=len(raw), protected_old_files=len(old), parents=len(release['parents']), children=len(release['children']), wheel_members=len(names), failures_preserved=release['failed_checks_retained'], c01_interpretation='Original 70-case review round had isolation/decode failures; two affected original methods passed targeted completion. Not a first-round all-green claim.', native_sessions=0, product_tests_run=False, process_release_basis='Owned recorded starts and waited exits, not an OS/profile scan')
(OUT/'review-archive-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
