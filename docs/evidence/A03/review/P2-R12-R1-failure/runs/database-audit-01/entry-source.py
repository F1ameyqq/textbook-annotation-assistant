# -*- coding: utf-8 -*-
"""Exactly twelve own immutable SQLite copies; no runtime/product calls."""
import json
from pathlib import Path
import sqlite3
from collections import Counter
from evidence import OUT,EV,raw,doc,file,sha,canon,ref,read_author,write
checks=[]
def check(name,value):checks.append({'check':name,'passed':bool(value)})
def boundary(rows):
    r=rows['runtime']['tables'];t=rows['target']['tables'];reg=r['registrations'][0];bundle=json.loads(read_author(reg['bundle_path']))
    lookup={canon(ref(a)):a for a in bundle['artifacts']}
    check('SQL artifacts equals current bundle refs',{canon(json.loads(a['ref'])) for a in r['artifacts']}==set(lookup))
    formal=[]
    for row in r['artifacts']:
        b=read_author(row['path']);a=json.loads(b)
        check('formal artifact raw identity '+a['artifact_id'],ref(a)==json.loads(row['ref']) and lookup.get(canon(ref(a)))==a)
        check('formal content hash '+a['artifact_id'],sha(canon({k:v for k,v in a.items() if k!='content_hash'}))==a['content_hash'])
        formal.append({'ref':ref(a),'path':row['path'],'raw_sha256':sha(b)})
    ledger_files=[]
    for row in r['files']:
        path=Path(reg['package_root']).parents[1]/row['path'];b=read_author(path)
        check('ledger file '+str(path),sha(b)==row['sha'] and len(b)==row['size'])
        ledger_files.append({'path':str(path),'sha256':sha(b),'bytes':len(b)})
    events=[json.loads(row['body']) for row in r['events']]
    for i,e in enumerate(events):
        check('event hash '+str(e['sequence']),sha(canon({k:v for k,v in e.items() if k!='event_hash'}))==e['event_hash'])
        if i:check('event predecessor '+str(e['sequence']),e['previous_hash']==events[i-1]['event_hash'])
    if events:check('book event head',(r['books'][0]['head_sequence'],r['books'][0]['head_hash'])==(events[-1]['sequence'],events[-1]['event_hash']))
    resources={}
    def resource(value):
        b=read_author(Path(reg['package_root'])/value['path']);check('Resource '+value['path'],sha(b)==value['sha256']);return b
    def walk(v):
        if isinstance(v,dict):
            if {'path','sha256','media_type'}<=set(v):
                key=(v['path'],v['sha256'],v['media_type'])
                if key in resources:return
                b=resource(v);resources[key]={'resource':v,'bytes':len(b),'actual_sha256':sha(b)}
                if v['media_type']=='application/json':walk(json.loads(b))
            else:
                for x in v.values():walk(x)
        elif isinstance(v,list):
            for x in v:walk(x)
    walk(bundle)
    meta={v['key']:v['value'] for v in t.get('meta',[])};state=json.loads(meta['state']) if 'state' in meta else {}
    facts=[];plan=next((a for a in bundle['artifacts'] if a['kind']=='ApplyPlan'),None)
    for a in r['actions']:
        if a['fact']:
            fr=json.loads(a['fact']);fact=json.loads(resource(fr));walk(fact)
            issue='issue-save-unknown-'+sha(canon(fact))[:32]
            check('fact action binding',fact['action_id']==a['id'] and fact['action_digest']==a['digest'])
            if plan:check('fact exact plan',fact['plan_ref']==ref(plan))
            intent=next(v for v in r['intents'] if v['id']==a['intent'])
            check('fact exact intent',fact['intent_ref']==json.loads(intent['ref']))
            facts.append({'resource':fr,'body':fact,'derived_unknown_issue_id':issue})
    issue_objects=[i for a in bundle['artifacts'] if a['kind']=='CheckReport' for i in a['payload'].get('issues',[]) if isinstance(i,dict)]
    receipts=[a for a in bundle['artifacts'] if a['kind']=='ExecutionReceipt']
    posts=[a for a in bundle['artifacts'] if a['kind']=='CheckReport' and a['payload'].get('stage')=='POST_APPLY']
    return {'formal':formal,'ledger_files':ledger_files,'resources':list(resources.values()),'events':events,
      'kind_counts':dict(Counter(a['kind'] for a in bundle['artifacts'])),'facts':facts,'formal_issue_objects':issue_objects,
      'receipts':receipts,'POSTs':posts,'book':r['books'][0],'actions':r['actions'],'plans':r['plans'],'intents':r['intents'],'permits':r['permits'],
      'call_attempt_resolution_counts':{n:len(r[n]) for n in ('calls','attempts','resolutions')},
      'native_report_reads':len(r['native_report_reads']) if 'native_report_reads' in r else 'TABLE_ABSENT_LEGACY',
      'target_effect_rows':len(t.get('effects',[])),'target_effects':t.get('effects',[]),
      'target_questions':state.get('target',{}).get('questions',[]),'target_frames':state.get('target',{}).get('frames',[]),
      'target_observations':t.get('observations',[]),'target_state':state,'plan_ref':ref(plan) if plan else None,
      'expected_frames':len(json.loads(plan['payload']['actions'][0]['expected_after']['frames'])) if plan else None}

results=[]
for scene,stages in [('L1',['before-build','unknown-established','after-release']),('U1',['before-build','first-failure','after-release'])]:
    for stage in stages:
        prefix=EV+'validation/author-01/cases/'+scene+'/captures/'+stage+'/'
        capture=doc(prefix+'capture.json');expected=doc(prefix+'SQL.json');actual={};db_records=[]
        for name in ('runtime','target'):
            source=prefix+name+'.sqlite3';body=raw(source);record=next(r for r in capture['records'] if r['kind']==name)
            check('capture raw SHA '+source,sha(body)==record['sha256'] and len(body)==record['size'])
            copy=OUT/'databases'/scene/stage/(name+'.sqlite3');write(copy,body)
            queries=[];db=sqlite3.connect(copy.resolve().as_uri()+'?mode=ro&immutable=1',uri=True);db.row_factory=sqlite3.Row
            try:
                db.set_trace_callback(queries.append);db.execute('PRAGMA query_only=ON')
                quick=db.execute('PRAGMA quick_check').fetchone()[0]
                app=db.execute('PRAGMA application_id').fetchone()[0];version=db.execute('PRAGMA user_version').fetchone()[0]
                schema=[dict(r) for r in db.execute("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name")]
                names=[r['name'] for r in schema if r['type']=='table']
                rows={n:[dict(r) for r in db.execute('SELECT * FROM "'+n.replace('"','""')+'"')] for n in names}
            finally:db.close()
            check('immutable DB bytes '+source,sha(copy.read_bytes())==sha(raw(source))==sha(body))
            check('quick_check '+source,quick=='ok')
            check('captured SQL rows '+source,rows==expected[name]['tables'])
            check('SQLite namespace '+source,app==expected[name]['application_id'] and version==expected[name]['user_version'])
            actual[name]={'application_id':app,'user_version':version,'tables':rows}
            db_records.append({'source_target_path':source,'source_export':str(file(source)),'own_SQL_copy':str(copy),'bytes':len(body),
              'sha256_before_after':sha(body),'quick_check':quick,'schema':schema,'queries':queries,'SQL_connection':'OWN_COPY_ONLY_MODE_RO_IMMUTABLE_QUERY_ONLY',
              'original_capture':record,'live_database_opened':False})
        results.append({'scene':scene,'stage':stage,'databases':db_records,'SQL':actual,'boundary':boundary(actual),
          'capture_metadata':capture,'cross_database_atomic':False})
scene_results=[]
for scene,middle in [('L1','unknown-established'),('U1','first-failure')]:
    selected={r['stage']:r for r in results if r['scene']==scene};b=selected['before-build'];m=selected[middle];a=selected['after-release'];v=m['boundary'];av=a['boundary']
    check(scene+' effects once',v['target_effect_rows']==av['target_effect_rows']==1)
    check(scene+' partial frames',len(v['target_frames'])==len(av['target_frames'])==1 and v['expected_frames']==2)
    check(scene+' UNKNOWN fact',len(v['facts'])==1 and v['facts'][0]['body']['result']['outcome']=='UNKNOWN' and v['actions'][0]['state']=='UNKNOWN')
    check(scene+' actual attempt fact',v['facts'][0]['body']['result']['attempt_fact']=='MAY_HAVE_BEEN_ATTEMPTED' and not v['facts'][0]['body']['result']['replay_allowed'])
    check(scene+' pending consumed interrupted',v['intents'][0]['state']=='PENDING' and v['permits'][0]['state']=='CONSUMED' and v['plans'][0]['status']=='INTERRUPTED')
    for table in ('actions','intents','permits','plans','calls','attempts','resolutions'):
        check(scene+' release preserves '+table,m['SQL']['runtime']['tables'][table]==a['SQL']['runtime']['tables'][table])
    check(scene+' target unchanged after release',m['SQL']['target']==a['SQL']['target'])
    check(scene+' owner released',av['book']['owner'] is None and av['book']['phase']=='RELEASED' and av['book']['lease']==0 and av['book']['pid'] is None)
    check(scene+' no recovery',set(v['call_attempt_resolution_counts'].values())=={0})
    released=doc(EV+'validation/author-01/cases/'+scene+'/released-status.json')
    if scene=='U1':
        check('U1 no formal result/report',all(v['kind_counts'].get(k,0)==0 for k in ('ExecutionReceipt','ExecutionProgress','BatchReport')) and not v['POSTs'])
        check('U1 receipt NULL and no issue owner',v['intents'][0]['receipt'] is None and not any(i.get('issue_id')==v['facts'][0]['derived_unknown_issue_id'] for i in v['formal_issue_objects']))
        check('U1 expected issue ID',v['facts'][0]['derived_unknown_issue_id']=='issue-save-unknown-1c539a7e21cad8405cbf61cb958992af')
        check('U1 no report reads',v['native_report_reads']==0)
    else:
        check('L1 finite receipt/progress/POST',len(v['receipts'])==1 and v['kind_counts'].get('ExecutionProgress')==1 and len(v['POSTs'])==1)
        receipt=v['receipts'][0];issue=v['facts'][0]['derived_unknown_issue_id']
        check('L1 formal issue binding',receipt['payload']['unresolved_issue_ids']==[issue] and any(i.get('issue_id')==issue for i in v['formal_issue_objects']))
        check('L1 intent receipt binding',json.loads(v['intents'][0]['receipt'])==ref(receipt))
    scene_results.append({'scene':scene,'middle_stage':middle,'before_counts':{n:len(rows) for n,rows in b['SQL']['runtime']['tables'].items()},
      'middle':v,'after_release_book':av['book'],'released_status':released,
      'raw_db_sha256_by_stage':{s:{r['source_target_path'].rsplit('/',1)[1]:r['sha256_before_after'] for r in selected[s]['databases']} for s in selected}})
write(OUT/'database-review.json',{'status':'FROZEN_FAILURE_SQL_CONFIRMED' if all(r['passed'] for r in checks) else 'EVIDENCE_INCONSISTENCY',
 'checks':checks,'failed_checks':[r for r in checks if not r['passed']],'stages':results,'scene_summaries':scene_results,
 'exported_stage_originals':12,'own_immutable_SQL_copies':12,'product_imports_or_calls':0,'runtime_or_author_DB_connections':0,
 'new_functional_calls':0,'observed_SQL_queries_only':True})
print(json.dumps({'status':'FROZEN_FAILURE_SQL_CONFIRMED' if all(r['passed'] for r in checks) else 'EVIDENCE_INCONSISTENCY',
 'stage_DB_copies':12,'checks':len(checks),'failed_checks':sum(not r['passed'] for r in checks),'product_calls':0}))
