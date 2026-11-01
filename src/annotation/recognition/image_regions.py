"""Source-pixel-backed image regions, separate from diagnostic OCR labels.

Reviewed search regions are development input. Pixel checks can prove that a
candidate retains the frozen local ink witness; they cannot certify diagram
semantics, source acquisition completeness, or a whole book's business quality.
"""
import copy
import hashlib
import math
from pathlib import Path, PurePosixPath, PureWindowsPath

import cv2
import numpy as np
from PIL import Image

from .baseline import digest, valid_bbox, file_digest, code_digest

REVIEW_SCHEMA = "b-image-review-trial/0.1"
REGION_SCHEMA = "b-image-regions-trial/0.1"
CHECK_SCHEMA = "b-image-region-check-trial/0.1"


def ref(value):
    return {key: value[key] for key in ("artifact_id", "revision", "content_hash")}


def envelope(schema, kind, evidence, payload, inputs):
    return {"schema_version":schema,"kind":kind,"artifact_id":kind.lower()+"-"+digest([inputs,payload])[:24],
            "revision":1,"book_id":evidence["book_id"],"scope_id":evidence["scope_id"],
            "input_refs":inputs,"content_hash":digest(payload),"payload":payload,
            "producer":{"module":__name__,"version":"0.1.0","code_sha256":code_digest(Path(__file__))}}


def checked(value, schema):
    if value.get("schema_version") != schema or value.get("content_hash") != digest(value.get("payload")):
        raise ValueError("invalid or changed image-region artifact")


def contains(outer, inner):
    return outer[0] <= inner[0] < inner[2] <= outer[2] and outer[1] <= inner[1] < inner[3] <= outer[3]


def rgb_hash(image):
    return hashlib.sha256(image.convert("RGB").tobytes()).hexdigest()


def subimage(capture, descriptor, box):
    ox,oy=descriptor["source_bbox"][:2]
    if not contains(descriptor["source_bbox"],box):
        raise ValueError("region is outside its source capture")
    return capture.crop((box[0]-ox,box[1]-oy,box[2]-ox,box[3]-oy))


def load_capture(root, descriptor):
    relative=descriptor["path"]
    if (not isinstance(relative,str) or "\\" in relative or PurePosixPath(relative).is_absolute()
            or PureWindowsPath(relative).drive or ".." in PurePosixPath(relative).parts):
        raise ValueError("capture path must stay in fixture package")
    path=(Path(root)/relative).resolve()
    if not path.is_relative_to(Path(root).resolve()) or file_digest(path) != descriptor["sha256"]:
        raise ValueError("capture file hash mismatch")
    image=Image.open(path).convert("RGB")
    box=descriptor["source_bbox"]
    if image.size != (box[2]-box[0],box[3]-box[1]) or rgb_hash(image) != descriptor["rgb_sha256"]:
        raise ValueError("capture pixel identity or dimensions mismatch")
    return image


def ink_witness(capture, descriptor, box):
    """Retain connected ink, including labels that OCR did not recognize."""
    image=subimage(capture,descriptor,box)
    mask=(np.asarray(image.convert("L"))<160).astype(np.uint8)
    count,labels,stats,_=cv2.connectedComponentsWithStats(mask,8)
    keep=np.zeros(mask.shape,dtype=np.uint8)
    for index in range(1,count):
        if stats[index,cv2.CC_STAT_AREA] >= 1:
            keep[labels==index]=1
    ys,xs=np.nonzero(keep)
    if not len(xs):
        raise ValueError("empty image-region ink witness")
    return {"bbox":[int(xs.min()+box[0]),int(ys.min()+box[1]),int(xs.max()+box[0]+1),int(ys.max()+box[1]+1)],
            "ink_pixels":int(keep.sum()),"mask_sha256":hashlib.sha256(keep.tobytes()).hexdigest(),
            "roi_rgb_sha256":rgb_hash(image),"threshold":160,"minimum_component_pixels":1}


def _sources(evidence, review, root):
    checked(review,REVIEW_SCHEMA)
    if (evidence.get("content_hash") != digest(evidence.get("payload"))
            or (evidence["book_id"],evidence["scope_id"]) != (review["book_id"],review["scope_id"])):
        raise ValueError("image review book/evidence mismatch")
    if (review["payload"].get("reference_quality") != "MODEL_VISUAL_DEVELOPMENT_REVIEW"
            or review["payload"].get("business_acceptance") is not False):
        raise ValueError("image review is not unverified development evidence")
    pages={p["asset_id"]:p for p in evidence["payload"]["pages"]}
    captures={}
    for descriptor in review["payload"]["captures"]:
        asset=descriptor["asset_id"]
        if asset in captures or asset not in pages or descriptor["source_sha256"] != pages[asset]["source"]["sha256"]:
            raise ValueError("capture source identity mismatch")
        source=pages[asset]["source"]
        if (descriptor.get("source_size") != [source["width"],source["height"]]
                or not valid_bbox(descriptor["source_bbox"],source["width"],source["height"])):
            raise ValueError("capture geometry mismatch")
        captures[asset]=(descriptor,load_capture(root,descriptor))
    return pages,captures


def build_image_regions(evidence, review, capture_root):
    pages,captures=_sources(evidence,review,capture_root)
    lines={l["line_id"]:(p,l) for p in pages.values() for l in p["ocr_lines"]}
    regions=[]
    for spec in review["payload"]["regions"]:
        descriptor,image=captures[spec["asset_id"]]
        witness=ink_witness(image,descriptor,spec["search_bbox"])
        if witness != spec["ink_witness"]:
            raise ValueError("review ink witness changed")
        boxes=[witness["bbox"]]+[lines[r][1]["bbox"] for r in spec["required_line_ids"]]
        box=[math.floor(min(b[0] for b in boxes))-2,math.floor(min(b[1] for b in boxes))-2,
             math.ceil(max(b[2] for b in boxes))+2,math.ceil(max(b[3] for b in boxes))+2]
        if not contains(spec["search_bbox"],box):
            raise ValueError("review search region has insufficient padding")
        regions.append({"region_id":spec["region_id"],"asset_id":spec["asset_id"],"source_sha256":descriptor["source_sha256"],
                        "bbox":box,"content_type":"image","role":"answer","figure_number":spec["figure_number"],
                        "section_path":copy.deepcopy(spec["section_path"]),"printed_number":spec["printed_number"],
                        "diagnostic_ocr_refs":list(spec["required_line_ids"]),"caption_ref":spec["caption_ref"],
                        "source_capture_ref":descriptor["sha256"],"crop_rgb_sha256":rgb_hash(subimage(image,descriptor,box)),
                        "verification_status":"UNVERIFIED","semantic_status":"UNVERIFIED_SEMANTICS",
                        "reference_quality":"MODEL_VISUAL_DEVELOPMENT_REVIEW","business_acceptance":False})
    return envelope(REGION_SCHEMA,"ImageRegionsTrial",evidence,{"regions":regions,"review_ref":ref(review),"platform_actions":[]},[ref(evidence),ref(review)])


def validate_image_regions(evidence, artifact, review, capture_root):
    issues=[]
    def issue(code, region=None):issues.append({"code":code,"region_id":region})
    try:
        checked(artifact,REGION_SCHEMA)
        pages,captures=_sources(evidence,review,capture_root)
    except (ValueError,KeyError,OSError) as exc:
        return envelope(CHECK_SCHEMA,"ImageRegionCheckTrial",evidence,{"accepted":False,"decision":"HOLD","issues":[{"code":"IMAGE_REGION_SOURCE_INVALID","detail":str(exc)}],"validated_regions":[],"business_acceptance":False},[ref(evidence),ref(artifact),ref(review)])
    if artifact["input_refs"] != [ref(evidence),ref(review)] or artifact["payload"]["review_ref"] != ref(review):
        issue("IMAGE_REGION_STALE_BINDING")
    if (artifact.get("book_id"),artifact.get("scope_id")) != (evidence["book_id"],evidence["scope_id"]):
        issue("IMAGE_REGION_HEADER_MISMATCH")
    if artifact["payload"].get("platform_actions") != []:
        issue("IMAGE_REGION_ACTIONS_FORBIDDEN")
    specifications={s["region_id"]:s for s in review["payload"]["regions"]}
    regions=artifact["payload"]["regions"]
    if len(regions)!=len(specifications) or {r["region_id"] for r in regions} != set(specifications):
        issue("IMAGE_REGION_SET_INCOMPLETE")
    lines={l["line_id"]:(p,l) for p in pages.values() for l in p["ocr_lines"]}
    for region in regions:
        rid=region["region_id"]; spec=specifications.get(rid)
        if not spec:
            issue("IMAGE_REGION_UNKNOWN",rid);continue
        asset=spec["asset_id"]; descriptor,image=captures[asset]
        if any(region.get(k) != spec.get(k) for k in ("asset_id","figure_number","section_path","printed_number","caption_ref")):
            issue("IMAGE_REGION_OWNERSHIP_MISMATCH",rid)
        if (region.get("source_sha256")!=descriptor["source_sha256"] or region.get("source_capture_ref")!=descriptor["sha256"]
                or region.get("content_type")!="image" or region.get("role")!="answer"):
            issue("IMAGE_REGION_SOURCE_MISMATCH",rid)
        if (region.get("verification_status")!="UNVERIFIED" or region.get("semantic_status")!="UNVERIFIED_SEMANTICS"
                or region.get("reference_quality")!="MODEL_VISUAL_DEVELOPMENT_REVIEW" or region.get("business_acceptance") is not False
                or region.get("human_verified",False) is not False):
            issue("IMAGE_REGION_FALSE_VERIFICATION",rid)
        bbox=region.get("bbox")
        source=pages[asset]["source"]
        if (not valid_bbox(bbox,source["width"],source["height"]) or any(type(v) is not int for v in bbox)
                or not contains(spec["search_bbox"],bbox)):
            issue("IMAGE_REGION_OUTSIDE_REVIEW_SCOPE",rid);continue
        try:
            witness=ink_witness(image,descriptor,spec["search_bbox"])
        except ValueError:
            issue("IMAGE_REGION_INK_WITNESS_INVALID",rid);continue
        if witness!=spec["ink_witness"] or not contains(bbox,witness["bbox"]):
            issue("IMAGE_REGION_INK_TRUNCATED",rid)
        if region["crop_rgb_sha256"] != rgb_hash(subimage(image,descriptor,bbox)):
            issue("IMAGE_REGION_PIXEL_MISMATCH",rid)
        if region.get("diagnostic_ocr_refs") != spec["required_line_ids"]:
            issue("IMAGE_REGION_LABEL_SET_MISMATCH",rid)
        for line_id in spec["required_line_ids"]:
            page,line=lines.get(line_id,({},{}))
            if (page.get("asset_id")!=asset or not contains(bbox,line.get("bbox",[0,0,0,0]))
                    or (line.get("location") or {}).get("section_path") != spec["section_path"]):
                issue("IMAGE_REGION_LABEL_SOURCE_MISMATCH",rid)
        caption=lines.get(spec["caption_ref"],({},{}))[1]
        if caption.get("text","").replace(" ","") != "图"+spec["figure_number"]:
            issue("IMAGE_REGION_CAPTION_MISMATCH",rid)
    accepted=not issues
    return envelope(CHECK_SCHEMA,"ImageRegionCheckTrial",evidence,{"accepted":accepted,"decision":"HOLD","issues":issues,
                    "validated_regions":copy.deepcopy(regions) if accepted else [],"structural_status":"PIXEL_REGION_VALIDATED" if accepted else "REJECTED",
                    "semantic_status":"UNVERIFIED_SEMANTICS","business_acceptance":False},[ref(evidence),ref(artifact),ref(review)])
