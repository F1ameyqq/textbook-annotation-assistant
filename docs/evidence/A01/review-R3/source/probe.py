"""Independent bounded R3-01 path/components review; no URL fetching."""
import argparse
import hashlib
import json
import os
import platform
import shutil
import sys
import traceback
from pathlib import Path
from urllib.parse import urlsplit

sys.dont_write_bytecode=True
parser=argparse.ArgumentParser()
parser.add_argument('--snapshot',required=True,type=Path)
parser.add_argument('--stage',required=True,type=Path)
args=parser.parse_args()
SNAPSHOT,STAGE=args.snapshot.resolve(),args.stage.resolve()
OUT=Path(__file__).resolve().parent
OLD_Q=Path('D:/1800/docs/evidence/A01/review-R2/primary-url-path')
OLD_U=Path('D:/1800/docs/evidence/A01/review-R2/source')
STAGE.mkdir(parents=True,exist_ok=False)
for key in ('TMP','TEMP','TMPDIR'):
    os.environ[key]=str(STAGE)
os.environ['PYTHONPATH']=str(SNAPSHOT/'src')
os.environ['PYTHONDONTWRITEBYTECODE']='1'
sys.path.insert(0,str(SNAPSHOT/'src'))
import PIL
import pydantic
import annotation.contracts as contracts
import annotation.source.static.importer as importer
import annotation.source.static.consistency as consistency
from annotation.contracts import load_bundle,seal_artifact
from annotation.source.static import load_static_bundle
for module in (contracts,importer,consistency):
    assert Path(module.__file__).resolve().is_relative_to(SNAPSHOT/'src')
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
def hashes(root):
    return {p.relative_to(root).as_posix():sha(p) for p in sorted(root.rglob('*')) if p.is_file()}
before_snapshot,before_Q,before_U=hashes(SNAPSHOT),hashes(OLD_Q),hashes(OLD_U)
BASES={}
for version,relative in (('legacy','examples/a01/bundles'),('R1','examples/a01/R1/bundles'),('R2','examples/a01/R2/bundles'),('R3','examples/a01/R3/bundles')):
    for book in ('46006966','46007447'):
        BASES[(version,book)]=SNAPSHOT/relative/book/'exchange.json'
environment={'target_commit':'180bb1e86fb2a7eb1546be85af70f466f069daf5',
             'implementation_commit':'31d715a5f2e6435af3a7e98a6c19b41b72d883bd',
             'fixed_code_reference':'aeb7ca306b3dba9d51740071f96592d8e677ec66',
             'python_executable':sys.executable,'python_version':sys.version,'platform':platform.platform(),
             'pillow':PIL.__version__,'pydantic':pydantic.__version__,'command_argv':sys.argv,
             'PYTHONPATH':os.environ['PYTHONPATH'],'sys_path':sys.path,
             'temporary_environment':{k:os.environ[k] for k in ('TMP','TEMP','TMPDIR')},
             'module_files':{m.__name__:m.__file__ for m in (contracts,importer,consistency)},
             'module_hashes':{m.__name__:sha(Path(m.__file__)) for m in (contracts,importer,consistency)},
             'script_sha256':sha(Path(__file__)),'offline':True,'network_calls':0,'browser_calls':0,
             'credential_reads':0,'ocr_calls':0,'model_calls':0}
write(OUT/'environment.json',environment)

def update_resource(data,relative,digest):
    for item in data['evidence']+data['artifacts'][0]['payload']['history']:
        if item['resource']['path']==relative:
            item['resource']['sha256']=digest
def history_image(path,image,viewer=14):
    relative='history/00-independent-source-page14.json' if viewer==14 else 'history/01-independent-source-page173.json'
    archive='docs/evidence/A05/review/independent-source-page'+str(viewer)+'.json'
    data,value=read(path),read(path.parent/relative)
    value['data']['pages'][0]['image']=image
    write(path.parent/relative,value)
    digest=sha(path.parent/relative)
    update_resource(data,relative,digest)
    integrity=read(path.parent/'input-integrity.json')
    matched=[r for r in integrity['inputs'] if r['archive_path']==archive]
    assert len(matched)==1
    matched[0].update(before_sha256=digest,after_sha256=digest)
    write(path.parent/'input-integrity.json',integrity)
    update_resource(data,'input-integrity.json',sha(path.parent/'input-integrity.json'))
    data['artifacts']=[seal_artifact(a) for a in data['artifacts']]
    write(path,data)

RESULTS=[]
def run(identifier,expected,description,action,expected_code=None):
    result={'id':identifier,'expected':expected,'description':description,'expected_code':expected_code}
    try:
        result.update(actual='ACCEPT',detail=action(identifier))
    except Exception as error:
        result.update(actual='REJECT',error_type=type(error).__name__,error=str(error),
                      code=getattr(error,'code',None),location=getattr(error,'location',None),
                      issues=getattr(error,'issues',None),traceback=traceback.format_exc())
    public_file=OUT/'cases'/identifier/'public-load.json'
    result['public_resource_validation_passed']=public_file.exists() and read(public_file).get('actual')=='ACCEPT'
    result['matches_expectation']=(result['actual']==expected and result['public_resource_validation_passed'] and
                                  (expected_code is None or expected_code==result.get('code')))
    RESULTS.append(result)
    write(OUT/'cases'/identifier/'result.json',result)
    print(identifier+': '+result['actual']+(' expected' if result['matches_expectation'] else ' UNEXPECTED'),flush=True)

def consume(identifier,path,book,baseline=None):
    changed={} if baseline is None else {k:v for k,v in hashes(path.parent).items() if baseline.get(k)!=v}
    for relative in changed:
        if (path.parent/relative).suffix in ('.json','.txt'):
            target=OUT/'cases'/identifier/'changed-inputs'/relative
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(path.parent/relative,target)
    uris=[]
    if book=='46007447':
        for relative in ('history/00-independent-source-page14.json','history/01-independent-source-page173.json'):
            raw=read(path.parent/relative)['data']
            page=raw['pages'][0]
            image=page['image']
            parsed=urlsplit(image)
            uris.append({'resource':relative,'file_id':raw['file_id'],'page_index':page['page_index'],'image':image,
                         'parsed_components':{'scheme':parsed.scheme,'netloc':parsed.netloc,'path':parsed.path,'query':parsed.query,'fragment':parsed.fragment},
                         'literal_query_delimiter':'?' in image,'literal_fragment_delimiter':'#' in image})
    write(OUT/'cases'/identifier/'input.json',{'exchange':str(path),'exchange_sha256':sha(path),'book_id':book,
                                             'changed_files':changed,'historical_URL_components':uris})
    public=load_bundle(path,verify_assets=True)
    write(OUT/'cases'/identifier/'public-load.json',{'actual':'ACCEPT','source_hash':public.artifacts[0].content_hash})
    result=load_static_bundle(path,expected_book_id=book)
    return {'public_load':'ACCEPT','A01_load':'ACCEPT','same_result':public==result,'source_hash':result.artifacts[0].content_hash}
def mutated_url(identifier,image,viewer=14):
    target=STAGE/identifier/'bundle'
    shutil.copytree(BASES[('R3','46007447')].parent,target)
    baseline=hashes(target)
    path=target/'exchange.json'
    history_image(path,image,viewer)
    return consume(identifier,path,'46007447',baseline)

for (version,book),path in BASES.items():
    run('C-'+version+'-'+book,'ACCEPT','Exact frozen normal '+version+' bundle; no rebuild.',lambda n,p=path,b=book:consume(n,p,b))
for name in ('Q01-cross-book-path-query-tail','Q02-wrong-index-path-fragment-tail'):
    def replay_Q(identifier,name=name):
        original=OLD_Q/name
        target=STAGE/'exact-replays'/name
        shutil.copytree(original,target)
        manifest=hashes(original)
        assert hashes(target)==manifest
        shutil.copytree(target,OUT/'replay-inputs'/name)
        write(OUT/'cases'/identifier/'exact-reconstruction.json',{'source':str(original),'expected_files':manifest,'actual_files':hashes(target),'all_bytes_equal':True})
        return consume(identifier,target/'exchange.json','46007447')
    run(name,'REJECT','Replay original complete frozen Q package, exact bytes.',replay_Q,'SOURCE_URL_COMPONENT')

old_snapshot=read(OLD_U/'preservation.json')['snapshot_before']
prefix='examples/a01/R2/bundles/46007447/'
old_base={k[len(prefix):]:v for k,v in old_snapshot.items() if k.startswith(prefix)}
assert old_base and old_base==hashes(BASES[('R2','46007447')].parent)
for name in ('U23-query-masks-wrong-path-book','U24-fragment-masks-wrong-path-index','U25-query-masks-wrong-path-index'):
    def replay_U(identifier,name=name):
        record=read(OLD_U/'cases'/name/'input.json')
        original_delta=OLD_U/'cases'/name/'changed-inputs'
        target=STAGE/'exact-replays'/name
        shutil.copytree(BASES[('R2','46007447')].parent,target)
        expected=dict(old_base)
        for relative,digest in record['changed_files'].items():
            assert sha(original_delta/relative)==digest
            shutil.copy2(original_delta/relative,target/relative)
            expected[relative]=digest
        actual=hashes(target)
        assert actual==expected and sha(target/'exchange.json')==record['exchange_sha256']
        shutil.copytree(target,OUT/'replay-inputs'/name)
        write(OUT/'cases'/identifier/'exact-reconstruction.json',{'R2_base_source':'review-R2/source/preservation.json:snapshot_before',
              'delta_source':str(original_delta),'expected_files':expected,'actual_files':actual,'all_bytes_equal':True})
        return consume(identifier,target/'exchange.json','46007447')
    run(name,'REJECT','Reconstruct frozen U package from original byte-verified R2 base and exact saved delta.',replay_U,'SOURCE_URL_COMPONENT')

HOST='https://archive.example.invalid'
CORRECT='/upload_images/46007447/46007447_page_13.jpg'
paths=(('first-book','/upload_images/46006966/46007447_page_13.jpg','BOOK_CONFLICT'),
       ('second-book','/upload_images/46007447/46006966_page_13.jpg','BOOK_CONFLICT'),
       ('both-books','/upload_images/46006966/46006966_page_13.jpg','BOOK_CONFLICT'),
       ('left-index','/upload_images/46007447/46007447_page_12.jpg','MAPPING_CONFLICT'),
       ('right-index','/upload_images/46007447/46007447_page_14.jpg','MAPPING_CONFLICT'),
       ('other-acquired-index','/upload_images/46007447/46007447_page_172.jpg','MAPPING_CONFLICT'),
       ('unrelated','/unrelated.jpg','BOOK_CONFLICT'),
       ('prefix','/prefix'+CORRECT,'BOOK_CONFLICT'),
       ('root','/','BOOK_CONFLICT'),('no-path','','BOOK_CONFLICT'))
for label,path,code in paths:
    run('D-'+label,'REJECT','Wrong actual direct path without query/fragment.',lambda n,p=path:mutated_url(n,HOST+p),code)
for label,path in (('first-book',paths[0][1]),('second-book',paths[1][1]),('wrong-index',paths[5][1]),('unrelated','/unrelated.jpg'),('no-path','')):
    for tail_id,tail in (('query','?echo='+CORRECT),('fragment','#'+CORRECT),('query-fragment','?#'+CORRECT),('fragment-query','#?'+CORRECT)):
        run('S-'+label+'-'+tail_id,'REJECT','Query/fragment swap cannot supply missing/correct path identity.',
            lambda n,p=path,t=tail:mutated_url(n,HOST+p+t),'SOURCE_URL_COMPONENT')
for label,tail in (('empty-query','?'),('empty-fragment','#'),('both-empty','?#'),('empty-reversed','#?'),
                   ('query-text','?x=1'),('fragment-text','#view'),('both-text','?x=1#view'),('reversed-text','#view?x=1')):
    run('T-'+label,'REJECT','Declared component rejection also applies to correct path and empty separators.',
        lambda n,t=tail:mutated_url(n,HOST+CORRECT+t),'SOURCE_URL_COMPONENT')
for label,url in (('https',HOST+CORRECT),('http','http://archive.example.invalid'+CORRECT),
                  ('uppercase-scheme','HTTPS://archive.example.invalid'+CORRECT),
                  ('host-not-book-auth','https://46006966.example.invalid'+CORRECT)):
    run('L-'+label,'ACCEPT','Legal direct HTTP(S) image text retains path identity; host is not authentication.',lambda n,u=url:mutated_url(n,u))
run('L-answer-http','ACCEPT','Second archived response retains viewer173/source172 direct HTTP URL.',
    lambda n:mutated_url(n,'http://archive.example.invalid/upload_images/46007447/46007447_page_172.jpg',173))
run('D-answer-index','REJECT','Second archived response source172 cannot become source13 in its direct path.',
    lambda n:mutated_url(n,HOST+CORRECT,173),'MAPPING_CONFLICT')
for label,url in (('missing-host','https:///upload_images/46007447/46007447_page_13.jpg'),('relative',CORRECT)):
    run('D-'+label,'REJECT','Absolute HTTP(S) source URL precondition remains explicit.',lambda n,u=url:mutated_url(n,u),'SOURCE_URL')
for scheme in ('http','https'):
    def old_book_direct(identifier,scheme=scheme):
        source=BASES[('R3','46006966')]
        consume(identifier,source,'46006966')
        url=scheme+'://archive.example.invalid/upload_images/46006966/46006966_page_7.jpg'
        actual=importer.url_index(url,'46006966','independent.old-book.image')
        assert actual==7
        write(OUT/'cases'/identifier/'direct-helper.json',{'entrypoint':'importer.url_index','url':url,'book_id':'46006966','expected':7,'actual':actual,
                                                         'note':'Pure local string check after old-book fixed bundle public/A01 validation; no URL fetching.'})
        return {'url_index':actual,'public_old_book_validation':'ACCEPT'}
    run('L-old-book-'+scheme,'ACCEPT','Old-book supported direct HTTP(S) path resolves same literal source7.',old_book_direct)

after_snapshot,after_Q,after_U=hashes(SNAPSHOT),hashes(OLD_Q),hashes(OLD_U)
summary={'target_commit':environment['target_commit'],'source_subdecision':'ACCEPTED' if all(r['matches_expectation'] for r in RESULTS) else 'REWORK',
         'cases':RESULTS,'case_count':len(RESULTS),'counts':{k:sum(r['actual']==k for r in RESULTS) for k in ('ACCEPT','REJECT')},
         'all_public_resource_checks_passed':all(r['public_resource_validation_passed'] for r in RESULTS),
         'all_expected_codes_and_results_matched':all(r['matches_expectation'] for r in RESULTS),
         'unexpected_cases':[r['id'] for r in RESULTS if not r['matches_expectation']],
         'snapshot_unchanged':before_snapshot==after_snapshot,'snapshot_file_count':len(before_snapshot),
         'old_Q_evidence_unchanged':before_Q==after_Q,'old_U_evidence_unchanged':before_U==after_U,
         'component_policy':'All literal query/fragment separators, including empty ones, reject with SOURCE_URL_COMPONENT.',
         'scope':'R3-01 path/component strategy only; parent handles verify representations and consumers.',
         'limitations':'No general URL support, host authentication, signed URLs, source authenticity, S01/D01/N15 repair or platform assertions.'}
write(OUT/'results.json',summary)
write(OUT/'preservation.json',{'snapshot_before':before_snapshot,'snapshot_after':after_snapshot,
                              'old_Q_before':before_Q,'old_Q_after':after_Q,'old_U_before':before_U,'old_U_after':after_U})
print(json.dumps({k:summary[k] for k in ('source_subdecision','case_count','counts','all_public_resource_checks_passed','all_expected_codes_and_results_matched','unexpected_cases','snapshot_unchanged','old_Q_evidence_unchanged','old_U_evidence_unchanged')},indent=2),flush=True)
