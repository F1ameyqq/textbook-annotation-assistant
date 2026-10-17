"""Fixed two-parent object-only composition check; no A01 integration or tests."""
import hashlib,json,subprocess
from pathlib import Path
root=Path('D:/1800');main='2d1dc8b97713ee06ec5bf35febe0b894ece584b2';delivery='5f872150a237b195f73c78e02e13a91d2f4f46a7';expected='0645ac862f79fb4e232e4cfbd5f6bb5055a68d62'
def git(*args):return subprocess.check_output(['git',*args],cwd=root,timeout=60)
def tree(rev):
 result={}
 for row in git('ls-tree','-r','-z',rev).split(b'\0'):
  if row:
   meta,p=row.split(b'\t',1);result[p.decode('utf-8')]=meta.split()[2].decode()
 return result
base=git('merge-base',main,delivery).decode().strip();combined=git('merge-tree','--write-tree',main,delivery).decode().strip();assert combined==expected
b,m,d,c=map(tree,(base,main,delivery,combined));dd={p for p in set(b)|set(d) if b.get(p)!=d.get(p)};md={p for p in set(b)|set(m) if b.get(p)!=m.get(p)}
conflicting=[p for p in dd&md if d.get(p)!=m.get(p)];assert not conflicting,conflicting
assert all(c.get(p)==d.get(p) for p in dd)
preserved=[p for p in m if p not in dd];assert all(c.get(p)==m[p] for p in preserved)
changed=sorted(p for p in set(m)|set(c) if m.get(p)!=c.get(p));assert set(changed)<=dd
identity='examples/a02/R1/identity.py';assert c[identity]==m[identity] and c[identity]==git('rev-parse','a1e5be00909172429d792b6c41bdaf384258694e:'+identity).decode().strip()
critical=sorted(p for p in d if p.startswith(('src/annotation/geometry/','src/annotation/source/','examples/a01/integration-R1/','tests/fixtures/a01/integration-R1/')) or p in ('tests/test_a01_rework_r3.py','examples/a01/R3/verify.py','examples/a01/R3/reference.json'))
assert all(c[p]==d[p] for p in critical)
for p in ('.gitattributes','pyproject.toml','docs/coordination-state.json'):assert c[p]==m[p]
result={'result':'READY_FOR_BOUNDED_INDEPENDENT_COMBINED_REVIEW','main_parent':main,'delivery_parent':delivery,'merge_base':base,'combined_tree':combined,'actual_main_A01_integration':False,'conflicting_overlap_paths':conflicting,'main_paths_preserved_outside_A01_delta':len(preserved),'A01_delta_paths':len(dd),'combined_changed_paths':changed,'critical_A01_blobs':[{'path':p,'oid':c[p]} for p in critical],'A02_identity_blob':c[identity],'A02_identity_sha256':hashlib.sha256(git('cat-file','blob',c[identity])).hexdigest(),'root_policy_and_state_preserved':True,'functional_tests_run':False,'A04_D01_released':False,'remote_push':False}
with Path(__file__).with_name('preflight.json').open('x',encoding='utf-8',newline='\n') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({'result':result['result'],'combined_tree':combined,'changed_paths':len(changed),'critical_A01':len(critical),'preserved_main':len(preserved)}))
