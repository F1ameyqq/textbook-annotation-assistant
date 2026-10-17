"""Read-only file/preservation audit; never imports checker or data_check."""
import ast,json,os,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5];EX=ROOT/'examples/a03/P2-R6-mixed-control';sys.path.insert(0,str(EX))
from files import BASE,OUT,git,load,old_inventory,sha,write
REPORT=ROOT/'docs/tasks/A03-P2-R6-mixed-control-delivery.md'
def audit(final=False):
    before=load(OUT/'old-preservation-before.json');after=old_inventory();assert before==after
    assert before['old_paths']==28318
    pins=load(OUT/'raw-input-pins.json')['inputs']
    for row in pins:
        raw=git('show',row['commit']+':'+row['path']);assert len(raw)==row['bytes']and sha(raw)==row['sha256']
        assert git('rev-parse',row['commit']+':'+row['path']).decode().strip()==row['git_blob']
        assert raw==(ROOT/row.get('copy',row['path'])).read_bytes()
    case=load(EX/'case.json');index=load(EX/'case-index.json');assert sha((EX/'case.json').read_bytes())==index['case_sha256']
    assert sha((ROOT/case['bundle']).read_bytes())==case['bundle_sha256']
    for r in case['resources']:assert sha((ROOT/r['file']).read_bytes())==r['raw_sha256']and(ROOT/r['file']).stat().st_size==r['bytes']
    pre=load(OUT/'precheck.json');entry=load(OUT/'entry-result.json');syntax=load(OUT/'driver-syntax-check.json')
    assert pre['status']=='DATA_CONSISTENCY_PASSED_BEFORE_PACKAGE'and pre['Package_calls']==0
    assert pre['data']['consumer_failures']==[]and len(pre['prefix_semantic_changes'])==15 and len(pre['bundle_semantic_changes'])==1
    assert pre['bundle_sha256']==entry['candidate_sha256']==case['bundle_sha256']and entry['precheck_sha256']==sha((OUT/'precheck.json').read_bytes())
    assert entry['measured_calls']=={'R5_complete_entry':1,'R3_inherited_entry':1,'R2_inherited_entry':1}and entry['R3_entry_counter_delta']==1
    assert entry['actual']=='MIXED_CYCLE'and entry['reached_layers']==['MIXED_DAG']and entry['consumer_failures']==[]and entry['matched_specified_layer_and_counts']
    assert all(e['observed_in_actual_graph']for e in entry['actual_ring_edges'])and entry['none_book_real_consumers']==0
    assert syntax['Package_calls_before_syntax_repair']==0 and syntax['current_driver_sha256']==sha((EX/'entry.py').read_bytes())
    failed=(OUT/'runs/entry-01/registered-script.py').read_bytes();assert sha(failed)==syntax['failed_script_sha256']
    try:ast.parse(failed.decode('utf8'));raise AssertionError('expected parse-only original driver error')
    except SyntaxError:pass
    for p in list(EX.glob('*.py'))+list(OUT.glob('*.py')):ast.parse(p.read_text(encoding='utf8'))
    current=os.environ.get('A03_R6_RUN_ID');completed=0
    for p in sorted((OUT/'runs').iterdir()):
        registration=load(p/'registration.json');assert sha((p/'registered-script.py').read_bytes())==registration['script_sha256']
        if p.name==current:continue
        end=load(p/'exit.json');assert not end['alive']and not end['timed_out']and end['owned_pid']>0
        assert end['exit_code']==(1 if p.name=='entry-01'else 0),p.name;completed+=1
    assert load(OUT/'runs/precheck-01/exit.json')['completed_at']<load(OUT/'runs/entry-02/registration.json')['registered_at']
    allowed=('examples/a03/P2-R6-mixed-control/','docs/evidence/A03/execution/P2-R6-mixed-control/','docs/tasks/A03-P2-R6-mixed-control-delivery.md')
    changed=git('diff','--name-only',BASE).decode().splitlines()+git('ls-files','--others','--exclude-standard').decode().splitlines();assert all(any(p.startswith(a)for a in allowed)for p in changed)
    pending={OUT/n for n in('old-preservation-after.json','archive-verification.json','sha256-manifest.json','process-release.json')};links=0
    for p in(REPORT,EX/'README.md'):
        for url in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf8')):
            if '://'in url or url.startswith('#'):continue
            target=(p.parent/url.split('#',1)[0]).resolve();assert target.is_file()or(not final and target in pending),(str(p),url);links+=1
    count=None
    if final:
        assert load(OUT/'old-preservation-after.json')==after
        release=load(OUT/'process-release.json');assert release['status']=='OWNED_SYNCHRONOUS_CHILDREN_EXITED'
        for r in release['runs']:
            p=OUT/'runs'/r['run'];assert not r['alive']and not load(p/'exit.json')['alive']
            assert sha((p/'stdout.txt').read_bytes())==r['stdout_sha256']and sha((p/'stderr.txt').read_bytes())==r['stderr_sha256']
        manifest=load(OUT/'sha256-manifest.json');actual={REPORT.relative_to(ROOT).as_posix()}|{p.relative_to(ROOT).as_posix()for root in(EX,OUT)for p in root.rglob('*')if p.is_file()and p!=OUT/'sha256-manifest.json'}
        assert actual=={r['path']for r in manifest['files']}
        for r in manifest['files']:
            raw=(ROOT/r['path']).read_bytes();assert len(raw)==r['bytes']and sha(raw)==r['sha256'],r['path']
        count=len(manifest['files'])
    result={'status':'ARCHIVE_CONSISTENT_REVIEW','old_paths_preserved':before['old_paths'],'old_mode_type_blob_and_checkout_digest_preserved':True,'raw_git_inputs':len(pins),'candidate_count':1,'measured_complete_R5_calls':entry['measured_calls']['R5_complete_entry'],'inherited_R3_counter_delta':entry['R3_entry_counter_delta'],'Package_calls_this_archive':0,'data_check_reruns_this_archive':0,'actual_layer':'MIXED_DAG','actual_code':entry['actual'],'consumer_failures':entry['consumer_failures'],'parse_only_driver_launch_failures':1,'completed_prior_owned_runs':completed,'markdown_links':links,'manifest_files':count,'other_six_cases_or_old_matrix_runs':0,'product_imports':0,'field_reset_probe':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'}
    if not final:write(OUT/'old-preservation-after.json',after);write(OUT/'archive-verification.json',result)
    return result
if __name__=='__main__':
    assert not sys.argv[1:]or sys.argv[1:]==['--check']
    print(json.dumps(audit(bool(sys.argv[1:]))))
