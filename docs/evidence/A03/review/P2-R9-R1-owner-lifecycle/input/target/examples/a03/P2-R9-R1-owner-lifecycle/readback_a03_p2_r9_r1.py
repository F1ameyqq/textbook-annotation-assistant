"""Frozen file/SQL ownership evidence only; no product imports or calls."""
import hashlib
import json
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'docs/evidence/A03/execution/P2-R9-R1-owner-lifecycle'
CASES = OUT / 'validation/owner-r1-01/cases'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def database(path):
    if not path.is_file():
        return {'status': 'NOT_CREATED'}
    raw = path.read_bytes()
    with sqlite3.connect(path.as_uri() + '?mode=ro&immutable=1', uri=True) as db:
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA query_only=ON')
        tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        rows = {name: [dict(r) for r in db.execute('SELECT * FROM "' + name.replace('"', '""') + '"')] for name in tables}
        result = {'path': path.relative_to(ROOT).as_posix(), 'sha256': sha(raw), 'bytes': len(raw),
            'quick_check': db.execute('PRAGMA quick_check').fetchone()[0],
            'counts': {name: len(values) for name, values in rows.items()}, 'tables': rows}
    assert raw == path.read_bytes()
    result['bytes_unchanged_after_read'] = True
    return result


def ref(a):
    return {k: a[k] for k in ('artifact_id', 'revision', 'kind', 'content_hash')}


if __name__ == '__main__':
    records = {}
    for name in ('D1', 'standalone', 'borrow'):
        case = CASES / name
        runtime, target = database(case / 'runtime/runtime.sqlite3'), database(case / 'target/target.sqlite3')
        reg = runtime['tables']['registrations'][0]
        path = Path(reg['bundle_path'])
        raw = path.read_bytes()
        bundle = json.loads(raw)
        refs = [json.loads(r['ref']) for r in runtime['tables']['artifacts']]
        assert all(ref(a) in refs for a in bundle['artifacts'])
        posts = [a for a in bundle['artifacts'] if a['kind'] == 'CheckReport' and a['payload']['stage'] == 'POST_APPLY']
        batches = [a for a in bundle['artifacts'] if a['kind'] == 'BatchReport']
        assert len(posts) == len(batches) == 1
        receipt = next(a for a in bundle['artifacts'] if ref(a) == posts[0]['payload']['receipt'])
        assert batches[0]['payload']['receipt'] == ref(receipt) and batches[0]['payload']['postcheck'] == ref(posts[0])
        assert posts[0]['payload']['content_check_status'] == batches[0]['payload']['content_check_status'] == 'PENDING'
        assert posts[0]['payload']['submission_status'] == batches[0]['payload']['submission_status'] == 'NOT_SUBMITTED'
        assert runtime['counts']['native_report_reads'] == target['counts']['effects'] == 1
        facts = []
        for row in runtime['tables']['actions']:
            resource = json.loads(row['fact'])
            data = (Path(reg['package_root']) / resource['path']).read_bytes()
            assert sha(data) == resource['sha256']
            facts.append({'resource': resource, 'fact': json.loads(data)})
        records[name] = {'runtime': runtime, 'target': target, 'current_bundle_path': path.relative_to(ROOT).as_posix(),
            'current_bundle_sha256': sha(raw), 'current_bundle': bundle, 'all_current_refs_formally_registered': True,
            'report_receipt_ref': ref(receipt), 'post_ref': ref(posts[0]), 'batch_ref': ref(batches[0]), 'facts': facts}
    with (OUT / 'database-readback.json').open('xb') as stream:
        stream.write((json.dumps({'mode': 'stdlib mode=ro&immutable=1; query_only', 'cases': records,
            'D2': 'NOT_RUN_AFTER_BORROW_GROUP_FAILURE'}, ensure_ascii=False, indent=2) + '\n').encode())
    print(json.dumps({'frozen_cases': list(records), 'each_effect_count': 1, 'each_report_read_count': 1,
        'each_POST_Batch': 'PENDING/NOT_SUBMITTED', 'product_calls': 0}))
