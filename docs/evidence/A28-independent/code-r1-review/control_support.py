"""Independent controls: exact frozen reads; synthetic process replies only."""
import copy, hashlib, json, sys
from pathlib import Path
from contextlib import ExitStack, contextmanager
from unittest.mock import patch
P=Path('D:/1800/.local/stages/a28-independent-20261023/code-r1-review')
O=Path('D:/1800/docs/evidence/A28-independent/code-r1-review')
sys.path.insert(0,str(P/'workspace/src'))
from annotation.runtime.usense_live import lesson_insert as ins, lesson_batch as batch, insertion, update as u
def sha(b): return hashlib.sha256(b).hexdigest()
def norm(p): return str(p).replace('\\','/').lower()
def dump(p,v):
 p.parent.mkdir(parents=True,exist_ok=True)
 raw=(json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf8')
 with p.open('xb') as f: f.write(raw)
 return {'path':str(p),'bytes':len(raw),'sha256':sha(raw)}
members=json.loads((O/'intake.json').read_bytes())['members']
def member(suffix):
 rows=[m for m in members if norm(m['source_path']).endswith(suffix.lower())]
 assert len(rows)==1,suffix
 return rows[0]
def frozen(suffix): return Path(member(suffix)['copy'])
def load(suffix): return json.loads(frozen(suffix).read_bytes())
data={}
for m in members:
 raw=Path(m['copy']).read_bytes(); assert sha(raw)==m['sha256']
 for k in ('source_path','frozen_path','root_frozen'):
  if m.get(k): data[norm(m[k])]=raw
raw_read=Path.read_bytes; text_read=Path.read_text; is_file=Path.is_file
@contextmanager
def frozen_io(overrides=None):
 values=dict(data);values.update(overrides or {})
 def read(p): return values[norm(p)] if norm(p) in values else raw_read(p)
 def text(p,encoding=None,errors=None):
  return read(p).decode(encoding or 'utf8',errors or 'strict') if norm(p) in values else text_read(p,encoding=encoding,errors=errors)
 with patch.object(Path,'read_bytes',read),patch.object(Path,'read_text',text),patch.object(Path,'is_file',lambda p:norm(p) in values or is_file(p)):
  yield values
def audit(event,args):
 if event=='socket.connect':
  f=sys._getframe(1)
  if f.f_code.co_name=='_fallback_socketpair' and f.f_code.co_filename.replace(chr(92),'/').endswith('/Lib/socket.py') and args[1][0]=='127.0.0.1':return
  raise RuntimeError('INDEPENDENT_OFFLINE_DENIAL:'+event)
 if event in ('socket.getaddrinfo','subprocess.Popen','os.system'): raise RuntimeError('INDEPENDENT_OFFLINE_DENIAL:'+event)
 if event=='open' and isinstance(args[0],str) and ('browser-profiles' in norm(args[0]) or 'worktrees/b-latest' in norm(args[0])):raise RuntimeError('INDEPENDENT_ACTIVE_RESOURCE_READ_DENIED')
sys.addaudithook(audit)
ACTOR='SYNTHETIC-INDEPENDENT-A28-ACTOR'
ACTORS={'runtime_actor_sha256':u.text_digest('SYNTHETIC-INDEPENDENT-USERNAME'),'runtime_user_id_sha256':u.text_digest(ACTOR)}
def witness(plan):
 before=plan['before_full'];order=plan['new_order'];index=order-23
 stamp=f'2026-10-23T23:0{index}:00'
 after={k:copy.deepcopy(before[k]) for k in ins.GLOBAL_KEYS};nodes={}
 def walk(values):
  for n in values:nodes[n['id']]=n;walk(n.get('children',[]))
 walk(after['directory']['data']['directory_data'])
 node={'isQuestion':True,'order_in_level':str(order),'id':'SYNTHETIC-INDEPENDENT-A28-NODE-'+str(order),'label':str(order)}
 nodes[ins.DIRECTORY]['children'].append(copy.deepcopy(node));nodes[ins.TAIL_NODE].update(order_in_level=str(order+1),label=str(order+1))
 for row in after['frames']['data']:
  if row['order_in_level']==str(order):row.update(order_in_level=str(order+1),updated_at=stamp)
 for row in plan['payload_candidate']['annotations_upsert']:
  values=dict(row,verified=0,file_id=ins.BOOK,order_in_level=str(order),user_id=ACTOR,created_at=stamp,updated_at=stamp)
  after['frames']['data'].append({k:values[k] for k in insertion.ROW_KEYS})
 after['frames']['data'].sort(key=lambda r:r['rect_id'])
 for suffix in ins.SUFFIXES:after[f'q{order+1}_{suffix}']=copy.deepcopy(before[f'q{order}_{suffix}'])
 after[f'q{order+1}_info']['data'].update(order_in_level=str(order+1),updated_at=stamp)
 after[f'q{order+1}_annotations']['data']=[copy.deepcopy(r) for r in after['frames']['data'] if r['order_in_level']==str(order+1)]
 for suffix in ins.SUFFIXES:after[f'q{order}_{suffix}']=copy.deepcopy(before[f'q{order}_{suffix}'])
 after[f'q{order}_annotations']['data']=[copy.deepcopy(r) for r in after['frames']['data'] if r['order_in_level']==str(order)]
 after[f'q{order}_info']['data']={'id':'SYNTHETIC-INDEPENDENT-A28-INFO-'+str(order),'tishi':plan['payload_candidate']['question_info']['tishi'],
  'tilei':None,'tixu':None,'tihao':None,'file_id':ins.BOOK,'order_in_level':str(order),'created_at':stamp,'updated_at':stamp}
 subs={r['zone']:r for r in plan['payload_candidate']['ocr_submissions']}
 for zone in u.ZONES:after[f'q{order}_{zone}']['data']=({'success':True,'ocr_result':subs[zone]['ocr_result'],'rect_ids':subs[zone]['rect_ids']} if zone in subs else copy.deepcopy(u.ABSENT))
 receipt={'code':0,'message':'success','data':{'inserted':True,'question_order':order,'inserted_question_node':node,'success':True,'append_at_global_end':False}}
 window={'start':f'2026-10-23T15:0{index}:00+00:00','end':f'2026-10-23T15:0{index}:01+00:00'}
 return after,receipt,window
def prepared_for(root):
 profile=root/'synthetic-profile';profile.mkdir(parents=True)
 ledger=root/'usense-existing-ledger';ledger.mkdir();(ledger/'old-fixed.json').write_bytes(b'{"synthetic_old":true}')
 manifest=member('/targets-r1.json');delivery=load('/fixed-delivery-r1.json')
 prepared=batch.prepare(manifest['source_path'],manifest['sha256'],delivery['baseline'],profile,'SYNTHETIC-NO-LIVE-AUTHORITY')
 return prepared,profile,delivery['baseline']
