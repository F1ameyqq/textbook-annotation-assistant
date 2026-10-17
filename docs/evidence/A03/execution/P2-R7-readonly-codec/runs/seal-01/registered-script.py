"""Reseal raw-log attributes only; no codec, data validation or test reruns."""
import ast,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5];EX=ROOT/'examples/a03/P2-R7-readonly-codec';sys.path.insert(0,str(EX))
from ops import OUT,PRODUCT,load,sha,write
previous=load(OUT/'provisional/sha256-manifest.json');old_rows={r['path']:r for r in previous['files']}
assert sha((OUT/'provisional/sha256-manifest.json').read_bytes())=='67e58477e7c2aae46214e3864f4e9600772d33f6aa1e4033b72e7d3ab05081f3'
old_attributes=(OUT/'provisional/gitattributes-before.txt').read_bytes();attributes=(OUT/'.gitattributes').read_bytes()
assert attributes==old_attributes+b'**/stdout.txt -whitespace\n**/stderr.txt -whitespace\n'
for row in previous['files']:
    path=row['path']
    if path.endswith('/process-release.json')and path=='docs/evidence/A03/execution/P2-R7-readonly-codec/process-release.json':p=OUT/'provisional/process-release.json'
    else:p=ROOT/path
    if path in('docs/evidence/A03/execution/P2-R7-readonly-codec/.gitattributes','docs/evidence/A03/execution/P2-R7-readonly-codec/runner.py','docs/tasks/A03-P2-R7-readonly-codec-delivery.md'):continue
    raw=p.read_bytes();assert len(raw)==row['bytes']and sha(raw)==row['sha256'],path
sources=[{'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p.read_bytes())}for p in sorted(PRODUCT.glob('*.py'))];assert sources==load(OUT/'pre-execution-static-audit.json')['product_source']
for p in(OUT/'runner.py',Path(__file__)):ast.parse(p.read_text(encoding='utf8'))
write(OUT/'seal-adjustment.json',{'status':'RAW_LOG_BYTES_PRESERVED_ATTRIBUTES_ONLY','initial_manifest_sha256':sha((OUT/'provisional/sha256-manifest.json').read_bytes()),'initial_raw_log_whitespace_check':'wheel-01/stderr.txt:4 new blank line at EOF','log_bytes_changed':False,'product_fixture_or_test_changes':False,'new_role_or_rule_changes':False,'test_or_codec_reruns':0,'metadata_changes':['raw stdout/stderr -whitespace attributes','runner accepts seal_check','report explains original whitespace result'],'prior_manifest_and_release_retained':'provisional/'})
print(json.dumps({'status':'RAW_LOG_SEAL_ADJUSTMENT_CHECKED','codec_or_test_calls':0}))
