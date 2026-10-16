"""Independent offline R2-01 partition probes; no author case generators."""
import argparse
import copy
import hashlib
import json
import os
import platform
import shutil
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
ap = argparse.ArgumentParser()
ap.add_argument('--snapshot', required=True)
ap.add_argument('--out', required=True)
ap.add_argument('--temp-root', required=True)
args = ap.parse_args()
ROOT = Path(args.snapshot).resolve()
OUT = Path(args.out).resolve()
TEMP = Path(args.temp_root).resolve()
OUT.mkdir(parents=True, exist_ok=True)
TEMP.mkdir(parents=True, exist_ok=True)
os.environ['TMP'] = os.environ['TEMP'] = str(TEMP)
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
tempfile.tempdir = str(TEMP)
RUN = Path(tempfile.mkdtemp(prefix='partition-run-', dir=TEMP))
sys.path.insert(0, str(ROOT/'src'))
import annotation.source.static.importer as importer
import annotation.source.static.consistency as consistency
import annotation.contracts as contracts
import annotation.contracts.validation as validation
import pydantic

assert Path(importer.__file__).resolve() == ROOT/'src/annotation/source/static/importer.py'
assert Path(consistency.__file__).resolve() == ROOT/'src/annotation/source/static/consistency.py'
assert Path(validation.__file__).resolve() == ROOT/'src/annotation/contracts/validation.py'

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def save(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)+'\n', encoding='utf-8')

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def result(fn):
    try:
        value = fn()
        return {'ok': True, 'artifacts':len(value.artifacts)}
    except Exception as exc:
        return {'ok':False,'exception':type(exc).__name__,'code':getattr(exc,'code',None),
                'location':getattr(exc,'location',None),'message':str(exc)}

def partition_oracle(p, artifact):
    """Independent set equations and public reference counts, no tested helper."""
    total=p['metadata_page_count']
    if type(total) is not int or total<=0 or total != artifact['payload']['metadata_page_count']:
        return False
    arrays=[ [m['source_index'] for m in p['mappings']], p['selected_source_indices'],
             p['selected_missing_source_indices'],p['outside_selected_scope_unacquired_indices'] ]
    if any(not isinstance(v,list) for v in arrays): return False
    for values in arrays:
        if any(type(v) is not int or not 0<=v<total for v in values) or len(values)!=len(set(values)):
            return False
    a,s,m,o=map(set,arrays)
    expected=artifact['payload']['pages_expected']; acquired=artifact['payload']['pages_acquired']
    return (not(a&m) and s==a|m and o==set(range(total))-s
            and type(p['acquired_unique_images']) is int and p['acquired_unique_images']==len(a)
            and len(expected)==len(s) and len(acquired)==len(a)
            and len(set(expected)-set(acquired))==len(m))

def mark_and_seal(folder, exchange, p):
    save(folder/'provenance.json',p)
    resource_digest=sha(folder/'provenance.json')
    # Provenance is referenced both as evidence and as archived history. Update
    # every public resource alias before sealing, so source probes pass C01.
    def refresh(value):
        if isinstance(value,dict):
            if value.get('path')=='provenance.json' and 'sha256' in value:
                value['sha256']=resource_digest
            for child in value.values():refresh(child)
        elif isinstance(value,list):
            for child in value:refresh(child)
    refresh(exchange)
    for item in exchange['evidence']:
        if item['resource']['path']=='provenance.json':
            item['mode']='SYNTHETIC'
            item['description']='SYNTHETIC independent R2 partition test; archive bytes preserved; no platform or coverage claim'
    for artifact in exchange['artifacts']:
        artifact['producer']['evidence_mode']='SYNTHETIC'
    exchange['artifacts']=[contracts.seal_artifact(a) for a in exchange['artifacts']]
    save(folder/'exchange.json',exchange)

def missing_intent(exchange,p,missing):
    a={m['source_index'] for m in p['mappings']}
    total=p['metadata_page_count']
    selected=a|set(missing)
    p['selected_source_indices']=sorted(selected)
    p['selected_missing_source_indices']=sorted(missing)
    p['outside_selected_scope_unacquired_indices']=sorted(set(range(total))-selected)
    artifact=exchange['artifacts'][0]
    artifact['payload']['pages_expected']=list(artifact['payload']['pages_acquired'])+[
        'synthetic-missing-{}-source-{}'.format(artifact['book_id'],i) for i in sorted(missing)]

rows=[]
def run_case(book,label,mutate=None,expected='accept',codes=None,version='R2',portable=False):
    parent=ROOT/'examples/a01'/('bundles' if version=='original' else version+'/bundles')/book
    folder=RUN/(book+'-'+version+'-'+label)
    shutil.copytree(parent,folder)
    exchange=read(folder/'exchange.json'); p=read(folder/'provenance.json')
    if mutate is not None:
        mutate(exchange,p)
        mark_and_seal(folder,exchange,p)
    oracle=partition_oracle(p,exchange['artifacts'][0])
    public=result(lambda:contracts.load_bundle(folder/'exchange.json',verify_assets=True))
    actual=result(lambda:importer.load_static_bundle(folder/'exchange.json',expected_book_id=book))
    if expected=='accept': passed=oracle and public['ok'] and actual['ok']
    elif expected=='reject-source':
        passed=(not oracle and public['ok'] and not actual['ok'] and actual['exception']=='StaticSourceError'
                and bool(actual['location']) and (codes is None or actual['code'] in codes))
    else: passed=not public['ok'] and not actual['ok']
    portable_result=None
    if portable and public['ok'] and actual['ok']:
        moved=RUN/'portable destination with spaces'/folder.name
        shutil.copytree(folder,moved)
        oldcwd=Path.cwd()
        elsewhere=RUN/'unrelated cwd';elsewhere.mkdir(exist_ok=True)
        try:
            os.chdir(elsewhere)
            portable_result={'path':str(moved/'exchange.json'),'cwd':str(Path.cwd()),
                             'public':result(lambda:contracts.load_bundle(moved/'exchange.json',verify_assets=True)),
                             'source':result(lambda:importer.load_static_bundle(moved/'exchange.json',expected_book_id=book))}
        finally: os.chdir(oldcwd)
        passed=passed and portable_result['public']['ok'] and portable_result['source']['ok']
    case_id=book+'.'+version+'.'+label
    evidence=OUT/'inputs'/case_id
    save(evidence/'provenance.json',p);save(evidence/'exchange.json',exchange)
    save(evidence/'limitations.json',read(folder/'limitations.json'))
    hashes=[{'path':str(f.relative_to(folder)).replace('\\','/'),'bytes':f.stat().st_size,'sha256':sha(f)}
            for f in sorted(folder.rglob('*')) if f.is_file()]
    save(evidence/'package-sha256.json',hashes)
    row={'id':case_id,'kind':'SYNTHETIC' if mutate else 'frozen baseline','expected':expected,'oracle_valid':oracle,
         'public':public,'source':actual,'outcome':'PASS' if passed else 'FAIL','package':str(folder/'exchange.json'),
         'evidence_input':str(evidence),'portable':portable_result,
         'scope':{'metadata':p['metadata_page_count'],'A':[m['source_index'] for m in p['mappings']],
                  'S':p['selected_source_indices'],'M':p['selected_missing_source_indices'],
                  'O':p['outside_selected_scope_unacquired_indices'],
                  'expected_ids':exchange['artifacts'][0]['payload']['pages_expected'],
                  'acquired_ids':exchange['artifacts'][0]['payload']['pages_acquired'],
                  'unknown':read(folder/'limitations.json')['independent_denominator_status'],
                  'coverage_eligible':read(folder/'limitations.json')['coverage_eligible']}}
    rows.append(row)

for book,total,first in [('46006966',250,7),('46007447',214,13)]:
    for version in ['original','R1','R2']:
        run_case(book,'unchanged',version=version)
    for label,missing in [('missing-zero',[0]),('missing-upper',[total-1]),('missing-both-boundaries',[0,total-1])]:
        run_case(book,label,lambda e,p,m=missing:missing_intent(e,p,m),portable=True)
    def all_selected(e,p):
        a={m['source_index'] for m in p['mappings']}
        missing_intent(e,p,sorted(set(range(p['metadata_page_count']))-a))
    run_case(book,'all-selected-empty-outside',all_selected,portable=True)
    def reorder(e,p):
        missing_intent(e,p,[0,total-1])
        p['selected_source_indices'].reverse();p['outside_selected_scope_unacquired_indices'].reverse()
        p['selected_missing_source_indices'].reverse()
        e['artifacts'][0]['payload']['pages_expected'].reverse()
    run_case(book,'order-independent',reorder)
    # Fixed prior failures and nearby independent set contradictions.
    run_case(book,'fixed-acquired-also-missing',lambda e,p:p.__setitem__('selected_missing_source_indices',[first]),
             expected='reject-source',codes=['SCOPE_PARTITION'])
    run_case(book,'fixed-acquired-also-outside',lambda e,p:p['outside_selected_scope_unacquired_indices'].append(first),
             expected='reject-source',codes=['SCOPE_PARTITION'])
    run_case(book,'acquired-not-selected',lambda e,p:p['selected_source_indices'].remove(first),
             expected='reject-source',codes=['SCOPE_PARTITION'])
    run_case(book,'unselected-missing',lambda e,p:p.__setitem__('selected_missing_source_indices',[0]),
             expected='reject-source',codes=['SCOPE_PARTITION'])
    run_case(book,'outside-omission',lambda e,p:p['outside_selected_scope_unacquired_indices'].remove(0),
             expected='reject-source',codes=['SCOPE_PARTITION'])
    run_case(book,'selected-missing-omission',lambda e,p:p['selected_source_indices'].append(0),
             expected='reject-source',codes=['SCOPE_PARTITION'])
    def overlap(e,p):
        missing_intent(e,p,[0]);p['outside_selected_scope_unacquired_indices'].append(0)
    run_case(book,'missing-also-outside',overlap,expected='reject-source',codes=['SCOPE_PARTITION'])
    for field in ['selected_source_indices','selected_missing_source_indices','outside_selected_scope_unacquired_indices']:
        for kind,value in [('bool',False),('float',0.0),('negative',-1),('at-count',total),('above-count',total+1)]:
            def invalid(e,p,field=field,value=value):
                missing_intent(e,p,[0,total-1]);p[field].append(value)
            run_case(book,field+'-'+kind,invalid,expected='reject-source',codes=['SCOPE_INDICES'])
        def duplicate(e,p,field=field):
            missing_intent(e,p,[0,total-1]);p[field].append(p[field][0])
        run_case(book,field+'-duplicate',duplicate,expected='reject-source',codes=['SCOPE_INDICES'])
        def wrongshape(e,p,field=field):p[field]=None
        run_case(book,field+'-null',wrongshape,expected='reject-source',codes=['SCOPE_INDICES'])
    def no_expected_placeholder(e,p):
        missing_intent(e,p,[0]);e['artifacts'][0]['payload']['pages_expected'].pop()
    run_case(book,'missing-no-expected-placeholder',no_expected_placeholder,expected='reject-source',codes=['SCOPE_COUNT'])
    def extra_expected(e,p):e['artifacts'][0]['payload']['pages_expected'].append('synthetic-extra-not-selected')
    run_case(book,'extra-expected-not-selected',extra_expected,expected='reject-source',codes=['SCOPE_COUNT'])
    run_case(book,'metadata-float',lambda e,p:p.__setitem__('metadata_page_count',float(total)),
             expected='reject-source',codes=['SCOPE_COUNT'])
    run_case(book,'acquired-count-float',lambda e,p:p.__setitem__('acquired_unique_images',float(len(p['mappings']))),
             expected='reject-source',codes=['SCOPE_COUNT'])
    def mapping_float(e,p):p['mappings'][0]['source_index']=float(p['mappings'][0]['source_index'])
    run_case(book,'mapped-index-float',mapping_float,expected='reject-source',codes=['SCOPE_INDICES'])
    # The public layer itself owns asset/acquired identity and list uniqueness.
    def acquired_missing_id(e,p):e['artifacts'][0]['payload']['pages_acquired'].pop()
    run_case(book,'public-acquired-identity-control',acquired_missing_id,expected='reject-public')
    def acquired_duplicate(e,p):e['artifacts'][0]['payload']['pages_acquired'].append(e['artifacts'][0]['payload']['pages_acquired'][0])
    run_case(book,'public-acquired-duplicate-control',acquired_duplicate,expected='reject-public')

environment={'delivery_commit':'c3aff9598b6705ab4122062615a13ae3774698b2','implementation_commit':'63ac5a184798326d629a43d1dfed25fa73a1a27e',
             'snapshot':str(ROOT),'run_root':str(RUN),'TMP':os.environ['TMP'],'TEMP':os.environ['TEMP'],'python':sys.version,
             'python_executable':sys.executable,'platform':platform.platform(),'pydantic':pydantic.__version__,
             'sys_path_0':sys.path[0],'dont_write_bytecode':sys.dont_write_bytecode,
             'modules':[{'file':m.__file__,'sha256':sha(m.__file__)} for m in [importer,consistency,validation]]}
summary={'environment':environment,'cases':len(rows),'pass':sum(r['outcome']=='PASS' for r in rows),
         'fail':sum(r['outcome']=='FAIL' for r in rows),'legal_cases':sum(r['expected']=='accept' for r in rows),
         'source_rejection_cases':sum(r['expected']=='reject-source' for r in rows),
         'public_control_cases':sum(r['expected']=='reject-public' for r in rows),
         'portable_legal_cases':sum(r['portable'] is not None for r in rows),
         'conclusion':'REWORK' if any(r['outcome']=='FAIL' for r in rows) else 'ACCEPTED'}
save(OUT/'results.json',rows);save(OUT/'summary.json',summary)
(OUT/'run.log').write_text('\n'.join('{} {} expected={} public={} source={}'.format(r['outcome'],r['id'],r['expected'],json.dumps(r['public'],ensure_ascii=False),json.dumps(r['source'],ensure_ascii=False)) for r in rows)+'\n',encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
sys.exit(1 if summary['fail'] else 0)
