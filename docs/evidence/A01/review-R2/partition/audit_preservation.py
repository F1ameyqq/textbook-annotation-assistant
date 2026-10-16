"""Read-only audit that partition probes preserved all non-mutated package bytes."""
import hashlib
import json
import sys
from pathlib import Path
sys.dont_write_bytecode=True
root=Path(sys.argv[1]).resolve()
out=Path(sys.argv[2]).resolve()
rows=json.loads((out/'results.json').read_text(encoding='utf-8'))
audits=[]
for row in rows:
    book,version,_=row['id'].split('.',2)
    base=root/'examples/a01'/('bundles' if version=='original' else version+'/bundles')/book
    package=Path(row['package']).parent
    checked=[];mismatches=[]
    for source in sorted(base.rglob('*')):
        if not source.is_file():continue
        rel=source.relative_to(base)
        if rel.as_posix() in ['exchange.json','provenance.json']:continue
        before=hashlib.sha256(source.read_bytes()).hexdigest()
        target=package/rel
        after=hashlib.sha256(target.read_bytes()).hexdigest() if target.is_file() else None
        checked.append(rel.as_posix())
        if before!=after:mismatches.append(rel.as_posix())
    original=json.loads((base/'exchange.json').read_text(encoding='utf-8'))
    actual=json.loads((package/'exchange.json').read_text(encoding='utf-8'))
    assets_same=original['artifacts'][0]['payload']['assets']==actual['artifacts'][0]['payload']['assets']
    audits.append({'id':row['id'],'checked_resource_count':len(checked),'resource_mismatches':mismatches,
                   'asset_inventory_unchanged':assets_same,'pass':not mismatches and assets_same})
result={'cases':len(audits),'pass':sum(a['pass'] for a in audits),'fail':sum(not a['pass'] for a in audits),
        'excluded_intentional_mutations':['exchange.json','provenance.json'],'audits':audits}
(out/'preservation-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='audits'}))
sys.exit(1 if result['fail'] else 0)
