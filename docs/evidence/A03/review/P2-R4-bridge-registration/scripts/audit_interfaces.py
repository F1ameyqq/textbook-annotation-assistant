"""Text/AST only: never imports, compiles or executes product modules."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess

OUT=Path(__file__).resolve().parents[1];ROOT=OUT/'input/checkout'
EX=ROOT/'examples/a03/P2-R4-bridge-registration';EV=ROOT/'docs/evidence/A03/execution/P2-R4-bridge-registration'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def load(p):return json.loads(p.read_bytes())
def write(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf8',newline='\n')as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
proposal=load(EX/'bridge-interface-proposal.json');index=load(EV/'input-index.json')
functions={};types=[]
for x in index['product_text']:
    raw=(ROOT/x['copy']).read_bytes();assert sha(raw)==x['sha256'];source=raw.decode('utf8');tree=ast.parse(source)
    def walk(body,prefix=''):
        for node in body:
            if isinstance(node,ast.ClassDef):
                types.append({'path':x['path'],'name':prefix+node.name,'line':node.lineno,
                 'fields':[{'name':n.target.id,'annotation':ast.unparse(n.annotation)}for n in node.body if isinstance(n,ast.AnnAssign)and isinstance(n.target,ast.Name)]})
                walk(node.body,prefix+node.name+'.')
            elif isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
                functions[(x['path'],prefix+node.name)]=(node,source,x)
    walk(tree.body)
rows=[];excerpts=[]
assert len(proposal['interfaces'])==19
for item in proposal['interfaces']:
    e=item['existing'];node,source,pin=functions[(e['path'],e['qualified_name'])]
    segment=ast.get_source_segment(source,node);args=ast.unparse(node.args)
    assert node.lineno==e['start']and node.end_lineno==e['end']and args==e['args']
    assert e['signature_normalized']==node.name+'('+args+')'
    assert sha(segment.encode())==e['function_source_sha256']and pin['sha256']==e['source_sha256']and pin['raw_git_blob']==e['source_blob']
    rows.append({'id':item['id'],'path':e['path'],'qualified_name':e['qualified_name'],'lines':[node.lineno,node.end_lineno],
       'current_signature':e['signature_normalized'],'function_source_sha256':sha(segment.encode()),'all_exact_fields_match':True})
    excerpts.append({'id':item['id'],'path':e['path'],'start':node.lineno,'end':node.end_lineno,'source':segment,
                     'current_output_or_shape':item['current_output_or_shape'],'proposed_contract':item['proposed_contract']})
new=proposal['proposed_new_pre_boundary'];future=subprocess.run(['git','ls-tree',proposal['base'],'--',new['future_path']],cwd='D:/1800',stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
assert not future.stdout
assert new['status']=='PROPOSED_NOT_EXISTING'and proposal['native_execution_authorized']is False
assert all(x['proposal_status']=='NOT_IMPLEMENTED_NOT_ADOPTED'for x in proposal['interfaces'])
write(OUT/'interface-ast-audit.json',{'mode':'SOURCE_TEXT_AST_ONLY','source_files':12,'existing_interfaces':rows,
 'proposed_pre_boundary':new,'proposed_pre_path_absent_at_base':True,'new_types_proposed':proposal['new_types_proposed_not_existing'],
 'product_imports_or_calls':0,'native_or_version_adoption':False})
write(OUT/'interface-source-excerpts.json',{'functions':excerpts,'type_inventory':types})
for row in excerpts:print(json.dumps({k:v for k,v in row.items()if k!='source'},ensure_ascii=False))
print(json.dumps({'result':'19_SIGNATURES_AND_FUNCTION_SOURCES_EXACT','new_pre_boundary':'PROPOSED_ONLY_PATH_ABSENT','product_calls':0}))
