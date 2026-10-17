"""Verify saved product evidence and bytes only; never execute codec/tests."""
import ast,json,os,re,sys,zipfile
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5];EX=ROOT/'examples/a03/P2-R7-readonly-codec';sys.path.insert(0,str(EX))
from ops import BASE,FIX,OUT,PRODUCT,git,load,preservation,raw_git_batch,sha,verify_old_exception,write
REPORT=ROOT/'docs/tasks/A03-P2-R7-readonly-codec-delivery.md';TEST=ROOT/'tests/test_a03_r7_readonly_codec.py'
def audit(final=False):
    before=load(OUT/'old-preservation-before.json');after=preservation();assert before==after and before['preserved_old_paths']==28410
    exception=verify_old_exception()
    pins=load(OUT/'raw-input-pins.json')['inputs']+load(OUT/'compatibility-input-pins.json')['inputs']
    keys=[(r['commit'],r['path'])for r in pins];raw_inputs=raw_git_batch(keys)
    for row in pins:
        blob,raw=raw_inputs[(row['commit'],row['path'])];assert blob==row['git_blob']and len(raw)==row['bytes']and sha(raw)==row['sha256']
        if row['path']=='pyproject.toml':continue
        actual=(ROOT/row.get('copy',row['path'])).read_bytes()
        assert sha(actual)==row.get('checkout_sha256',row['sha256'])
        if actual!=raw:assert actual.replace(b'\r\n',b'\n')==raw.replace(b'\r\n',b'\n')
    old_default=load(OUT/'raw-input-pins.json')['default_contracts_sha256'];assert sha((ROOT/'src/annotation/contracts/__init__.py').read_bytes())==old_default
    sources=[{'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p.read_bytes())}for p in sorted(PRODUCT.glob('*.py'))]
    assert sources==load(OUT/'pre-execution-static-audit.json')['product_source']
    for p in list(PRODUCT.glob('*.py'))+list(EX.glob('*.py'))+list(OUT.glob('*.py'))+[TEST]:ast.parse(p.read_text(encoding='utf8'))
    data_index=load(OUT/'packaged-data-index.json')['data'];assert len(data_index)==9
    for row in data_index:
        raw=(PRODUCT/'data'/row['name']).read_bytes();assert len(raw)==row['bytes']and sha(raw)==row['sha256']
        if row['source']!='NEW_A_INTERNAL_READONLY_RECORD':assert raw==raw_inputs[(BASE,row['source'])][1]
    index=load(FIX/'index.json');expected_files={'.gitattributes','index.json'};bad_cases=0
    for row in index['cases']:
        original=load(ROOT/row['source_case']);raw=(FIX/row['bundle']).read_bytes();assert raw==raw_inputs[(BASE,original['bundle'])][1]and sha(raw)==row['bundle_sha256']
        metadata=FIX/row['bundle'];metadata=metadata.parent/'case.json';assert load(metadata)==row
        expected_files|={row['bundle'],metadata.relative_to(FIX).as_posix()};bad=[]
        for resource in row['resources']:
            path=FIX/row['asset_root']/resource['path'];body=path.read_bytes();assert len(body)==resource['bytes']and sha(body)==resource['actual_sha256'];expected_files.add(path.relative_to(FIX).as_posix())
            if sha(body)!=resource['declared_sha256']:bad.append(resource)
        assert bad==row['intentional_digest_mismatches_preserved'];bad_cases+=bool(bad)
    assert bad_cases==1 and expected_files=={p.relative_to(FIX).as_posix()for p in FIX.rglob('*')if p.is_file()}
    initial=load(OUT/'product-01-result.json');path=load(OUT/'path-01-result.json');c01=load(OUT/'c01-01-result.json');isolated=load(OUT/'isolation-result.json');wheel=load(OUT/'wheel-result.json')
    assert initial['successful']and initial['tests_run']==13 and len(initial['skipped'])==1 and not initial['failures']and not initial['errors']
    assert len([r for r in initial['observations']if r['group']=='migration'])==7
    assert path['successful']and path['tests_run']==1 and not path['skipped']and path['observations'][0]['result']=='EXPECTED_REJECTION'
    assert c01['successful']and c01['tests_run']==70 and not c01['skipped']
    assert wheel['status']=='OFFLINE_WHEEL_BUILT'and isolated['status']=='OUTSIDE_REPOSITORY_WHEEL_IMPORT_PASSED'and isolated['PYTHONPATH_absent']
    assert len(isolated['observations'])==2 and isolated['observations'][0]['actual']=='STATIC_ACCEPTED'and isolated['observations'][1]['actual']=='FRAME_REGISTRATION_TARGET'
    assert not Path(load(OUT/'isolation-launch-context.json')['outside_directory']).exists()
    wheel_path=ROOT/wheel['wheel'];assert sha(wheel_path.read_bytes())==wheel['wheel_sha256']
    with zipfile.ZipFile(wheel_path)as z:
        assert z.namelist()==wheel['files']
        for row in data_index:assert sha(z.read('annotation/contracts/a03_bridge/data/'+row['name']))==row['sha256']
        for row in sources:
            relative=Path(row['path']).relative_to('src').as_posix();assert sha(z.read(relative))==row['sha256']
    current=os.environ.get('A03_R7_RUN_ID');finished=[]
    for p in sorted((OUT/'runs').iterdir()):
        registration=load(p/'registration.json');assert sha((p/'registered-script.py').read_bytes())==registration['script_sha256']
        assert sha((p/'product-source-index.json').read_bytes())==registration['product_source_index_sha256']
        if p.name==current:continue
        end=load(p/'exit.json');assert not end['alive']and not end['timed_out']and end['owned_pid']>0
        assert end['exit_code']==(1 if p.name in('freeze-01','prepare-01')else 0),p.name
        finished.append(p.name)
    nested=[]
    for p in sorted((OUT/'nested-processes').glob('*/*')):
        r=load(p/'registration.json');started=load(p/'started.json');end=load(p/'exit.json')
        assert r['argv']==started['argv']==end['argv']and started['pid']==end['pid']and not end['alive']and not end['timed_out']
        assert(end['exit_code']in(0,1))and(p/'stdout.txt').is_file()and(p/'stderr.txt').is_file()
        nested.append({'record':p.relative_to(ROOT).as_posix(),'pid':end['pid'],'exit_code':end['exit_code'],'alive':False,'timed_out':False,'stdout_sha256':sha((p/'stdout.txt').read_bytes()),'stderr_sha256':sha((p/'stderr.txt').read_bytes())})
    assert len(nested)==10
    allowed=('src/annotation/contracts/a03_bridge/','tests/test_a03_r7_readonly_codec.py','tests/fixtures/a03/P2-R7-readonly-codec/','examples/a03/P2-R7-readonly-codec/','docs/evidence/A03/execution/P2-R7-readonly-codec/','docs/tasks/A03-P2-R7-readonly-codec-delivery.md','pyproject.toml')
    changed=git('diff','--name-only',BASE).decode().splitlines()+git('ls-files','--others','--exclude-standard').decode().splitlines();assert all(any(name.startswith(a)for a in allowed)for name in changed)
    pending={OUT/name for name in('old-preservation-after.json','archive-verification.json','process-release.json','nested-process-release.json','sha256-manifest.json')};links=0
    for p in(REPORT,EX/'README.md'):
        for url in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf8')):
            if'://'in url or url.startswith('#'):continue
            target=(p.parent/url.split('#',1)[0]).resolve();assert target.is_file()or(not final and target in pending),(str(p),url);links+=1
    count=None
    if final:
        assert load(OUT/'old-preservation-after.json')==after and load(OUT/'nested-process-release.json')['children']==nested
        release=load(OUT/'process-release.json');assert release['status']=='OWNED_RECORDED_COMMANDS_EXITED'
        for row in release['runs']:
            p=OUT/'runs'/row['run'];assert not row['alive']and not load(p/'exit.json')['alive'];assert sha((p/'stdout.txt').read_bytes())==row['stdout_sha256']and sha((p/'stderr.txt').read_bytes())==row['stderr_sha256']
        manifest=load(OUT/'sha256-manifest.json');roots=[PRODUCT,FIX,EX,OUT];actual={TEST.relative_to(ROOT).as_posix(),REPORT.relative_to(ROOT).as_posix(),'pyproject.toml'}|{p.relative_to(ROOT).as_posix()for root in roots for p in root.rglob('*')if p.is_file()and p!=OUT/'sha256-manifest.json'}
        assert actual=={r['path']for r in manifest['files']}
        for row in manifest['files']:
            raw=(ROOT/row['path']).read_bytes();assert len(raw)==row['bytes']and sha(raw)==row['sha256'],row['path']
        count=len(manifest['files'])
    result={'status':'REVIEW_PRODUCT_READONLY_ARCHIVE_CONSISTENT','preserved_old_paths':before['preserved_old_paths'],'mode_type_blob_and_checkout_preserved_except_authorized_pyproject':True,'pyproject_exception':exception,'raw_input_pin_entries':len(pins),'fixed_product_migration_cases':7,'initial_R7_tests':13,'initial_skip':1,'supplemental_path_tests':1,'all_named_R7_checks_covered':True,'C01_tests':70,'isolated_wheel_cases':2,'data_files':9,'wheel_sha256':wheel['wheel_sha256'],'product_rules_changed_after_initial_tests':False,'nested_children_completed':len(nested),'nested_exit_codes':dict(Counter(str(r['exit_code'])for r in nested)),'completed_prior_parent_runs':len(finished),'markdown_links':links,'manifest_files':count,'codec_or_test_calls_this_archive':0,'old_A03_entry_or_36_matrix_runs':0,'native_DB_network_model_calls':0,'field_reset_probe':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'}
    if not final:
        write(OUT/'old-preservation-after.json',after)
        write(OUT/'nested-process-release.json',{'status':'OWNED_NESTED_CHILDREN_EXITED','children':nested,'basis':'recorded parent communicate/wait completion; no OS/profile scan','expected_nonzero_C01_CLI_rejections_retained':True})
        write(OUT/'archive-verification.json',result)
    return result
if __name__=='__main__':
    assert not sys.argv[1:]or sys.argv[1:]==['--check']
    print(json.dumps(audit(bool(sys.argv[1:]))))
