"""Verify scoped merge bytes and imports; no plan generation or execution."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

root = Path('D:/1800')
os.environ['GIT_NO_LAZY_FETCH'] = '1'
base = 'a3aa161bc1edd75a92a2f01d573513cb25140537'
merged = '07479d69edcbfe8c051f347d21bea714b085e70f'
author = 'd2e710c817cf85505ac4fad4919dd51d1062d33a'
review = 'efe440d07d3600ee9755f1709778a2a742bb2f52'
workflow = 'b1c84db9d1d5603a4fd6aa5487d7c45ec6fca50a'
candidate = '6dad9b9a40a10989c102d91cf7b54f19c012015f'

def git(*args):
    return subprocess.check_output(['git','-c','core.longpaths=true',*args],cwd=root)

def tree(rev):
    return dict((entry.split(b'\t',1)[1].decode(),tuple(entry.split(b'\t',1)[0].decode().split()))
                for entry in git('ls-tree','-r','-z',rev).split(b'\0') if entry)

trees = {r:tree(r) for r in (base,merged,author,review,workflow,candidate)}
old, current = trees[base], trees[merged]
assert all(current[p] == value for p,value in old.items())
author_paths = set(trees[author]) - set(trees[workflow])
review_paths = set(trees[review]) - set(trees[candidate])
assert set(current) - set(old) == author_paths | review_paths
assert len(author_paths) == 64 and len(review_paths) == 55
for revision,paths in ((author,author_paths),(review,review_paths)):
    assert all(current[p] == trees[revision][p] for p in paths)

stage = root / '.local/stages/coordinator/a07-integrated-import-20261018'
stage.mkdir(parents=True,exist_ok=False)
source_members = []
for path,(mode,kind,oid) in current.items():
    if path.startswith('src/'):
        raw = git('cat-file','blob',oid)
        target = stage / path
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(raw)
        source_members.append({'path':path,'blob_oid':oid,'sha256':hashlib.sha256(raw).hexdigest()})
sys.dont_write_bytecode = True
sys.path.insert(0,str(stage/'src'))
import annotation.source.b_q1
import annotation.quality.q1_offline
import annotation.delivery.q1_offline
from annotation.contracts import load_bundle, assert_plan_ready, artifact_ref

# Exact raw export already checked during coordinator acceptance; only read it.
recorded = root / '.local/stages/coordinator/a07-fixed-artifact-recheck-20261018/run'
complete = load_bundle(recorded/'exchange.json')
pre = load_bundle(recorded/'pre-execution.json')
plan = next(a for a in pre.artifacts if a.kind == 'ApplyPlan')
assert_plan_ready(pre,artifact_ref(plan),plan.payload.snapshot)
result = {'at':datetime.now(timezone.utc).isoformat(),'result':'PASS_SCOPED_LOCAL_INTEGRATION',
          'base':base,'integration_commit':merged,
          'author_merge_commit':'ee554db57fa7e26ed5938cc522f8f2ce7b6c7b9d',
          'author_delivery':author,'review_delivery':review,
          'old_path_count':len(old),'all_old_path_mode_type_blob_preserved':True,
          'added_paths':len(author_paths|review_paths),'author_added_paths':64,'review_added_paths':55,
          'updated_paths':0,'deleted_paths':0,'all_fixed_additions_raw_equal':True,
          'raw_source_export_members':source_members,
          'new_modules_imported':['annotation.source.b_q1','annotation.quality.q1_offline','annotation.delivery.q1_offline'],
          'recorded_C01_exchange_assets_valid':True,'recorded_C01_pre_assets_valid':True,
          'recorded_C01_plan_ready':True,'new_business_attempts':0,'new_targets':0,'new_dispatches':0,
          'platform_actions':0,'network_calls':0,'pushed':False,'message_sent_to_B':False}
output = root/'docs/evidence/coordinator/a07-acceptance-20261018/integration-check.json'
output.write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode())
print(json.dumps({k:v for k,v in result.items() if k != 'raw_source_export_members'},indent=2))
