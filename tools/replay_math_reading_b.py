"""Replay source-bound mathematical role readings, or explicitly collect CPU OCR.

Default operation uses committed raw CPU receipts and source pixels. It does not
import an OCR runtime or access the network. Candidate transcription is always
unverified/HOLD and never changes a graph or website annotation.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
from annotation.recognition.math_reading import collect_math_roles, build_math_reading
from annotation.recognition.math_reading_quality import audit_math_reading
from replay_math_b import replay as replay_layout


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def run(fixture, *, role_evidence=None, recognize=False, probe='unit2-q16'):
    fixture = Path(fixture)
    layout, layout_check, crop = replay_layout(fixture, probe)
    if not layout_check['geometry_and_token_coverage_valid']:
        raise ValueError('source layout failed its geometry and input-token audit')
    if recognize and role_evidence is not None:
        raise ValueError('choose cached evidence or explicit CPU collection')
    evidence = (collect_math_roles(layout, crop) if recognize
                else read(role_evidence or fixture / 'math-role-evidence.json'))
    reading = build_math_reading(layout, evidence, crop)
    check = audit_math_reading(layout, evidence, reading, crop)
    summary = {
        'operation': 'LOCAL_MATH_ROLE_READING', 'decision': 'HOLD',
        'evidence_schema': evidence['schema_version'], 'reading_schema': reading['schema_version'],
        'independent_audit_accepted': check['payload']['accepted'],
        'layout_fractions': len(layout['payload']['fraction_candidates']),
        'source_roles': len(evidence['payload']['roles']),
        'recorded_cpu_passes': sum(len(r['variants']) for r in evidence['payload']['roles']),
        'new_cpu_collection': recognize,
        'new_ocr_calls': sum(len(r['variants']) for r in evidence['payload']['roles']) if recognize else 0,
        'previously_missing_roles': sum(f[r]['missing_ocr'] for f in layout['payload']['fraction_candidates']
                                        for r in ('numerator', 'denominator')),
        'roles_with_raised_pixel_risks': sum(bool(f[r]['pixel_risks']) for f in reading['payload']['fractions']
                                            for r in ('numerator', 'denominator')),
        'complete': False, 'formula_text_reconstructed': False,
        'transcription_verified': False, 'business_acceptance': False,
        'layout_or_graph_modified': False, 'platform_actions': 0, 'website_requests': 0,
        'independent_check_summary': check['payload'].get('summary', {}),
    }
    return {'math-layout.json': layout, 'math-layout-check.json': layout_check,
            'math-role-evidence.json': evidence, 'math-reading.json': reading,
            'math-reading-check.json': check, 'summary.json': summary}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', type=Path, default=ROOT / 'tests/fixtures/book46007447')
    parser.add_argument('--probe', default='unit2-q16')
    parser.add_argument('--role-evidence', type=Path, help='saved raw role evidence; defaults to fixture cache')
    parser.add_argument('--recognize', action='store_true', help='explicitly run local CPU OCR instead of replay')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error('--out must be a new directory')
    try:
        results = run(args.fixture, role_evidence=args.role_evidence,
                      recognize=args.recognize, probe=args.probe)
    except (ValueError, KeyError, OSError, StopIteration) as exc:
        parser.exit(1, f'Math role replay failed: {exc}\n')
    args.out.mkdir(parents=True)
    for name, value in results.items():
        (args.out / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    print(json.dumps(results['summary.json'], ensure_ascii=True))
    if not results['summary.json']['independent_audit_accepted']:
        parser.exit(1, 'Independent math reading audit rejected the output; inspect math-reading-check.json.\n')


if __name__ == '__main__':
    main()
