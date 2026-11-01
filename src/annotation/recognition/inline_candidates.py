"""Verbatim inline formula alternatives; parser support is never approval."""
import copy
from pathlib import Path
from .baseline import code_digest,digest
from .formula_syntax import parse_inline_formula_latex

def ref(v):return {k:v[k]for k in ('artifact_id','revision','content_hash')}

def build_inline_candidates(observations):
    if(observations.get('schema_version')!='b-inline-formula-observation-trial/0.1'
            or observations.get('content_hash')!=digest(observations.get('payload'))):raise ValueError('invalid inline formula observations')
    entries=[];by_unit={};issues=[]
    for call in observations['payload']['calls']:
        observed=call['observation']
        raw=observed['payload']['raw_latex']if observed else None
        parsed=parse_inline_formula_latex(raw)
        candidate=dict(call_id=call['plan']['call_id'],state=call['state'],raw_latex=raw,parse_result=parsed,
            observation_ref=ref(observed)if observed else None,unit_bindings=copy.deepcopy(call['plan']['unit_bindings']),
            complete=False,transcription_verified=False,business_acceptance=False,selected=False)
        candidate['candidate_id']='inline-formula-candidate-'+digest([ref(observations),candidate])[:24]
        entries.append(candidate)
        for binding in candidate['unit_bindings']:
            values=by_unit.setdefault(binding['unit_id'],[])
            if not any(v['candidate_id']==candidate['candidate_id']for v in values):values.append(candidate)
        if call['state']!='DONE':issues.append(dict(code='INLINE_FORMULA_CALL_NOT_DONE',call_id=call['plan']['call_id']))
        elif not parsed['supported']:issues.append(dict(code='INLINE_FORMULA_SYNTAX_UNSUPPORTED',call_id=call['plan']['call_id']))
    units=[]
    for uid,values in by_unit.items():
        normalized=[v['parse_result']['normalized_ast']for v in values]
        agreement=bool(values)and all(v['state']=='DONE'and v['parse_result']['supported']for v in values)and all(n==normalized[0]for n in normalized)
        units.append(dict(unit_id=uid,candidate_refs=[v['candidate_id']for v in values],exact_ast_agreement=agreement,
                          selected_candidate_refs=[],complete=False,transcription_verified=False))
        if not agreement:issues.append(dict(code='INLINE_FORMULA_VARIANT_DISAGREEMENT_OR_UNPARSED',unit_id=uid))
    payload=dict(observation_ref=ref(observations),observations_archive=copy.deepcopy(observations),candidates=entries,units=units,
        not_inference_units=copy.deepcopy(observations['payload']['not_inference_units']),issues=issues,
        entire_answer_reconstructed=False,decision='HOLD',complete=False,transcription_verified=False,business_acceptance=False,
        selected_candidate_refs=[],expected_text_consumed=False,graph_modified=False,platform_actions=[])
    producer=dict(module=__name__,version='0.1.0',code_sha256=code_digest(Path(__file__)),
        syntax_code_sha256=code_digest(Path(__file__).with_name('formula_syntax.py')))
    body=dict(schema_version='b-inline-formula-candidate-trial/0.1',kind='InlineFormulaCandidateTrial',revision=1,
        book_id=observations['book_id'],scope_id=observations['scope_id'],input_refs=[ref(observations)],producer=producer,payload=payload)
    return {**body,'artifact_id':'inline-formula-candidates-'+digest(body)[:24],'content_hash':digest(payload)}
