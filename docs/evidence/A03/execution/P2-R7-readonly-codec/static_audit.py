"""Pre-execution AST, exact data/fixture and permitted-diff audit only."""
import ast,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5];EX=ROOT/'examples/a03/P2-R7-readonly-codec';sys.path.insert(0,str(EX))
from ops import BASE,FIX,OUT,PRODUCT,git,load,raw_write,sha,verify_old_exception,write
for p in list(PRODUCT.glob('*.py'))+list(EX.glob('*.py'))+list(OUT.glob('*.py'))+[ROOT/'tests/test_a03_r7_readonly_codec.py']:
    tree=ast.parse(p.read_text(encoding='utf8'))
    if p.is_relative_to(PRODUCT):
        for node in ast.walk(tree):
            if isinstance(node,ast.Call)and isinstance(node.func,ast.Name):assert node.func.id not in('exec','eval','compile','__import__'),str(p)
            if isinstance(node,(ast.Import,ast.ImportFrom)):
                text=ast.get_source_segment(p.read_text(encoding='utf8'),node);assert'all_static'not in text and'oracle_verifier'not in text
for row in load(OUT/'packaged-data-index.json')['data']:
    raw=(PRODUCT/'data'/row['name']).read_bytes();assert sha(raw)==row['sha256']
    if row['source']!='NEW_A_INTERNAL_READONLY_RECORD':assert raw==git('show',BASE+':'+row['source'])
index=load(FIX/'index.json');assert len(index['cases'])==7
for row in index['cases']:
    original=load(ROOT/row['source_case']);raw=(FIX/row['bundle']).read_bytes();assert raw==git('show',BASE+':'+original['bundle'])and sha(raw)==row['bundle_sha256']
    mismatches=[]
    for resource in row['resources']:
        body=(FIX/row['asset_root']/resource['path']).read_bytes();assert sha(body)==resource['actual_sha256']
        if sha(body)!=resource['declared_sha256']:mismatches.append(resource)
    assert mismatches==row['intentional_digest_mismatches_preserved']
    assert len(mismatches)==(1 if row['id']=='global-resource-hash-corruption'else 0)
source='examples/contracts/consume.py';raw=git('show',BASE+':'+source);assert raw.replace(b'\r\n',b'\n')==(ROOT/source).read_bytes().replace(b'\r\n',b'\n')
write(OUT/'compatibility-input-pins.json',{'inputs':[{'commit':BASE,'path':source,'bytes':len(raw),'sha256':sha(raw),'git_blob':git('rev-parse',BASE+':'+source).decode().strip(),'checkout_sha256':sha((ROOT/source).read_bytes())}]})
write(OUT/'pre-execution-static-audit.json',{'status':'IMPLEMENTATION_AND_FIXTURES_STATIC_READY','product_source':[{'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p.read_bytes())}for p in sorted(PRODUCT.glob('*.py'))],'data_files':9,'fixed_cases':7,'intentional_bad_digest_cases':1,'fixture_business_JSON_unchanged':True,'pyproject_exception':verify_old_exception(),'old_product_default_entry_unchanged':not bool(git('diff','--name-only','--','src/annotation/contracts/__init__.py').strip()),'old_static_entry_calls':0})
print(json.dumps({'status':'STATIC_READY','cases':7,'bad_digest_preserved':True,'product_tests_run':0}))
