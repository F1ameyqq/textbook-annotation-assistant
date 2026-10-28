"""Project raw formula observations into unselected source-bound syntax trees."""
from __future__ import annotations
import copy
from datetime import datetime, timezone
from pathlib import Path
import re

from .baseline import code_digest, digest
from .formula_backend import CONFIG, SCHEMA, plan_formula_units, preprocess_formula, reference
from .formula_syntax import fraction_count, parse_formula_latex


def _check_producer(value):
    producer = value.get('producer', {})
    if (producer.get('module') != 'annotation.recognition.formula_backend'
            or producer.get('version') != '0.1.0'
            or producer.get('configuration') != CONFIG or producer.get('configuration_sha256') != digest(CONFIG)
            or not re.fullmatch('[0-9a-f]{64}', str(producer.get('code_sha256', '')))
            or value.get('artifact_id') != 'formula-observations-'+digest([value.get('input_refs'), producer, value.get('payload')])[:24]
            or value.get('kind') != 'FormulaObservationTrial' or type(value.get('revision')) is not int or value['revision'] != 1):
        raise ValueError('formula observation producer or deterministic identity changed')
    execution = producer.get('execution_kind')
    if execution == 'SYNTHETIC_TEST':
        if producer.get('backend') != 'injected-test-only' or any(k in producer for k in ('model_files', 'providers', 'backend_version')):
            raise ValueError('synthetic formula observation cannot impersonate a CPU model')
    elif execution == 'CPU_RAPID_LATEX_OCR':
        model_files = producer.get('model_files', [])
        deps = producer.get('dependencies', {})
        code = producer.get('backend_code', {})
        hashes = [m.get('sha256', '') for m in model_files]+list(code.values())+[producer.get('backend_configuration_sha256', '')]
        if (producer.get('backend') != 'rapid-latex-ocr' or producer.get('backend_version') != '0.0.9'
                or producer.get('providers') != [['CPUExecutionProvider']]*3
                or len(model_files) != 4 or {m.get('name') for m in model_files} != {'image_resizer.onnx', 'encoder.onnx', 'decoder.onnx', 'tokenizer.json'}
                or any(type(m.get('bytes')) is not int or m['bytes'] <= 0 for m in model_files)
                or set(code) != {'main.py', 'models.py', 'utils.py', 'utils_load.py'}
                or any(not re.fullmatch('[0-9a-f]{64}', str(h)) for h in hashes)
                or set(deps) != {'rapid-latex-ocr', 'onnxruntime', 'numpy', 'Pillow', 'tokenizers', 'opencv-python', 'PyYAML', 'chardet'}
                or any(not isinstance(v, str) or not v for v in deps.values())
                or deps['rapid-latex-ocr'] != '0.0.9' or producer.get('decode_tokens_capped') != CONFIG['maximum_decode_tokens']):
            raise ValueError('formula CPU observation lacks its locked backend/model receipt')
    else:
        raise ValueError('unknown formula observation execution kind')


def build_formula_candidates(layout, observations, crop_path):
    image, source, plan = plan_formula_units(layout, crop_path)
    p = observations.get('payload', {})
    if (observations.get('schema_version') != SCHEMA or observations.get('content_hash') != digest(p)
            or (observations.get('book_id'), observations.get('scope_id')) != (layout['book_id'], layout['scope_id'])
            or observations.get('input_refs') != [reference(layout)] or p.get('layout_ref') != reference(layout)
            or p.get('source') != source or p.get('decision') != 'HOLD' or p.get('complete') is not False
            or p.get('transcription_verified') is not False or p.get('business_acceptance') is not False
            or p.get('platform_actions') != [] or p.get('expected_text_consumed') is not False or p.get('graph_modified') is not False):
        raise ValueError('changed or incorrectly bound formula observations')
    if len(p.get('units', [])) != len(plan):
        raise ValueError('formula observations do not cover every layout fraction')
    _check_producer(observations)
    if observations.get('run_id') != layout.get('run_id'):
        raise ValueError('formula observation belongs to another run')
    units, issues = [], []
    for expected, raw_unit in zip(plan, p['units']):
        if {k: v for k, v in raw_unit.items() if k != 'variants'} != expected:
            raise ValueError('formula observation source or order changed')
        if len(raw_unit.get('variants', [])) != len(CONFIG['variants']):
            raise ValueError('formula observation preprocessing set changed')
        unit = copy.deepcopy(raw_unit)
        for definition, variant in zip(CONFIG['variants'], unit['variants']):
            metadata, _ = preprocess_formula(image, expected, definition)
            if any(variant.get(k) != value for k, value in metadata.items()):
                raise ValueError('formula observation preprocessing pixels changed')
            if variant.get('seed') != CONFIG['seed'] or variant.get('verification_status') != 'UNVERIFIED':
                raise ValueError('formula execution or verification metadata changed')
            if variant.get('recognition_error') is None and not isinstance(variant.get('raw_latex'), str):
                raise ValueError('successful formula observation must preserve raw text')
            if variant.get('recognition_error') is not None and (variant.get('raw_latex') is not None or variant.get('engine_elapsed_seconds') is not None):
                raise ValueError('failed formula observation cannot supply text')
            parsed = parse_formula_latex(variant['raw_latex'])
            shape = bool(parsed['supported'] and parsed['normalized_ast'].get('type') == 'fraction'
                         and fraction_count(parsed['ast']) == 1)
            variant.update(candidate_id='formula-candidate-'+digest([reference(observations), unit['unit_id'],
                variant['variant_id'], variant['raw_latex']])[:24], parse_result=parsed,
                fraction_node_count=fraction_count(parsed['ast']), source_fraction_shape_matches=shape,
                complete=False, transcription_verified=False)
            if not parsed['supported']:
                issues.append({'code': 'FORMULA_SYNTAX_UNSUPPORTED', 'unit_id': unit['unit_id'], 'variant_id': variant['variant_id']})
            elif not shape:
                issues.append({'code': 'FORMULA_SOURCE_FRACTION_SHAPE_MISMATCH', 'unit_id': unit['unit_id'], 'variant_id': variant['variant_id']})
        variants = unit['variants']
        agreement = (all(v['parse_result']['supported'] for v in variants)
                     and variants[0]['parse_result']['normalized_ast'] == variants[1]['parse_result']['normalized_ast'])
        unit.update(exact_ast_agreement=agreement, selected_candidate_refs=[], complete=False,
                    transcription_verified=False, status='FORMULA_CANDIDATES_UNVERIFIED')
        if not agreement:
            issues.append({'code': 'FORMULA_VARIANT_DISAGREEMENT_OR_UNPARSED', 'unit_id': unit['unit_id']})
        units.append(unit)
    payload = {'layout_ref': reference(layout), 'observation_ref': reference(observations), 'source': source,
               'units': units, 'reading_groups': copy.deepcopy(layout['payload']['reading_groups']),
               'source_layout_issues': copy.deepcopy(layout['payload']['issues']), 'issues': issues,
               'decision': 'HOLD', 'complete': False, 'transcription_verified': False,
               'business_acceptance': False, 'graph_modified': False, 'platform_actions': [],
               'expected_text_consumed': False, 'entire_answer_reconstructed': False}
    producer = {'module': __name__, 'version': '0.1.0', 'code_sha256': code_digest(Path(__file__)),
                'syntax_code_sha256': code_digest(Path(__file__).with_name('formula_syntax.py')),
                'execution_kind': observations['producer']['execution_kind']}
    inputs = [reference(layout), reference(observations)]
    return {'schema_version': 'b-formula-candidate-trial/0.1', 'kind': 'FormulaCandidateTrial',
            'artifact_id': 'formula-candidates-'+digest([inputs, producer, payload])[:24], 'revision': 1,
            'book_id': layout['book_id'], 'scope_id': layout['scope_id'], 'run_id': layout.get('run_id'),
            'input_refs': inputs, 'producer': producer, 'created_at': datetime.now(timezone.utc).isoformat(),
            'payload': payload, 'content_hash': digest(payload)}
