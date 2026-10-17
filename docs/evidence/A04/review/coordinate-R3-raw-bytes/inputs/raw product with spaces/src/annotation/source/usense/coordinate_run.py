"""Coordinate-R1 live entry; same bounded read-only collector and lifecycle."""
import argparse
import json
from pathlib import Path

from annotation.delivery.usense_readonly.coordinates import DEPENDENCY_COMMIT
from .collector import collect_live,save_json
from .cli import build_exchange


def main(argv=None):
    p=argparse.ArgumentParser(description='A04 coordinate-R1 bounded read-only verification')
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--login-root',type=Path,required=True)
    p.add_argument('--coordination-state',type=Path,required=True)
    p.add_argument('--references',type=Path,required=True)
    p.add_argument('--ignore-https-errors',action='store_true')
    args=p.parse_args(argv)
    try:
        state=json.loads(args.coordination_state.read_text(encoding='utf-8-sig'))
        session=state.get('platform_session',{})
        if (session.get('book_id')!='46007447' or session.get('reservation_task')!='A04'
                or session.get('reservation_stage') not in ('coordinate-R1-execution','coordinate-R1-review')):
            raise ValueError('reservation')
        resume=state.get('tasks',{}).get('A04',{}).get('coordinate_resume',{})
        if resume.get('dependency_commit')!=DEPENDENCY_COMMIT:
            raise ValueError('dependency')
        refs=json.loads(args.references.read_text(encoding='utf-8'))
        if refs.get('book_id')!='46007447' or set(refs.get('pages',{}))!={'14','173'}:
            raise ValueError('reference scope')
        capture=collect_live(args.output,args.login_root,ignore_https_errors=args.ignore_https_errors,coordinate_refs=refs)
        build_exchange(capture,args.output)
        save_json(args.output/'evidence/coordinate-result.json',{'geometry_status':'OBSERVED_REFERENCE_CHECKED',
            'dependency_commit':DEPENDENCY_COMMIT,'acceptance':'NOT_ASSERTED',
            'reference_pages':[14,173],'acquired_pages':[14,15,173],'clean_install':'NOT_TESTED_D01_SEPARATE'})
        print('A04_COORDINATE_CAPTURED; ACCEPTANCE_NOT_ASSERTED')
        return 0
    except Exception as error:
        code=getattr(error,'code','COORDINATE_RUN_FAILED')
        if not isinstance(code,str) or len(code)>64 or not code.replace('_','').isalnum():
            code='COORDINATE_RUN_FAILED'
        print('A04_FAILED:'+code)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
