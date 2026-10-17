"""Copy fixed P1 counterexample inputs and recursive resources byte-for-byte."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[5]
OLD = ROOT/'examples/a03/P1'
OUT = Path(__file__).resolve().parent/'before/P1'

def walk(value):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)

def main():
    rows = {}
    active = set()
    def copy(relative, expected=None):
        source = (OLD/relative).resolve()
        if OLD.resolve() not in source.parents:
            raise ValueError('Escaping original resource')
        data = source.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        if expected and sha != expected:
            raise ValueError('Original resource hash mismatch: '+relative)
        if relative in rows:
            return
        if relative in active:
            raise ValueError('Resource cycle')
        active.add(relative)
        target = OUT/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if target.read_bytes() != data:
                raise ValueError('Existing preserved input differs: '+relative)
        else:
            with target.open('xb') as handle:
                handle.write(data)
        rows[relative] = {'path': relative, 'bytes': len(data), 'sha256': sha}
        if relative.endswith('.json'):
            value = json.loads(data)
            for node in walk(value):
                if (isinstance(node, dict) and {'path','sha256','media_type'} <= node.keys()
                        and all(isinstance(node[k],str) for k in ('path','sha256','media_type'))):
                    copy(node['path'], node['sha256'])
        active.remove(relative)
    for name in ('cases/normal.json', 'cases/partial-with-complete-absent.json'):
        copy(name)
    # Keep the exact original producer/API material which exposed the null-intent gap.
    for name in ('api-proposal.json', 'action-fact.schema.json'):
        copy(name)
    index = {'evidence_kind': 'P1_FIXED_PRE_REPAIR_COUNTEREXAMPLES',
             'source_commit': '2d5ae2a53945a7fa20ef60a6b61e7b31c91dbea9',
             'copied_bytes_only': True, 'functional_result': 'NOT_EXECUTED',
             'files': sorted(rows.values(), key=lambda row: row['path'])}
    with (OUT.parent/'before-manifest.json').open('x',encoding='utf-8',newline='\n') as handle:
        json.dump(index,handle,ensure_ascii=False,indent=2)
        handle.write('\n')
    print(json.dumps({'before_files':len(rows),'source_commit':index['source_commit']}))

if __name__ == '__main__':
    main()
