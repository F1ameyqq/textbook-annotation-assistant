"""Exactly one complete static Package call; --readonly prints without writes."""
import json,os,sys
from common import EX,OUT,ROOT,load,sha,write
args=sys.argv[1:];readonly='--readonly'in args
if readonly:args.remove('--readonly')
repair='--repair'in args
if repair:args.remove('--repair')
assert len(args)==1
index=load(EX/('repair-case-index.json'if repair else'case-index.json'));row=next(r for r in index['cases']if r['id']==args[0]);case=load(ROOT/row['case'])
assert sha((ROOT/row['case']).read_bytes())==row['case_sha256']
raw=(ROOT/case['bundle']).read_bytes();assert sha(raw)==case['bundle_sha256']
over={r['logical']:(ROOT/r['file']).read_bytes()for r in case['resources']}
assert all(sha(over[r['logical']])==r['raw_sha256']for r in case['resources'])
pins=load(OUT/'input-index.json')['inputs']
if repair:pins=pins+load(OUT/'repair-input-index.json')['inputs']
for pin in pins:
    p=ROOT/pin.get('copy',pin['path']);assert sha(p.read_bytes())==pin['sha256']
from registration import Package,Rejected
from load_static import LOADER,r3,base
package=Package(json.loads(raw),over);tail=[];read_failures=[]
source=(ROOT/'examples/a03/P2-R2-proposal/check.py').read_text(encoding='utf8').splitlines()
anchors={}
for i,line in enumerate(source,1):
    if line.strip()=='for n in list(self.edges):visit(n)':anchors[i]='MIXED_DAG'
    if line.strip()=='for found,declared,book,scope,path in self.consumers:':anchors[i]='CONSUMER_DECLARATIONS_BOOK_SCOPE'
    if "==a['content_hash'],'ARTIFACT_HASH'"in line:anchors[i]='ARTIFACT_HASH'
    if line.strip()=='return self'and i<115:anchors[i]='FULL_R2_TAIL_RETURN'
def trace(frame,event,arg):
    if frame.f_code is r3.OriginalPackage.validate.__code__ and event=='line':
        label=anchors.get(frame.f_lineno)
        if label and label not in tail:tail.append(label)
    if frame.f_code is r3.OriginalPackage.read.__code__ and event=='exception'and isinstance(arg[1],Rejected):
        read_failures.append({'code':arg[1].code,'path':arg[1].path,'active_real_contexts':len(package.contexts)})
    return trace
sys.settrace(trace)
try:
    package.validate();actual='STATIC_ACCEPTED';error=None
except Rejected as e:actual=e.code;error={'code':e.code,'path':e.path}
finally:sys.settrace(None)
assert not any(getattr(m,'__file__',None)and str(ROOT/'src')in str(m.__file__)for m in list(sys.modules.values()))
result={'id':row['id'],'expected':row['expected'],'actual':actual,'matched':actual==row['expected'],'error':error,'entry':'registration.Package.validate','package_calls':1,'full_entry_returned':package.full_entry_returned,'inherited_tail_trace':tail,'prefix_visits':package.prefix_visits,'registration_checks':package.registration_checks,'global_frames':package.global_frames,'resource_read_failures':read_failures,'consumer_failures':package.consumer_failures(),'formal_evidence_refs':package.evidence_refs,'graph_nodes':len(package.edges),'real_consumers':len(package.consumers),'none_book_real_consumers':sum(book is None for found,declared,book,scope,path in package.consumers),'loader':LOADER,'overlay_sha256':sha((EX/'registration.py').read_bytes()),'bundle_sha256':sha(raw),'old_36_matrix_runs':0,'product_calls':0,'native_qualification':False,'field_reset_probe':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'}
if not readonly:
    label=os.environ['A03_R5_RUN_ID'];write(OUT/'results'/(label+'.json'),result)
print(json.dumps(result,ensure_ascii=False));sys.exit(0 if result['matched']else 1)
