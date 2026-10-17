"""Replay two exact frozen URL inputs and three portable masking variants."""
import argparse
import hashlib
import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/"src"))
import annotation.contracts as contracts
import annotation.source.static.importer as importer
from fixtures import reconstruct

spec = importlib.util.spec_from_file_location("r2_cases_for_r3",ROOT/"examples/a01/R2/cases.py")
cases = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cases)


def inspect(path):
    public = contracts.load_bundle(path,verify_assets=True)
    raw = cases.read(path.parent/"history/00-independent-source-page14.json")["data"]["pages"][0]["image"]
    try:
        importer.load_static_bundle(path,expected_book_id="46007447")
        actual = dict(result="ACCEPT")
    except Exception as error:
        actual = dict(result="REJECT",exception=type(error).__name__,code=getattr(error,"code",None),
                      location=getattr(error,"location",None),message=str(error))
    return dict(public_assets="ACCEPT",source_content_hash=public.artifacts[0].content_hash,url=raw,actual_path=urlsplit(raw).path,
                expected="reject unsupported query/fragment; actual path alone supplies identity",actual=actual,
                matches_expectation=actual.get("exception") == "StaticSourceError" and bool(actual.get("code")) and bool(actual.get("location")))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination",type=Path)
    args = parser.parse_args()
    out = args.destination.resolve(); out.mkdir(parents=True,exist_ok=False)
    rows = []
    with tempfile.TemporaryDirectory(prefix="a01 R3 URL probes ") as work:
        work = Path(work)
        for name,path in reconstruct(ROOT,"URL-official",work/"official").items():
            rows.append(dict(id=name,mode="exact fixed fixture reconstructed",**inspect(path)))
        prefix = "https://archive.example.invalid"
        correct = "/upload_images/46007447/46007447_page_13.jpg"
        for name,url in (
            ("U23",prefix+"/upload_images/46006966/46006966_page_13.jpg?echo="+correct),
            ("U24",prefix+"/upload_images/46007447/46007447_page_172.jpg#"+correct),
            ("U25",prefix+"/upload_images/46007447/46007447_page_172.jpg?echo="+correct),
        ):
            package = cases.Package(ROOT/"examples/a01/R2/bundles/46007447",work/name)
            package.page_url(lambda p:p.update(image=url))
            path = package.seal()
            rows.append(dict(id=name,mode="portable literal masking variant",**inspect(path)))
    result = dict(task="A01-R3",status="REVIEW",command=sys.argv,cwd=str(Path.cwd()),rows=rows,
                  passed=sum(r["matches_expectation"] for r in rows),failed=sum(not r["matches_expectation"] for r in rows),
                  modules={m.__name__:dict(path=m.__file__,sha256=hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest()) for m in (contracts,importer)},
                  platform_network_browser_model_calls=0)
    (out/"results.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(dict(passed=result["passed"],failed=result["failed"],status="REVIEW")))
    return bool(result["failed"])


if __name__ == "__main__":
    raise SystemExit(main())
