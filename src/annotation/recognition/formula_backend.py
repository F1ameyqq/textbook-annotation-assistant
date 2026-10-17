"""Explicit local formula-model observations; no automatic model downloads.

The raw LaTeX is an unverified observation. This collector accepts source pixels
and layout only, never expected mathematical text or answers. Cached consumers
do not import a model runtime. Test recognizers are always labelled synthetic.
"""
from __future__ import annotations

import copy
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import math
from pathlib import Path
import time

import numpy as np
from PIL import Image, ImageEnhance

from .baseline import code_digest, digest, file_digest, valid_bbox

SCHEMA = 'b-formula-observation-trial/0.1'
CONFIG = {'padding_pixels': 2,
          'variants': [{'variant_id': 'scale3', 'scale': 3, 'contrast': 1.0},
                       {'variant_id': 'scale4-contrast15', 'scale': 4, 'contrast': 1.5}],
          'resize': 'PIL_LANCZOS', 'color': 'RGB', 'seed': 0,
          'maximum_decode_tokens': 128, 'temperature': .00001}
MODEL_NAMES = ('image_resizer.onnx', 'encoder.onnx', 'decoder.onnx', 'tokenizer.json')


def reference(value):
    return {k: value[k] for k in ('artifact_id', 'revision', 'content_hash')}


def pixel_digest(image):
    return hashlib.sha256(np.asarray(image, dtype=np.uint8).tobytes()).hexdigest()


def plan_formula_units(layout, crop_path):
    """Bound complete fraction crops, including two-pixel role context."""
    if (layout.get('schema_version') != 'b-math-layout-trial/0.1'
            or layout.get('content_hash') != digest(layout.get('payload'))):
        raise ValueError('invalid or changed source mathematical layout')
    p = layout['payload']
    crop_box = p['crop_bbox']
    if (any(type(x) is not int for x in crop_box)
            or not valid_bbox(crop_box, *p['source_size'])
            or file_digest(Path(crop_path)) != p['crop_sha256']):
        raise ValueError('source mathematical crop changed')
    image = Image.open(crop_path).convert('RGB')
    if image.size != (crop_box[2]-crop_box[0], crop_box[3]-crop_box[1]):
        raise ValueError('source mathematical crop dimensions changed')
    units, seen = [], set()
    for fraction in p['fraction_candidates']:
        fid = fraction['fraction_id']
        if not isinstance(fid, str) or not fid or fid in seen:
            raise ValueError('missing or repeated fraction identity')
        seen.add(fid)
        boxes = [fraction['bar_bbox'], fraction['numerator']['pixel_bbox'], fraction['denominator']['pixel_bbox']]
        for box in boxes:
            if (any(type(x) is not int for x in box) or not valid_bbox(box, *p['source_size'])
                    or not crop_box[0] <= box[0] < box[2] <= crop_box[2]
                    or not crop_box[1] <= box[1] < box[3] <= crop_box[3]):
                raise ValueError('fraction lies outside bound source crop')
        bar, numerator, denominator = boxes
        if (numerator[3] > bar[1]+1 or denominator[1] < bar[3]-1
                or any(min(role[2], bar[2])-max(role[0], bar[0]) <= 0 for role in (numerator, denominator))):
            raise ValueError('fraction role is on the wrong side of its source bar')
        pad = CONFIG['padding_pixels']
        box = [max(crop_box[0], min(b[0] for b in boxes)-pad),
               max(crop_box[1], min(b[1] for b in boxes)-pad),
               min(crop_box[2], max(b[2] for b in boxes)+pad),
               min(crop_box[3], max(b[3] for b in boxes)+pad)]
        local = [box[i]-crop_box[i % 2] for i in range(4)]
        tile = image.crop(local)
        units.append({'unit_id': 'formula-unit-'+digest([reference(layout), fid, box])[:24],
                      'fraction_id': fid, 'source_bbox': box, 'crop_local_bbox': local,
                      'bar_bbox': list(fraction['bar_bbox']),
                      'role_bboxes': {r: list(fraction[r]['pixel_bbox']) for r in ('numerator', 'denominator')},
                      'source_ocr_refs': {r: list(fraction[r]['ocr_refs']) for r in ('numerator', 'denominator')},
                      'crop_rgb_sha256': pixel_digest(tile), 'crop_size': list(tile.size)})
    source = {k: copy.deepcopy(p[k]) for k in ('asset_id', 'source_sha256', 'source_size', 'crop_bbox', 'crop_sha256')}
    source['base_crop_rgb_sha256'] = pixel_digest(image)
    return image, source, units


def preprocess_formula(image, unit, definition):
    tile = image.crop(unit['crop_local_bbox'])
    s = definition['scale']
    transformed = ImageEnhance.Contrast(tile.resize((tile.width*s, tile.height*s), Image.Resampling.LANCZOS)).enhance(definition['contrast'])
    return {'variant_id': definition['variant_id'], 'scale': s, 'contrast': definition['contrast'],
            'resize': CONFIG['resize'], 'color': CONFIG['color'], 'transformed_size': list(transformed.size),
            'transformed_rgb_sha256': pixel_digest(transformed),
            'transformed_to_source': [[1/s, 0, unit['source_bbox'][0]], [0, 1/s, unit['source_bbox'][1]], [0, 0, 1]]}, transformed


def _local_cpu_backend(model_dir):
    if model_dir is None:
        raise ValueError('explicit local formula model directory required')
    directory = Path(model_dir)
    paths = {name: directory/name for name in MODEL_NAMES}
    if any(not path.is_file() or not path.stat().st_size for path in paths.values()):
        raise ValueError('all three ONNX models and local tokenizer must exist before importing backend')
    # Providing every model path prevents the upstream package's download path.
    from rapid_latex_ocr import LaTeXOCR
    import rapid_latex_ocr
    version = importlib.metadata.version('rapid-latex-ocr')
    if version != '0.0.9':
        raise ValueError('formula adapter is locked to rapid-latex-ocr0.0.9')
    engine = LaTeXOCR(image_resizer_path=paths['image_resizer.onnx'], encoder_path=paths['encoder.onnx'],
                      decoder_path=paths['decoder.onnx'], tokenizer_json=paths['tokenizer.json'])
    engine.encoder_decoder.max_seq_len = CONFIG['maximum_decode_tokens']
    engine.encoder_decoder.decoder.max_seq_len = CONFIG['maximum_decode_tokens']
    engine.temperature = CONFIG['temperature']
    sessions = [engine.image_resizer.session, engine.encoder_decoder.encoder.session,
                engine.encoder_decoder.decoder.session.session]
    providers = [s.get_providers() for s in sessions]
    if any(p != ['CPUExecutionProvider'] for p in providers):
        raise ValueError('formula adapter requires CPU-only ONNX sessions')
    package = Path(rapid_latex_ocr.__file__).parent
    receipt = {'execution_kind': 'CPU_RAPID_LATEX_OCR', 'backend': 'rapid-latex-ocr', 'backend_version': version,
               'providers': providers,
               'dependencies': {name: importlib.metadata.version(name) for name in
                                ('rapid-latex-ocr', 'onnxruntime', 'numpy', 'Pillow', 'tokenizers', 'opencv-python', 'PyYAML', 'chardet')},
               'model_files': [{'name': n, 'bytes': p.stat().st_size, 'sha256': file_digest(p)} for n, p in paths.items()],
               'backend_code': {n: code_digest(package/n) for n in ('main.py', 'models.py', 'utils.py', 'utils_load.py')},
               'backend_configuration_sha256': file_digest(package/'config.yaml'),
               'decode_tokens_capped': CONFIG['maximum_decode_tokens']}
    return engine, receipt


def collect_formula_observations(layout, crop_path, *, model_dir=None, recognizer=None):
    """Read every complete fraction twice, preserving raw errors and hypotheses."""
    image, source, planned = plan_formula_units(layout, crop_path)
    if recognizer is None:
        engine, backend = _local_cpu_backend(model_dir)
    else:
        engine, backend = recognizer, {'execution_kind': 'SYNTHETIC_TEST', 'backend': 'injected-test-only'}
    producer = {'module': __name__, 'version': '0.1.0', 'code_sha256': code_digest(Path(__file__)),
                'configuration': copy.deepcopy(CONFIG), 'configuration_sha256': digest(CONFIG), **backend}
    units = []
    for plan in planned:
        unit = copy.deepcopy(plan)
        unit['variants'] = []
        for definition in CONFIG['variants']:
            metadata, transformed = preprocess_formula(image, unit, definition)
            started = time.perf_counter()
            state = np.random.get_state()
            raw, elapsed, error = None, None, None
            try:
                np.random.seed(CONFIG['seed'])
                # Upstream LoadImage accepts RGB ndarray and converts it itself.
                raw, elapsed = engine(np.asarray(transformed))
                if not isinstance(raw, str) or not isinstance(elapsed, (int, float, np.number)) or isinstance(elapsed, bool) or not math.isfinite(float(elapsed)) or elapsed < 0:
                    raise ValueError('formula backend must return raw text and finite elapsed seconds')
                elapsed = float(elapsed)
            except Exception as exc:
                raw, elapsed = None, None
                error = {'type': type(exc).__name__, 'status': 'RECOGNITION_FAILED'}
            finally:
                np.random.set_state(state)
            unit['variants'].append({**metadata, 'raw_latex': raw, 'engine_elapsed_seconds': elapsed,
                                     'wall_elapsed_seconds': time.perf_counter()-started,
                                     'recognition_error': error, 'seed': CONFIG['seed'],
                                     'verification_status': 'UNVERIFIED'})
        units.append(unit)
    payload = {'layout_ref': reference(layout), 'source': source, 'units': units,
               'decision': 'HOLD', 'complete': False, 'transcription_verified': False,
               'business_acceptance': False, 'platform_actions': [],
               'expected_text_consumed': False, 'graph_modified': False,
               'limitations': ['Raw formula-model output is not mathematical or source-content verification.',
                               'Fraction crops do not reconstruct the entire surrounding proof or answer.',
                               'A model may agree with itself and still omit or substitute a symbol.']}
    inputs = [reference(layout)]
    return {'schema_version': SCHEMA, 'kind': 'FormulaObservationTrial',
            'artifact_id': 'formula-observations-'+digest([inputs, producer, payload])[:24],
            'revision': 1, 'book_id': layout['book_id'], 'scope_id': layout['scope_id'],
            'run_id': layout.get('run_id'), 'input_refs': inputs, 'producer': producer,
            'created_at': datetime.now(timezone.utc).isoformat(), 'payload': payload, 'content_hash': digest(payload)}
