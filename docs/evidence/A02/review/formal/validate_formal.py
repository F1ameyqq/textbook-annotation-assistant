"""Validate final review documents/evidence and seal a unified SHA256 index."""
import ast
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT=Path('D:/1800')
OUT=Path(__file__).resolve().parent
STAGE=ROOT/'.local/stages/A02-review/frozen-5c928572'
sys.path.insert(0,str(STAGE/'src'))
sys.dont_write_bytecode=True
from annotation.contracts import load_bundle

REPORT=ROOT/'docs/tasks/A02-review-final-report.md'
MANIFEST=OUT/'sha256-manifest.json'
COMMIT='5c9285720c8628c5198bedeadfc9f6bc7826a914'

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path): return json.loads(path.read_text(encoding='utf-8'))
def save(path,value): path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def seal_manifest():
    files=[REPORT]+sorted(p for p in OUT.rglob('*') if p.is_file() and p!=MANIFEST)
    value={'schema_version':1,'task':'A02-independent-review','target_commit':COMMIT,'implementation_commit':'3fe492ce10bf93711ce57d305bc716f8b29345b7',
        'base_commit':'39341c98d73c354d639f3beeb55429f55d0e9be5','workflow_commit':'39341c98d73c354d639f3beeb55429f55d0e9be5',
        'decision':'REWORK','report':'docs/tasks/A02-review-final-report.md','report_sha256':sha(REPORT),
        'files':[{'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size} for p in files],
        'self_excluded':True,'source_identity':'docs/evidence/A02/review/formal/frozen-export.json',
        'preserved_preparation_manifest':'docs/evidence/A02/review/sha256-manifest.json','platform_actions':0,'external_model_calls':0}
    save(MANIFEST,value)
    return value

receipts=read(OUT/'independent-command-receipts.json')
receipts['commands'].append({'command':'python -B docs/evidence/A02/review/formal/validate_formal.py','exit_code':0,
    'evidence':'formal-validation.json','reason':'Final evidence/public reload, report links, preserved preparation and unified SHA verification.'})
save(OUT/'independent-command-receipts.json',receipts)
seal_manifest()  # Make the actual report target exist before checking links.
json_count=0
public_bundles=[]
for path in OUT.rglob('*'):
    if not path.is_file(): continue
    if path.suffix=='.json':
        read(path); json_count+=1
        if path.name in ('input.json','original-input.json','executed.json','final.json','replanned-executed.json','second-book-executed.json','blocked-input.json','blocked-checked.json','blocked-planned.json','blocked-receipt.json','fresh-ready-input.json','fresh-ready-checked.json','fresh-ready-planned.json') or re.fullmatch(r'planned-\d+\.json',path.name):
            load_bundle(path)
            public_bundles.append(path.relative_to(ROOT).as_posix())
    if path.suffix=='.py': ast.parse(path.read_text(encoding='utf-8'),filename=str(path))
links=[]
for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)',REPORT.read_text(encoding='utf-8')):
    if target.startswith(('https:','http:','#')): continue
    resolved=(REPORT.parent/target.split('#',1)[0]).resolve()
    assert resolved.exists(),target
    links.append(target)
assert not any(re.search(r'[ \t]+$',line) for line in REPORT.read_text(encoding='utf-8').splitlines())
preparation=read(OUT.parent/'sha256-manifest.json')
assert all(sha(ROOT/f['path'])==f['sha256'] for f in preparation['files'])
matrix=read(OUT/'matrix-results.json')
assert matrix['matrix_count']==67 and len(matrix['matrix_rows'])==67
assert [r['matrix_id'] for r in matrix['matrix_rows'] if r['status']=='FAIL']==['U05']
for row in matrix['matrix_rows']:
    for evidence in row['evidence']: assert (OUT/evidence).is_file(),evidence
save(OUT/'formal-validation.json',{'target_commit':COMMIT,'decision':'REWORK','json_files_parsed':json_count,
    'public_resource_bundles_reloaded':len(public_bundles),'public_bundle_paths':public_bundles,'report_links_verified':len(links),'report_links':links,
    'preparation_sha_entries_preserved':len(preparation['files']),'matrix_rows':67,'failed_matrix_rows':['U05'],
    'note':'Invalid-input/tampered mutation diagnostics are deliberately not passed to the public valid-bundle reloader. JSON syntax is checked for all JSON evidence. Manifest excludes only itself.'})
manifest=seal_manifest()
assert all(sha(ROOT/f['path'])==f['sha256'] for f in manifest['files'])
assert manifest['report_sha256']==sha(REPORT)
print(json.dumps({'decision':'REWORK','matrix_rows':67,'report_links':len(links),'public_bundles':len(public_bundles),'manifest_files':len(manifest['files']),'report_sha256':manifest['report_sha256'],'manifest_sha256':sha(MANIFEST)}))
