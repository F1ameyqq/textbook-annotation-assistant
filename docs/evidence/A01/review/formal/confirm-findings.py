"""Primary reviewer separately confirms the smallest adversarial findings."""
import hashlib
import json
import math
import shutil
import sys
from pathlib import Path

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[5]
OUT=Path(__file__).resolve().parent / "primary-confirmation"
STAGE=ROOT / ".local/stages/A01-review/a8d5e96d128e10d341de935d4856682e50df79d9"
SNAPSHOT=STAGE / "snapshot-verified"
sys.path.insert(0,str(SNAPSHOT / "src"))
import annotation.geometry as geometry
import annotation.source.static.importer as importer
from annotation.contracts import load_bundle, seal_artifact
from annotation.geometry import ImageBinding, OriginalBox, Transform


def capture(fn):
    try:
        result=fn()
        return {"returned":result.model_dump(mode="json") if hasattr(result,"model_dump") else result}
    except Exception as error:
        return {"exception":type(error).__name__,"code":getattr(error,"code",None),"message":str(error)}


def main():
    OUT.mkdir(exist_ok=False)
    work=STAGE / "primary minimal counterexamples"
    work.mkdir(exist_ok=False)
    records=[]
    def image(width,height):
        return ImageBinding(asset_id="original",width=width,height=height,sha256="1"*64)
    def observe(case, inputs, expected, fn):
        result=capture(fn)
        records.append({"id":case,"input":inputs,"expected":expected,"actual":result})
        return result
    original=image(5,1)
    t=Transform(original,crop=(2,0,5,1),scale=(7/3,1))
    processed=t.processed_binding("processed","2"*64)
    observe("F01-point",{"image":original.model_dump(),"crop":t.crop,"scale":t.scale,"point":[5,0]},[7,0],lambda:t.forward_point((5,0),original))
    observe("F01-box",{"bbox":[2,0,5,1]},[0,0,7,1],lambda:t.forward_box(OriginalBox(image=original,bbox=[2,0,5,1]),processed))
    original=image(3,7)
    t=Transform(original,crop=(0,1,3,7),scale=(1/3,1),rotation_degrees=90)
    processed=t.processed_binding("processed","2"*64)
    observe("F02-point",{"image":original.model_dump(),"crop":t.crop,"scale":t.scale,"rotation":90,"point":[6,0]},[0,1],lambda:t.inverse_point((6,0),processed,processed))
    observe("F02-box",{"bbox":[0,0,6,1]},[0,1,3,7],lambda:t.inverse_box(OriginalBox(image=processed,bbox=[0,0,6,1]),processed))
    original=image(4,1)
    t=Transform(original,crop=(1,0,4,1),scale=(2,1),padding=(1,0,0,0))
    processed=t.processed_binding("processed","2"*64)
    outside=math.nextafter(1.0,0.0)
    observe("F03-point",{"image":original.model_dump(),"crop":t.crop,"scale":t.scale,"padding":t.padding,"point":[outside,0],"strictly_left_of_content":outside<1},"GeometryError/BOUNDS",lambda:t.inverse_point((outside,0),processed,processed))
    observe("F03-box",{"bbox":[outside,0,3,1]},"GeometryError/BOUNDS",lambda:t.inverse_box(OriginalBox(image=processed,bbox=[outside,0,3,1]),processed))
    t=Transform(image(1,1),padding=(2**53+1,0,0,0))
    observe("F04-integer",{"padding":[2**53+1,0,0,0]},"reject unrepresentable value or preserve exact integer",lambda:{"padding":t.padding,"output_size":t.output_size})
    for case, mutate, expected in (
        ("S-origins-empty",lambda p:p.update(origins=[]),"reject source-chain inventory removed"),
        ("S-origin-manifest-digest-conflict",lambda p:p["origins"][0].update(manifest_sha256="0"*64),"reject origin digest inconsistent with same path in original_manifests"),
    ):
        folder=work / case
        shutil.copytree(SNAPSHOT / "examples/a01/bundles/46006966",folder)
        path=folder / "exchange.json"
        data=json.loads(path.read_text(encoding="utf-8"))
        prov=json.loads((folder/"provenance.json").read_text(encoding="utf-8"))
        mutate(prov)
        (folder/"provenance.json").write_text(json.dumps(prov,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        digest=hashlib.sha256((folder/"provenance.json").read_bytes()).hexdigest()
        for evidence in data["evidence"]:
            if evidence["resource"]["path"] == "provenance.json":
                evidence["resource"]["sha256"]=digest
        for history in data["artifacts"][0]["payload"]["history"]:
            if history["resource"]["path"] == "provenance.json":
                history["resource"]["sha256"]=digest
        data["artifacts"][0]=seal_artifact(data["artifacts"][0])
        path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        observe(case,{"exchange":str(path),"sidecar_mutation":case,"same_manifest_digest":prov["original_manifests"][0]["sha256"]},expected,
                lambda path=path:{"book":importer.load_static_bundle(path,expected_book_id="46006966").artifacts[0].book_id,"accepted":True})
        # Retain a compact complete portable failed input, not only a text mutation.
        shutil.copytree(folder,OUT / case)
    result={"target_commit":"a8d5e96d128e10d341de935d4856682e50df79d9",
            "modules":{"geometry":geometry.__file__,"importer":importer.__file__},"records":records}
    (OUT/"results.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"confirmed_geometry_cases":7,"confirmed_source_cases":2,"target_commit":result["target_commit"]}))


if __name__ == "__main__":
    main()
