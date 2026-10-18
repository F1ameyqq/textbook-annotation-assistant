"""Check real application imports and capture durations without business calls."""
import json
from pathlib import Path
import sys
from audit import SNAP,HERE,EV,map_path,load,sha,save

def run(root):
    entries={};annotation_paths=set();count=0
    files=set(root.rglob('import-processes/*.json'))|set(root.rglob('imports/*.json'))
    for path in sorted(files):
        record=load(path);items=record.get('imports',record)
        if not isinstance(items,dict):continue
        for name,entry in items.items():
            if not isinstance(entry,dict) or not {'path','sha256'}<=set(entry):continue
            source=map_path(entry['path'])
            assert sha(source.read_bytes())==entry['sha256'],str(path)+' '+name
            if name.startswith('annotation'):
                assert source.is_relative_to(SNAP/'examples/a03/T1-capture/runtime-view/src'),str(source)
                annotation_paths.add(str(source.relative_to(SNAP)))
            entries[str(path.relative_to(root))+'::'+name]={'path':str(source),'sha256':entry['sha256']}
            count+=1
    assert entries and annotation_paths
    captures=[]
    for path in root.glob('cases/*/captures/*/capture.json'):
        c=load(path);b=c['writer_boundary']
        captures.append({'path':str(path.relative_to(root)),
            'copy_and_audit_seconds':(b['copy_boundary_ended_at_ns']-b['joined_at_ns'])/1e9,
            'stop_join_seconds':(b['joined_at_ns']-b['requested_at_ns'])/1e9})
    assert len(captures)==28
    return dict(import_records=len(files),entries_checked=count,annotation_modules=len(annotation_paths),
        annotation_paths=sorted(annotation_paths),imports=entries,capture_timings=captures,
        max_copy_and_audit_seconds=max(x['copy_and_audit_seconds'] for x in captures),
        max_stop_join_seconds=max(x['stop_join_seconds'] for x in captures))

label=sys.argv[1]
root=SNAP/'docs/evidence/A03/T1/execution/validation'/('author-01' if label=='author' else 'independent-01')
result=run(root)
save(EV/(label+'-import-and-timing-audit.json'),result)
print(json.dumps({k:result[k] for k in ('import_records','entries_checked','annotation_modules','max_copy_and_audit_seconds','max_stop_join_seconds')},indent=2))
