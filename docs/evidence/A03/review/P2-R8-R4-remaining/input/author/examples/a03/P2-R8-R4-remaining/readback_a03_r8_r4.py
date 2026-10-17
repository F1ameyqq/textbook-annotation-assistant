"""Frozen R4 SQL readback, standard library only, no product imports."""
import hashlib
import json
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'docs/evidence/A03/execution/P2-R8-R4-remaining'
VALIDATION = OUT / 'validation/r4-native-01'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read_database(path):
    if not path.exists():
        return {'status': 'NOT_CREATED'}
    before = path.read_bytes()
    with sqlite3.connect(path.as_uri() + '?mode=ro&immutable=1', uri=True) as db:
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA query_only=ON')
        names = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        rows = {name: [dict(r) for r in db.execute('SELECT * FROM "' + name.replace('"', '""') + '"')] for name in names}
        result = {'path': path.relative_to(ROOT).as_posix(), 'sha256': sha(before), 'bytes': len(before),
            'quick_check': db.execute('PRAGMA quick_check').fetchone()[0],
            'application_id': db.execute('PRAGMA application_id').fetchone()[0],
            'user_version': db.execute('PRAGMA user_version').fetchone()[0],
            'counts': {name: len(values) for name, values in rows.items()}, 'tables': rows}
    assert before == path.read_bytes()
    result['bytes_unchanged_after_read'] = True
    return result


if __name__ == '__main__':
    result = {'mode': 'stdlib only; mode=ro&immutable=1; connection-local query_only',
        'runtime': read_database(VALIDATION / 'cases/N1/runtime/runtime.sqlite3'),
        'target': read_database(VALIDATION / 'cases/N1/target/target.sqlite3'),
        'interrupted_runtime': read_database(VALIDATION / 'cases/N7-before-completion/runtime/runtime.sqlite3'),
        'interrupted_target': read_database(VALIDATION / 'cases/N7-before-completion/target/target.sqlite3')}
    bundle = json.loads((VALIDATION / 'N6/full-current-history.json').read_bytes())
    registered = [json.loads(r['ref']) for r in result['runtime']['tables']['artifacts']]
    def ref(item):
        return {k: item[k] for k in ('artifact_id', 'revision', 'kind', 'content_hash')}
    key_kinds = {'ApplyPlan', 'ExecutionReceipt', 'ExecutionProgress', 'ReconciliationResult', 'CheckReport', 'BatchReport'}
    selected = [a for a in bundle['artifacts'] if a['kind'] in key_kinds]
    assert all(ref(a) in registered for a in selected)
    result['complete_history_formal_refs'] = [ref(a) for a in selected]
    result['full_history_count'] = len(bundle['artifacts'])
    result['full_current_history_raw_sha256'] = sha((VALIDATION / 'N6/full-current-history.json').read_bytes())
    result['creation_anchor'] = result['runtime']['tables']['native_creation_anchors']
    assert len(result['creation_anchor']) == 1
    assert result['runtime']['counts']['permits'] == 1
    assert result['target']['counts']['effects'] == 1
    assert result['interrupted_runtime']['counts']['meta'] == 0
    with (OUT / 'database-readback.json').open('xb') as stream:
        stream.write((json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode())
    print(json.dumps({'full_history_count': len(bundle['artifacts']), 'formal_selected_refs': len(selected),
        'effect_count': 1, 'product_execution': False}))
