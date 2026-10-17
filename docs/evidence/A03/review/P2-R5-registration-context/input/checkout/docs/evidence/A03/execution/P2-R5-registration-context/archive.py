"""Audit saved inputs/results/old files only. Never load a checker or product."""
import json,os,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5];EX=ROOT/'examples/a03/P2-R5-registration-context';sys.path.insert(0,str(EX))
from common import BASE,OUT,git,h,isres,load,sha,write
REPORT=ROOT/'docs/tasks/A03-P2-R5-registration-context-delivery.md'
def tree_records(raw):
    result={}
    for token in raw.split(b'\0'):
        if token:
            header,name=token.split(b'\t',1);mode,kind,oid=header.decode().split();result[name.decode('utf8')]=(mode,kind,oid)
    return result
def saved_results():
    rows=[load(p)for p in sorted((OUT/'results').glob('*.json'))]
    assert len(rows)==8 and sum(r['package_calls']for r in rows)==8
    assert all(r['overlay_sha256']=='3f0281c5cfc9aeec99b11fa2de30ba40e9984a19dd0e651b747d99ebe29772ba'for r in rows)
    assert all(r['none_book_real_consumers']==0 and r['product_calls']==r['old_36_matrix_runs']==0 for r in rows)
    assert all(r['loader']['fixed_R3_Package_AST_unchanged']for r in rows)
    original=load(OUT/'results/case-07.json');repaired=load(OUT/'results/case-07-repair-01.json')
    assert original['actual']=='SHAPE_oneOf'and not original['matched']and repaired['actual']=='MIXED_CYCLE'and repaired['matched']
    positive=next(r for r in rows if r['id']=='registration-positive');assert positive['full_entry_returned']
    assert positive['inherited_tail_trace']==['MIXED_DAG','CONSUMER_DECLARATIONS_BOOK_SCOPE','ARTIFACT_HASH','FULL_R2_TAIL_RETURN']
    assert len(positive['prefix_visits'])==2 and len(positive['global_frames'])==6
    target=next(r for r in rows if r['id']=='target-tuple-negative');assert all(target['registration_checks'][0]['binding_checks'].values())
    assert target['registration_checks'][0]['target_checks']['snapshot_target_id']is False
    global_hash=next(r for r in rows if r['id']=='global-resource-hash-corruption');assert global_hash['resource_read_failures']==[{'code':'RESOURCE_HASH','path':'r5-static/global-only-proof.txt','active_real_contexts':0}]
    return rows
def control_residual():
    info=load(ROOT/load(EX/'repair-case-index.json')['cases'][0]['case'])
    item=next(r for r in info['resources']if r['logical']=='r5-static/cycle-prefix.json');prefix=load(ROOT/item['file']);mismatches=[]
    previous='0'*64
    for i,f in enumerate(prefix['frames'],1):
        e=f['event'];assert e['sequence']==i and e['previous_hash']==previous and h({k:v for k,v in e.items()if k!='event_hash'})==e['event_hash']
        p=e['payload']
        if 'initial_event_head'in p and p['initial_event_head']!={'sequence':i-1,'hash':previous}:
            mismatches.append({'event':e['event'],'sequence':i,'declared_initial_event_head':p['initial_event_head'],'actual_predecessor_head':{'sequence':i-1,'hash':previous}})
        previous=e['event_hash']
    assert len(mismatches)==1 and mismatches[0]['sequence']==8
    return {'status':'MIXED_CYCLE_CONTROL_NOT_CLEANLY_CLOSED','case':'artifact-resource-frame-mixed-cycle','repair_rounds_used':1,'further_repair_or_package_calls':0,'method':'read saved input fields and recompute existing hashes only; no Package invocation','input_path':item['file'],'input_sha256':item['raw_sha256'],'observed_package_rejection':'MIXED_CYCLE','event_hash_chain_valid':True,'mismatches':mismatches,'stop':'one permitted local round exhausted; preserve residual and REVIEW','field_reset_probe':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'}
def audit(final=False):
    inputs=load(OUT/'input-index.json');pins=inputs['inputs']+load(OUT/'repair-input-index.json')['inputs'];pin_paths={p['path']for p in pins if p['commit']==BASE}
    assert sha((OUT/'old-tree.raw').read_bytes())==inputs['old_tree_sha256']
    assert git('ls-tree','-r','-z',BASE)==(OUT/'old-tree.raw').read_bytes()
    current_tree=tree_records(git('ls-tree','-r','-z','HEAD'));old=[json.loads(line)for line in(OUT/'old-preservation.jsonl').read_bytes().splitlines()];assert len(old)==28113
    staged={}
    for token in git('ls-files','--stage','-z').split(b'\0'):
        if token:
            header,name=token.split(b'\t',1);mode,oid,stage=header.decode().split();assert stage=='0';staged[name.decode('utf8')]=(mode,oid)
    for row in old:
        path=ROOT/row['path'];raw=path.read_bytes();assert len(raw)==row['bytes']and sha(raw)==row['checkout_sha256']and path.is_symlink()==row['symlink'],row['path']
        assert current_tree[row['path']]==(row['mode'],row['type'],row['blob'])and staged[row['path']]==(row['mode'],row['blob']),row['path']
    for pin in pins:
        raw=git('show',pin['commit']+':'+pin['path']);assert len(raw)==pin['bytes']and sha(raw)==pin['sha256']
        assert git('rev-parse',pin['commit']+':'+pin['path']).decode().strip()==pin['git_blob']
        assert raw==(ROOT/pin.get('copy',pin['path'])).read_bytes()
    assert sha((EX/'registration.py').read_bytes())=='3f0281c5cfc9aeec99b11fa2de30ba40e9984a19dd0e651b747d99ebe29772ba'
    rows=saved_results();residual=control_residual();resource_visits=0;intentional=[]
    for name in('case-index.json','repair-case-index.json'):
        for row in load(EX/name)['cases']:
            raw=(ROOT/row['case']).read_bytes();assert sha(raw)==row['case_sha256'];case=json.loads(raw);bundle_raw=(ROOT/case['bundle']).read_bytes();assert sha(bundle_raw)==case['bundle_sha256'];bundle=json.loads(bundle_raw)
            assert all(h({k:v for k,v in a.items()if k!='content_hash'})==a['content_hash']for a in bundle['artifacts'])
            over={r['logical']:(ROOT/r['file']).read_bytes()for r in case['resources']}
            for r in case['resources']:assert sha(over[r['logical']])==r['raw_sha256']and len(over[r['logical']])==r['bytes']
            if case.get('source_case_copy')and row['id']!='r3-original-undeclared-evidence':
                source=case['source'];assert git('show',BASE+':'+source['bundle'])==bundle_raw
                assert git('show',BASE+':'+source['case'])==(ROOT/case['source_case_copy']).read_bytes()
            seen=set()
            def walk(v):
                nonlocal resource_visits
                if isres(v):
                    token=(v['path'],v['sha256'])
                    if token in seen:return
                    seen.add(token);resource_visits+=1
                    if v['path']in over:body=over[v['path']]
                    else:
                        target=ROOT/'examples/a03/P2-R2-proposal/candidate-final'/v['path'];assert target.relative_to(ROOT).as_posix()in pin_paths;body=target.read_bytes()
                    if sha(body)!=v['sha256']:
                        assert row['id']=='global-resource-hash-corruption'and v['path']=='r5-static/global-only-proof.txt';intentional.append({'case':row['id'],'path':v['path']});return
                    if v['media_type']=='application/json':walk(json.loads(body))
                elif isinstance(v,dict):
                    for x in v.values():walk(x)
                elif isinstance(v,list):
                    for x in v:walk(x)
            walk(bundle)
    assert intentional==[{'case':'global-resource-hash-corruption','path':'r5-static/global-only-proof.txt'}]
    allowed=('examples/a03/P2-R5-registration-context/','docs/evidence/A03/execution/P2-R5-registration-context/','docs/tasks/A03-P2-R5-registration-context-delivery.md')
    names=git('diff','--name-only',BASE).decode().splitlines()+git('ls-files','--others','--exclude-standard').decode().splitlines()
    assert all(any(n.startswith(a)for a in allowed)for n in names)
    current=os.environ.get('A03_R5_RUN_ID');runs=0
    for p in sorted((OUT/'runs').iterdir()):
        reg=load(p/'registration.json');assert sha((p/'registered-script.py').read_bytes())==reg['script_sha256']
        if p.name==current:continue
        e=load(p/'exit.json');assert not e['alive']and not e['timed_out']and e['owned_pid']>0
        assert e['exit_code']==(1 if p.name=='case-07'else 0),p.name
        if e['mode']=='case':assert sha((p/'source-registration.py').read_bytes())=='3f0281c5cfc9aeec99b11fa2de30ba40e9984a19dd0e651b747d99ebe29772ba'
        runs+=1
    if not final:
        write(OUT/'control-residual.json',residual)
        write(OUT/'results-summary.json',{'status':'REVIEW_WITH_CONTROL_RESIDUAL','initial_cases':7,'package_calls':8,'local_repair_rounds':1,'affected_case_retests':1,'final_error_codes_matching':7,'qualified_scenarios':6,'mixed_cycle_control':'MIXED_CYCLE observed; internal initial_event_head mismatch remains','results':[{'id':r['id'],'expected':r['expected'],'actual':r['actual'],'matched':r['matched'],'error':r['error'],'full_entry_returned':r['full_entry_returned']}for r in rows],'overlay_sha256_unchanged':rows[0]['overlay_sha256'],'old_36_matrix_runs':0,'product_calls':0,'native_qualification':False,'field_reset_probe':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'})
    else:assert load(OUT/'control-residual.json')==residual
    pending={OUT/n for n in('archive-verification.json','sha256-manifest.json','process-release.json')};links=0
    for p in(REPORT,EX/'README.md'):
        for url in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf8')):
            if '://'in url or url.startswith('#'):continue
            target=(p.parent/url.split('#',1)[0]).resolve();assert target.is_file()or(not final and target in pending),(str(p),url);links+=1
    count=None
    if final:
        release=load(OUT/'process-release.json');assert release['status']=='OWNED_SYNCHRONOUS_CHILDREN_EXITED'
        for r in release['runs']:
            p=OUT/'runs'/r['run'];assert not r['alive']and not load(p/'exit.json')['alive']
            assert sha((p/'stdout.txt').read_bytes())==r['stdout_sha256']and sha((p/'stderr.txt').read_bytes())==r['stderr_sha256']
        manifest=load(OUT/'sha256-manifest.json');actual={REPORT.relative_to(ROOT).as_posix()}|{p.relative_to(ROOT).as_posix()for root in(EX,OUT)for p in root.rglob('*')if p.is_file()and p!=OUT/'sha256-manifest.json'}
        assert actual=={r['path']for r in manifest['files']}
        for r in manifest['files']:
            raw=(ROOT/r['path']).read_bytes();assert len(raw)==r['bytes']and sha(raw)==r['sha256'],r['path']
        count=len(manifest['files'])
    result={'status':'ARCHIVE_CONSISTENT_REVIEW_WITH_CONTROL_RESIDUAL','old_paths_preserved':len(old),'old_mode_type_blob_preserved':True,'raw_git_input_pins':len(pins),'saved_package_calls':8,'package_calls_this_audit':0,'resource_visits':resource_visits,'intentional_bad_resource_bodies':len(intentional),'initial_head_control_residuals':1,'completed_prior_owned_runs':runs,'markdown_links':links,'manifest_files':count,'product_imports':0,'old_36_matrix_runs':0,'field_reset_probe':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'}
    if not final:write(OUT/'archive-verification.json',result)
    return result
if __name__=='__main__':
    assert not sys.argv[1:]or sys.argv[1:]==['--check']
    print(json.dumps(audit(bool(sys.argv[1:]))))
