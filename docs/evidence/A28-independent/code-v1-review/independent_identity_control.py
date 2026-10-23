"""Frozen real-input contract control, then one existing-info identity counterexample.

No product resources or network. Synthetic after/receipt are labelled and private.
"""
import copy, hashlib, json, sys
from pathlib import Path

PRIVATE=Path('D:/1800/.local/stages/a28-independent-20261023/code-v1-review')
PUBLIC=Path('D:/1800/docs/evidence/A28-independent/code-v1-review')
sys.path.insert(0,str(PRIVATE/'workspace/src'))
from annotation.runtime.usense_live import lesson_insert as contract, insertion, update


def sha(raw):return hashlib.sha256(raw).hexdigest()
def dump(path,value):
 path.parent.mkdir(parents=True,exist_ok=True)
 raw=(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
 with path.open('xb') as f:f.write(raw)
 return {'path':str(path),'bytes':len(raw),'sha256':sha(raw)}


intake=json.loads((PUBLIC/'intake.json').read_bytes())
members=intake['members']
def find(suffix):
 selected=[m for m in members if m['source_path'].replace('\\','/').endswith(suffix)]
 assert len(selected)==1,suffix
 return selected[0]
def load(member):
 raw=Path(member['copy']).read_bytes();assert sha(raw)==member['sha256']
 return json.loads(raw)

base='/tail-preservation-source-01/runs/usense-readonly-20261023-140753-df1cc5f2/'
before={name:load(find(base+name+'.json')) for name in contract.full_endpoints(tail_order=23)}
candidate_member=find('/content-v1/q6-candidate.json')
candidate=load(candidate_member)
proof_member=find('/remote-crops-01/crop-proof.json')
sources={f['source']['path']:f['source']['sha256'] for f in candidate['frames']}
approved={'candidate_ref':candidate_member['source_path'],'candidate_sha256':candidate_member['sha256'],
 'review_ref':candidate['review']['path'],'review_sha256':candidate['review']['sha256'],
 'crop_evidence_ref':proof_member['source_path'],'crop_evidence_sha256':proof_member['sha256'],
 'source_evidence':[{'path':p,'sha256':h} for p,h in sources.items()], 'candidate':copy.deepcopy(candidate)}
plan=contract.make_insert_plan(before,candidate,approved)
contract.validate_insert_plan(plan)
assert plan['insert_after_order']==22 and plan['new_order']==23
after={k:copy.deepcopy(before[k]) for k in contract.GLOBAL_KEYS}
nodes={}
def walk(values):
 for n in values:
  nodes[n['id']]=n;walk(n.get('children',[]))
walk(after['directory']['data']['directory_data'])
node={'isQuestion':True,'order_in_level':'23','id':'SYNTHETIC-INDEPENDENT-A28-NEW-NODE','label':'23'}
nodes[contract.DIRECTORY]['children'].append(copy.deepcopy(node))
nodes[contract.TAIL_NODE]['order_in_level']='24';nodes[contract.TAIL_NODE]['label']='24'
stamp='2026-10-23T23:00:00'
actor='SYNTHETIC-INDEPENDENT-A28-ACTOR'
for row in after['frames']['data']:
 if row['order_in_level']=='23':row.update(order_in_level='24',updated_at=stamp)
for row in plan['payload_candidate']['annotations_upsert']:
 values=dict(row,verified=0,file_id=contract.BOOK,order_in_level='23',user_id=actor,created_at=stamp,updated_at=stamp)
 after['frames']['data'].append({k:values[k] for k in insertion.ROW_KEYS})
after['frames']['data'].sort(key=lambda row:row['rect_id'])
for suffix in contract.SUFFIXES:
 after['q24_'+suffix]=copy.deepcopy(before['q23_'+suffix])
after['q24_info']['data'].update(order_in_level='24',updated_at=stamp)
after['q24_annotations']['data']=[copy.deepcopy(row) for row in after['frames']['data'] if row['order_in_level']=='24']
after['q23_annotations']=copy.deepcopy(before['q23_annotations'])
after['q23_annotations']['data']=[copy.deepcopy(row) for row in after['frames']['data'] if row['order_in_level']=='23']
after['q23_info']=copy.deepcopy(before['q23_info'])
after['q23_info']['data']={'id':'SYNTHETIC-INDEPENDENT-A28-NEW-INFO','tishi':'xuanze','tilei':None,'tixu':None,'tihao':None,
 'file_id':contract.BOOK,'order_in_level':'23','created_at':stamp,'updated_at':stamp}
submissions={s['zone']:s for s in plan['payload_candidate']['ocr_submissions']}
for zone in update.ZONES:
 after['q23_'+zone]=copy.deepcopy(before['q23_'+zone])
 after['q23_'+zone]['data']=({'success':True,'ocr_result':submissions[zone]['ocr_result'],'rect_ids':submissions[zone]['rect_ids']}
  if zone in submissions else copy.deepcopy(update.ABSENT))
receipt={'code':0,'message':'success','data':{'inserted':True,'question_order':23,'inserted_question_node':node,
 'success':True,'append_at_global_end':False}}
actors={'runtime_actor_sha256':update.text_digest('SYNTHETIC-INDEPENDENT-A28-USERNAME'),'runtime_user_id_sha256':update.text_digest(actor)}
window={'start':'2026-10-23T15:00:00+00:00','end':'2026-10-23T15:00:01+00:00'}
out=PRIVATE/'identity-control';out.mkdir()
normal=contract.compare_insert_readback(plan,after,receipt,runtime_actor_hashes=actors,send_window=window)
dump(out/'normal-result.json',normal)
assert normal['ok'],normal['differences']
q22_member=find('/final-recovery-live/last-question-batch/usense-readonly-20261023-120904-83938d02/q22_info.json')
old_info=load(q22_member)['data']['id']
aliased=copy.deepcopy(after)
aliased['q23_info']['data']['id']=old_info
counter=contract.compare_insert_readback(plan,aliased,receipt,runtime_actor_hashes=actors,send_window=window)
artifacts=[dump(out/'plan.json',plan),dump(out/'normal-after.json',after),dump(out/'aliased-after.json',aliased),
 dump(out/'receipt.json',receipt),dump(out/'actors-window.json',{'actors':actors,'window':window}),dump(out/'alias-result.json',counter)]
result={'schema':'A28IndependentKnownOldInfoAliasControl/v1','scope':'SYNTHETIC_AFTER_AND_RECEIPT_WITH_FROZEN_REAL_BEFORE_AND_ACCEPTED_Q6_CANDIDATE',
 'normal_control':'PASS' if normal['ok'] else 'FAIL','alias_rejection_expected':True,'alias_actually_accepted':counter['ok'],
 'status':'FAIL_NEW_INFO_CAN_ALIAS_KNOWN_OLD_INFO' if counter['ok'] else 'PASS_ALIAS_REJECTED',
 'old_info_source_sha256':q22_member['sha256'],'old_info_id':old_info,'new_native_order':23,
 'only_counterexample_change':'q23_info.data.id replaced with frozen accepted q22_info.data.id',
 'actual_comparison_status':counter['status'],'comparison_differences':counter['differences'],
 'private_artifacts':artifacts,'remaining_independent_controls':'NOT_RUN_AFTER_FIRST_SEMANTIC_FAILURE' if counter['ok'] else 'PENDING',
 'platform_requests':0,'author_code_modified':False}
dump(PUBLIC/'identity-control.json',result)
print(json.dumps({k:result[k] for k in ('status','normal_control','alias_actually_accepted','actual_comparison_status')},ensure_ascii=True))
