# -*- coding: utf-8 -*-
"""Independent standard-library immutable SQL/byte checks, shared by two isolated cases."""
from collections import Counter
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
from evidence import OUT,sha,canon,ref,write

def verify_case(label,read,runtime_source,target_source,expect_hold):
    temp=Path(tempfile.mkdtemp(prefix='a03-r2-review-immutable-')).resolve();dbs={};records=[]
    try:
        for role,source in [('runtime',runtime_source),('target',target_source)]:
            body=read(source);before=sha(body);copy=temp/(role+'.sqlite3')
            with copy.open('xb') as f:f.write(body)
            db=sqlite3.connect(copy.as_uri()+'?mode=ro&immutable=1',uri=True);db.row_factory=sqlite3.Row;sql=[]
            try:
                db.set_trace_callback(sql.append);db.execute('PRAGMA query_only=ON')
                assert db.execute('PRAGMA quick_check').fetchone()[0]=='ok'
                app=db.execute('PRAGMA application_id').fetchone()[0];version=db.execute('PRAGMA user_version').fetchone()[0]
                names=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
                counts={n:db.execute('SELECT count(*) FROM "'+n.replace('"','""')+'"').fetchone()[0] for n in names}
                selected=('books','registrations','plans','actions','intents','permits','resolutions','artifacts','native_pre_runs','native_report_reads','native_creation_anchors','events') if role=='runtime' else ('effects',)
                values={n:[dict(r) for r in db.execute('SELECT * FROM '+n)] for n in selected}
                values['meta']={r[0]:r[1] for r in db.execute('SELECT * FROM meta')}
            finally:db.close()
            after=sha(copy.read_bytes());assert before==after==sha(read(source))
            dbs[role]={'counts':counts,'rows':values}
            records.append({'role':role,'source':source,'source_sha256':before,'copy_path':str(copy),
              'copy_sha256_before':before,'copy_sha256_after':after,'source_sha256_after':sha(read(source)),
              'mode':'mode=ro&immutable=1; query_only=ON','quick_check':'ok','application_id':app,'user_version':version,
              'counts':counts,'sql':sql,'selected_rows':values})
        rc=dbs['runtime']['counts'];v=dbs['runtime']['rows'];tc=dbs['target']['counts']
        assert all(rc[t]==1 for t in ('plans','actions','intents','permits','resolutions','native_pre_runs','native_report_reads','native_creation_anchors'))
        assert tc['effects']==1
        reg=v['registrations'][0];book=v['books'][0];planrow=v['plans'][0];action=v['actions'][0];intent=v['intents'][0]
        run=v['native_pre_runs'][0];permit=v['permits'][0];headrow=v['resolutions'][0]
        def doc(p):return json.loads(read(p))
        bundle=doc(reg['bundle_path']);artifacts=bundle['artifacts'];lookup={canon(ref(a)):a for a in artifacts}
        for a in artifacts:assert sha(canon({k:x for k,x in a.items() if k!='content_hash'}))==a['content_hash']
        formal={canon(json.loads(a['ref'])) for a in v['artifacts']}
        assert formal==set(lookup)
        planref=json.loads(planrow['ref']);intentref=json.loads(intent['ref']);headref=json.loads(headrow['ref'])
        plan=lookup[canon(planref)];head=lookup[canon(headref)]
        assert sha(canon(planref))==planrow['id']==action['plan']==intent['plan']
        assert len(plan['payload']['actions'])==1 and plan['payload']['actions'][0]['operation']=='CREATE_FRAMES'
        assert plan['payload']['actions'][0]['action_id']==action['id']==intent['action']
        assert action['intent']==intent['id']==permit['intent']==headrow['intent']
        assert planrow['status']=='FINISHED' and action['state']=='APPLIED' and intent['state']=='RESOLVED_APPLIED'
        assert permit['state']=='CONSUMED'
        receipts=[a for a in artifacts if a['kind']=='ExecutionReceipt'];assert len(receipts)==1
        receipt=receipts[0];receiptref=ref(receipt);assert json.loads(intent['receipt'])==receiptref and canon(receiptref) in formal
        package=reg['package_root'].replace('\\','/')
        def resource(r):
            p=package+'/'+r['path'];b=read(p);assert sha(b)==r['sha256'];return json.loads(b)
        factref=json.loads(action['fact']);fact=resource(factref)
        assert fact['origin_phase']=='RECOVERY' and fact['plan_ref']==planref and fact['intent_ref']==intentref
        assert fact['action_id']==action['id'] and fact['action_digest']==action['digest']
        assert fact['result']['action_id']==action['id'] and fact['result']['intent_ref']==intentref
        assert fact['result']['attempt_fact']=='MAY_HAVE_BEEN_ATTEMPTED' and fact['result']['outcome']=='APPLIED'
        assert receipt['payload']['plan']==planref and receipt['payload']['action_fact_refs']==[factref]
        assert receipt['payload']['results']==[fact['result']]
        assert fact['resolution_ref']==headref and head['payload']['resolution']=='RESOLVED_APPLIED'
        assert head['payload']['original_receipt_ref'] is None and head['payload']['intent_ref']==intentref
        effect=json.loads(dbs['target']['rows']['effects'][0]['body'])
        assert effect['plan_ref']==planref and effect['action_id']==action['id'] and effect['action_digest']==action['digest'] and effect['mutated']
        assert run['status']=='ADMITTED' and run['accepted_plan']==planrow['id'] and json.loads(run['binding'])['context']['kind']=='INITIAL'
        preref=json.loads(run['pre_ref']);pre=lookup[canon(preref)]
        assert pre['payload']['stage']=='PRE_APPLY' and type(pre['payload']['coverage']) is dict and pre['payload']['decision']=='PASS'
        runref=pre['payload']['synthetic_run_ref'];runvalue=resource(runref);assert run['run_sha']==runref['sha256']
        checks={r['check_id']:r['outcome'] for r in pre['payload']['checks']};assert checks==runvalue['checks'] and set(checks.values())=={'PASS'} and len(checks)==5
        progresses=[a for a in artifacts if a['kind']=='ExecutionProgress']
        unknown=[a for a in progresses if a['payload']['actions'][0]['effective_outcome']=='UNKNOWN']
        assert unknown and all(a['payload']['actions'][0]['receipt_ref'] is None for a in unknown)
        material=[]
        for a in progresses:
            item=a['payload']['actions'][0]
            if item['result_fact'] is None:continue
            terms={'plan_ref':a['payload']['plan_ref']==fact['plan_ref'],'action_id':item['action_id']==fact['action_id'],
              'intent_ref':item['intent_ref']==fact['intent_ref'],'attempt_fact':item['attempt_fact']==fact['result']['attempt_fact']}
            assert all(terms.values()) and item['result_fact']==factref and item['receipt_ref']==receiptref
            assert item['attempt_evidence_refs']==fact['result']['attempt_evidence_refs']
            material.append({'ref':ref(a),'four_bindings':terms,'attempt_fact':item['attempt_fact'],'attempt_evidence_refs':item['attempt_evidence_refs'],
              'result_fact':item['result_fact'],'receipt_ref':item['receipt_ref']})
        assert len(material)==2
        posts=[a for a in artifacts if a['kind']=='CheckReport' and a['payload']['stage']=='POST_APPLY'];batches=[a for a in artifacts if a['kind']=='BatchReport']
        assert len(posts)==len(batches)==1;post,batch=posts[0],batches[0];pp,bp=post['payload'],batch['payload']
        assert pp['receipt']==receiptref and pp['frame_structure']=='PASS' and pp['content_check_status']=='PENDING' and pp['submission_status']=='NOT_SUBMITTED'
        assert bp['receipt']==receiptref and bp['postcheck']==ref(post) and bp['state']=='CONTENT_PENDING' and bp['submission_status']=='NOT_SUBMITTED'
        assert bp['content_check_status']=='PENDING' and pp['report_snapshot_ref']==bp['report_snapshot_ref']
        assert canon(pp['report_snapshot_ref']) in formal and pp['report_snapshot_ref']!=fact['observed_snapshot_ref']
        report_observation=resource(pp['report_observation']);assert pp['report_observation']['sha256']!=fact['readback']['sha256']
        assert v['native_report_reads'][0]['plan_id']==planrow['id'] and v['native_report_reads'][0]['reads']==1
        binding=pp['action_bindings'][0]
        assert len(pp['action_bindings'])==1 and binding['action_id']==action['id'] and binding['action_digest']==action['digest']
        assert binding['intent_ref']==intentref and binding['fact_ref']==factref and binding['resolution_head_ref']==headref and binding['head_original_receipt_ref'] is None
        events=[json.loads(r['body']) for r in v['events']]
        holds=[e for e in events if e['event']=='TARGET_DRIFT_HOLD']
        if expect_hold:
            assert book['hold'] and any(e['payload']['hold_id']==book['hold'] for e in holds)
            assert book['phase']=='RELEASED' and book['owner'] is None
        else:assert book['hold'] is None and not holds
        anchor=v['native_creation_anchors'][0];assert sha(read(anchor['input_path']))==anchor['input_sha']
        boundary={'status':'FORMAL_N1_BOUNDARIES_VERIFIED','label':label,'counts':{'runtime':rc,'target':tc},
          'current_bundle_path':reg['bundle_path'],'current_bundle_sha256':sha(read(reg['bundle_path'])),'artifact_kinds':dict(Counter(a['kind'] for a in artifacts)),
          'plan_ref':planref,'plan_database_id':planrow['id'],'action_id':action['id'],'action_digest':action['digest'],'intent_id':intent['id'],'intent_ref':intentref,
          'PRE':{'ref':preref,'status':'ADMITTED','run_resource':runref,'checks':checks,'binding':json.loads(run['binding'])},
          'permit':permit,'effect_count':1,'effect':effect,'formal_receipt_ref':receiptref,'receipt_three_way_registration':True,
          'terminal_head_ref':headref,'terminal_original_receipt_ref':None,'original_UNKNOWN':[ref(a) for a in unknown],
          'material_fact_ref':factref,'material_fact':fact,'material_progress':material,
          'POST_ref':ref(post),'Batch_ref':ref(batch),'report_snapshot_ref':pp['report_snapshot_ref'],'report_observation_ref':pp['report_observation'],
          'independent_report_read_count':1,'content_check_status':'PENDING','submission_status':'NOT_SUBMITTED',
          'book':book,'hold_events':holds,'POST_HOLD_run_rows':sum(json.loads(r['binding'])['context']['kind']=='POST_HOLD' for r in v['native_pre_runs']),
          'creation_anchor_sha256':anchor['input_sha'],'history_recompute_after_UNKNOWN':'NOT_RUN',
          'native_API_or_product_calls_by_this_auditor':0}
    finally:
        assert temp.parent==Path(tempfile.gettempdir()).resolve() and temp.name.startswith('a03-r2-review-immutable-') and not temp.is_symlink()
        shutil.rmtree(temp)
    write(OUT/(label+'-database-review.json'),{'status':'IMMUTABLE_DB_COPIES_VERIFIED','label':label,'copies':records,
      'temporary_root':str(temp),'removed':not temp.exists(),'source_DB_SQL_connections':0})
    write(OUT/(label+'-boundary-review.json'),boundary)
    return boundary
