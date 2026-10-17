"""Materialize exact packaged data and seven test roots, including bad bytes."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5];EX=ROOT/'examples/a03/P2-R7-readonly-codec';sys.path.insert(0,str(EX))
from ops import BASE,DATA,FIX,OUT,PRODUCT,PACKAGE_DATA_APPEND,git,load,raw_git_batch,raw_write,sha,write
inputs=load(OUT/'raw-input-pins.json');pin_by_path={r['path']:r for r in inputs['inputs']if r['commit']==BASE}
def pinned(name):
    raw=git('show',BASE+':'+name);row=pin_by_path[name];assert len(raw)==row['bytes']and sha(raw)==row['sha256'];return raw
profile_raw=pinned('examples/a03/P2-R2-proposal/candidate-final/profile.json');profile=json.loads(profile_raw)
data_rows=[]
for name in('profile.json','api.json')+[row['path']for row in profile['schema_pins']]:
    source='examples/a03/P2-R2-proposal/candidate-final/'+name;raw=pinned(source);target=PRODUCT/'data'/name;raw_write(target,raw);data_rows.append({'name':name,'source':source,'sha256':sha(raw),'bytes':len(raw)})
adoption={'codec_id':'a03-static-readonly-v1','role':'STATIC_INSPECTION','exchange_version':profile['exchange_version'],'artifact_versions':[profile['new_artifact_version'],'1.1.0-a-recovery-proposal'],'profile_id':profile['profile_id'],'profile_sha256':sha(profile_raw),'schema_pins':[[r['path'],r['sha256']]for r in profile['schema_pins']],'api_sha256':profile['api_sha256'],'validation_rules_id':'a03-r2-r3-r5-r6-static-closure','adoption_scope':'A_INTERNAL_READONLY','source_profile_status':profile['status'],'source_implementation_authorized':profile['implementation_authorized'],'limits':['STATIC_INSPECTION_ONLY','NO_CURRENT_ROLE','NO_NATIVE_PRE_OR_WRITE_AUTHORITY'],'rule_source_sha256':{'R2_Package':'7bf3ea27424f7afaf3d3b264d2ab3d0bfa0fdc8bba1c178e6f488bef09e6257b','R3_formal_closure':'ff650507bca971f8c9418a09e6e4f8df7c7691016841ffe7bd15ff66382579a5','R5_registration':'3f0281c5cfc9aeec99b11fa2de30ba40e9984a19dd0e651b747d99ebe29772ba'}}
write(PRODUCT/'data/readonly-adoption.json',adoption);data_rows.append({'name':'readonly-adoption.json','source':'NEW_A_INTERNAL_READONLY_RECORD','sha256':sha((PRODUCT/'data/readonly-adoption.json').read_bytes()),'bytes':(PRODUCT/'data/readonly-adoption.json').stat().st_size})
case_rows=[]
for item in inputs['cases']:
    original=load(ROOT/item['case']);bundle_raw=pinned(original['bundle']);assert sha(bundle_raw)==original['bundle_sha256'];case_dir=FIX/item['id'];raw_write(case_dir/'bundle.json',bundle_raw)
    over={r['logical']:pinned(r['file'])for r in original['resources']};seen={};resources=[];mismatches=[]
    def collect(value):
        if isinstance(value,dict)and{'path','sha256','media_type'}<=set(value):
            logical=value['path']
            if logical in seen:
                assert seen[logical]==value['sha256'];return
            seen[logical]=value['sha256'];body=over[logical]if logical in over else pinned((DATA/logical).relative_to(ROOT).as_posix())
            target=case_dir/'assets'/logical;assert target.resolve().is_relative_to((case_dir/'assets').resolve());raw_write(target,body)
            resources.append({'path':logical,'declared_sha256':value['sha256'],'actual_sha256':sha(body),'bytes':len(body)})
            if sha(body)!=value['sha256']:mismatches.append(resources[-1])
            if value['media_type']=='application/json':collect(json.loads(body))
        elif isinstance(value,dict):
            for child in value.values():collect(child)
        elif isinstance(value,list):
            for child in value:collect(child)
    collect(json.loads(bundle_raw));assert len(mismatches)==(1 if item['id']=='global-resource-hash-corruption'else 0)
    record={'id':item['id'],'source_case':item['case'],'source_case_sha256':item['case_sha256'],'bundle':(case_dir/'bundle.json').relative_to(FIX).as_posix(),'bundle_sha256':sha(bundle_raw),'asset_root':(case_dir/'assets').relative_to(FIX).as_posix(),'expected':item['expected'],'expected_layer':item['expected_layer'],'resources':resources,'intentional_digest_mismatches_preserved':mismatches}
    write(case_dir/'case.json',record);case_rows.append(record)
write(FIX/'index.json',{'base':BASE,'cases':case_rows,'original_business_JSON_unchanged':True,'bad_digest_bytes_repaired':False,'old_entry_calls':0})
original=pinned('pyproject.toml');before=(ROOT/'pyproject.toml').read_bytes();assert before.replace(b'\r\n',b'\n')==original
write(OUT/'pyproject-before.json',{'raw_git_sha256':sha(original),'checkout_sha256':sha(before),'checkout_newline_conversion_only':before!=original})
(ROOT/'pyproject.toml').write_bytes(original+PACKAGE_DATA_APPEND)
write(OUT/'packaged-data-index.json',{'data':data_rows,'adoption_sha256':data_rows[-1]['sha256'],'profile_original_bytes_unchanged':True,'only_role':'STATIC_INSPECTION'})
print(json.dumps({'status':'EXACT_DATA_AND_FIXTURES_PREPARED','cases':len(case_rows),'adoption_sha256':data_rows[-1]['sha256'],'bad_resource_cases_preserved':sum(bool(r['intentional_digest_mismatches_preserved'])for r in case_rows)}))
