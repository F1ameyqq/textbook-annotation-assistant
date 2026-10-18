"""Seal only this review's new evidence, with explicit raw-view exclusions."""
import hashlib
import json
from pathlib import Path
import re
import shutil

ROOT=Path('D:/1800-worktrees/a03-r1-review-54e86adf')
OUT=Path(__file__).resolve().parent
MAIN=Path('D:/1800')
R=ROOT/'docs/evidence/A03/R1/review'
REPORT=MAIN/'docs/tasks/A03-R1-review-report.md'

def sha(raw):return hashlib.sha256(raw).hexdigest()
def load(p):return json.loads(p.read_bytes())
def main():
    expected={r['path']:r['sha256'] for r in load(OUT/'snapshot-index.json')['exported']}
    view_audits=[]
    for name in ('preflight','business'):
        index=load(R/name/'runtime-identities.json')
        for row in index['files']:
            actual=sha((R/name/'runtime-view'/row['path']).read_bytes())
            assert actual==row['raw_sha256']==expected[row['path']]
        view_audits.append(dict(name=name,files=len(index['files']),raw_bytes_match=True))
    imports=[]
    for group,folder in [('author',ROOT/'docs/evidence/A03/R1/execution'),('independent',R)]:
        for f in folder.rglob('*.json'):
            if 'runtime-view' in f.parts:continue
            if not (f.name.startswith('imports-') or f.name in ('imports.json','process-result.json')):continue
            d=load(f)
            modules=d.get('modules') or d.get('imports') or (d if f.name=='imports.json' else None)
            if modules is None:continue
            rows=modules if isinstance(modules,list) else [dict(module=k,**v) for k,v in modules.items()]
            checked=0
            for row in rows:
                p=row['file'].replace('\\','/')
                assert '/src/annotation/' in p,p
                path='src/annotation/'+p.split('/src/annotation/',1)[1]
                assert row['sha256']==expected[path],(f,path)
                if group=='independent':assert p.lower().startswith(str(ROOT).replace('\\','/').lower()+'/')
                checked+=1
            if 'capture_sha256' in d:
                assert d['capture_sha256']=='3e07d56f409d8203c42f252f7a2900e902e31f56e1ff5fc7475335d33d0b042b'
            imports.append(dict(group=group,path=str(f.relative_to(ROOT)),modules=checked,raw_hashes_match=True))
    destination=OUT/'runs'
    destination.mkdir(exist_ok=False)
    copied=[]
    excluded=[]
    for file in sorted(R.rglob('*')):
        if not file.is_file():continue
        rel=file.relative_to(R)
        if 'runtime-view' in rel.parts or rel.parts[0]=='legacy':
            excluded.append(dict(path=str(rel).replace('\\','/'),reason='RECONSTRUCTIBLE_FIXED_RAW_VIEW' if 'runtime-view' in rel.parts else 'UNCHANGED_FROZEN_LEGACY_INPUT_REFERENCED_BY_COMMIT'))
            continue
        target=destination/rel;target.parent.mkdir(parents=True,exist_ok=True)
        raw=file.read_bytes()
        with target.open('xb') as stream:stream.write(raw)
        assert sha(raw)==sha(target.read_bytes())
        copied.append(dict(source=str(file),retained=str(target.relative_to(MAIN)).replace('\\','/'),bytes=len(raw),sha256=sha(raw)))
    audit=dict(view_audits=view_audits,import_records=imports,copied_files=copied,
               exclusions=excluded,product_and_author_files_modified=False)
    (OUT/'archive-audit.json').write_text(json.dumps(audit,indent=2)+'\n',encoding='utf-8')
    # Local relative report links must resolve after the new evidence is retained.
    missing=[]
    for label,url in re.findall(r'\[([^\]]+)\]\(([^)]+)\)',REPORT.read_text(encoding='utf-8')):
        if url.startswith(('http:','https:')):continue
        path=(REPORT.parent/url).resolve()
        if path.name=='manifest.json':continue
        if not path.exists():missing.append(dict(label=label,url=url))
    assert not missing,missing
    files=sorted([p for p in OUT.rglob('*') if p.is_file() and p.name!='manifest.json']+[REPORT])
    rows=[dict(path=str(p.relative_to(MAIN)).replace('\\','/'),bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in files]
    manifest=dict(delivery='54e86adfaf144093a688b62fe0dad5190ceb2fa6',
        product='6097a06de937fee8876feccedf46920510850b83',conclusion='REWORK_WITH_FINITE_M_L1_ACCEPTANCE',
        members=rows,excluded=['manifest self','reconstructible raw runtime-view exports',
        'unchanged legacy input copies: delivery docs/evidence/A03/R1/execution/deltas-correction/legacy',
        'original author and historical evidence: exact commit references only'],
        missing_report_links=missing,no_product_mutation=True)
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    assert all(sha((MAIN/r['path']).read_bytes())==r['sha256'] for r in rows)
    print(json.dumps(dict(retained=len(copied),members=len(rows),import_records=len(imports),
        bytes=sum(r['bytes'] for r in rows),report_sha256=sha(REPORT.read_bytes()),
        manifest_sha256=sha((OUT/'manifest.json').read_bytes()),links='PASS')))

if __name__=='__main__':main()
