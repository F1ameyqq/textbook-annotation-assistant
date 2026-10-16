"""Independent decode, provenance inventory, preservation and relocation checks."""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent / "inventory-relocation" / "run-02"
STAGE = ROOT / ".local/stages/A01-review/a8d5e96d128e10d341de935d4856682e50df79d9"
SNAPSHOT = STAGE / "snapshot-verified"
sys.path.insert(0, str(SNAPSHOT / "src"))
from PIL import Image
import annotation.contracts as contracts
from annotation.source.static import load_static_bundle


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def files(folder):
    return {p.relative_to(folder).as_posix():sha(p) for p in folder.rglob("*") if p.is_file()}


def image_info(relative):
    path = SNAPSHOT / relative
    with Image.open(path) as image:
        image.load()
        return {"path":relative,"sha256":sha(path),"width":image.width,"height":image.height,
                "format":image.format}


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    work = STAGE / "root inventory relocation 02"
    work.mkdir(exist_ok=False)
    cwd = work / "unrelated cwd"
    cwd.mkdir()
    temp = work / "temporary files"
    temp.mkdir()
    records, assertions = [], []
    def check(name, value, expected):
        assertions.append({"name":name,"actual":value,"expected":expected,"pass":value == expected})
    original_inventory = read(ROOT / "docs/evidence/A01/review/input-inventory-before.json")["records"]
    check("27 preparation inputs unchanged in main and frozen blob",
          all(sha(ROOT/r["path"]) == r["sha256"] == sha(SNAPSHOT/r["path"]) for r in original_inventory),True)
    old_archive = [image_info("技术证据/只读样本-46006966/viewer-page-{:04d}.jpg".format(n)) for n in (8,9,10,234)]
    old_raw = [image_info("data/raw/images/46006966_page_{}.jpg".format(n)) for n in (7,8,9,10,233,234)]
    new_review = [image_info("docs/evidence/A05/review/independent-original-{}.jpg".format(role)) for role in ("question","answer")]
    new_execution = [image_info("docs/evidence/A05/execution/source-viewer{}.jpg".format(n)) for n in (14,173)]
    check("old 4 plus 6 sources deduplicate to 6",len({r["sha256"] for r in old_archive+old_raw}),6)
    check("new review and execution copies deduplicate to 2",len({r["sha256"] for r in new_review+new_execution}),2)
    check("old archive and raw dimensions and bytes",[(r["sha256"],r["width"],r["height"]) for r in old_archive],
          [(r["sha256"],r["width"],r["height"]) for r in [old_raw[i] for i in (0,1,2,4)]])
    check("new review and execution dimensions and bytes",[(r["sha256"],r["width"],r["height"]) for r in new_review],
          [(r["sha256"],r["width"],r["height"]) for r in new_execution])
    old_listing=read(SNAPSHOT / "技术证据/只读样本-46006966/source-images-complete.json")
    new_listing=read(SNAPSHOT / "docs/evidence/A05/review/independent-originals.json")
    check("old archived page mapping",sorted((r["viewerPage"],r["sourceImageIndex"]) for r in old_listing),[(8,7),(9,8),(10,9),(234,233)])
    check("new archived page mapping",sorted((r["viewer_page"],r["source_index"]) for r in new_listing),[(14,13),(173,172)])
    check("old metadata count",read(SNAPSHOT / "技术证据/只读样本-46006966/book-info-readonly.json")["book"]["page_count"],250)
    check("new metadata count",read(SNAPSHOT / "docs/evidence/A05/execution/source-metadata.json")["data"]["total_pages"],214)
    expected_mapping={"46006966":{7:8,8:9,9:10,10:None,233:234,234:None},"46007447":{13:14,172:173}}
    env=dict(os.environ,PYTHONPATH=str(SNAPSHOT / "src"),PYTHONDONTWRITEBYTECODE="1",TMP=str(temp),TEMP=str(temp),TMPDIR=str(temp))
    for book, originals, count, meta, origin_count in (("46006966",old_raw,6,250,10),("46007447",new_review,2,214,4)):
        folder=SNAPSHOT / "examples/a01/bundles" / book
        original_hashes=files(folder)
        bundle=load_static_bundle(folder / "exchange.json",expected_book_id=book)
        source=bundle.artifacts[0]
        provenance=read(folder / "provenance.json")
        limits=read(folder / "limitations.json")
        check(book+" assets",len(source.payload.assets),count)
        check(book+" original byte sets",sorted(a.sha256 for a in source.payload.assets),sorted(r["sha256"] for r in originals))
        check(book+" metadata total",source.payload.metadata_page_count,meta)
        check(book+" declared mapping",{m["source_index"]:m["viewer_page"] for m in provenance["mappings"]},expected_mapping[book])
        check(book+" origins",len(provenance["origins"]),origin_count)
        check(book+" printed page remains unknown",all(m["printed_page"] is None for m in provenance["mappings"]),True)
        check(book+" missing outside selected",len(provenance["outside_selected_scope_unacquired_indices"]),meta-count)
        check(book+" reference completeness ineligible",[limits["coverage_eligible"],limits["independent_denominator_status"],limits["scope_manifest_status"]],[False,"UNKNOWN","REFERENCE_ONLY"])
        check(book+" no PlatformSnapshot",[a.kind for a in bundle.artifacts],["SourceBundle"])
        check(book+" history stays UNVERIFIED",all(h.quality == "UNVERIFIED" for h in source.payload.history),True)
        histories=[]
        for h in source.payload.history:
            if h.reason.startswith("Byte-preserved archived reference: "):
                relative=h.reason.split("Byte-preserved archived reference: ",1)[1].split(";",1)[0]
                equal=(folder / h.resource.path).read_bytes() == (SNAPSHOT / relative).read_bytes()
                histories.append({"original":relative,"resource":h.resource.path,"sha256":sha(folder/h.resource.path),"bytes_equal":equal})
                check(book+" history "+relative,equal,True)
        if book == "46006966":
            check("old missing original JSON count",sum(m["missing_original_json"] for m in limits["missing_sources"]),4)
            check("old unavailable original-location count",len(limits["missing_sources"]),5)
            check("old historical x2 unmodified",limits["historical_box_issues"][0]["bbox"][2],1181.0944752623527)
            check("old export row count",len((folder/"history/02-paper-questions-original.txt").read_bytes().splitlines()),14)
        for a in source.payload.assets:
            with Image.open(folder/a.path) as image:
                image.load()
                check(book+" asset decode "+a.asset_id,[image.width,image.height],[a.width,a.height])
        resource_paths=[a.path for a in source.payload.assets]+[e.resource.path for e in bundle.evidence]+[h.resource.path for h in source.payload.history]
        check(book+" all executable refs bounded and present",all((folder/p).is_file() and (folder/p).resolve().is_relative_to(folder.resolve()) for p in resource_paths),True)
        # A private path in a source sidecar would be a portability leak; archived
        # HTTPS source strings in history are evidence text, never fetched here.
        personal_leaks=[]
        for p in folder.rglob("*.json"):
            if re.search(r"(?:(?<![A-Za-z])[A-Za-z]:[\\/]|\\\\Users\\|/Users/)",p.read_text(encoding="utf-8-sig")):
                personal_leaks.append(p.relative_to(folder).as_posix())
        check(book+" no local absolute path in output JSON",personal_leaks,[])
        copy=work/("copied portable book "+book)
        shutil.copytree(folder,copy)
        check(book+" relocation preserves complete package bytes",files(copy),original_hashes)
        command=[sys.executable,"-B",str(SNAPSHOT / "examples/a01/consume.py"),str(copy/"exchange.json"),"--book-id",book]
        proc=subprocess.run(command,cwd=cwd,env=env,capture_output=True)
        (OUT/(book+"-relocated.stdout.txt")).write_bytes(proc.stdout)
        (OUT/(book+"-relocated.stderr.txt")).write_bytes(proc.stderr)
        check(book+" relocated consumer exit",proc.returncode,0)
        summary=json.loads(proc.stdout)
        check(book+" consumer explicitly ineligible",summary["coverage_eligible"],False)
        check(book+" source outputs unchanged after read/relocation",files(folder),original_hashes)
        records.append({"book":book,"source_hash":source.content_hash,"original_images":originals,"histories":histories,
                        "package_files":original_hashes,"command":command,"cwd":str(cwd),"exit_code":proc.returncode,
                        "summary":summary,"limitations":limits,"observation":provenance["observation"]})
    result={"snapshot":str(SNAPSHOT),"actual_contract_import":contracts.__file__,"checks":assertions,"books":records,
            "images":{"old_archive":old_archive,"old_raw":old_raw,"new_review":new_review,"new_execution":new_execution},
            "passed":sum(c["pass"] for c in assertions),"failed":sum(not c["pass"] for c in assertions)}
    (OUT/"results.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"passed":result["passed"],"failed":result["failed"],"actual_contract_import":contracts.__file__}))
    raise SystemExit(bool(result["failed"]))


if __name__ == "__main__":
    main()
