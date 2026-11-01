"""Reuse the existing geometry-only layout baseline; never load an OCR model."""
import hashlib
import io
from pathlib import Path
from PIL import Image
import numpy as np
from annotation.recognition.baseline import legacy_backend, code_digest, LEGACY_PATH


def detect(raw, source_sha):
    backend = legacy_backend()
    cfg = dict(backend.CFG)
    gray = np.asarray(Image.open(io.BytesIO(raw)).convert('L'))
    mask = gray < cfg['thresh']
    height, width = mask.shape
    subpages, _ = backend.split_subpages(mask, cfg)
    columns = []
    for subpage in subpages:
        left, right = int(subpage['x1']), int(subpage['x2'])
        # The original baseline only subdivides very wide scans. A portrait
        # textbook may also have a long blank gutter; reuse its guarded finder.
        cut = backend.best_internal_split_column(mask, left, right, cfg)
        if cut is not None and left+(right-left)*.3 <= cut <= left+(right-left)*.7:
            columns.extend([(left, cut), (cut, right)])
        else:
            columns.append((left, right))
    boxes, seen = [], set()
    for left, right in columns:
        lines = backend.detect_lines(mask, left, right, 0, height, cfg)
        groups, _ = backend.group_by_gaps(lines, cfg)
        chunks = []
        for group in groups:
            chunk = []
            for line in group:
                if chunk and line['bbox'][3]-chunk[0]['bbox'][1] > max(48, height*.12):
                    chunks.append(chunk)
                    chunk = []
                chunk.append(line)
            if chunk:
                chunks.append(chunk)
        for group in chunks:
            bbox = backend.union_bbox([line['bbox'] for line in group])
            bbox = [max(0, bbox[0]), max(0, bbox[1]), min(width, bbox[2]), min(height, bbox[3])]
            key = tuple(bbox)
            if key in seen or bbox[2]-bbox[0] < 2 or bbox[3]-bbox[1] < 2:
                continue
            seen.add(key)
            identity = hashlib.sha256((source_sha+repr(key)).encode()).hexdigest()[:24]
            boxes.append(dict(box_id='auto-'+identity, bbox=bbox, kind='candidate',
                              origin='AUTO_GEOMETRY', status='DRAFT'))
    boxes.sort(key=lambda b: (b['bbox'][1], b['bbox'][0], b['box_id']))
    return boxes, dict(method='EXISTING_PROJECTION_CONNECTED_COMPONENTS_GAP_GROUPING',
                      backend_sha256=code_digest(LEGACY_PATH), wrapper_sha256=code_digest(Path(__file__)),
                      columns=columns, maximum_group_height_ratio=.12, ocr_enabled=False,
                      can_identify_complete_questions=False)
