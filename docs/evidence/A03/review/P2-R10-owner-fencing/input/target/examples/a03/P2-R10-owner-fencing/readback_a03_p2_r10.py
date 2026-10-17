"""Frozen raw SQL, identity and barrier timeline cross-checks; stdlib only."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'docs/evidence/A03/execution/P2-R10-owner-fencing'
RUN = OUT / 'validation/r10-01'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def read_db(path):
    raw = path.read_bytes()
    with sqlite3.connect(path.as_uri() + '?mode=ro&immutable=1', uri=True) as db:
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA query_only=ON')
        tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        rows = {name: [dict(r) for r in db.execute('SELECT * FROM "' + name.replace('"', '""') + '"')] for name in tables}
        quick = db.execute('PRAGMA quick_check').fetchone()[0]
    assert raw == path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'sha256': sha(raw), 'bytes': len(raw),
        'quick_check': quick, 'counts': {k: len(v) for k, v in rows.items()}, 'tables': rows, 'bytes_unchanged_after_read': True}


if __name__ == '__main__':
    result = {'mode': 'stdlib only; mode=ro&immutable=1; query_only', 'cases': {}}
    for group in ('C1', 'C2'):
        case = RUN / 'cases' / group
        runtime, target = read_db(case / 'runtime/runtime.sqlite3'), read_db(case / 'target/target.sqlite3')
        assert all(runtime['counts'][name] == 0 for name in ('plans', 'actions', 'intents', 'permits'))
        assert target['counts']['effects'] == 0
        book = runtime['tables']['books'][0]
        assert book['owner'] is None and book['phase'] == 'RELEASED'
        reg = runtime['tables']['registrations'][0]
        bundle_path = Path(reg['bundle_path'])
        bundle_raw = bundle_path.read_bytes()
        bundle = json.loads(bundle_raw)
        refs = [json.loads(r['ref']) for r in runtime['tables']['artifacts']]
        def ref(a):
            return {k: a[k] for k in ('artifact_id', 'revision', 'kind', 'content_hash')}
        assert all(ref(a) in refs for a in bundle['artifacts'])
        result['cases'][group] = {'runtime': runtime, 'target': target, 'current_bundle': bundle,
            'current_bundle_path': bundle_path.relative_to(ROOT).as_posix(), 'current_bundle_sha256': sha(bundle_raw),
            'all_current_refs_formally_registered': True}
    c1 = RUN / 'control/C1'
    common = load(c1 / 'claim-go.barrier')
    competition = load(c1 / 'simultaneous-competition.json')
    before_common = load(c1 / 'before-common-release.json')
    completions = {role: load(RUN / 'processes' / ('C1-' + role) / 'completed.json') for role in ('A', 'B')}
    for role in ('A', 'B'):
        marker = before_common['markers'][role + '-BEFORE_CLAIM.json']
        marker_seconds = datetime.fromisoformat(marker['at'].replace('Z', '+00:00')).timestamp()
        assert marker_seconds < common['at_ns'] / 1e9
        assert competition['claims'][role]['at_ns'] > common['at_ns']
        assert completions[role]['ended_at_ns'] > competition['at_ns']
        assert completions[role]['exit_code'] == 0 and not completions[role]['alive']
    assert competition['both_processes_still_alive']
    assert len({competition['claims'][role]['pid'] for role in ('A', 'B')}) == 2
    assert len({competition['claims'][role]['instance'] for role in ('A', 'B')}) == 2
    result['C1_timeline'] = {'both_markers_before_common_release': True, 'both_results_after_release': True,
        'both_process_exits_after_live_observation': True, 'common_release': common, 'competition': competition,
        'worker_completions': completions}
    c2 = RUN / 'control/C2'
    names = ('A-qualified.json', 'A-released.json', 'B-active.json', 'A-stale-attempt.barrier',
        'A-stale-result.json', 'after-stale-live-observation.json', 'B-released.json')
    timeline = {name: load(c2 / name) for name in names}
    times = [timeline[name]['at_ns'] for name in names]
    assert times == sorted(times)
    a, b = timeline['A-qualified.json'], timeline['B-active.json']
    assert a['pid'] != b['pid'] and b['claim']['generation'] > a['claim']['generation']
    assert timeline['A-stale-result.json']['refusal']['root_lease_guard_reached']
    assert timeline['after-stale-live-observation.json']['both_alive']
    for role in ('A', 'B'):
        completed = load(RUN / 'processes' / ('C2-' + role) / 'completed.json')
        assert completed['ended_at_ns'] > timeline['after-stale-live-observation.json']['at_ns']
    pre = next(a for a in result['cases']['C2']['current_bundle']['artifacts'] if a['kind'] == 'CheckReport' and a['payload']['stage'] == 'PRE_APPLY')
    plan = next(a for a in result['cases']['C2']['current_bundle']['artifacts'] if a['kind'] == 'ApplyPlan')
    assert ref(plan) == timeline['A-qualified.json']['plan_ref']
    assert ref(pre) == timeline['A-qualified.json']['pre_ref']
    result['C2_timeline'] = {'ordered_real_qualification_release_claim_stale_refusal_and_final_release': True, 'records': timeline}
    with (OUT / 'database-and-timeline-readback.json').open('xb') as stream:
        stream.write((json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode())
    print(json.dumps({'C1': 'concurrent_live_claim_mutex', 'C2': 'actual_turnover_live_old_owner_refused',
        'each_effect_count': 0, 'product_calls': 0}))
