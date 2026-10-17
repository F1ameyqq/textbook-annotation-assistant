"""Coordinator audit of the frozen R6 review and single corrected mixed-cycle control."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path('D:/1800')
OUT = Path(__file__).resolve().parent
REVIEW = ROOT / 'docs/evidence/A03/review/P2-R6-mixed-control'
MANIFEST = REVIEW / 'sha256-manifest.json'
REPORT = ROOT / 'docs/tasks/A03-P2-R6-mixed-control-review-report.md'
TARGET = '81d3ec7e42e0a1a76ad744bf59536fc5f68adee4'

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def load(path):
    return json.loads(path.read_bytes())

def write(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write('\n')

def audit_manifest():
    manifest = load(MANIFEST)
    assert sha(MANIFEST.read_bytes()) == 'd8a220955728b327301c2602b7b0fe42d3dc5a65c0eef8964a025b18724744e7'
    assert sha(REPORT.read_bytes()) == 'bd0735fde3f6980d7b38315a4aa9511c197e5c70617524626cfddb68e8ff4d25'
    assert len(manifest['files']) == 157
    assert load(REVIEW / 'input-index.json')['delivery'] == TARGET
    expected = {row['path'] for row in manifest['files']}
    actual = {p.relative_to(ROOT).as_posix() for p in REVIEW.rglob('*') if p.is_file() and p != MANIFEST}
    actual.add(REPORT.relative_to(ROOT).as_posix())
    assert expected == actual
    for row in manifest['files']:
        path = (ROOT / row['path']).resolve()
        assert path.is_relative_to(ROOT)
        raw = path.read_bytes()
        assert len(raw) == row['bytes'] and sha(raw) == row['sha256'], row['path']
    return manifest

def audit_inputs():
    rows = load(REVIEW / 'input-index.json')['files']
    assert len(rows) == 123
    requests = [row['commit'] + ':' + row['path'] for row in rows]
    result = subprocess.run(['git', 'cat-file', '--batch'], cwd=ROOT,
                            input=('\n'.join(requests) + '\n').encode(), capture_output=True, timeout=30)
    assert result.returncode == 0
    data = result.stdout
    offset = 0
    for row in rows:
        end = data.index(b'\n', offset)
        oid, kind, size = data[offset:end].split()
        offset = end + 1
        raw = data[offset:offset + int(size)]
        offset += int(size)
        assert data[offset:offset + 1] == b'\n'
        offset += 1
        assert kind == b'blob' and oid.decode() == row['raw_git_sha1']
        assert raw == (REVIEW / row['file']).read_bytes()
        assert len(raw) == row['bytes'] and sha(raw) == row['sha256']
    assert offset == len(data)
    return len(rows)

def run(name, script, expected_exit, extra=()):
    command = [sys.executable, '-X', 'utf8', '-B', str(script), *extra]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1')
    env.pop('PYTHONPATH', None)
    start = time.monotonic()
    with (OUT / (name + '.stdout.log')).open('xb') as stdout, (OUT / (name + '.stderr.log')).open('xb') as stderr:
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=stdout, stderr=stderr)
        write(OUT / (name + '.start.json'), {'argv': command, 'cwd': str(ROOT), 'pid': process.pid,
              'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'timeout_seconds': 30, 'PYTHONPATH': 'REMOVED', 'source_sha256': sha(script.read_bytes())})
        timed_out = False
        try:
            code = process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()
            code = process.wait(timeout=5)
    record = {'argv': command, 'cwd': str(ROOT), 'pid': process.pid, 'exit_code': code,
              'expected_exit_code': expected_exit, 'elapsed_seconds': time.monotonic() - start,
              'timed_out': timed_out, 'alive': process.poll() is None}
    write(OUT / (name + '.completion.json'), record)
    assert not timed_out and code == expected_exit
    return record

manifest = audit_manifest()
inputs = audit_inputs()
stage = REVIEW / 'input/checkout'
case = load(stage / 'examples/a03/P2-R6-mixed-control/case.json')
old_case = load(stage / 'examples/a03/P2-R5-registration-context/cases/artifact-resource-frame-mixed-cycle/repair-01/case.json')
def resources(c):
    out = {}
    for row in c['resources']:
        raw = (stage/row['file']).read_bytes()
        assert sha(raw) == row['raw_sha256']
        out[row['logical']] = raw
    return out
def diffs(a,b,path=''):
    assert type(a) is type(b),path
    if isinstance(a,dict):
        assert set(a)==set(b),path
        return [d for key in a for d in diffs(a[key],b[key],path+'/'+key)]
    if isinstance(a,list):
        assert len(a)==len(b),path
        return [d for i,(x,y) in enumerate(zip(a,b)) for d in diffs(x,y,path+'/'+str(i))]
    return [path] if a!=b else []
old_res,new_res = resources(old_case),resources(case)
assert set(old_res)==set(new_res)
changed = [k for k in old_res if old_res[k]!=new_res[k]]
assert changed == ['r5-static/cycle-prefix.json']
old_prefix,new_prefix = json.loads(old_res[changed[0]]),json.loads(new_res[changed[0]])
prefix_diff = diffs(old_prefix,new_prefix)
expected = {'/frames/7/event/payload/initial_event_head/hash','/expected_book_head/hash'}
expected |= {'/frames/'+str(i)+'/event/event_hash' for i in range(7,14)}
expected |= {'/frames/'+str(i)+'/event/previous_hash' for i in range(8,14)}
assert len(prefix_diff)==15 and set(prefix_diff)==expected
previous=new_prefix['predecessor']['hash']
for frame in new_prefix['frames']:
    e=frame['event'];assert e['previous_hash']==previous
    assert sha(json.dumps({k:v for k,v in e.items() if k!='event_hash'},ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode())==e['event_hash']
    if 'initial_event_head' in e['payload']:assert e['payload']['initial_event_head']=={'sequence':e['sequence']-1,'hash':previous}
    previous=e['event_hash']
for name in ['accepted_anchor','expected_book_head']:
    value=new_prefix[name];assert value['hash']==new_prefix['frames'][value['sequence']-1]['event']['event_hash']
old_bundle,new_bundle=load(stage/old_case['bundle']),load(stage/case['bundle'])
assert diffs(old_bundle,new_bundle)==['/evidence/1/resource/sha256']
assert new_bundle['evidence'][1]['resource']['sha256']==sha(new_res[changed[0]])
archive = run('archive-verification', REVIEW / 'scripts/archive.py', 0)
entry = run('single-control-replay', stage / 'examples/a03/P2-R6-mixed-control/entry.py', 0, ['--readonly'])
result=load(OUT/'single-control-replay.stdout.log')
assert result['actual']=='MIXED_CYCLE' and result['reached_layers']==['MIXED_DAG']
assert result['measured_calls']=={'R5_complete_entry':1,'R3_inherited_entry':1,'R2_inherited_entry':1}
assert result['R3_entry_counter_delta']==1 and not result['consumer_failures']
assert result['none_book_real_consumers']==0 and len(result['actual_ring_edges'])==5 and all(x['observed_in_actual_graph'] for x in result['actual_ring_edges'])
release=load(REVIEW/'process-release.json')
assert len(release['owned_runs'])==3 and all(x['exit_code']==0 and not x['timed_out'] and not x['alive_after_wait'] for x in release['owned_runs'])
assert release['remaining_owned_background_workers']==release['native_sessions']==0
audit_manifest()
checks={'task_id':'A03','target_commit':TARGET,'decision':'ACCEPTED_STATIC_LIMITED','scope':'R6 single corrected mixed-cycle control proof only',
 'review_manifest_entries':len(manifest['files']),'raw_git_inputs_verified':inputs,'review_archive_unchanged_after_reproduction':True,
 'report_sha256':sha(REPORT.read_bytes()),'manifest_sha256':sha(MANIFEST.read_bytes()),
 'data_only_verification':{'changed_resources':changed,'prefix_changed_paths':prefix_diff,'bundle_changed_paths':['/evidence/1/resource/sha256'],'event_chain_and_internal_heads_valid':True},
 'archive_command':archive,'entry_command':entry,'entry_result':result,'coordinator_Package_calls':1,
 'review_owned_runs_exited':3,'coordinator_owned_runs_exited':2,'product_native_DB_platform_model_calls':0,
 'full_suite_rerun':False,'integrated':False,'remote_push':False,'oracle_adopted':False,'A03_product_accepted':False,'I01_released':False,
 'field_reset':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'}
write(OUT/'A03-R6-review-check.json',checks)
print(json.dumps({k:checks[k] for k in ['decision','scope','review_manifest_entries','raw_git_inputs_verified','coordinator_Package_calls']}))
