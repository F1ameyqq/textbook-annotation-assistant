"""Independent byte/immutable-SQL audit; no product imports or business APIs."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sqlite3
import sys
import time

import bootstrap as b

H = Path(__file__).resolve().parent
R = H / 'c'
E = R / 'docs/evidence/A03/T2/execution'
I = E / 'validation/independent-01'
A = E / 'validation/author-01'
STAGES = ('before-build', 'unknown-established', 'after-release', 'before-reconcile',
          'after-reconcile', 'before-report', 'after-report')
CHECKS = []

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')

def load(path):
    return json.loads(path.read_bytes())

def check(condition, label):
    CHECKS.append({'check': label, 'pass': bool(condition)})
    if not condition:
        raise AssertionError(label)

def ref(a):
    return {k: a[k] for k in ('artifact_id', 'revision', 'kind', 'content_hash')}

def map_path(text):
    text = text.replace('\\', '/')
    old = 'D:/1800-worktrees/a03-t2/'
    path = R / text[len(old):] if text.startswith(old) else Path(text)
    path = path.resolve()
    path.relative_to(R.resolve())
    return path

def sql(path):
    raw_sha = sha(path.read_bytes())
    db = sqlite3.connect(path.resolve().as_uri() + '?mode=ro&immutable=1', uri=True)
    db.row_factory = sqlite3.Row
    try:
        check(db.execute('PRAGMA quick_check').fetchone()[0] == 'ok', 'immutable quick_check: ' + str(path))
        names = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        result = {'application_id': db.execute('PRAGMA application_id').fetchone()[0],
                  'user_version': db.execute('PRAGMA user_version').fetchone()[0],
                  'tables': {name: [dict(r) for r in db.execute('SELECT * FROM "' + name.replace('"', '""') + '" ORDER BY rowid')]
                             for name in names}}
    finally:
        db.close()
    check(sha(path.read_bytes()) == raw_sha, 'immutable bytes unchanged: ' + str(path))
    return result

def manifest():
    value = load(E / 'manifest.json')
    files = value['files']
    check(len(files) == 317, 'author manifest has 317 members')
    stream = b.proc('author-manifest-blobs', ['cat-file', '--batch'],
                    data=''.join(b.TARGET + ':' + f['path'] + '\n' for f in files).encode('utf-8'))
    offset, records = 0, []
    for item in files:
        end = stream.index(b'\n', offset)
        oid, kind, size = stream[offset:end].decode('ascii').split()
        size = int(size)
        raw = stream[end + 1:end + 1 + size]
        offset = end + 2 + size
        check(kind == 'blob' and len(raw) == size and sha(raw) == item['sha256'] and size == item['bytes'],
              'author raw manifest: ' + item['path'])
        records.append(dict(item, git_blob=oid))
    check(offset == len(stream), 'author raw stream consumed exactly')
    b.write(H / 'author-manifest-check.json', {'target': b.TARGET, 'members': records, 'mismatches': [],
             'manifest_sha256': sha((E / 'manifest.json').read_bytes()), 'history_reconstructed': False})

def phase_audit(root):
    case = root / 'cases/H1'
    stages, summaries = {}, []
    for stage in STAGES:
        folder = case / 'captures' / stage
        capture = load(folder / 'capture.json')
        expected = load(folder / 'SQL.json')
        check(capture['status'] == 'RAW_COPIES_RETAINED' and capture['cross_database_atomic'] is False,
              root.name + ' non-atomic raw copies: ' + stage)
        quiet = capture['writer_boundary']
        check(quiet['business_call_in_flight'] is False and quiet['quiescent']['owned_async_writers'] == 0
              and len(quiet['threads_quiet']) == 1 and quiet['threads_quiet'][0]['name'] == 'MainThread',
              root.name + ' joined writers: ' + stage)
        values, digests = {}, {}
        for record in capture['records']:
            kind = record['kind']
            path = folder / (kind + '.sqlite3')
            raw = path.read_bytes()
            check(not record['sidecars_after_writer_join'] and sha(raw) == record['sha256']
                  == record['source_sha256_after_copy'] == record['source_sha256_after_copy_audit']
                  and len(raw) == record['size'], root.name + ' capture bytes: ' + stage + '/' + kind)
            values[kind] = sql(path)
            check(values[kind] == expected[kind], root.name + ' captured SQL exact: ' + stage + '/' + kind)
            digests[kind] = {'sha256': sha(raw), 'bytes': len(raw), 'file': str(path)}
        tables = values['runtime']['tables']
        registry, = tables['registrations']
        package = map_path(registry['package_root'])
        artifacts = []
        for row in tables['artifacts']:
            artifact = load(map_path(row['path']))
            check(ref(artifact) == json.loads(row['ref']) and sha(canonical({k: v for k, v in artifact.items() if k != 'content_hash'}))
                  == artifact['content_hash'], root.name + ' registered artifact raw/content: ' + stage + '/' + artifact['artifact_id'])
            artifacts.append(artifact)
        for item in tables['files']:
            raw = map_path(item['path']).read_bytes()
            check(sha(raw) == item['sha'] and len(raw) == item['size'], root.name + ' immutable file: ' + stage + '/' + item['path'])
        known = {canonical(ref(a)): a for a in artifacts}
        resources = set()
        def walk(value, refs):
            if isinstance(value, dict):
                if set(value) == {'artifact_id', 'revision', 'kind', 'content_hash'}:
                    check(canonical(value) in known, root.name + ' actual ordinary reference exists: ' + stage)
                    refs.add(canonical(value))
                    return
                if {'path', 'sha256', 'media_type'} <= set(value):
                    path = (package / value['path']).resolve()
                    path.relative_to(package)
                    raw = path.read_bytes()
                    check(sha(raw) == value['sha256'], root.name + ' actual resource hash: ' + stage + '/' + value['path'])
                    token = (value['path'], value['sha256'])
                    if token not in resources:
                        resources.add(token)
                        if value['media_type'] == 'application/json':
                            walk(json.loads(raw), refs)
                    return
                for child in value.values():
                    walk(child, refs)
            elif isinstance(value, list):
                for child in value:
                    walk(child, refs)
        for artifact in artifacts:
            refs = set()
            # Per-consumer traversal may not inherit another consumer's declarations.
            resources.clear()
            walk(artifact, refs)
            check(refs <= {canonical(x) for x in artifact['input_refs']}, root.name + ' declared closure: ' + stage + '/' + artifact['artifact_id'])
        events = [json.loads(row['body']) for row in tables['events']]
        predecessor = '0' * 64
        for sequence, event in enumerate(events, 1):
            check(event['sequence'] == sequence and event['previous_hash'] == predecessor
                  and sha(canonical({k: v for k, v in event.items() if k != 'event_hash'})) == event['event_hash'],
                  root.name + ' actual event hash chain: ' + stage + '/' + str(sequence))
            predecessor = event['event_hash']
        book, = tables['books']
        check(book['head_hash'] == predecessor and book['head_sequence'] == len(events), root.name + ' actual event head: ' + stage)
        stages[stage] = {'raw': values, 'artifacts': artifacts, 'registry': registry, 'package': package, 'events': events}
        target = json.loads(next(r['value'] for r in values['target']['tables']['meta'] if r['key'] == 'state'))
        summaries.append({'stage': stage, 'raw_databases': digests, 'artifact_count': len(artifacts), 'event_count': len(events),
            'intent_states': [r['state'] for r in tables['intents']], 'action_states': [r['state'] for r in tables['actions']],
            'native_report_reads': tables['native_report_reads'], 'effects': len(values['target']['tables']['effects']),
            'questions': len(target['target']['questions']), 'frames': len(target['target']['frames']),
            'owner': {k: book[k] for k in ('owner', 'pid', 'phase', 'lease', 'generation')}})

    def rt(stage):
        return stages[stage]['raw']['runtime']['tables']
    def tt(stage):
        return stages[stage]['raw']['target']['tables']
    def artifacts(stage, kind):
        return [a for a in stages[stage]['artifacts'] if a['kind'] == kind]
    def resource(value):
        raw = (stages['after-report']['package'] / value['path']).read_bytes()
        check(sha(raw) == value['sha256'], root.name + ' fact/report resource exact')
        return json.loads(raw)
    check(not rt('before-build')['intents'] and not tt('before-build')['effects'], root.name + ' true pre-intent origin')
    unknown, = artifacts('unknown-established', 'ExecutionReceipt')
    original_ref = ref(unknown)
    original_fact_ref, = unknown['payload']['action_fact_refs']
    original_fact = resource(original_fact_ref)
    issue = 'issue-save-unknown-' + sha(canonical(original_fact))[:32]
    result, = unknown['payload']['results']
    check(result['outcome'] == 'UNKNOWN' and result['replay_allowed'] is False and result == original_fact['result']
          and unknown['payload']['unresolved_issue_ids'] == [issue] and original_fact['resolution_ref'] is None,
          root.name + ' real original UNKNOWN and stable Issue source')
    check(rt('unknown-established')['actions'][0]['state'] == 'UNKNOWN' and rt('unknown-established')['intents'][0]['state'] == 'PENDING'
          and rt('unknown-established')['permits'][0]['state'] == 'CONSUMED' and rt('unknown-established')['plans'][0]['status'] == 'INTERRUPTED',
          root.name + ' unknown SQL pending/permit/plan')
    for stage in STAGES[1:]:
        check(unknown in stages[stage]['artifacts'] and json.loads(rt(stage)['intents'][0]['receipt']) == original_ref,
              root.name + ' original receipt retained: ' + stage)
        check(tt(stage)['effects'] == tt('unknown-established')['effects'] and len(tt(stage)['effects']) == 1,
              root.name + ' exactly one effect, no resend: ' + stage)
        state = json.loads(next(r['value'] for r in tt(stage)['meta'] if r['key'] == 'state'))
        original_state = json.loads(next(r['value'] for r in tt('unknown-established')['meta'] if r['key'] == 'state'))
        check(all(state[k] == original_state[k] for k in ('target', 'internal_bindings', 'frame_projections'))
              and len(state['target']['questions']) == 1 and len(state['target']['frames']) == 2,
              root.name + ' actual target business state unchanged: ' + stage)
    for stage in ('after-release', 'before-reconcile', 'after-reconcile', 'before-report', 'after-report'):
        book, = rt(stage)['books']
        check(book['owner'] is None and book['pid'] is None and book['lease'] == 0 and book['phase'] == 'RELEASED',
              root.name + ' released owner: ' + stage)
    for stage in STAGES[:-1]:
        check(not rt(stage)['native_report_reads'] and not artifacts(stage, 'BatchReport')
              and not [a for a in artifacts(stage, 'CheckReport') if a['payload']['stage'] == 'POST_APPLY'],
              root.name + ' no premature report observation: ' + stage)
    terminal, = artifacts('after-reconcile', 'ReconciliationResult')
    p = terminal['payload']
    check(p['resolution'] == 'RESOLVED_APPLIED' and p['observation'] == 'MATCH' and p['original_receipt_ref'] == original_ref
          and p['intent_ref'] == original_fact['intent_ref'] and p['action_id'] == original_fact['action_id']
          and p['action_digest'] == original_fact['action_digest'] and p['obligation_id'] == original_fact['obligation_id'],
          root.name + ' terminal exact original binding')
    late_receipt, = [a for a in artifacts('after-reconcile', 'ExecutionReceipt') if ref(a) != original_ref]
    late_ref, = late_receipt['payload']['action_fact_refs']
    late = resource(late_ref)
    check(late['origin_phase'] == 'RECOVERY' and late['resolution_ref'] == ref(terminal) and late['intent_ref'] == original_fact['intent_ref']
          and late['result']['outcome'] == 'APPLIED' and late['result']['attempt_fact'] == original_fact['result']['attempt_fact']
          and not late_receipt['payload']['unresolved_issue_ids'], root.name + ' late fact preserves history and attempt provenance')
    for stage in ('after-reconcile', 'before-report', 'after-report'):
        tables = rt(stage)
        check(len(tables['resolutions']) == len(tables['calls']) == len(tables['attempts']) == 1
              and tables['intents'][0]['state'] == 'RESOLVED_APPLIED' and tables['actions'][0]['state'] == 'APPLIED'
              and tables['permits'] == rt('before-reconcile')['permits'], root.name + ' one complete reconcile: ' + stage)
    post, = [a for a in artifacts('after-report', 'CheckReport') if a['payload']['stage'] == 'POST_APPLY']
    batch, = artifacts('after-report', 'BatchReport')
    pp, bp = post['payload'], batch['payload']
    binding, = pp['action_bindings']
    check(pp['receipt'] == ref(late_receipt) and pp['subject'] == ref(late_receipt) and pp['recovery_refs'] == [ref(terminal)]
          and binding['fact_ref'] == late_ref and binding['intent_ref'] == original_fact['intent_ref']
          and binding['resolution_head_ref'] == ref(terminal) and binding['head_original_receipt_ref'] == original_ref,
          root.name + ' actual POST original/current/head binding')
    check(pp['decision'] == 'HOLD' and pp['frame_structure'] == 'PASS' and bp['state'] == 'CONTENT_PENDING'
          and bp['postcheck'] == ref(post) and bp['receipt'] == pp['receipt'] and bp['recovery_refs'] == pp['recovery_refs']
          and all(v['content_check_status'] == 'PENDING' and v['submission_status'] == 'NOT_SUBMITTED' for v in (pp, bp)),
          root.name + ' actual POST/Batch pending and not submitted')
    report, recovery = resource(pp['report_observation']), resource(p['readback'])
    check(report['read_sequence'] > recovery['read_sequence'] and report['observation_id'] != recovery['observation_id']
          and report['observed_at'] > recovery['observed_at'] and pp['report_snapshot_ref'] != p['observed_snapshot_ref'],
          root.name + ' independent newer report observation')
    descriptor = json.loads(next(r['value'] for r in tt('after-report')['meta'] if r['key'] == 'descriptor'))
    observations = {r['observation_id']: json.loads(r['body']) for r in tt('after-report')['observations']}
    for observation in (recovery, report):
        check(observations[observation['observation_id']] == observation
              and observation['store_id'] == observation['target_store_id'] == descriptor['store_id']
              and observation['target_key'] == descriptor['target_key']
              and observation['source_ref'] == descriptor['fixed_source_ref'] and observation['scope_id'] == descriptor['fixed_scope_id'],
              root.name + ' report/recovery raw persisted observation identity')
    reads, = rt('after-report')['native_report_reads']
    check(reads['reads'] == 1 and reads['plan_id'] == sha(canonical(unknown['payload']['plan'])), root.name + ' one durable report read')
    owner = load(case / 'owner-release.json')
    check(owner['current_boundary_stopped'] and owner['normal_release'] and owner['keepers']['owned_async_writers'] == 0
          and all(not t['alive'] and t['error'] is None for t in owner['keepers']['all_keeper_threads']), root.name + ' all keeper threads joined')
    c = load(root / 'C-result.json')
    expected = load(R / 'examples/a03/T2-history/inputs.json')['contract_cases']
    check(c['cases_run'] == 12 and len(c['results']) == 12 and c['dispatches'] == c['observations'] == c['runtime_databases_created'] == 0,
          root.name + ' exact single pure-contract batch')
    for result, target in zip(c['results'], expected):
        check(result['name'] == target['name'] and result['actual_codes'] == ([] if target['expected_code'] is None else [target['expected_code']]),
              root.name + ' actual C target error layer: ' + target['name'])
    return {'root': str(root), 'stages': summaries, 'original_unknown_receipt': original_ref,
            'original_unknown_fact': original_fact_ref, 'stable_issue_id': issue, 'late_receipt': ref(late_receipt),
            'resolution': ref(terminal), 'post': ref(post), 'batch': ref(batch),
            'recovery_read_sequence': recovery['read_sequence'], 'report_read_sequence': report['read_sequence'],
            'report_reads': reads, 'C_results': c['results'], 'keeper_release': owner}

def process_records():
    folders = {p.parent for p in I.rglob('started.json')}
    folders.add(E / 'launch/independent-01')
    folders.add(H / 'launches/validation')
    records = []
    for folder in sorted(folders):
        prereg, start, end = (load(folder / name) for name in ('preregistered.json', 'started.json', 'completed.json'))
        check(start['pid'] == end['pid'] and end['exit_code'] == 0 and not end.get('timeout', False)
              and not end.get('alive', False), 'actual wait/reap complete: ' + str(folder))
        streams = []
        for stream in ('stdout', 'stderr'):
            path = next(p for p in (folder / (stream + '.txt'), folder / (stream + '.bin')) if p.is_file())
            check(sha(path.read_bytes()) == end[stream + '_sha256'], 'raw subprocess stream exact: ' + str(path))
            streams.append({'path': str(path), 'sha256': sha(path.read_bytes()), 'bytes': path.stat().st_size})
        if prereg['argv'][0] == 'git':
            check(prereg['argv'][1:3] == ['-c', 'core.longpaths=true'], 'explicit longpaths Git child')
        elapsed = (end['ended_at_ns'] - start['started_at_ns']) / 1e9
        check(elapsed < prereg['timeout_seconds'] + 1, 'actual process budget: ' + str(folder))
        records.append({'folder': str(folder), 'preregistered': prereg, 'started': start, 'completed': end,
                        'elapsed_seconds': elapsed, 'streams': streams})
    return records

def imports():
    folders = (E / 'import-processes', I / 'import-processes')
    result = []
    for folder in folders:
        for path in sorted(folder.glob('*.json')):
            record = load(path)
            products = []
            for name, imported in record['imports'].items():
                file = Path(imported['path'])
                check(sha(file.read_bytes()) == imported['sha256'], 'actual import bytes: ' + str(record['pid']) + '/' + name)
                if name.startswith('annotation'):
                    relative = file.relative_to(R / 'examples/a03/T2-history/runtime-view/src').as_posix()
                    check(sha(file.read_bytes()) == sha((R / 'src' / relative).read_bytes()), 'raw view actual import: ' + name)
                    products.append(name)
            result.append({'path': str(path), 'pid': record['pid'], 'product_modules': products, 'record': record})
    check(len(result) == 9 and any('annotation.contracts.a03_native' in r['product_modules'] for r in result), 'nine actual Python import records including native validator')
    return result

def main():
    manifest()
    author, independent = phase_audit(A), phase_audit(I)
    processes, actual_imports = process_records(), imports()
    index = load(R / 'examples/a03/T2-history/inputs.json')
    for name, expected in index['files'].items():
        check(sha((R / name).read_bytes()) == expected, 'post-run frozen execution unchanged: ' + name)
    limits = load(E / 'sealing/process-recording-limit.json')
    check(len(limits['calls']) == 3 and limits['PID_and_start_records_retained'] is False
          and [r['actual_exit_code'] for r in limits['calls']] == [2, 0, 0] and limits['business_process_metadata_gap'] is False,
          'author static Git gaps preserved, not backfilled')
    b.write(H / 'audit.json', {'status': 'FINITE_T2_ACCEPTED', 'target': b.TARGET, 'workflow': '0beba0d0c82376b119c46b1d35a137fde541113c',
        'checks': CHECKS, 'author': author, 'independent': independent, 'independent_processes': processes,
        'actual_imports': actual_imports, 'python': sys.version, 'executable': sys.executable,
        'pydantic_version': importlib.metadata.version('pydantic'),
        'author_static_metadata_limitation': limits,
        'limitation_assessment': 'Three author pre-candidate static Git PID/start/stream gaps remain a finite audit limitation; independently verified target raw members, execution bytes, intermediate originals, actual imports and complete independent business wait/reap establish this C12/H1 result without reconstructing those gaps. No claim of complete author static subprocess preregistration.',
        'business_reruns': 0, 'business_calls_in_this_audit': 0, 'SQL_only_own_retained_immutable_copies': True,
        'field_reset': 'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION', 'A03_overall': 'REWORK', 'I01_released': False})
    print(json.dumps({'status': 'FINITE_T2_ACCEPTED', 'checks': len(CHECKS), 'failures': 0,
          'author_raw_manifest': 317, 'independent_phase_raw_databases': 14, 'independent_process_records': len(processes),
          'import_records': len(actual_imports), 'recovery_read_sequence': independent['recovery_read_sequence'],
          'report_read_sequence': independent['report_read_sequence'], 'business_calls': 0}))

if __name__ == '__main__':
    try:
        main()
    except BaseException as error:
        b.write(H / 'audit-first-failure.json', {'error': repr(error), 'checks': CHECKS, 'business_calls': 0})
        raise
