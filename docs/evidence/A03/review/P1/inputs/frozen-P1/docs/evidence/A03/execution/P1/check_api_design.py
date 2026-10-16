"""A03-P1 API/schema design consistency only; no application or recovery calls."""
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[5]
P1=ROOT/'examples/a03/P1'

def load(path):
    def unique(pairs):
        out={}
        for k,v in pairs:
            if k in out:raise ValueError('Duplicate key '+k)
            out[k]=v
        return out
    return json.loads(path.read_text(encoding='utf-8-sig'),object_pairs_hook=unique,
                      parse_constant=lambda x:(_ for _ in ()).throw(ValueError(x)))

def main():
    api=load(P1/'api-proposal.json')
    schema=load(P1/'recovery-exchange.schema.json')
    ledger=load(P1/'ledger-export.schema.json')
    manifest=load(P1/'case-manifest.json')
    errors=[]
    def check(condition,message):
        if not condition:errors.append(message)
    check(api['implementation_authorized'] is False,'P1 must not authorize P2')
    check(api['schema_version']=='1.1.0-a-recovery-proposal','schema version')
    check(api['exchange_version']=='a03-exchange-1','exchange version')
    check(api['design_constants']['recovery_attempt_limit']==3,'read attempt limit')
    check([g['id'] for g in api['groups']]==['G1','G2','G3','G4'],'four adapter groups')
    current_entries=0
    proposed_entries=0
    for group in api['groups']:
        for current in group['current']:
            lines=(ROOT/current['file']).read_text(encoding='utf-8-sig').splitlines()
            check(1<=current['line_start']<=current['line_end']<=len(lines),'current source range '+current['file'])
            current_entries+=1
        for proposed in group['proposed']:
            for key in ('signature','owner','responsibility','inputs','outputs','failure_codes','compatibility'):
                check(key in proposed,'missing '+key+' in '+proposed.get('signature','?'))
            proposed_entries+=1
    definitions=schema['$defs']
    for kind in ('WriteIntent','ExecutionProgress','ReconciliationResult'):
        check(kind in definitions,'missing artifact '+kind)
    check('obligation_id' in definitions['ReconciliationResultPayload']['required'],'obligation binding')
    check('prepared_before' in definitions['WriteIntentPayload']['required'],'per-action before evidence')
    check('origin' in definitions['Resource']['required'],'explicit resource origin')
    check(ledger['properties']['db_version']['const']=='a03-runtime-db-1','runtime DB version')
    for method in api['runtime_authority_protocol']['methods']:
        for key in ('signature','responsibility','inputs','outputs','failure_codes'):
            check(key in method,'authority field '+key)
    signatures='\n'.join(m['signature'] for m in api['runtime_authority_protocol']['methods'])
    for method in ('verify_claim','issue_first_dispatch','consume_first_dispatch','verify_target_authorization','verify_context','clear_target_drift_hold','commit_reconciliation'):
        check(method+'(' in signatures,'missing authority method '+method)
    facts=load(P1/'action-fact.schema.json')
    for key in ('origin_phase','resolution_ref'):
        check(key in facts.get('required',[]),'action-fact missing '+key)
    receipt=definitions['ReceiptPayload']
    check('action_fact_refs' in receipt['required'],'receipt fact aggregation')
    for case in manifest['cases']:
        check(case['semantic_execution']=='EXPECTED_NOT_EXECUTED','mislabelled semantics '+case['case_id'])
    parsed=0
    for path in sorted(P1.rglob('*.json')):
        load(path)
        parsed+=1
    result={'check_kind':'P1_STATIC_DESIGN_CONSISTENCY_ONLY','json_files_parsed':parsed,
            'adapter_groups':4,'current_entries_checked':current_entries,
            'proposed_group_interfaces_checked':proposed_entries,
            'authority_protocol_methods':len(api['runtime_authority_protocol']['methods']),
            'semantic_or_recovery_execution':False,'errors':errors,'passed':not errors}
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if not errors else 1

if __name__=='__main__':sys.exit(main())
