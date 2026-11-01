"""Replay a frozen remaining-source handoff; run the copy at an extracted ZIP root.

Requires the existing Python/Pillow environment. No network, model calls, or platform I/O.
Compare archive and manifest hashes with the repository receipt before executing.
"""
from pathlib import Path, PurePosixPath
import argparse, hashlib, json, sys, zipfile

BASE_SHA='5d8dc9770ee0a84b5f36e2fc530eda468d132bee7169d8f914ea8bd9bded3af6'
sha=lambda raw:hashlib.sha256(raw).hexdigest()


def member_path(root,name):
    relative=PurePosixPath(name)
    if relative.is_absolute() or '..' in relative.parts or '\\' in name or ':' in name:
        raise ValueError('UNSAFE_MEMBER')
    target=(root/name).resolve()
    if not target.is_relative_to(root.resolve()):raise ValueError('UNSAFE_TARGET')
    return target


def verify(root):
    manifest=json.loads((root/'manifest.json').read_bytes())
    names=[row['path'] for row in manifest['members']]
    if len(names)!=len(set(names)):raise ValueError('DUPLICATE_MANIFEST_MEMBER')
    for row in manifest['members']:
        raw=member_path(root,row['path']).read_bytes()
        if len(raw)!=row['bytes'] or sha(raw)!=row['sha256']:raise ValueError('MEMBER_HASH '+row['path'])
    return len(names)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    root=Path(__file__).resolve().parent
    members=verify(root)
    if args.out.exists():raise ValueError('USE_FRESH_OUTPUT_DIRECTORY')
    def guard(event,values):
        if event=='socket.connect':raise RuntimeError('NETWORK_DISABLED')
        if event=='import' and str(values[0]).split('.')[0] in {
                'torch','transformers','rapidocr_onnxruntime','onnxruntime','openai','httpx','requests'}:
            raise RuntimeError('MODEL_NETWORK_IMPORT_DISABLED')
    sys.addaudithook(guard)
    archive_path=root/'base-workspace.zip'
    if sha(archive_path.read_bytes())!=BASE_SHA:raise ValueError('FIXED_BASE_ARCHIVE')
    # Extract only the hash-bound prior package. Its replay script is never executed.
    base_root=args.out/'fixed-base'
    with zipfile.ZipFile(archive_path) as archive:
        names=archive.namelist()
        if len(names)!=len(set(names)):raise ValueError('DUPLICATE_ZIP_MEMBER')
        for name in names:
            target=member_path(base_root,name)
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(archive.read(name))
    base_members=verify(base_root)
    sys.path[:0]=[str(root/'tools'),str(base_root/'tools')]
    import build_chapter_workspace_b as base
    import process_remaining_sources_b as process
    import render_remaining_sources_b as renderer
    catalog=base.unique_object((base_root/'inputs.json').read_bytes())
    if catalog['parent_archive_sha256']!={k:v[1] for k,v in {**base.PINS,**base.EXTRA}.items()}:
        raise ValueError('FIXED_PARENT_PROVENANCE')
    inputs={'packages':{}}
    for key,entries in catalog['packages'].items():
        inputs['packages'][key]={}
        for name,row in entries.items():
            raw=member_path(base_root,row['blob']).read_bytes()
            if len(raw)!=row['bytes'] or sha(raw)!=row['sha256']:raise ValueError('SOURCE_BLOB')
            inputs['packages'][key][name]=raw
    for key,(name,pin) in base.JSON_PINS.items():
        inputs[key]=base.fixed_json(member_path(base_root,name).read_bytes(),pin)
    parent=base.build_workspace(inputs);parent_audit=base.audit_workspace(parent,inputs)
    if not parent_audit['source_and_structure_accepted']:raise ValueError(parent_audit['errors'])
    if base.encode(parent)!=(base_root/'reference/workspace.json').read_bytes():raise ValueError('BASE_WORKSPACE_BYTES')
    if base.encode(parent_audit)!=(base_root/'reference/audit.json').read_bytes():raise ValueError('BASE_AUDIT_BYTES')
    for key,(name,pin) in process.PINS.items():
        inputs[key]=base.fixed_json(member_path(root,name).read_bytes(),pin)
    view=process.build_processing(inputs,parent);audit=process.audit_processing(view,inputs)
    if not audit['source_and_structure_accepted']:raise ValueError(audit['errors'])
    outputs={'workspace.json':base.encode(view),'audit.json':base.encode(audit),
             'acceptance-queue.json':base.encode(view['payload']['acceptance_queue'])}
    for name,raw in outputs.items():
        if raw!=(root/'reference'/name).read_bytes():raise ValueError('REFERENCE_BYTES '+name)
    html=renderer.render(view,inputs).encode('utf-8')
    if sha(html)!=(root/'reference/html-sha256.txt').read_text().strip():raise ValueError('HTML_BYTES')
    for name,raw in {**outputs,'review.html':html}.items():(args.out/name).write_bytes(raw)
    receipt=dict(manifest_members=members,fixed_base_members=base_members,base_archive_sha256=BASE_SHA,
        workspace_hash=view['content_hash'],counts=view['payload']['counts'],reference_bytes_match=True,
        html_bytes_match=True,network_disabled=True,model_import_disabled=True,paid_calls=0,new_ocr_calls=0,
        website_requests=0,old_parent_zip_containers_reverified=False,historical_pipeline_rerun=False,
        clean_dependency_installation=False,decision='HOLD',human_accepted=False,chapter_accepted=False)
    (args.out/'receipt.json').write_bytes(base.encode(receipt))
    print(json.dumps(receipt,ensure_ascii=False))


if __name__=='__main__':main()
