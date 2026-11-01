"""Materialize a fixed single-page source draft without changing its base graph."""
from pathlib import Path
import argparse
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from annotation.recognition.question_content import apply_question_content,read_json
from annotation.recognition.question_content_quality import audit_question_content

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('source','evidence','graph','plan','out'):parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--plan-sha256',required=True,help='Externally retained exact plan file SHA; never computed from changed input to bypass rejection')
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    try:
        e,g=read_json(args.evidence),read_json(args.graph)
        app=apply_question_content(args.source,e,g,args.plan,expected_plan_sha256=args.plan_sha256,output_dir=args.out/'source-crops')
        check=audit_question_content(args.source,e,g,args.plan,app,expected_plan_sha256=args.plan_sha256,crop_dir=args.out/'source-crops')
        for name,value in [('application',app),('check',check)]:
            (args.out/(name+'.json')).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(dict(accepted=check['accepted'],decision='HOLD',application_ref={k:app[k]for k in('artifact_id','revision','content_hash')},check_hash=check['content_hash'])))
        return 0 if check['accepted'] else 2
    except (ValueError,KeyError,TypeError,OSError)as exc:
        print(json.dumps(dict(accepted=False,decision='HOLD',error=str(exc))));return 2

if __name__=='__main__':raise SystemExit(main())
