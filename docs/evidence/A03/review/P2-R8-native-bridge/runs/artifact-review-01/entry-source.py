# -*- coding: utf-8 -*-
"""Read actual frozen run/package resources; do not recompute quality or call native APIs."""
import json
from evidence import OUT,EV,INDEX,document,raw,text,sha,write

digest='6845ce79b980ff45dd5d03fb1cf8d0625d03bc3e527aa728ca6c868577452d58'
paths=[r['path'] for r in INDEX if r['path'].endswith('/assets/native-pre/'+digest+'.json')]
assert len(paths)==1
path=paths[0];body=raw(path);assert sha(body)==digest
run=json.loads(body);package=path.split('/assets/native-pre/',1)[0]
assert run['format_version']=='a03-native-pre-run-1'
assert run['runtime_status']=='ACTUAL_CHECKS_COMPUTED' and run['admission']=='RUNTIME_RECHECK_REQUIRED'
assert set(run['checks'])=={'source_integrity','structure','answer_matching','coverage','policy'}
assert set(run['checks'].values())=={'PASS'}
assert run['context']=={'kind':'INITIAL','hold_id':None,'hold_head':None,'hold_ref':None}
assert run['implementation_sha256']==sha(raw('src/annotation/quality/synthetic_precheck.py'))
resources=[]
for ref in run['input_manifest']+[run['actual_observation'],run['oracle']]:
    source=package+'/'+ref['path'];value=raw(source);assert sha(value)==ref['sha256']
    resources.append({'path':source,'bytes':len(value),'sha256':sha(value)})
assert run['oracle']['sha256']==sha(raw('src/annotation/contracts/a03_native/data/oracle.json'))
canon=lambda v:json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
packages=[]
for row in INDEX:
    source=row['path']
    if not source.startswith(package+'/bundle-') or not source.endswith('.json'):continue
    bundle=document(source)
    kinds=[a['kind'] for a in bundle['artifacts']]
    assert all(k in ('SourceBundle','EvidenceBundle','QuestionGraph','PlatformSnapshot') for k in kinds)
    for artifact in bundle['artifacts']:
        assert sha(canon({k:v for k,v in artifact.items() if k!='content_hash'}))==artifact['content_hash']
    packages.append({'path':source,'file_sha256':sha(raw(source)),
      'canonical_sha256':sha(canon(bundle)),'artifacts':len(kinds),'kinds':kinds})
assert len(packages)==2 and sorted(p['artifacts'] for p in packages)==[4,5]
assert run['input_raw_sha256'] in {p['canonical_sha256'] for p in packages}
assert 'bbox: List[float]' in text('src/annotation/contracts/models.py')
fixture=document('tests/fixtures/a03/P2-R8-native-bridge/initial.json')
evidence=next(a for a in fixture['artifacts'] if a['kind']=='EvidenceBundle')
assert all(type(v)is int for r in evidence['payload']['regions'] for v in r['box']['bbox'])
value={'status':'COMPUTED_UNADMITTED_RUN_AND_PREFIX_ARTIFACTS_CONFIRMED',
 'run_path':path,'run_sha256':digest,'runtime_status':run['runtime_status'],'admission':run['admission'],
 'checks_recorded_in_actual_bytes':run['checks'],'quality_checks_recomputed':False,
 'context':run['context'],'implementation_sha256':run['implementation_sha256'],
 'raw_linked_resources_verified':resources,'packages':packages,
 'no_PRE_TARGET_plan_receipt_POST_Batch_artifacts_in_persisted_packages':True,
 'first_failure_support':{'fixture_bbox_types':'int','C01_model_bbox_type':'List[float]',
 'actual_failure_index':'artifacts[1] EvidenceBundle in initial fixture',
 'normalization_not_executed_by_reviewer':True},
 'candidate_imports_native_api_or_target_effects':0}
write(OUT/'artifact-boundary-review.json',value)
print(json.dumps({'status':value['status'],'recorded_checks':run['checks'],
 'linked_resources':len(resources),'persisted_package_artifact_counts':[p['artifacts'] for p in packages]}))
