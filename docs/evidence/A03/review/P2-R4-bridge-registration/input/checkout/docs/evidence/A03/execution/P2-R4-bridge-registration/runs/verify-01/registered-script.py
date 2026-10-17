"""Read-only delivery integrity audit; never imports product or Package checker."""
import ast,hashlib,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5];OUT=Path(__file__).resolve().parent
EX=ROOT/'examples/a03/P2-R4-bridge-registration';REPORT=ROOT/'docs/tasks/A03-P2-R4-bridge-registration-delivery.md'
BASE='87606b73e0754fa670491d9fb958a416c26bfe88';WORKFLOW='ef1d2f4a20971b416afae500889aa5c090dfe89b'
def load(p):return json.loads(p.read_bytes())
def sha(raw):return hashlib.sha256(raw).hexdigest()
def digest(v):return sha(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf8'))
def git(*args):return subprocess.check_output(['git','-c','core.longpaths=true',*args],cwd=ROOT)
def audit(final=False):
    old=load(OUT/'old-baseline.json')['files'];assert len(old)==28002
    for row in old:
        raw=(ROOT/row['path']).read_bytes();assert len(raw)==row['bytes']and sha(raw)==row['sha256'],row['path']
    index=load(OUT/'input-index.json');assert index['base']==BASE and index['workflow']==WORKFLOW
    pins=index['documents']+index['product_text']+index['reused_inputs']+load(OUT/'resource-input-pins.json')['inputs']
    for row in pins:
        raw=git('show',row['commit']+':'+row['path']);assert sha(raw)==row['sha256']and len(raw)==row['bytes']
        if 'raw_git_blob'in row:assert git('rev-parse',row['commit']+':'+row['path']).decode().strip()==row['raw_git_blob']
        assert (ROOT/row.get('copy',row['path'])).read_bytes()==raw
    proposal=load(EX/'bridge-interface-proposal.json');assert sha((EX/'bridge-interface-proposal.json').read_bytes())=='b57d0af5d72a03c4b16e6eeedc267bda50f1dfcf022728b1f107f5b158a22207'
    inventory=load(OUT/'function-inventory.json');functions={(r['path'],r['qualified_name']):r for r in inventory['functions']}
    assert len(proposal['interfaces'])==19 and proposal['proposed_new_pre_boundary']['status']=='PROPOSED_NOT_EXISTING'
    for row in proposal['interfaces']:
        f=row['existing'];assert functions[(f['path'],f['qualified_name'])]==f
        raw=(OUT/'inputs/product-text'/f['path']).read_bytes();assert sha(raw)==f['source_sha256'];tree=ast.parse(raw.decode('utf8'))
        node=next(n for n in ast.walk(tree)if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))and n.lineno==f['start'])
        assert node.end_lineno==f['end']
        segment=ast.get_source_segment(raw.decode('utf8'),node)
        assert sha(segment.encode('utf8'))==f['function_source_sha256']
    results=load(OUT/'four-package-results.json');assert results['fixed_package_calls']==4 and results['old_36_matrix_runs']==0
    assert len(results['checks'])==4 and results['checks'][0]['matched']is False
    assert [r['case']for r in results['checks']]==['registration-positive','source-binding-negative','snapshot-binding-negative','target-tuple-negative']
    for r in results['checks']:
        assert r['actual']=='FRAME_REGISTRATION_BINDING'
        case=load(ROOT/r['case_path']);bundle_raw=(ROOT/case['bundle']).read_bytes();assert sha(bundle_raw)==case['bundle_sha256']
        bundle=json.loads(bundle_raw);assert len(bundle['artifacts'])==10
        for a in bundle['artifacts']:assert digest({k:v for k,v in a.items()if k!='content_hash'})==a['content_hash']
        resources={x['logical']:x for x in case['resources']}
        for item in resources.values():assert sha((ROOT/item['file']).read_bytes())==item['sha256']
        prefix=load(ROOT/resources[case['prefix_resource']['path']]['file']);assert len(prefix['frames'])==6
        previous='0'*64
        for i,frame in enumerate(prefix['frames'],1):
            event=frame['event'];assert event['sequence']==i and event['previous_hash']==previous
            assert digest({k:v for k,v in event.items()if k!='event_hash'})==event['event_hash'];previous=event['event_hash']
        assert prefix['expected_book_head']=={'sequence':6,'hash':previous}
        last=prefix['frames'][-1]['event'];assert last['event']=='TARGET_DRIFT_HOLD'and last['plan_ref']is None and last['payload']['plan_ref']is None
    routing=load(OUT/'fixed-entry-routing.json');assert routing['package_class_ast_unchanged']and routing['no_package_semantic_changes']and not routing['old_36_matrix_called']
    residual=load(OUT/'minimal-residual-assessment.json');assert residual['package_calls_total']==4
    assert residual['guard_inputs'][0]['existing_guard_in_actual_consumer_context']is True
    assert residual['guard_inputs'][0]['existing_guard_in_global_pool_context']is False
    assert residual['guard_inputs'][3]['target_tuple_matches']is False
    expected={'freeze-01':0,'prepare-01':1,'assess-01':1,'assess-02':0}
    for label,code in expected.items():
        run=OUT/'runs'/label;v=load(run/'exit.json');registration=load(run/'registration.json')
        assert v['exit_code']==code and not v['alive']and v['owned_pid']>0
        assert sha((run/'registered-script.py').read_bytes())==registration['script_sha256']
        assert (run/'stdout.txt').is_file()and(run/'stderr.txt').is_file()
    pending={OUT/'process-release.json',OUT/'sha256-manifest.json'}
    links=0
    for p in(REPORT,EX/'README.md'):
        for ref in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf8')):
            if '://'in ref or ref.startswith('#'):continue
            target=(p.parent/ref.split('#',1)[0]).resolve();assert target.is_file()or(not final and target in pending),(str(p),ref);links+=1
    allowed=('examples/a03/P2-R4-bridge-registration/','docs/evidence/A03/execution/P2-R4-bridge-registration/','docs/tasks/A03-P2-R4-bridge-registration-delivery.md')
    changed=git('diff','--name-only',BASE).decode().splitlines()
    untracked=git('ls-files','--others','--exclude-standard').decode().splitlines()
    assert all(any(p.startswith(a)for a in allowed)for p in changed+untracked),changed+untracked
    final_files=None
    if final:
        release=load(OUT/'process-release.json');assert release['status']=='OWNED_STATIC_CHILDREN_EXITED'
        for row in release['runs']:
            assert not row['alive'];v=load(OUT/'runs'/row['run']/'exit.json');assert not v['alive']and v['exit_code']==row['exit_code']
        manifest=load(OUT/'sha256-manifest.json');expected_paths={REPORT.relative_to(ROOT).as_posix()}
        expected_paths.update(p.relative_to(ROOT).as_posix()for root in(OUT,EX)for p in root.rglob('*')if p.is_file()and p!=OUT/'sha256-manifest.json')
        assert expected_paths=={r['path']for r in manifest['files']}
        for row in manifest['files']:
            raw=(ROOT/row['path']).read_bytes();assert len(raw)==row['bytes']and sha(raw)==row['sha256'],row['path']
        final_files=len(manifest['files'])
    return {'status':'INTEGRITY_AUDITED_REVIEW_REMAINS','protected_old_files':len(old),'raw_git_input_pins':len(pins),'existing_interfaces':19,'proposed_nonexistent_pre_boundary':1,'saved_package_checks':4,'package_calls_this_audit':0,'old_36_matrix_runs':0,'new_markdown_links':links,'manifest_files':final_files,'product_imports_or_calls':0,'field_reset_probe':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'}
if __name__=='__main__':
    final=sys.argv[1:]==['--check'];assert final or not sys.argv[1:]
    result=audit(final)
    if not final:
        with(OUT/'delivery-verification.json').open('xb')as f:f.write(json.dumps(result,indent=2).encode('utf8')+b'\n')
    print(json.dumps(result))
