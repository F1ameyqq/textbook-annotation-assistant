"""P1-R1 static API/schema/mapping consistency only. No candidate API runs."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[5]
P1 = ROOT/'examples/a03/P1'
R1 = ROOT/'examples/a03/P1-R1'

def load(path):
    def unique(pairs):
        out = {}
        for key,value in pairs:
            if key in out:
                raise ValueError('Duplicate key: '+key)
            out[key] = value
        return out
    return json.loads(path.read_text(encoding='utf-8-sig'), object_pairs_hook=unique,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))

def main():
    api = load(R1/'api-proposal.json')
    old_api = load(P1/'api-proposal.json')
    data = R1/'data'
    manifest = load(data/'case-manifest.json')
    mapping = load(data/'case-mapping.json')
    fact = load(data/'action-fact.schema.json')
    basis = load(data/'unattempted-basis.schema.json')
    errors = []
    def check(value, message):
        if not value:
            errors.append(message)
    check(api['implementation_authorized'] is False, 'P2 authority must remain false')
    check(api['phase']=='A03-P1-R1', 'explicit R1 candidate profile')
    check(api['schema_version']==old_api['schema_version'], 'candidate top-level schema string unchanged')
    check(api['exchange_version']==old_api['exchange_version'], 'candidate exchange string unchanged')
    check([g['id'] for g in api['groups']]==['G1','G2','G3','G4'], 'four groups retained')
    signature = ('runtime.storage.commit_unattempted_absence(bundle, request, *, owner_id, '
                 'generation, asset_root, observer) -> UnattemptedAbsenceRecord')
    new_methods = [p for g in api['groups'] for p in g['proposed'] if p['signature']==signature]
    check(len(new_methods)==1, 'one G2 unattempted fact commit entry')
    for old_group in old_api['groups']:
        new_group = next(g for g in api['groups'] if g['id']==old_group['id'])
        for old_method in old_group['proposed']:
            check(any(p['signature']==old_method['signature'] for p in new_group['proposed']),
                  'old signature missing: '+old_method['signature'])
    if new_methods:
        for key in ('owner','responsibility','inputs','outputs','failure_codes','compatibility'):
            check(key in new_methods[0], 'new method field '+key)
        for code in ('PLAN_STATE_INVALID','PLAN_ACTION_MISMATCH','ACTION_DIGEST_MISMATCH',
                     'EVENT_PREFIX_INCOMPLETE','ACTION_ALREADY_ATTEMPTED','OWNER_GENERATION_STALE',
                     'EVENT_HEAD_CAS_MISMATCH','OBSERVATION_NOT_FRESH','CONCLUSIVE_READBACK_REQUIRED',
                     'PREPARED_BEFORE_MISMATCH','UNATTEMPTED_FACT_DUPLICATE','UNATTEMPTED_FACT_CONFLICT'):
            check(code in new_methods[0]['failure_codes'], 'missing new refusal '+code)
    check('UNATTEMPTED_ABSENCE' in fact['properties']['origin_phase']['enum'], 'fact origin enum')
    check('unattempted_basis' in fact['required'], 'fact basis field required (nullable by origin)')
    check(basis['properties']['format_version'].get('const')=='a03-unattempted-basis-1', 'basis version')
    for key in ('registration_id','journal_id','target_key','target_store_id','target_session_id',
                'source_ref','scope_id','plan_ref','action_id','action_digest','owner_id','generation',
                'expected_event_head','complete_uncalled_prefix','first_observation_ref',
                'readonly_prepared_ref','second_observation_ref'):
        check(key in basis['required'], 'basis missing binding '+key)
    old_manifest = load(P1/'case-manifest.json')
    old_ids = {row['case_id'] for row in old_manifest['cases']}
    check(len(mapping['mappings'])==42, '42 original mapping rows')
    check({row['old_case_id'] for row in mapping['mappings']}==old_ids, 'all old case coverage mapped')
    for row in mapping['mappings']:
        check(hashlib.sha256((P1/row['old_path']).read_bytes()).hexdigest()==row['old_sha256'],
              'old case byte mapping '+row['old_case_id'])
        check(hashlib.sha256((data/row['r1_path']).read_bytes()).hexdigest()==row['r1_sha256'],
              'R1 case byte mapping '+row['r1_case_id'])
    for row in manifest['cases']:
        check(row['semantic_execution']=='EXPECTED_NOT_EXECUTED', 'semantic not-executed marker '+row['case_id'])
    parsed = 0
    # Failed stdout and partial drafting scenes remain evidence, not candidate JSON.
    for path in [R1/'api-proposal.json'] + sorted(data.rglob('*.json')):
        load(path)
        parsed += 1
    result = {'check_kind':'P1_R1_STATIC_API_SCHEMA_MAPPING_ONLY', 'four_groups_retained':True,
              'mapped_original_cases':len(mapping['mappings']), 'case_count':len(manifest['cases']),
              'candidate_json_files_parsed':parsed, 'failed_attempt_outputs_excluded_from_candidate_parse':True,
              'errors':errors, 'passed':not errors,
              'candidate_api_calls':0, 'runtime_or_recovery_executed':False}
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if not errors else 1

if __name__ == '__main__':
    sys.exit(main())
