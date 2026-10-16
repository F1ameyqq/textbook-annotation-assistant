"""Bounded independent R2 source review; no network or executable URL use."""
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

sys.dont_write_bytecode = True
parser = argparse.ArgumentParser()
parser.add_argument('--snapshot',required=True,type=Path)
parser.add_argument('--stage',required=True,type=Path)
args = parser.parse_args()
SNAPSHOT, STAGE = args.snapshot.resolve(), args.stage.resolve()
OUT = Path(__file__).resolve().parent
OLD_REPLAYS = Path('D:/1800/docs/evidence/A01/review-R1/primary-source-confirmation')
STAGE.mkdir(parents=True,exist_ok=False)
for key in ('TEMP','TMP','TMPDIR'):
    os.environ[key] = str(STAGE)
os.environ['PYTHONPATH'] = str(SNAPSHOT/'src')
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
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
BASES = {}
for version,relative in (('legacy','examples/a01/bundles'),('R1','examples/a01/R1/bundles'),('R2','examples/a01/R2/bundles')):
    for book in ('46006966','46007447'):
        BASES[(version,book)] = SNAPSHOT/relative/book/'exchange.json'
before_snapshot = hashes(SNAPSHOT)
before_replays = hashes(OLD_REPLAYS)
environment = {'target_commit':'c3aff9598b6705ab4122062615a13ae3774698b2',
               'implementation_commit':'63ac5a184798326d629a43d1dfed25fa73a1a27e',
               'python_executable':sys.executable,'python_version':sys.version,'platform':platform.platform(),
               'pillow':PIL.__version__,'pydantic':pydantic.__version__,'command_argv':sys.argv,
               'PYTHONPATH':os.environ['PYTHONPATH'],'sys_path':sys.path,
               'temporary_environment':{k:os.environ[k] for k in ('TMP','TEMP','TMPDIR')},
               'module_files':{m.__name__:m.__file__ for m in (contracts,importer,consistency)},
               'module_hashes':{m.__name__:sha(Path(m.__file__)) for m in (contracts,importer,consistency)},
               'script_sha256':sha(Path(__file__)),'offline':True,'network_calls':0,'browser_calls':0,
               'credential_reads':0,'ocr_calls':0,'model_calls':0}
write(OUT/'environment.json',environment)

def resource_digest(data,relative,digest):
    for item in data['evidence']+data['artifacts'][0]['payload']['history']:
        if item['resource']['path']==relative:
            item['resource']['sha256'] = digest
def reseal(path,data):
    data['artifacts'] = [seal_artifact(a) for a in data['artifacts']]
    write(path,data)
def sidecar(path,relative,mutation):
    data,value = read(path),read(path.parent/relative)
    mutation(value)
    write(path.parent/relative,value)
    resource_digest(data,relative,sha(path.parent/relative))
    reseal(path,data)
def historical_page(path,mutation,viewer=14):
    relative = 'history/00-independent-source-page14.json' if viewer==14 else 'history/01-independent-source-page173.json'
    archive = 'docs/evidence/A05/review/independent-source-page'+str(viewer)+'.json'
    data,value = read(path),read(path.parent/relative)
    mutation(value['data'])
    write(path.parent/relative,value)
    digest = sha(path.parent/relative)
    resource_digest(data,relative,digest)
    integrity = read(path.parent/'input-integrity.json')
    records = [r for r in integrity['inputs'] if r['archive_path']==archive]
    assert len(records)==1
    records[0].update(before_sha256=digest,after_sha256=digest)
    write(path.parent/'input-integrity.json',integrity)
    resource_digest(data,'input-integrity.json',sha(path.parent/'input-integrity.json'))
    reseal(path,data)

RESULTS=[]
def run(identifier,expected,description,action,expected_code=None):
    result={'id':identifier,'expected':expected,'expected_code':expected_code,'description':description}
    try:
        detail=action(identifier)
        result.update(actual='ACCEPT',detail=detail)
    except Exception as error:
        result.update(actual='REJECT',error_type=type(error).__name__,error=str(error),
                      code=getattr(error,'code',None),location=getattr(error,'location',None),
                      issues=getattr(error,'issues',None),traceback=traceback.format_exc())
    public_file=OUT/'cases'/identifier/'public-load.json'
    result['public_resource_validation_passed'] = public_file.exists() and read(public_file).get('actual')=='ACCEPT'
    result['matches_expectation'] = (result['actual']==expected and
        (expected_code is None or expected_code==result.get('code')) and result['public_resource_validation_passed'])
    RESULTS.append(result)
    write(OUT/'cases'/identifier/'result.json',result)
    print(identifier+': '+result['actual']+(' expected' if result['matches_expectation'] else ' UNEXPECTED'),flush=True)

def consume(identifier,path,book,baseline=None):
    if baseline is not None:
        changed={k:v for k,v in hashes(path.parent).items() if baseline.get(k)!=v}
        for relative in changed:
            if (path.parent/relative).suffix in ('.json','.txt'):
                target=OUT/'cases'/identifier/'changed-inputs'/relative
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(path.parent/relative,target)
    else:
        changed={}
    # URL components are only recorded as local text; they are never fetched.
    uri=[]
    if book=='46007447':
        for relative in ('history/00-independent-source-page14.json','history/01-independent-source-page173.json'):
            value=read(path.parent/relative)['data']
            page=value['pages'][0]
            image=page.get('image')
            parsed=None
            if isinstance(image,str):
                try:
                    p=urlsplit(image)
                    parsed={'scheme':p.scheme,'netloc':p.netloc,'path':p.path,'query':p.query,'fragment':p.fragment}
                except ValueError as error:
                    parsed={'parse_error':str(error)}
            uri.append({'resource':relative,'file_id':value.get('file_id'),'page_index':page.get('page_index'),'image':image,'parsed_components':parsed})
    write(OUT/'cases'/identifier/'input.json',{'exchange':str(path),'exchange_sha256':sha(path),'book_id':book,
                                             'changed_files':changed,'historical_URL_components':uri})
    public=load_bundle(path,verify_assets=True)
    write(OUT/'cases'/identifier/'public-load.json',{'actual':'ACCEPT','source_hash':public.artifacts[0].content_hash})
    source=load_static_bundle(path,expected_book_id=book)
    return {'public_load':'ACCEPT','A01_load':'ACCEPT','same_result':public==source,'source_hash':source.artifacts[0].content_hash}
def mutated(identifier,mutation,book='46007447'):
    target=STAGE/identifier/'bundle'
    shutil.copytree(BASES[('R2',book)].parent,target)
    before=hashes(target)
    path=target/'exchange.json'
    mutation(path)
    return consume(identifier,path,book,before)
def url_case(identifier,value,viewer=14):
    return mutated(identifier,lambda p:historical_page(p,lambda d:d['pages'][0].update(image=value),viewer))
def observation_case(identifier,mutation,book='46007447'):
    return mutated(identifier,lambda p:sidecar(p,'provenance.json',mutation),book)

for (version,book),path in BASES.items():
    run('C-'+version+'-'+book,'ACCEPT','Exact frozen '+version+' fixed sample, no rebuild.',lambda n,p=path,b=book:consume(n,p,b))
for name,book,code in (
    ('P01-acquired-also-missing','46006966','SCOPE_PARTITION'),
    ('P02-page-response-cross-book-url','46007447','BOOK_CONFLICT'),
    ('P03-page-response-index-url-conflict','46007447','MAPPING_CONFLICT'),
    ('P04-observation-index-digest-conflict','46007447','OBSERVATION_SOURCE')):
    def replay(identifier,name=name,book=book):
        source=OLD_REPLAYS/name
        target=STAGE/'replays'/name
        shutil.copytree(source,target)
        assert hashes(source)==hashes(target)
        shutil.copytree(target,OUT/'replay-inputs'/name)
        return consume(identifier,target/'exchange.json',book)
    run(name,'REJECT','Replay exact byte-preserved R1 formal package.',replay,code)

prefix='https://archive.example.invalid/upload_images/'
for label,url,code in (
    ('U01-first-book-wrong',prefix+'46006966/46007447_page_13.jpg','BOOK_CONFLICT'),
    ('U02-second-book-wrong',prefix+'46007447/46006966_page_13.jpg','BOOK_CONFLICT'),
    ('U03-both-books-wrong',prefix+'46006966/46006966_page_13.jpg','BOOK_CONFLICT'),
    ('U04-index-left',prefix+'46007447/46007447_page_12.jpg','MAPPING_CONFLICT'),
    ('U05-index-right',prefix+'46007447/46007447_page_14.jpg','MAPPING_CONFLICT'),
    ('U06-index-other-acquired',prefix+'46007447/46007447_page_172.jpg','MAPPING_CONFLICT'),
    ('U07-ftp','ftp://archive.example.invalid/upload_images/46007447/46007447_page_13.jpg','SOURCE_URL'),
    ('U08-relative','/upload_images/46007447/46007447_page_13.jpg','SOURCE_URL'),
    ('U09-missing-host','https:///upload_images/46007447/46007447_page_13.jpg','SOURCE_URL'),
    ('U10-file-scheme','file://archive.example.invalid/upload_images/46007447/46007447_page_13.jpg','SOURCE_URL'),
    ('U11-null',None,'SOURCE_URL'),
    ('U12-list',[],'SOURCE_URL'),
    ('U13-broken-jpeg-suffix',prefix+'46007447/46007447_page_13.png','BOOK_CONFLICT')):
    run(label,'REJECT','Historical URL identity/index/scheme malformed; history/input hashes synchronized.',lambda n,u=url:url_case(n,u),code)
for label,url in (
    ('U14-valid-https',prefix+'46007447/46007447_page_13.jpg'),
    ('U15-valid-http','http://archive.example.invalid/upload_images/46007447/46007447_page_13.jpg'),
    ('U16-valid-uppercase-scheme','HTTPS://archive.example.invalid/upload_images/46007447/46007447_page_13.jpg'),
    ('U17-host-text-not-book-auth','https://46006966.example.invalid/upload_images/46007447/46007447_page_13.jpg')):
    run(label,'ACCEPT','Legal archived HTTP(S) direct JPEG path; host text is not book authentication.',lambda n,u=url:url_case(n,u))
for label,value in (('U18-page-index-bool',True),('U19-page-index-float',13.0),('U20-page-index-string','13')):
    run(label,'REJECT','Raw page_index type must be integer and match retained mapping.',
        lambda n,v=value:mutated(n,lambda p:historical_page(p,lambda d:d['pages'][0].update(page_index=v))),'MAPPING_CONFLICT')
run('U21-answer-legitimate','ACCEPT','Second archived response viewer173 retains source172 with different valid host.',
    lambda n:url_case(n,prefix+'46007447/46007447_page_172.jpg',173))
run('U22-answer-wrong-source','REJECT','Second archived response source172 conflicts with URL source13.',
    lambda n:url_case(n,prefix+'46007447/46007447_page_13.jpg',173),'MAPPING_CONFLICT')
for label,url in (
    ('U23-query-masks-wrong-path-book',prefix+'46006966/46006966_page_13.jpg?ignored=/upload_images/46007447/46007447_page_13.jpg'),
    ('U24-fragment-masks-wrong-path-index',prefix+'46007447/46007447_page_172.jpg#/upload_images/46007447/46007447_page_13.jpg'),
    ('U25-query-masks-wrong-path-index',prefix+'46007447/46007447_page_172.jpg?ignored=/upload_images/46007447/46007447_page_13.jpg')):
    run(label,'REJECT','Parsed URL path contradicts raw file_id/page_index; query/fragment must not supply path identity.',lambda n,u=url:url_case(n,u))

NETWORK='docs/evidence/A05/review/independent-network.json'
for label,mutation,code in (
    ('O01-sha-zero',lambda p:p['observation']['observation_index_source'].update(sha256='0'*64),'OBSERVATION_SOURCE'),
    ('O02-index-none',lambda p:p['observation'].update(observation_index_source=None),'OBSERVATION_SOURCE'),
    ('O03-path-absent',lambda p:p['observation']['observation_index_source'].update(archive_path='missing.json'),'OBSERVATION_SOURCE'),
    ('O04-path-traversal',lambda p:p['observation']['observation_index_source'].update(archive_path='../index.json'),'SOURCE_PATH'),
    ('O05-sha-malformed',lambda p:p['observation']['observation_index_source'].update(sha256='G'*64),'SOURCE_DIGEST'),
    ('O06-sha-wrong-type',lambda p:p['observation']['observation_index_source'].update(sha256=0),'SOURCE_DIGEST'),
    ('O07-index-list',lambda p:p['observation'].update(observation_index_source=[]),'OBSERVATION_SOURCE'),
    ('O08-source-wrong-identity',lambda p:p['observation'].update(source='docs/evidence/A05/review/independent-book.json'),'OBSERVATION_SOURCE')):
    run(label,'REJECT','Observation index/source identity or digest contradicts retained input inventory.',lambda n,m=mutation:observation_case(n,m),code)
run('O09-input-index-absent','REJECT','Required observation index entry removed from retained inventory.',
    lambda n:mutated(n,lambda p:sidecar(p,'input-integrity.json',lambda i:i.update(inputs=[r for r in i['inputs'] if r['archive_path']!=NETWORK]))),'OBSERVATION_SOURCE')
def wrong_index(path):
    inputs=read(path.parent/'input-integrity.json')['inputs']
    other=next(i for i in inputs if i['archive_path'].endswith('/independent-book.json'))
    sidecar(path,'provenance.json',lambda p:p['observation'].update(observation_index_source={'archive_path':other['archive_path'],'sha256':other['before_sha256']}))
run('O10-wrong-existing-index-binding','REJECT','Index points to another retained input with its valid matching digest, but assigned observation identity differs.',
    lambda n:mutated(n,wrong_index),'OBSERVATION_SOURCE')
def wrong_digest(path):
    inputs=read(path.parent/'input-integrity.json')['inputs']
    other=next(i for i in inputs if i['archive_path'].endswith('/independent-book.json'))
    sidecar(path,'provenance.json',lambda p:p['observation']['observation_index_source'].update(sha256=other['before_sha256']))
run('O11-existing-sha-wrong-path-binding','REJECT','Network path retained, digest copied from different retained original.',lambda n:mutated(n,wrong_digest),'OBSERVATION_SOURCE')
run('O12-inventory-order-legal','ACCEPT','Reordering input inventory retains all identity/digest bindings.',
    lambda n:mutated(n,lambda p:sidecar(p,'input-integrity.json',lambda i:i['inputs'].reverse())))
run('O13-old-source-wrong-identity','REJECT','Old book observation source must still bind assigned historical session input.',
    lambda n:observation_case(n,lambda p:p['observation'].update(source='other-session.json'),'46006966'),'OBSERVATION_SOURCE')
def optional_old_index(path,wrong=False):
    inventory=read(path.parent/'input-integrity.json')['inputs']
    entry=next(e for e in inventory if e['archive_path'].endswith('/session-receipt-20261015.json'))
    sidecar(path,'provenance.json',lambda p:p['observation'].update(observation_index_source={
        'archive_path':entry['archive_path'],'sha256':'0'*64 if wrong else entry['before_sha256']}))
run('O14-old-optional-index-consistent','ACCEPT','Optional old-book observation index binds an actual retained historical session digest; no time authentication claimed.',
    lambda n:mutated(n,lambda p:optional_old_index(p),'46006966'))
run('O15-old-optional-index-digest-wrong','REJECT','Optional old-book observation index conflicts with its retained input digest.',
    lambda n:mutated(n,lambda p:optional_old_index(p,True),'46006966'),'OBSERVATION_SOURCE')

after_snapshot,after_replays=hashes(SNAPSHOT),hashes(OLD_REPLAYS)
summary={'target_commit':environment['target_commit'],'cases':RESULTS,'counts':{k:sum(r['actual']==k for r in RESULTS) for k in ('ACCEPT','REJECT')},
         'all_public_resource_checks_passed':all(r['public_resource_validation_passed'] for r in RESULTS),
         'frozen_P01_P04_all_rejected':all(r['matches_expectation'] for r in RESULTS if r['id'].startswith('P')),
         'old_R1_R2_two_books_all_accepted':all(r['matches_expectation'] for r in RESULTS if r['id'].startswith('C-')),
         'unexpected_cases':[r['id'] for r in RESULTS if not r['matches_expectation']],
         'snapshot_unchanged':before_snapshot==after_snapshot,'snapshot_file_count':len(before_snapshot),
         'old_formal_replays_unchanged':before_replays==after_replays,
         'scope':'R2-02/R2-03 and fixed P01-P04 only; exhaustive partition belongs to parent/other subagent.',
         'limits':'No external source authenticity, host trust, N15 authentication, S01/D01 repair, or platform assertion.'}
write(OUT/'results.json',summary)
write(OUT/'preservation.json',{'snapshot_before':before_snapshot,'snapshot_after':after_snapshot,
                              'R1_formal_inputs_before':before_replays,'R1_formal_inputs_after':after_replays})
print(json.dumps({k:summary[k] for k in ('counts','all_public_resource_checks_passed','frozen_P01_P04_all_rejected','old_R1_R2_two_books_all_accepted','unexpected_cases','snapshot_unchanged','old_formal_replays_unchanged')},indent=2),flush=True)
