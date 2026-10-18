"""Coordinator bounded corroboration; no product/business execution."""
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import sys

ROOT = Path('D:/1800')
OUT = Path(__file__).resolve().parent
LOCAL = ROOT / '.local/coordinator-hb-20261018-0252'
T1 = 'ed90664ab15afd1938725441e2bc86db7884f784'
T3 = '3fcdb73416142a0a85dfb951a7f839849871c549'
def sha(b): return hashlib.sha256(b).hexdigest()
def git(*a): return subprocess.check_output(['git','-c','core.longpaths=true',*a],cwd=ROOT,timeout=45)
def blob(c,p): return git('show',c+':'+p)
def save(p,v): p.write_bytes((json.dumps(v,indent=2,ensure_ascii=False)+'\n').encode())

LOCAL.mkdir(parents=True,exist_ok=False)
result = {'scope':'fixed independent review manifests, raw SQL copies, capture fixture, T3 references', 'business_calls':0,'full_suite':False,'platform_actions':0}
specs = [
 ('T1','docs/evidence/A03/T1/review/independent-01/manifest.json','4621301d4ed6a6fcf804e1f7a550c937532c745ed5f5fe50f921b0eb89605a27'),
 ('T3','docs/evidence/A03/T3/review/manifest.json','9b8732c0af648fb864e2ef8fd83209aad70128435f772bc538b97dd961bcb655')]
result['manifests']={}
for name,path,expected in specs:
 raw=(ROOT/path).read_bytes(); assert sha(raw)==expected
 m=json.loads(raw)
 entries=m.get('members') or [dict(path=p,**v) for p,v in m['files'].items()]
 for e in entries:
  b=(ROOT/e['path']).read_bytes()
  assert len(b)==e.get('bytes',e.get('size')) and sha(b)==e['sha256'],e['path']
 result['manifests'][name]={'path':path,'sha256':expected,'verified_members':len(entries)}

review=ROOT/'docs/evidence/A03/T1/review/independent-01'
release=json.loads((review/'release-proof.json').read_bytes())
assert len(release['processes'])==37
assert all(x['exit_code']==0 and not x['alive'] and not x['timeout'] for x in release['processes'].values())
assert all(x['owner'] is None and x['pid'] is None and x['lease']==0 and x['phase']=='RELEASED' for x in release['owners'].values())
result['release']={'registered_processes':37,'released_owners':6,'global_pid_scan':False}

def own_sql(p):
 b=p.read_bytes(); dest=LOCAL/('copy-'+sha(b)+'.sqlite3')
 if not dest.exists(): dest.write_bytes(b)
 conn=sqlite3.connect(dest.resolve().as_uri()+'?mode=ro&immutable=1',uri=True)
 conn.row_factory=sqlite3.Row
 try:
  assert conn.execute('PRAGMA quick_check').fetchone()[0]=='ok'
  names=[r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
  values={n:[dict(r) for r in conn.execute('SELECT * FROM "'+n.replace('"','""')+'" ORDER BY rowid')] for n in names}
 finally: conn.close()
 assert dest.read_bytes()==b and p.read_bytes()==b
 return values

result['cases']={}
for case in ['L1','U1','U2','U3','U4','U5']:
 c=review/'validation/independent-01/cases'/case
 final='after-release' if case=='L1' else 'after-reconcile'
 tables=own_sql(c/'captures'/final/'runtime.sqlite3')
 book,=tables['books']; assert book['owner'] is None and book['lease']==0
 if case=='L1': assert 'native_report_reads' not in tables
 else:
  assert tables['native_report_reads']==[]
  before=own_sql(c/'captures/before-reconcile/runtime.sqlite3')
  for name in ['actions','intents','permits']: assert before[name]==tables[name]
  bt=own_sql(c/'captures/before-reconcile/target.sqlite3')
  at=own_sql(c/'captures/after-reconcile/target.sqlite3')
  assert bt['effects']==at['effects']
  assert len(tables['resolutions'])==len(tables['calls'])==len(tables['attempts'])==1
 result['cases'][case]={'owner_released':True,'report_reads':None if case=='L1' else 0,'recovery_preserves_originals':case!='L1'}

fixture=LOCAL/'helper'
fixture.mkdir()
for name in ['capture.py','fixture.py']:
 raw=blob(T1,'examples/a03/T1-capture/'+name)
 (fixture/name).write_bytes(raw)
result['capture_sha256']=sha((fixture/'capture.py').read_bytes())
p=subprocess.run([sys.executable,'-X','utf8','-B',str(fixture/'fixture.py'),str(LOCAL/'fixture-result')],cwd=LOCAL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20)
(OUT/'fixture.stdout.bin').write_bytes(p.stdout);(OUT/'fixture.stderr.bin').write_bytes(p.stderr)
assert p.returncode==0,p.stderr
result['fixture']={'exit_code':p.returncode,'result':json.loads((LOCAL/'fixture-result/result.json').read_bytes()),'business_calls':0}

index=json.loads(blob(T3,'docs/evidence/A03/T3/execution/reference-index.json'))
refs=0;linked=0
for e in index['references']:
 b=blob(e['commit'],e['path']);assert sha(b)==e['raw_sha256'] and len(b)==e['raw_bytes']
 lines=b.decode('utf-8-sig').splitlines()
 for a in e['selected_anchors']:assert lines[a['line']-1]==a['text']
 for link in e.get('linked_manifest_release_indexes',[]):
  b=blob(link['commit'],link['path']);assert sha(b)==link['raw_sha256'] and len(b)==link['raw_bytes'];linked+=1
 refs+=1
matrix=blob(T3,'docs/tasks/A03-T3-remaining-matrix.md').decode()
ids=re.findall(r'^\| ([VR]\d{2}) \|',matrix,re.M)
assert len(ids)==28 and len(set(ids))==28
result['T3']={'references':refs,'linked_indexes':linked,'unique_original_ids':len(ids),'matrix':'ACCEPTED_LIMITED','plan':'C1_C4_REVISION_REQUIRED','product_execution':False}
result['decisions']={'T1':'ACCEPTED_CAPTURE_AND_L1_U1_U5_ONLY','T3':'ACCEPTED_28_MAPPING_ONLY','A03':'REWORK','I01':'NOT_RELEASED'}
save(OUT/'checks.json',result)
print(json.dumps({'manifests':result['manifests'],'capture_sha256':result['capture_sha256'],'fixture_exit':p.returncode,'T3':result['T3'],'decisions':result['decisions']},indent=2))
