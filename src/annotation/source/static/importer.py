"""C01 consumer/producer. No network, browser, OCR or implicit external paths."""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from PIL import Image

from annotation.contracts import (SCHEMA_VERSION, SourceBundle, artifact_ref, load_bundle,
                                  seal_artifact, seal_policy, validate_bundle, write_bundle)
from annotation.contracts.models import Resource

VERSION = "a01-static-1-r3"
OLD = "技术证据/只读样本-46006966"
NEW = "docs/evidence/A05/review"
EXECUTION = "docs/evidence/A05/execution"


class StaticSourceError(ValueError):
    def __init__(self, code, location, message):
        self.code, self.location = code, location
        super().__init__("{}: [{}] {}".format(location, code, message))


def fail(code, location, message):
    raise StaticSourceError(code, location, message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(data):
    return (json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)+"\n").encode("utf-8")


def parse(data):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                fail("JSON", key, "duplicate key")
            result[key] = value
        return result
    return json.loads(data.decode("utf-8-sig"), object_pairs_hook=pairs,
                      parse_constant=lambda v: fail("JSON", v, "nonfinite number"))


def safe_path(root, relative):
    # Reuse C01 portable-path validation; also reject resolved symlink/junction escape.
    Resource(path=relative, sha256="0"*64, media_type="application/json")
    root = Path(root).resolve()
    target = root.joinpath(relative).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        fail("PATH_ESCAPE", relative, "resource leaves its root")
    return target


def decode_image(path):
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            image.load()  # Header-only validation is insufficient.
            if image.format != "JPEG":
                fail("IMAGE_FORMAT", path.name, "assigned originals must be JPEG")
            return image.size
    except (OSError, ValueError, Image.DecompressionBombError) as error:
        fail("IMAGE_DECODE", path.name, str(error))


class Inputs:
    def __init__(self, root):
        self.root, self.bytes = Path(root).resolve(), {}

    def read(self, relative):
        if relative not in self.bytes:
            path = safe_path(self.root, relative)
            if not path.is_file():
                fail("INPUT_MISSING", relative, "required archive input is absent")
            self.bytes[relative] = path.read_bytes()
        return self.bytes[relative]

    def json(self, relative):
        return parse(self.read(relative))

    def unchanged(self):
        for relative, data in self.bytes.items():
            if safe_path(self.root, relative).read_bytes() != data:
                fail("INPUT_CHANGED", relative, "input changed during import; output is not released")


def url_index(url, book, location):
    # URL is checked as archived text, never fetched.
    if not isinstance(url,str):
        fail("SOURCE_URL",location,"archived image URL must be an absolute HTTP(S) string")
    try:
        parsed = urlsplit(url)
        valid = parsed.scheme in ("http","https") and bool(parsed.netloc) and bool(parsed.hostname)
    except ValueError:
        valid = False
    if not valid:
        fail("SOURCE_URL",location,"archived image URL must be an absolute HTTP(S) string")
    if "?" in url or "#" in url:
        fail("SOURCE_URL_COMPONENT",location,"query and fragment components are outside the direct-image URL format")
    match = re.fullmatch(r"/upload_images/([0-9]+)/([0-9]+)_page_([0-9]+)\.jpg", parsed.path)
    if not match or match[1] != book or match[2] != book:
        fail("BOOK_CONFLICT", location, "archived image URL belongs to a different book or is malformed")
    return int(match[3])


def check_book(actual, expected, location):
    if str(actual) != expected:
        fail("BOOK_CONFLICT", location, "book identifier differs from requested archive")


def prepare(inputs, book):
    images, raw, manifests = [], [], []
    if book == "46006966":
        manifest_path = OLD+"/source-images-complete.json"
        listing = inputs.json(manifest_path)
        if {(r["viewerPage"],r["sourceImageIndex"]) for r in listing} != {(8,7),(9,8),(10,9),(234,233)} or len(listing) != 4:
            fail("MAPPING_CONFLICT", manifest_path, "assigned four-page evidence mapping differs")
        for row in listing:
            if url_index(row["url"],book,manifest_path) != row["sourceImageIndex"]:
                fail("MAPPING_CONFLICT", manifest_path, "URL source index conflicts")
            images.append(dict(path=OLD+"/viewer-page-{:04d}.jpg".format(row["viewerPage"]),
                               source_index=row["sourceImageIndex"], viewer_page=row["viewerPage"],
                               sha256=row["sha256"], width=row["width"], height=row["height"],
                               manifest=manifest_path))
        manifests.append(manifest_path)
        derived_path = "data/derived/manifest.json"
        derived = inputs.json(derived_path)
        check_book(derived["file_id"],book,derived_path)
        if {r["page_index"] for r in derived["images"]} != {7,8,9,10,233,234} or len(derived["images"]) != 6:
            fail("MAPPING_CONFLICT", derived_path, "assigned six source indices differ")
        for row in derived["images"]:
            index = row["page_index"]
            if url_index(row["url"],book,derived_path) != index:
                fail("MAPPING_CONFLICT", derived_path, "URL source index conflicts")
            images.append(dict(path="data/raw/images/{}_page_{}.jpg".format(book,index),
                               source_index=index, viewer_page=None, sha256=row["sha256"],
                               width=row["dims"]["width"],height=row["dims"]["height"],manifest=derived_path))
        manifests.append(derived_path)
        raw = [OLD+"/directory.json",OLD+"/manual-annotations.json",OLD+"/paper-questions-original.jsonl",
               OLD+"/book-info-readonly.json",OLD+"/session-receipt-20261015.json",
               "data/derived/CORRECTION-page-mapping.md"]
        directory = inputs.json(raw[0])
        annotations = inputs.json(raw[1])
        check_book(directory["bookId"],book,raw[0])
        check_book(annotations["bookId"],book,raw[1])
        book_info = inputs.json(raw[3])["book"]
        check_book(book_info["id"],book,raw[3])
        metadata_count = book_info["page_count"]
        observation = dict(date=inputs.json(raw[4])["date"],precision="DATE_ONLY",source=raw[4])
        references = inputs.read(raw[2]).splitlines()
        if len(references) != 14:
            fail("REFERENCE_COUNT", raw[2], "assigned historical export must have 14 lines")
        for row in references:
            parse(row)
        reference_origin = raw[2]
        reference_positions = list(range(1,15))
        workspace_path = "data/raw/annotations/workspace1.jpg"
        if digest(inputs.read(workspace_path)) != derived["provenance"][-1]["sha256"]:
            fail("RESOURCE_HASH",workspace_path,"local workspace screenshot differs from historical declaration")
        raw.append(workspace_path)
        missing = [dict(file=r["file"], declared_sha256=r["sha256"],
                        original_external_location="UNAVAILABLE_NOT_PORTABLE",original_in_repository=r["file"] == "workspace1.jpg",
                        available_local_copy=workspace_path if r["file"] == "workspace1.jpg" else None,
                        missing_original_json=r["file"].endswith(".json")) for r in derived["provenance"]]
        directory_data = directory["directory_data"]
        history_annotations = annotations["annotations"]
    elif book == "46007447":
        manifest_path = NEW+"/independent-originals.json"
        listing = inputs.json(manifest_path)
        if {(r["viewer_page"],r["source_index"]) for r in listing} != {(14,13),(173,172)} or len(listing) != 2:
            fail("MAPPING_CONFLICT", manifest_path, "assigned two-page evidence mapping differs")
        for row in listing:
            viewer, index = row["viewer_page"], row["source_index"]
            page_path = NEW+"/independent-source-page{}.json".format(viewer)
            page = inputs.json(page_path)["data"]
            check_book(page["file_id"],book,page_path)
            if len(page["pages"]) != 1 or page["pages"][0]["page_index"] != index:
                fail("MAPPING_CONFLICT", page_path, "response source index conflicts")
            if url_index(page["pages"][0]["image"],book,page_path) != index or url_index(row["source_url"],book,manifest_path) != index:
                fail("MAPPING_CONFLICT", page_path, "URL source index conflicts")
            role = "question" if viewer == 14 else "answer"
            if row["file"] != "independent-original-{}.jpg".format(role) or row["planned_source_index"] != index:
                fail("MAPPING_CONFLICT", manifest_path, "assigned original identity conflicts")
            image_path = NEW+"/"+row["file"]
            inputs.read(image_path)
            width,height = decode_image(safe_path(inputs.root,image_path))
            for path in (image_path,EXECUTION+"/source-viewer{}.jpg".format(viewer)):
                images.append(dict(path=path,source_index=index,viewer_page=viewer,sha256=row["sha256"],
                                   width=width,height=height,manifest=manifest_path))
            raw.append(page_path)
        manifests.append(manifest_path)
        directory_path = NEW+"/independent-response-0003.json"
        book_path = NEW+"/independent-book.json"
        metadata_path = EXECUTION+"/source-metadata.json"
        observation_path = NEW+"/manifest.json"
        network_path = NEW+"/independent-network.json"
        raw += [directory_path,book_path,metadata_path,observation_path]
        book_info = inputs.json(book_path)["data"]
        metadata = inputs.json(metadata_path)["data"]
        check_book(book_info["id"],book,book_path)
        check_book(metadata["file_id"],book,metadata_path)
        metadata_count = metadata["total_pages"]
        if metadata_count != book_info["page_count"]:
            fail("METADATA_CONFLICT", metadata_path, "page totals conflict")
        # The manifest generation time is a historical archive boundary, not a live observation.
        observation = dict(archive_created_at=inputs.json(observation_path)["created_at"],
                           precision="ARCHIVE_BOUNDARY",source=observation_path)
        network = inputs.json(network_path)
        observation["archived_response_observations"] = [
            dict(body_file=r["body_file"],observed_at=r["at"]) for r in network]
        observation["observation_index_source"] = dict(archive_path=network_path,sha256=digest(inputs.read(network_path)))
        observation["note"] = "Preserved historical response times; aliases without exact matching response retain archive-boundary time only"
        directory_data = inputs.json(directory_path)["data"]["directory_data"]
        reference_origin,reference_positions = directory_path,["1792148510557"]
        history_annotations,missing = [],[]
    else:
        fail("BOOK_UNSUPPORTED", "book_id", "only 46006966 and 46007447 are assigned")
    if metadata_count != {"46006966":250,"46007447":214}[book]:
        fail("METADATA_CONFLICT", "metadata_page_count", "assigned metadata total differs")
    for path in raw:
        inputs.read(path)
    return dict(images=images,raw=raw,manifests=manifests,metadata_count=metadata_count,
                observation=observation,directory_data=directory_data,missing=missing,
                reference_origin=reference_origin,reference_positions=reference_positions,
                annotations=history_annotations)


def directories(tree, book):
    root_id = "directory-book-"+book
    result = [dict(directory_id=root_id,parent_id=None,label="Archive book container (not a page-to-chapter assertion)")]
    question_nodes = []
    def walk(nodes,parent):
        for node in nodes:
            if node.get("isQuestion"):
                question_nodes.append(node)
                continue
            identity = "directory-"+book+"-"+digest(str(node["id"]).encode())[:24]
            result.append(dict(directory_id=identity,parent_id=parent,label=node["label"]))
            walk(node.get("children",[]),identity)
    walk(tree,root_id)
    return result,question_nodes


def put(folder, relative, data, media="application/json"):
    target = safe_path(folder,relative)
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open("xb") as handle:
        handle.write(data)
    return dict(path=relative,sha256=digest(data),media_type=media)


def import_book(repo_root, book_id, destination, revision=1, previous=None, created_at=None):
    """Import fixed archive scope; reject an existing output, even when bytes match.

    C01 SourceBundle roots cannot have input_refs. Predecessor identity is recorded
    in a hashed provenance resource; revisions remain independent portable roots.
    """
    book = str(book_id)
    destination = Path(destination).resolve()
    if destination.exists():
        fail("OUTPUT_EXISTS", "destination", "preserve existing products; choose a new directory")
    if isinstance(revision,bool) or not isinstance(revision,int) or revision < 1:
        fail("REVISION", "revision", "positive integer required")
    predecessor = None
    if previous is not None:
        older = load_static_bundle(previous,expected_book_id=book)
        source = older.artifacts[0]
        if revision != source.revision+1:
            fail("REVISION", "revision", "explicit predecessor requires next revision")
        predecessor = dict(artifact=artifact_ref(source),exchange_sha256=digest(Path(previous).read_bytes()),
                           note="C01 immutable source root; dependency retained as provenance, not input_refs")
    elif revision != 1:
        fail("REVISION", "revision", "revision after 1 requires an explicit predecessor")
    inputs = Inputs(repo_root)
    for protected in ("data", "技术证据", "docs/evidence/A05", ".local"):
        try:
            destination.relative_to(inputs.root/protected)
        except ValueError:
            continue
        fail("OUTPUT_LOCATION","destination","output must not be inside original/archive/credential directories")
    spec = prepare(inputs,book)
    dirs,nodes = directories(spec["directory_data"],book)
    if book == "46007447" and sum(str(n["id"]) == spec["reference_positions"][0] for n in nodes) != 1:
        fail("REFERENCE_MISSING",spec["reference_origin"],"assigned A05 record is not unique in archived directory")
    inventory,origins,mappings = {},[],{}
    # Complete preflight before creating any output directory.
    for row in spec["images"]:
        data = inputs.read(row["path"])
        sha = digest(data)
        if sha != row["sha256"]:
            fail("IMAGE_HASH",row["path"],"declared digest differs from original bytes")
        if decode_image(safe_path(inputs.root,row["path"])) != (row["width"],row["height"]):
            fail("IMAGE_DIMENSIONS",row["path"],"decoded size differs from declared dimensions")
        index = row["source_index"]
        if index in mappings and mappings[index]["sha256"] != sha:
            fail("MAPPING_CONFLICT",row["path"],"one source index maps to different originals")
        if sha in inventory and inventory[sha]["source_index"] != index:
            fail("MAPPING_CONFLICT",row["path"],"one original has conflicting source indices")
        asset_id = "asset-"+book+"-"+sha
        inventory.setdefault(sha,dict(row,asset_id=asset_id,data=data))
        entry = mappings.setdefault(index,dict(asset_id=asset_id,source_index=index,viewer_page=None,
                                               printed_page=None,sha256=sha))
        if row["viewer_page"] is not None:
            if entry["viewer_page"] not in (None,row["viewer_page"]):
                fail("MAPPING_CONFLICT",row["path"],"one original has conflicting viewer pages")
            entry["viewer_page"] = row["viewer_page"]
        origins.append(dict(asset_id=asset_id,archive_path=row["path"],manifest_path=row["manifest"],
                            manifest_sha256=digest(inputs.read(row["manifest"])),source_index=index,
                            viewer_page=row["viewer_page"]))
    historical_issues = []
    for row in spec["annotations"]:
        check_book(row["file_id"],book,"history.annotations.file_id")
        mapping = next((m for m in mappings.values() if m["viewer_page"] == row["page_index"]),None)
        if mapping is None:
            fail("MAPPING_CONFLICT","history.annotations.page_index","historical annotation has no assigned original")
        image = inventory[mapping["sha256"]]
        bbox = [float(v) for v in row["rect_bbox"].split(",")]
        if len(bbox) != 4 or not (0 <= bbox[0] < bbox[2] <= image["width"] and 0 <= bbox[1] < bbox[3] <= image["height"]):
            historical_issues.append(dict(rect_id=row["rect_id"],asset_id=image["asset_id"],bbox=bbox,
                                          code="HISTORICAL_BOX_OUT_OF_BOUNDS",action="PRESERVED_UNMODIFIED_NOT_PROMOTED"))
    references = ["reference-"+book+"-"+digest((book+":"+digest(inputs.read(spec["reference_origin"]))+":"+str(p)).encode())
                  for p in spec["reference_positions"]]
    basis = "REFERENCE_ONLY: archived export rows (14)" if book == "46006966" else "REFERENCE_ONLY: archived A05 directory record (1)"
    basis += "; not an independent page/book denominator; completeness UNKNOWN; PRE_APPLY/coverage is ineligible. See limitations.json (S01)."
    limitations = dict(format_version="a01-limitations-1",book_id=book,coverage_eligible=False,
                       independent_denominator_status="UNKNOWN",scope_manifest_status="REFERENCE_ONLY",
                       reference_count=len(references),reference_origin=spec["reference_origin"],
                       missing_sources=spec["missing"],historical_box_issues=historical_issues,
                       proposal="S01: typed denominator status and missing_sources; no C01 modification",
                       platform_snapshot_generated=False,model_calls=0,model_cost=0)
    provenance = dict(format_version=VERSION,book_id=book,origins=origins,mappings=list(mappings.values()),
                      observation=spec["observation"],metadata_page_count=spec["metadata_count"],
                      selected_source_indices=sorted(mappings),acquired_unique_images=len(inventory),
                      selected_missing_source_indices=[],
                      outside_selected_scope_unacquired_indices=[i for i in range(spec["metadata_count"]) if i not in mappings],
                      original_manifests=[dict(archive_path=p,sha256=digest(inputs.read(p)),
                      note="original retained in repository; personal absolute paths omitted") for p in spec["manifests"]],
                      reference_records=[dict(reference_id=q,position=p) for q,p in zip(references,spec["reference_positions"])],
                      previous_import=predecessor)
    inputs.unchanged()
    destination.mkdir(parents=True,exist_ok=False)
    assets = []
    for sha,row in inventory.items():
        resource = put(destination,"assets/"+sha+".jpg",row["data"],"image/jpeg")
        assets.append(dict(resource,asset_id=row["asset_id"],width=row["width"],height=row["height"],
                           source_label="Archived original; see hashed provenance.json",provenance="ORIGINAL"))
    evidence,history = [],[]
    def attach(relative,data,description,media="application/json"):
        resource = put(destination,relative,data,media)
        evidence_id = "evidence-"+book+"-"+digest(relative.encode())[:24]
        evidence.append(dict(evidence_id=evidence_id,resource=resource,description=description,mode="OBSERVED"))
        history.append(dict(resource=resource,quality="UNVERIFIED",reason=description))
        return evidence_id
    for index,path in enumerate(spec["raw"]):
        suffix = ".json" if path.endswith(".json") else ".jpg" if path.endswith(".jpg") else ".txt"
        media = {".json":"application/json",".jpg":"image/jpeg",".txt":"text/plain"}[suffix]
        attach("history/{:02d}-{}{}".format(index,Path(path).stem,suffix),inputs.read(path),
               "Byte-preserved archived reference: "+path+"; not independently approved business truth",media)
    provenance_id = attach("provenance.json",encoded(provenance),"Sanitized source chain; historical observation, explicit selected scope")
    attach("limitations.json",encoded(limitations),"Blocking completeness limitations; no independent denominator or coverage PASS")
    # Hashes are measured before and after without changing or leaking original paths.
    inputs.unchanged()
    integrity = dict(format_version="a01-input-integrity-1",unchanged=True,
                     inputs=[dict(archive_path=p,before_sha256=digest(data),
                                  after_sha256=digest(safe_path(inputs.root,p).read_bytes())) for p,data in sorted(inputs.bytes.items())])
    attach("input-integrity.json",encoded(integrity),"Original input byte hashes before/after import")
    policy = seal_policy(dict(policy_id="a01-source-only-proposal",revision=1,confirmation_status="A_INTERNAL_PROPOSAL",
                             option_grouping="UNRESOLVED",role_mapping=dict(stem="Q",option="W",answer="A",explanation="E",shared_material="Q"),
                             source_notes=["Source-only exchange; required C01 policy placeholder; no execution or B confirmation"],
                             frame_save_status="UNVERIFIED",ocr_status="UNVERIFIED",applicability="PROPOSAL_ONLY"))
    source = seal_artifact(dict(schema_version=SCHEMA_VERSION,artifact_id="source-"+book+"-a01-archive",
                               revision=revision,kind="SourceBundle",run_id="import-"+book+"-r"+str(revision),
                               book_id=book,scope_id="scope-"+book+"-a01-archive",input_refs=[],
                               producer=dict(module="source.static",implementation_version=VERSION,config_version=VERSION,
                                             policy_versions=[],model_version=None,prompt_version=None,evidence_mode="OBSERVED"),
                               created_at=created_at or datetime.now(timezone.utc).isoformat(),
                               payload=dict(assets=assets,directories=dirs,pages_expected=[r["asset_id"] for r in assets],
                                            pages_acquired=[r["asset_id"] for r in assets],
                                            external_page_mappings=[dict(asset_id=m["asset_id"],directory_id=dirs[0]["directory_id"],
                                                                        external_page=json.dumps({k:m[k] for k in ("source_index","viewer_page","printed_page")},sort_keys=True),
                                                                        mapping_status="CONFIRMED" if m["viewer_page"] is not None else "UNCERTAIN",
                                                                        evidence_refs=[provenance_id]) for m in mappings.values()],
                                            history=history,scope_manifest=references,scope_manifest_basis=basis,
                                            metadata_page_count=spec["metadata_count"])))
    # Use the accepted sole type and public validation/sealing/serialization APIs.
    SourceBundle.model_validate(source)
    exchange = validate_bundle(dict(format_version="c01-exchange-1",artifacts=[source],policies=[policy],evidence=evidence),destination)
    path = write_bundle(exchange,destination/"exchange.json")
    load_static_bundle(path,expected_book_id=book)
    inputs.unchanged()
    return path


def load_static_bundle(path, expected_book_id):
    """Public C01 load plus full decode and A01 cross-book/mapping/resource checks."""
    path = Path(path).resolve()
    bundle = load_bundle(path,verify_assets=True)
    if len(bundle.artifacts) != 1 or not isinstance(bundle.artifacts[0],SourceBundle):
        fail("SOURCE_ONLY","artifacts","A01 exchange must contain exactly one SourceBundle")
    source = bundle.artifacts[0]
    check_book(source.book_id,str(expected_book_id),"SourceBundle.book_id")
    resources = {e.resource.path:e.resource for e in bundle.evidence}
    for name in ("provenance.json","limitations.json","input-integrity.json"):
        if name not in resources:
            fail("RESOURCE_MISSING",name,"required hashed A01 record absent")
    provenance = parse(safe_path(path.parent,"provenance.json").read_bytes())
    limitations = parse(safe_path(path.parent,"limitations.json").read_bytes())
    check_book(provenance["book_id"],source.book_id,"provenance.book_id")
    check_book(limitations["book_id"],source.book_id,"limitations.book_id")
    if limitations["coverage_eligible"] is not False or limitations["independent_denominator_status"] != "UNKNOWN":
        fail("DENOMINATOR_UNKNOWN","limitations","A01 archives cannot assert independent completeness")
    assets = {a.asset_id:a for a in source.payload.assets}
    mappings = provenance["mappings"]
    if len(mappings) != len(assets) or {m["asset_id"] for m in mappings} != set(assets):
        fail("MAPPING_CONFLICT","provenance.mappings","must match all acquired originals once")
    indices,viewers = set(),set()
    contract_mappings = {m.asset_id:m for m in source.payload.external_page_mappings}
    assigned = {"46006966":{7:8,8:9,9:10,10:None,233:234,234:None},"46007447":{13:14,172:173}}
    if source.book_id not in assigned or {m["source_index"]:m["viewer_page"] for m in mappings} != assigned[source.book_id]:
        fail("MAPPING_CONFLICT","provenance.mappings","assigned archive mapping differs; unknown viewer pages must remain unknown")
    for mapping in mappings:
        asset = assets[mapping["asset_id"]]
        if asset.asset_id != "asset-"+source.book_id+"-"+asset.sha256:
            fail("BOOK_CONFLICT",asset.asset_id,"asset belongs to another book")
        if mapping["sha256"] != asset.sha256:
            fail("MAPPING_CONFLICT",asset.asset_id,"mapping digest differs")
        index,viewer = mapping["source_index"],mapping["viewer_page"]
        if index in indices or (viewer is not None and viewer in viewers):
            fail("MAPPING_CONFLICT",asset.asset_id,"duplicate source/viewer page")
        indices.add(index)
        if viewer is not None:
            viewers.add(viewer)
        external = parse(contract_mappings[asset.asset_id].external_page.encode())
        if external != {k:mapping[k] for k in ("source_index","viewer_page","printed_page")}:
            fail("MAPPING_CONFLICT",asset.asset_id,"contract mapping differs from provenance")
        if contract_mappings[asset.asset_id].mapping_status != ("CONFIRMED" if viewer is not None else "UNCERTAIN"):
            fail("MAPPING_CONFLICT",asset.asset_id,"mapping confidence differs from archived evidence")
        if decode_image(safe_path(path.parent,asset.path)) != (asset.width,asset.height):
            fail("IMAGE_DIMENSIONS",asset.path,"decoded dimensions differ")
    for origin in provenance["origins"]:
        if origin["asset_id"] not in assets:
            fail("MAPPING_CONFLICT","origins.asset_id","unknown asset")
        safe_path(path.parent,origin["archive_path"])  # lexical portability only; origin is not a live dependency
        mapped = next(m for m in mappings if m["asset_id"] == origin["asset_id"])
        if origin["source_index"] != mapped["source_index"] or origin["viewer_page"] not in (None,mapped["viewer_page"]):
            fail("MAPPING_CONFLICT","origins","origin index/viewer conflicts with mapping")
    if provenance["acquired_unique_images"] != len(assets):
        fail("SOURCE_PAGES","provenance.acquired_unique_images","acquired count must match actual assets")
    if provenance["metadata_page_count"] != source.payload.metadata_page_count:
        fail("METADATA_CONFLICT","metadata_page_count","source and provenance totals differ")
    if len(source.payload.scope_manifest) != limitations["reference_count"] or "REFERENCE_ONLY" not in source.payload.scope_manifest_basis:
        fail("DENOMINATOR_UNKNOWN","scope_manifest","reference-only scope basis/count required")
    from .consistency import validate_archive_records
    integrity = parse(safe_path(path.parent,"input-integrity.json").read_bytes())
    validate_archive_records(path.parent,source,provenance,limitations,integrity)
    return bundle
