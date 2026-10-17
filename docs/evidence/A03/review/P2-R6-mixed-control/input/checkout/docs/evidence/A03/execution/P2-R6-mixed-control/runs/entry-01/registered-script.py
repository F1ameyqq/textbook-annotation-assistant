"""One unchanged R5 whole-package call, after persisted independent precheck."""
import json,os,sys
from files import EX,OUT,ROOT,load,sha,write
readonly=sys.argv[1:]==['--readonly'];assert readonly or not sys.argv[1:]
case=load(EX/'case.json');precheck=load(OUT/'precheck.json');assert precheck['status']=='DATA_CONSISTENCY_PASSED_BEFORE_PACKAGE'and precheck['Package_calls']==0
assert precheck['bundle_sha256']==case['bundle_sha256']and sha((ROOT/case['bundle']).read_bytes())==case['bundle_sha256']
assert load(OUT/'runs/precheck-01/exit.json')['exit_code']==0
for pin in load(OUT/'raw-input-pins.json')['inputs']:
    raw=(ROOT/pin.get('copy',pin['path'])).read_bytes();assert len(raw)==pin['bytes']and sha(raw)==pin['sha256']
over={r['logical']:(ROOT/r['file']).read_bytes()for r in case['resources']}
assert all(sha(over[r['logical']])==r['raw_sha256']for r in case['resources'])
if not readonly:write(OUT/'entry-invocation.json',{'run':os.environ['A03_R6_RUN_ID'],'candidate':case['bundle'],'candidate_sha256':case['bundle_sha256'],'precheck_sha256':sha((OUT/'precheck.json').read_bytes()),'one_shot_guard':'xb: no second owned invocation permitted'})
R5=ROOT/'examples/a03/P2-R5-registration-context';sys.path.insert(0,str(R5))
import registration
from load_static import r3,LOADER
assert __import__('pathlib').Path(registration.__file__).resolve()==R5/'registration.py'
assert sha((R5/'registration.py').read_bytes())=='3f0281c5cfc9aeec99b11fa2de30ba40e9984a19dd0e651b747d99ebe29772ba'
assert sha((R5/'load_static.py').read_bytes())=='734b8760b58f7778f4bd32608b77fc87f95a31c027ce457408d5fbdcf8166098'
pkg=registration.Package(load(ROOT/case['bundle']),over)
codes={registration.Package.validate.__code__:'R5_complete_entry',r3.Package.validate.__code__:'R3_inherited_entry',r3.OriginalPackage.validate.__code__:'R2_inherited_entry'}
counts={name:0 for name in codes.values()};reached=[]
source=(ROOT/'examples/a03/P2-R2-proposal/check.py').read_text(encoding='utf8').splitlines();mixed_line=next(i for i,line in enumerate(source,1)if line.strip()=='for n in list(self.edges):visit(n)')
def trace(frame,event,arg):
    if event=='call'and frame.f_code in codes:counts[codes[frame.f_code]]+=1
    if event=='line'and frame.f_code is r3.OriginalPackage.validate.__code__and frame.f_lineno==mixed_line and'MIXED_DAG'not in reached:reached.append('MIXED_DAG')
    return trace
before=r3.Package.entry_calls;old_trace=sys.gettrace();sys.settrace(trace)
try:
    pkg.validate();actual='STATIC_ACCEPTED';error=None
except registration.Rejected as error_value:actual=error_value.code;error={'code':error_value.code,'path':error_value.path}
finally:sys.settrace(old_trace)
after=r3.Package.entry_calls;failures=pkg.consumer_failures()
ring=[dict(edge,observed_in_actual_graph=edge['to']in pkg.edges.get(edge['from'],set()))for edge in precheck['ring_edges']]
assert not any(getattr(m,'__file__',None)and str(ROOT/'src')in str(m.__file__)for m in list(sys.modules.values()))
matched=actual=='MIXED_CYCLE'and reached==['MIXED_DAG']and all(n==1 for n in counts.values())and after-before==1 and not failures and all(e['observed_in_actual_graph']for e in ring)
result={'status':'REVIEW_EXPECTED_MIXED_CYCLE_OBSERVED'if matched else'REWORK_AFTER_SINGLE_ENTRY','candidate_count':1,'candidate_sha256':case['bundle_sha256'],'precheck_sha256':sha((OUT/'precheck.json').read_bytes()),'actual':actual,'error':error,'matched_specified_layer_and_counts':matched,'measured_calls':counts,'R3_entry_counter_before':before,'R3_entry_counter_after':after,'R3_entry_counter_delta':after-before,'reached_layers':reached,'full_entry_returned':pkg.full_entry_returned,'real_consumers':len(pkg.consumers),'none_book_real_consumers':sum(book is None for found,declared,book,scope,path in pkg.consumers),'consumer_failures':failures,'actual_ring_edges':ring,'graph_nodes':len(pkg.edges),'prefix_visits':pkg.prefix_visits,'loader':LOADER,'fixed_registration_sha256':sha((R5/'registration.py').read_bytes()),'fixed_loader_sha256':sha((R5/'load_static.py').read_bytes()),'other_six_scenarios_run':0,'old_36_matrix_runs':0,'session_conversion_or_oracle_calls':0,'product_calls':0,'native_qualification':False,'field_reset_probe':'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'}
if not readonly:write(OUT/'entry-result.json',result)
print(json.dumps(result,ensure_ascii=False));sys.exit(0 if matched else 1)
