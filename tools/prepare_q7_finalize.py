"""Offline Q7 phase-2 plan from source evidence and four real predecessor refs.

The tool consumes existing acceptance/resolution records. It neither creates an
outer acceptance nor changes a prior UNKNOWN result. No browser/network is used.
"""
import argparse
import json
import os
from pathlib import Path
import re
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('baseline', 'candidate', 'crop-proof', 'visual-review', 'predecessor-refs', 'out'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args(argv)
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
    from annotation.runtime.usense_live.core import parse, require, sha
    from annotation.runtime.usense_live.finalize_files import materialize_main
    refs_raw = Path(args.predecessor_refs).read_bytes()
    refs = parse(refs_raw)
    require(isinstance(refs, dict) and set(refs) == {'plan', 'receipt', 'comparison', 'outer_acceptance'},
            'COMPLETE_FOUR_PREDECESSOR_REFS_REQUIRED')
    for role, ref in refs.items():
        require(isinstance(ref, dict) and set(ref) == {'path', 'sha256'} and
                isinstance(ref['path'], str) and Path(ref['path']).is_absolute() and
                isinstance(ref['sha256'], str) and re.fullmatch('[0-9a-f]{64}', ref['sha256']) is not None,
                'ABSOLUTE_HASHED_PREDECESSOR_REF_REQUIRED_' + role)
    plan = materialize_main(args.candidate, args.crop_proof, args.visual_review, args.baseline, refs)
    raw = json.dumps(plan, ensure_ascii=False, allow_nan=False, indent=2).encode('utf-8')
    out = Path(args.out).resolve()
    with out.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({'status': 'OFFLINE_FINALIZE_PLAN_MATERIALIZED', 'plan': str(out),
        'plan_file_sha256': sha(raw), 'plan_sha256': plan['plan_sha256'], 'ledger_key': plan['ledger_key'],
        'predecessor_refs_file_sha256': sha(refs_raw), 'platform_requests': 0,
        'outer_acceptance_created': False, 'prior_unknown_rewritten': False}, ensure_ascii=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
