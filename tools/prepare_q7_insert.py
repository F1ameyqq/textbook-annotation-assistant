"""Build an immutable Q7 insertion plan from actual local evidence; no network."""
import argparse
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('baseline', 'candidate', 'crop-proof', 'visual-review', 'out'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
    from annotation.runtime.usense_live.core import parse, sha
    from annotation.runtime.usense_live.insertion_writer import full_endpoints
    from annotation.runtime.usense_live.q7_insert_candidate import materialize, DIRECTORY
    from annotation.runtime.usense_live.insertion import make_insert_plan, validate_insert_plan
    root = Path(args.baseline).resolve()
    before = {name: parse((root / (name + '.json')).read_bytes()) for name in full_endpoints()}
    ready = materialize(args.candidate, args.crop_proof, args.visual_review, before)
    plan = make_insert_plan(before, insert_after=7, parent_directory_id=DIRECTORY,
        payload_candidate=ready['payload_candidate'], approved_new_content=ready['approved_new_content'])
    validate_insert_plan(plan)
    target = Path(args.out).resolve()
    raw = json.dumps(plan, ensure_ascii=False, allow_nan=False, indent=2).encode('utf-8')
    with target.open('xb') as stream:
        stream.write(raw)
    print(json.dumps({'status': 'OFFLINE_INSERT_PLAN_VALIDATED', 'plan': str(target),
        'plan_file_sha256': sha(raw), 'plan_sha256': plan['plan_sha256'], 'ledger_key': plan['ledger_key'],
        'platform_requests': 0, 'future_post_count': 1, 'old_q7_deleted_or_updated': False}, ensure_ascii=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
