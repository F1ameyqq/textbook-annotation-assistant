"""Read-only replay of frozen official inputs plus portable R2 mutations."""
import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/"src"))
from cases import PRIMARY, mutated
import annotation.contracts as contracts
import annotation.source.static.importer as importer
import annotation.source.static.consistency as consistency


def observe(path,book):
    public = contracts.load_bundle(path,verify_assets=True)
    try:
        value = importer.load_static_bundle(path,expected_book_id=book)
        actual = dict(result="ACCEPT",book_id=value.artifacts[0].book_id)
    except Exception as error:
        actual = dict(result="REJECT",exception=type(error).__name__,code=getattr(error,"code",None),
                      location=getattr(error,"location",None),message=str(error))
    return dict(public_resource_validation="ACCEPT",source_content_hash=public.artifacts[0].content_hash,
                expected="StaticSourceError with code and location",actual=actual,
                matches_expectation=actual.get("exception") == "StaticSourceError" and bool(actual.get("code")) and bool(actual.get("location")))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination",type=Path)
    parser.add_argument("--official-inputs",type=Path)
    args = parser.parse_args()
    out = args.destination.resolve()
    out.mkdir(parents=True,exist_ok=False)
    rows = []
    if args.official_inputs:
        for folder in sorted(args.official_inputs.glob("P*")):
            if not folder.is_dir():
                continue
            path = folder/"exchange.json"
            book = json.loads(path.read_text(encoding="utf-8"))["artifacts"][0]["book_id"]
            rows.append(dict(id=folder.name,mode="exact frozen read-only input",input_path=str(path),**observe(path,book)))
    with tempfile.TemporaryDirectory(prefix="a01 R2 probes ") as work:
        for case in PRIMARY:
            book = "46006966" if case in ("P01","N14") else "46007447"
            base = ROOT/"examples/a01/R1/bundles"/book
            path = mutated(base,Path(work)/case,case)
            observation = observe(path,book)
            changed = []
            for file in path.parent.rglob("*"):
                if file.is_file() and file.read_bytes() != (base/file.relative_to(path.parent)).read_bytes():
                    relative = file.relative_to(path.parent)
                    target = out/case/relative
                    target.parent.mkdir(parents=True,exist_ok=True)
                    target.write_bytes(file.read_bytes())
                    changed.append(dict(path=relative.as_posix(),sha256=hashlib.sha256(file.read_bytes()).hexdigest()))
            rows.append(dict(id=case,mode="portable sealed mutation",base="examples/a01/R1/bundles/"+book,
                             changed_files=changed,**observation))
    result = dict(task="A01-R2",status="REVIEW",command=sys.argv,cwd=str(Path.cwd()),rows=rows,
                  passed=sum(r["matches_expectation"] for r in rows),failed=sum(not r["matches_expectation"] for r in rows),
                  modules={m.__name__:dict(path=m.__file__,sha256=hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest())
                           for m in (importer,consistency,contracts)},network_browser_platform_model_calls=0)
    (out/"results.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(dict(passed=result["passed"],failed=result["failed"],status="REVIEW")))
    return bool(result["failed"])


if __name__ == "__main__":
    raise SystemExit(main())
