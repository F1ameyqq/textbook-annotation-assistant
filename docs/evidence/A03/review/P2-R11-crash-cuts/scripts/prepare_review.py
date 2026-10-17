"""Static preparation only. Copy complete frozen driver and add raw capture hooks."""
import ast
import difflib
from evidence import OUT,WORK,EV,TARGET,BASE,raw,text,document,sha,write

original=text('tests/test_a03_p2_r11_crash_cuts.py')
assert sha(original.encode())=='0b58c6d589acfe6c81664e1d3940c7eb08e2b0ab77beab5b2a85194b0bae4abc'
capture='''
def capture_stage(case, stage, *, own_writer_keeper):
    """Retain actual sequential raw bytes, then SQL from retained immutable copies."""
    d = case / 'stages' / stage
    d.mkdir(parents=True, exist_ok=False)
    started = time.time_ns()
    result = {'stage': stage, 'pid': os.getpid(), 'started_at_ns': started,
        'own_writer_keeper_active': own_writer_keeper,
        'limit': 'Sequential raw files, not an atomic cross-database snapshot; no SQLite reconstruction.', 'databases': {}}
    for name in ('runtime', 'target'):
        source = case / name / (name + '.sqlite3')
        read_start = time.time_ns()
        body = source.read_bytes()
        read_end = time.time_ns()
        dest = d / (name + '.sqlite3')
        write(dest, body)
        sql = files.read_db(dest, True)
        assert sql['quick_check'] == 'ok' and sql['raw_sha256_before'] == sha(body) == sql['raw_sha256_after']
        sidecars = []
        for suffix in ('-journal', '-wal', '-shm'):
            p = Path(str(source) + suffix)
            if p.is_file():
                value = p.read_bytes()
                write(d / (name + '.sqlite3' + suffix + '.captured'), value)
                sidecars.append({'suffix': suffix, 'bytes': len(value), 'sha256': sha(value)})
        result['databases'][name] = {'source': str(source), 'copy': str(dest), 'bytes': len(body),
            'sha256': sha(body), 'read_started_at_ns': read_start, 'read_ended_at_ns': read_end,
            'source_sha256_after_copy': sha(source.read_bytes()), 'sidecars': sidecars, 'SQL': sql}
    result['ended_at_ns'] = time.time_ns()
    write(d / 'capture.json', result)
    return result

'''
driver=original.replace('import test_a03_p2_r10_owner_fencing as files',
    'sys.path.insert(0, '+repr(str(WORK/'tests'))+')\nimport test_a03_p2_r10_owner_fencing as files',1)
driver=driver.replace('ROOT = Path(__file__).resolve().parents[1]', 'ROOT = Path('+repr(str(WORK))+')',1)
driver=driver.replace('\ndef imports():',capture+'\ndef imports():',1)
driver=driver.replace('        return store, claim, keeper, config',
    "        capture_stage(case, 'pre-fault', own_writer_keeper=True)\n        return store, claim, keeper, config",1)
driver=driver.replace("    before_status = store.status(reg['id'])",
    "    if group in ('F2', 'F3'):\n        capture_stage(case, 'pending-before-projection', own_writer_keeper=False)\n    before_status = store.status(reg['id'])",1)
driver=driver.replace("        read_sequences = [json.loads(row['body'])['read_sequence']",
    "        capture_stage(case, 'UNKNOWN-before-reconcile', own_writer_keeper=False)\n        read_sequences = [json.loads(row['body'])['read_sequence']",1)
driver=driver.replace('            frozen = files.state(case, True)',
    "            capture_stage(case, 'cut-after-wait', own_writer_keeper=False)\n            frozen = files.state(case, True)",1)
driver=driver.replace("            run_phase(root, args.group, 'query')",
    "            run_phase(root, args.group, 'query')\n            capture_stage(case, 'after-query-or-recovery', own_writer_keeper=False)",1)
assert driver.count('capture_stage(case,')==6
assert driver.count('reconcile(store,')==original.count('reconcile(store,')==1
assert not any(t in driver for t in ('exec(', 'monkeypatch', 'mock.patch', 'INSERT ', 'UPDATE ', 'DELETE ', 'os._exit(', 'time.time =', '_pid_alive ='))
for p in WORK.rglob('*.py'):ast.parse(p.read_bytes(),filename=str(p))
ast.parse(driver)
with (OUT/'scripts/crash_driver.py').open('x',encoding='utf8',newline='\n') as f:f.write(driver)
with (OUT/'driver-diff.patch').open('x',encoding='utf8',newline='\n') as f:
    f.writelines(difflib.unified_diff(original.splitlines(True),driver.splitlines(True),fromfile='frozen-R11-driver',tofile='review-driver-with-stage-capture'))
profile=document('src/annotation/contracts/a03_native/data/profile.json')
for p,d in profile['schema_pins']:assert sha(raw('src/annotation/contracts/a03_native/data/'+p))==d
for p,d in profile['implementation_pins']:
    p='src/'+p[1:] if p.startswith('@') else 'src/annotation/contracts/a03_native/'+p
    assert sha(raw(p))==d
storage=text('src/annotation/runtime/storage/__init__.py');recovery=text('src/annotation/runtime/recovery/__init__.py');common=text('src/annotation/runtime/storage/common.py')
points={}
for point,source in [('BEFORE_INTENT_COMMIT',storage),('AFTER_DISPATCH_STARTED',storage),('AFTER_READBACK_CAPTURE',recovery),('AFTER_RECEIPT_COMMIT',storage)]:
    marker='self.fault("'+point+'")' if source is storage else 'store.fault("'+point+'")'
    points[point]={'line':source[:source.index(marker)].count('\n')+1,'source':'storage' if source is storage else 'recovery'}
assert storage.index('self.fault("BEFORE_INTENT_COMMIT")')<storage.index('with self.effect_gate',storage.index('def commit_intent'))
assert recovery.index('observed = observer.observe_target')<recovery.index('store.fault("AFTER_READBACK_CAPTURE")')<recovery.index('record = store.commit_action_result')
assert 'os._exit(int(self.specification.get("exit_code", 90)))' in common
expectations={g:{'point':p,'effect_at_cut':int(g in ('F3','F4')),'reconcile_calls':int(g in ('F2','F3')),'max_attempts':1 if g in ('F2','F3') else None} for g,p in
    [('F1','BEFORE_INTENT_COMMIT'),('F2','AFTER_DISPATCH_STARTED'),('F3','AFTER_READBACK_CAPTURE'),('F4','AFTER_RECEIPT_COMMIT')]}
scripts={p.name:sha(p.read_bytes()) for p in (OUT/'scripts').glob('*.py')}
write(OUT/'driver-preregistration.json',{'target':TARGET,'base':BASE,'original_driver_sha256':sha(original.encode()),
 'driver_sha256':sha(driver.encode()),'scripts':scripts,'expected':expectations,'fault_locations':points,'parent_watchdog_seconds':90,'worker_watchdog_seconds':45,
 'lease_seconds':10,'observation_seconds':2,'barrier_seconds':5,'product_recovery_deadline_unchanged':True,
 'frozen_before_functional_execution':True,'product_calls_in_preparation':0,'product_changes':0,'seed_database_files':0,
 'capture_stages':['pre-fault','cut-after-wait','pending-before-projection (F2/F3)','UNKNOWN-before-reconcile (F2/F3)','after-query-or-recovery'],
 'field_reset':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'})
write(OUT/'static-review.json',{'status':'READY_FOR_F1_THEN_F2_THEN_F3_THEN_F4_ONCE','complete_driver_copy_with_capture_hooks_only':True,
 'normal_imports_no_AST_exec_slicing':True,'product_calls':0,'source_seed_files':len(document_index:=__import__('evidence').load(OUT/'isolated-source-index.json')['files']),
 'schema_pins':len(profile['schema_pins']),'implementation_pins':len(profile['implementation_pins']),'fault_locations':points,
 'old_entries_preserved':32413,'author_intermediate_binary_limitation_preserved':document(EV+'stage-binary-preservation.json')})
print('{"status":"READY_FOR_F1_THEN_F2_THEN_F3_THEN_F4_ONCE","product_calls":0}')
