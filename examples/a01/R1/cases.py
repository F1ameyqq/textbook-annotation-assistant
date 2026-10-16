"""Literal R01-R04 inputs from the formal review; independent of implementation."""
import copy
import hashlib
import json
import math
import shutil
from pathlib import Path


def capture(function):
    try:
        value = function()
        if hasattr(value,"bbox"):
            value = value.bbox
        elif hasattr(value,"artifacts"):
            value = {"accepted_book":value.artifacts[0].book_id}
        elif isinstance(value,tuple):
            value = list(value)
        return {"returned":value}
    except Exception as error:
        return {"exception":type(error).__name__,"code":getattr(error,"code",None),
                "location":getattr(error,"location",None),"message":str(error)}


def geometry_cases(geometry):
    image = lambda w,h:geometry.ImageBinding(asset_id="original",width=w,height=h,sha256="1"*64)
    box = lambda binding,values:geometry.OriginalBox(image=binding,bbox=[float(v) for v in values])
    rows = []
    for name,size,config,point,bbox,expected_point,expected_box,direction in (
        ("R01-forward",(5,1),dict(crop=(2,0,5,1),scale=(7/3,1)),(5,0),(2,0,5,1),[7,0],[0,0,7,1],"forward"),
        ("R01-inverse",(3,7),dict(crop=(0,1,3,7),scale=(1/3,1),rotation_degrees=90),(6,0),(0,0,6,1),[0,1],[0,1,3,7],"inverse"),
        ("R02-padding",(4,1),dict(crop=(1,0,4,1),scale=(2,1),padding=(1,0,0,0)),
         (math.nextafter(1.,0.),0),(math.nextafter(1.,0.),0,3,1),"BOUNDS","BOUNDS","inverse"),
    ):
        original = image(*size)
        transform = geometry.Transform(original,**config)
        processed = transform.processed_binding("processed","2"*64)
        for kind,coordinates,expected in (("point",point,expected_point),("box",bbox,expected_box)):
            def invoke(kind=kind,coordinates=coordinates,transform=transform,original=original,processed=processed,direction=direction):
                if kind == "point":
                    return transform.forward_point(coordinates,original) if direction == "forward" else transform.inverse_point(coordinates,processed,processed)
                return transform.forward_box(box(original,coordinates),processed) if direction == "forward" else transform.inverse_box(box(processed,coordinates),processed)
            actual = capture(invoke)
            passed = actual.get("code") == expected if isinstance(expected,str) else actual.get("returned") == expected
            rows.append(dict(id=name+"-"+kind,input=dict(image=original.model_dump(),config=config,coordinates=coordinates),
                             expected=expected,actual=actual,matches_expectation=passed))
    huge = 2**53+1
    def integer_case():
        transform = geometry.Transform(image(1,1),padding=(huge,0,0,0))
        return {"padding":list(transform.padding),"output_size":list(transform.output_size)}
    actual = capture(integer_case)
    passed = actual.get("exception") == "GeometryError" or actual.get("returned",{}).get("padding",[None])[0] == huge
    rows.append(dict(id="R03-integer",input=dict(image_size=[1,1],padding=[huge,0,0,0]),
                     expected="GeometryError or exact integer preservation",actual=actual,matches_expectation=passed))
    return rows


SOURCE_CASES = {
    "S12":("provenance.json",lambda value:value.update(origins=[])),
    "S13":("provenance.json",lambda value:value["origins"][0].update(manifest_sha256="0"*64)),
    "S15":("limitations.json",lambda value:value.update(missing_sources=[])),
    "S16":("input-integrity.json",lambda value:(value.update(unchanged=False),value["inputs"][0].update(after_sha256="0"*64))),
    "S19":("limitations.json",lambda value:value.update(scope_manifest_status="INDEPENDENT_COMPLETE")),
    "S20":("provenance.json",lambda value:value["reference_records"][0].update(reference_id="reference-unrelated")),
}


def mutated_source(base,destination,case,seal_artifact):
    """New valid C01 envelope, contradictory A01 records. Retains existing assets."""
    shutil.copytree(base,destination)
    path = Path(destination)/"exchange.json"
    read = lambda p:json.loads(p.read_text(encoding="utf-8"))
    write = lambda p,v:p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    data = read(path)
    def sidecar(relative,mutate):
        value = read(path.parent/relative)
        mutate(value)
        write(path.parent/relative,value)
        sha = hashlib.sha256((path.parent/relative).read_bytes()).hexdigest()
        for record in data["evidence"]+data["artifacts"][0]["payload"]["history"]:
            if record["resource"]["path"] == relative:
                record["resource"]["sha256"] = sha
    if case in SOURCE_CASES:
        sidecar(*SOURCE_CASES[case])
    elif case == "S14":
        sidecar("provenance.json",lambda value:value["mappings"][0].update(printed_page=999))
        mapping = data["artifacts"][0]["payload"]["external_page_mappings"][0]
        value = json.loads(mapping["external_page"])
        value["printed_page"] = 999
        mapping["external_page"] = json.dumps(value,sort_keys=True)
    elif case == "S17":
        relative = next(h["resource"]["path"] for h in data["artifacts"][0]["payload"]["history"] if "manual-annotations" in h["resource"]["path"])
        sidecar(relative,lambda value:value.update(bookId="46007447"))
    elif case == "S18":
        for history in data["artifacts"][0]["payload"]["history"]:
            history["quality"] = "REVIEWED"
    else:
        raise ValueError("unknown R04 case: "+case)
    data["artifacts"][0] = seal_artifact(data["artifacts"][0])
    write(path,data)
    return path


SOURCE_IDS = ("S12","S13","S14","S15","S16","S17","S18","S19","S20")
