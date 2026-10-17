"""Make one candidate by correcting one internal head and required digests."""
import copy,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5];EX=ROOT/'examples/a03/P2-R6-mixed-control';sys.path.insert(0,str(EX))
from files import BASE,OLD_CASE,OUT,canon,h,load,raw_write,sha,write
old=load(ROOT/OLD_CASE);bundle=load(ROOT/old['bundle']);item=next(r for r in old['resources']if r['logical']=='r5-static/cycle-prefix.json')
raw=(ROOT/item['file']).read_bytes();assert sha(raw)=='4d153e82f0a75d233bb77bb7028a2a3dc2bdbcd4f22bda6514a15d0be4450de0'
prefix=json.loads(raw);event=prefix['frames'][7]['event'];assert event['event']=='READONLY_ABSENCE_STARTED'and event['sequence']==8
assert event['payload']['initial_event_head']=={'sequence':7,'hash':'87f8f86767e923c8fe7eb351c45eb57df3d6d4ebfdf855249fc7f5be025bbf84'}
assert prefix['frames'][6]['event']['event_hash']=='28ef8b468d67a04e9ba75fe3e41a45fb96f280deb95ddcef4cdc2097d6c195f9'
event['payload']['initial_event_head']={'sequence':7,'hash':prefix['frames'][6]['event']['event_hash']}
previous='0'*64
for i,frame in enumerate(prefix['frames'],1):
    e=frame['event'];e['previous_hash']=previous;e['event_hash']=h({k:v for k,v in e.items()if k!='event_hash'});previous=e['event_hash']
    if e['event']=='PLAN_ACCEPTED'and e['plan_ref']==prefix['subject_plan_ref']:prefix['accepted_anchor']={'sequence':i,'hash':previous}
prefix['expected_book_head']={'sequence':len(prefix['frames']),'hash':previous}
newraw=canon(prefix)+b'\n';raw_write(EX/'resources/prefix.json',newraw)
matches=[e for e in bundle['evidence']if e['resource']['path']==item['logical']];assert len(matches)==1
matches[0]['resource']=dict(matches[0]['resource'],sha256=sha(newraw))
bundle_raw=json.dumps(bundle,ensure_ascii=False,indent=2).encode('utf8')+b'\n';raw_write(EX/'bundle.json',bundle_raw)
resources=[{'logical':item['logical'],'file':(EX/'resources/prefix.json').relative_to(ROOT).as_posix(),'raw_sha256':sha(newraw),'bytes':len(newraw),'disposition':'R6_HEAD_FIX_AND_NECESSARY_EVENT_CHAIN_DIGESTS'}]
resources+=[dict(r,disposition='UNCHANGED_FROZEN_R5_INPUT')for r in old['resources']if r['logical']!=item['logical']]
write(EX/'case.json',{'id':'R6-single-mixed-control-head-correction','base':BASE,'source_case':OLD_CASE,'source_case_sha256':sha((ROOT/OLD_CASE).read_bytes()),'bundle':(EX/'bundle.json').relative_to(ROOT).as_posix(),'bundle_sha256':sha(bundle_raw),'resources':resources,'expected':'MIXED_CYCLE','entry':'unchanged R5 registration.Package.validate','candidate_count':1,'native_qualification':False})
write(EX/'case-index.json',{'candidate_count':1,'case':(EX/'case.json').relative_to(ROOT).as_posix(),'case_sha256':sha((EX/'case.json').read_bytes()),'source_case':OLD_CASE,'source_commit':BASE})
print(json.dumps({'status':'ONE_CANDIDATE_WRITTEN_PRECHECK_PENDING','Package_calls':0,'bundle_sha256':sha(bundle_raw),'prefix_sha256':sha(newraw)}))
