"""Minimize N17: preserve original URL hostname and replace only page suffix."""
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

sys.dont_write_bytecode = True
SNAPSHOT = Path(sys.argv[1]).resolve()
STAGE = Path(sys.argv[2]).resolve()
OUT = Path(__file__).resolve().parent / 'minimal-url'
STAGE.mkdir(parents=True, exist_ok=False)
OUT.mkdir(parents=True, exist_ok=False)
for key in ('TEMP','TMP','TMPDIR'):
    os.environ[key] = str(STAGE)
os.environ['PYTHONPATH'] = str(SNAPSHOT/'src')
sys.path.insert(0,str(SNAPSHOT/'src'))
from annotation.contracts import seal_artifact, load_bundle
from annotation.source.static import load_static_bundle
import annotation.source.static.consistency as consistency
assert Path(consistency.__file__).resolve().is_relative_to(SNAPSHOT/'src')
def read(path):
    return json.loads(path.read_text(encoding='utf-8'))
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

baseline = SNAPSHOT/'examples/a01/R1/bundles/46007447'
bundle = STAGE/'bundle'
shutil.copytree(baseline,bundle)
relative = 'history/00-independent-source-page14.json'
archive = 'docs/evidence/A05/review/independent-source-page14.json'
history = read(bundle/relative)
before_url = history['data']['pages'][0]['image']
after_url = before_url.replace('_page_13.jpg','_page_172.jpg')
assert after_url != before_url
history['data']['pages'][0]['image'] = after_url
write(bundle/relative,history)
history_sha = sha(bundle/relative)
integrity = read(bundle/'input-integrity.json')
entry = next(e for e in integrity['inputs'] if e['archive_path']==archive)
entry.update(before_sha256=history_sha,after_sha256=history_sha)
write(bundle/'input-integrity.json',integrity)
exchange = read(bundle/'exchange.json')
for collection in (exchange['evidence'],exchange['artifacts'][0]['payload']['history']):
    for record in collection:
        resource = record['resource']
        if resource['path'] in (relative,'input-integrity.json'):
            resource['sha256'] = sha(bundle/resource['path'])
exchange['artifacts'] = [seal_artifact(a) for a in exchange['artifacts']]
write(bundle/'exchange.json',exchange)
for name in (relative,'input-integrity.json','exchange.json'):
    (OUT/'changed-inputs'/name).parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(bundle/name,OUT/'changed-inputs'/name)
result = {'target_commit':'03c1af41a134945c406a52a48e3d4f6f0da33eb2', 'case':'N17-minimized',
          'command_argv':sys.argv, 'python_executable':sys.executable,
          'consistency_module':consistency.__file__, 'script_sha256':sha(Path(__file__)),
          'baseline_exchange_sha256':sha(baseline/'exchange.json'),
          'expected':'REJECT', 'actual':None,
          'raw_file_id':history['data']['file_id'], 'raw_page_index':history['data']['pages'][0]['page_index'],
          'before_image_url':before_url,'after_image_url':after_url,
          'URL_index_now':172, 'hash_records_updated_consistently':True,
          'exchange':str(bundle/'exchange.json'), 'network_calls':0}
try:
    load_bundle(bundle/'exchange.json',verify_assets=True)
    load_static_bundle(bundle/'exchange.json',expected_book_id='46007447')
    result.update(actual='ACCEPT',public_load='ACCEPT',a01_load='ACCEPT')
except Exception as error:
    result.update(actual='REJECT',error_type=type(error).__name__,error=str(error),
                  code=getattr(error,'code',None),location=getattr(error,'location',None))
write(OUT/'result.json',result)
print(json.dumps(result,ensure_ascii=False,indent=2))
