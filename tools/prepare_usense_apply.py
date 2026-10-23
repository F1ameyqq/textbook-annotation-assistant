"""Bind the observed preview, without sending apply or accessing a profile."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from annotation.runtime.usense_live import directory_apply as api
from annotation.runtime.usense_live.batch import file_ref,ref_bytes,read,write_new


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('move-draft','sha256','preview-request','preview-response','preview-execution','preview-network','preview-readback','out'):
        p.add_argument('--'+key,required=True)
    a=p.parse_args()
    try:
        from annotation.runtime.usense_live.update import loads
        obj=loads(ref_bytes({'path':str(Path(a.move_draft).resolve()),'sha256':a.sha256}))
        if obj.get('schema')=='b-usense-offline-structural-bundle/0.1':
            for ref in (*obj['raw_baseline_files'].values(),*obj['input_files'].values()):ref_bytes(ref)
            obj=obj['draft']
        refs={key:file_ref(getattr(a,'preview_'+key)) for key in ('request','response','execution','network','readback')}
        plan=api.make_apply_plan(obj,refs);write_new(a.out,plan)
        print(json.dumps({'status':'PREVIEW_BOUND_APPLY_PLAN_READY_REQUIRES_EXPLICIT_WRITER','plan':str(Path(a.out).resolve()),
          'sha256':file_ref(a.out)['sha256'],'platform_requests':0,'automatic_retry_allowed':False}))
        return 0
    except (ValueError,OSError,KeyError,TypeError) as e:
        print(json.dumps({'status':'HOLD_NO_RETRY','error':getattr(e,'code',type(e).__name__),'platform_requests':0}));return 2


if __name__=='__main__':raise SystemExit(main())
