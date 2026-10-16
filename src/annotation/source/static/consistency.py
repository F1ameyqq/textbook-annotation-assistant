"""A01 archive-record consistency, not unsigned-source authenticity or quality."""
import math
import re
from pathlib import Path

from annotation.contracts.models import Resource

from .importer import OLD, NEW, EXECUTION, check_book, digest, directories, fail, parse, safe_path, url_index


def require(condition,code,location,message):
    if not condition:
        fail(code,location,message)


def portable(value,location):
    try:
        Resource(path=value,sha256="0"*64,media_type="application/json")
    except ValueError:
        fail("SOURCE_PATH",location,"expected a portable archive reference")


def sha(value,location):
    require(isinstance(value,str) and re.fullmatch(r"[0-9a-f]{64}",value),
            "SOURCE_DIGEST",location,"expected SHA256")


def validate_scope_partition(source,provenance):
    """S=A disjoint-union M; metadata universe=S disjoint-union O.

    A is the actual mapped asset inventory. Missing expected IDs describe
    acquisition intent only; no image, dimensions or digest is invented.
    """
    count = provenance.get("metadata_page_count")
    require(type(count) is int and count > 0 and count == source.payload.metadata_page_count,
            "SCOPE_COUNT","provenance.metadata_page_count","positive integer metadata total must match source")
    def indices(values,location):
        require(isinstance(values,list),"SCOPE_INDICES",location,"expected index list")
        result = set()
        for i,value in enumerate(values):
            loc = location+"[{}]".format(i)
            require(type(value) is int and 0 <= value < count,"SCOPE_INDICES",loc,"source index must be an integer within metadata range")
            require(value not in result,"SCOPE_INDICES",loc,"duplicate source index")
            result.add(value)
        return result
    acquired = indices([m["source_index"] for m in provenance["mappings"]],"provenance.mappings.source_index")
    selected = indices(provenance.get("selected_source_indices"),"provenance.selected_source_indices")
    missing = indices(provenance.get("selected_missing_source_indices"),"provenance.selected_missing_source_indices")
    outside = indices(provenance.get("outside_selected_scope_unacquired_indices"),"provenance.outside_selected_scope_unacquired_indices")
    require(acquired <= selected,"SCOPE_PARTITION","provenance.selected_source_indices","selected scope must retain every acquired source index")
    require(acquired.isdisjoint(missing) and missing == selected-acquired,"SCOPE_PARTITION",
            "provenance.selected_missing_source_indices","selected missing must equal selected minus actual acquired inventory")
    require(outside.isdisjoint(selected) and len(selected)+len(outside) == count,"SCOPE_PARTITION",
            "provenance.outside_selected_scope_unacquired_indices","outside unacquired must be the metadata complement of selected scope")
    require(type(provenance.get("acquired_unique_images")) is int and provenance["acquired_unique_images"] == len(acquired),
            "SCOPE_COUNT","provenance.acquired_unique_images","actual asset count must match mapped acquisition count")
    expected,obtained = source.payload.pages_expected,source.payload.pages_acquired
    require(len(expected) == len(selected) and len(obtained) == len(acquired)
            and len(set(expected)-set(obtained)) == len(missing),"SCOPE_COUNT","pages_expected",
            "public expected/acquired page counts must match selected/acquired/missing partition")


def validate_observation_source(observation,inputs,book,source_path):
    """Cross-check retained archive identity/digest; do not authenticate time labels."""
    require(observation.get("source") == source_path and source_path in inputs,
            "OBSERVATION_SOURCE","provenance.observation.source","archive observation source conflicts with retained input identity")
    index = observation.get("observation_index_source")
    if book == "46007447" or index is not None:
        loc = "provenance.observation.observation_index_source"
        require(isinstance(index,dict),"OBSERVATION_SOURCE",loc,"observation index source record is required")
        path = index.get("archive_path")
        portable(path,loc+".archive_path")
        if book == "46007447":
            require(path == NEW+"/independent-network.json","OBSERVATION_SOURCE",loc+".archive_path","observation index identity differs from assigned archive")
        require(path in inputs,"OBSERVATION_SOURCE",loc+".archive_path","observation index is absent from retained input inventory")
        sha(index.get("sha256"),loc+".sha256")
        require(index["sha256"] == inputs[path],"OBSERVATION_SOURCE",loc+".sha256","observation index digest conflicts with retained before/after digest")


def validate_archive_records(folder,source,provenance,limitations,integrity):
    """All reads stay in the package; archive_path fields are inert provenance.

    An adversary replacing every mutually consistent record can still invent an
    unsigned archive. This gate rejects contradictions between retained records.
    """
    book = source.book_id
    require(integrity.get("unchanged") is True,"INPUT_CHANGED","input-integrity.unchanged",
            "archive import must retain an unchanged before/after record")
    require(integrity.get("format_version") == "a01-input-integrity-1","SOURCE_FORMAT","input-integrity.format_version","unknown record format")
    entries = integrity.get("inputs")
    require(isinstance(entries,list) and entries,"INPUT_INVENTORY","input-integrity.inputs","input inventory is required")
    inputs = {}
    for i,item in enumerate(entries):
        loc = "input-integrity.inputs[{}]".format(i)
        require(isinstance(item,dict),"INPUT_INVENTORY",loc,"expected input record")
        path = item.get("archive_path")
        portable(path,loc+".archive_path")
        require(path not in inputs,"INPUT_INVENTORY",loc+".archive_path","duplicate input path")
        before,after = item.get("before_sha256"),item.get("after_sha256")
        sha(before,loc+".before_sha256")
        sha(after,loc+".after_sha256")
        require(before == after,"INPUT_CHANGED",loc+".after_sha256","before/after digests differ")
        inputs[path] = before

    require(provenance.get("format_version") in ("a01-static-1","a01-static-1-r1","a01-static-1-r2"),
            "SOURCE_FORMAT","provenance.format_version","unknown archive format")
    validate_scope_partition(source,provenance)
    require(limitations.get("scope_manifest_status") == "REFERENCE_ONLY", "DENOMINATOR_UNKNOWN",
            "limitations.scope_manifest_status","archive reference scope cannot claim independent completeness")
    require(limitations.get("independent_denominator_status") == "UNKNOWN" and limitations.get("coverage_eligible") is False,
            "DENOMINATOR_UNKNOWN","limitations","independent denominator remains unknown")

    raw = ([OLD+"/directory.json",OLD+"/manual-annotations.json",OLD+"/paper-questions-original.jsonl",
            OLD+"/book-info-readonly.json",OLD+"/session-receipt-20261015.json",
            "data/derived/CORRECTION-page-mapping.md","data/raw/annotations/workspace1.jpg"] if book == "46006966" else
           [NEW+"/independent-source-page14.json",NEW+"/independent-source-page173.json",
            NEW+"/independent-response-0003.json",NEW+"/independent-book.json",
            EXECUTION+"/source-metadata.json",NEW+"/manifest.json"])
    history = {}
    for i,item in enumerate(source.payload.history):
        require(item.quality == "UNVERIFIED","HISTORY_QUALITY","history[{}].quality".format(i),
                "A01 archive has no independent business approval")
        path = item.resource.path
        require(path not in history,"HISTORY_REFERENCE","history[{}].resource.path".format(i),"duplicate history path")
        history[path] = item.resource
    originals = {}
    for i,archive in enumerate(raw):
        suffix = ".json" if archive.endswith(".json") else ".jpg" if archive.endswith(".jpg") else ".txt"
        relative = "history/{:02d}-{}{}".format(i,Path(archive).stem,suffix)
        require(relative in history,"HISTORY_REFERENCE",relative,"required archived history resource absent")
        require(archive in inputs,"INPUT_INVENTORY",archive,"history original absent from before/after inventory")
        data = safe_path(folder,relative).read_bytes()
        require(digest(data) == inputs[archive],"HISTORY_BYTES",relative,"history bytes conflict with retained original digest")
        originals[archive] = parse(data) if suffix == ".json" else data

    # Required origin inventories are determined by the explicitly assigned
    # archive layouts, not by the number of surviving origins in a mutated file.
    by_index = {m["source_index"]:m for m in provenance["mappings"]}
    expected_origins = {}
    if book == "46006966":
        for index,viewer in ((7,8),(8,9),(9,10),(233,234)):
            expected_origins[OLD+"/viewer-page-{:04d}.jpg".format(viewer)] = (index,viewer,OLD+"/source-images-complete.json")
        for index in (7,8,9,10,233,234):
            expected_origins["data/raw/images/{}_page_{}.jpg".format(book,index)] = (index,None,"data/derived/manifest.json")
    else:
        for index,viewer,role in ((13,14,"question"),(172,173,"answer")):
            for path in (NEW+"/independent-original-"+role+".jpg",EXECUTION+"/source-viewer{}.jpg".format(viewer)):
                expected_origins[path] = (index,viewer,NEW+"/independent-originals.json")
    records = provenance.get("original_manifests")
    require(isinstance(records,list),"SOURCE_MANIFEST","provenance.original_manifests","manifest inventory required")
    manifests = {}
    for i,record in enumerate(records):
        loc = "provenance.original_manifests[{}]".format(i)
        require(isinstance(record,dict),"SOURCE_MANIFEST",loc,"expected manifest record")
        path = record.get("archive_path")
        portable(path,loc+".archive_path")
        require(path not in manifests,"SOURCE_MANIFEST",loc,"duplicate manifest path")
        require(path in inputs and record.get("sha256") == inputs[path],
                "SOURCE_MANIFEST",loc+".sha256","manifest digest conflicts with retained input inventory")
        manifests[path] = record["sha256"]
    require(set(manifests) == {v[2] for v in expected_origins.values()},"SOURCE_MANIFEST",
            "provenance.original_manifests","assigned original manifest inventory differs")
    origins = provenance.get("origins")
    require(isinstance(origins,list) and len(origins) == len(expected_origins),"SOURCE_ORIGINS",
            "provenance.origins","assigned origin inventory is missing or duplicated")
    seen = set()
    for i,origin in enumerate(origins):
        loc = "provenance.origins[{}]".format(i)
        require(isinstance(origin,dict),"SOURCE_ORIGINS",loc,"expected origin record")
        path = origin.get("archive_path")
        require(path in expected_origins and path not in seen,"SOURCE_ORIGINS",loc+".archive_path","origin path missing, duplicated or outside assigned inventory")
        seen.add(path)
        index,viewer,manifest = expected_origins[path]
        require(origin.get("manifest_path") == manifest,"SOURCE_MANIFEST",loc+".manifest_path","origin manifest differs from assigned layout")
        require(origin.get("manifest_sha256") == manifests[manifest],"SOURCE_MANIFEST",loc+".manifest_sha256","origin manifest digest conflicts with original_manifests")
        require(origin.get("source_index") == index and origin.get("viewer_page") == viewer,"MAPPING_CONFLICT",loc,"origin index/viewer contradicts assigned layout")
        require(origin.get("asset_id") == by_index[index]["asset_id"],"SOURCE_ORIGINS",loc+".asset_id","origin asset conflicts with mapped original")
        require(path in inputs and inputs[path] == by_index[index]["sha256"],"SOURCE_ORIGINS",loc+".archive_path","origin bytes conflict with asset and retained input digest")
    for i,mapping in enumerate(provenance["mappings"]):
        require(mapping.get("printed_page") is None,"MAPPING_EVIDENCE","provenance.mappings[{}].printed_page".format(i),"assigned archive has no printed-page mapping evidence")

    missing = limitations.get("missing_sources")
    names = {"netdetail1.json","netdetail2.json","netdetail3.json","savectx.json","workspace1.jpg"} if book == "46006966" else set()
    require(isinstance(missing,list) and len(missing) == len(names) and
            all(isinstance(m,dict) for m in missing) and {m.get("file") for m in missing} == names,
            "MISSING_SOURCES","limitations.missing_sources","known unavailable-source declarations cannot be erased")
    for i,item in enumerate(missing):
        loc = "limitations.missing_sources[{}]".format(i)
        workspace = item["file"] == "workspace1.jpg"
        require(item.get("missing_original_json") is (not workspace) and item.get("original_in_repository") is workspace,
                "MISSING_SOURCES",loc,"local/missing original flags contradict assigned archive")
        require(item.get("original_external_location") == "UNAVAILABLE_NOT_PORTABLE","MISSING_SOURCES",loc,"external original remains unavailable")
        sha(item.get("declared_sha256"),loc+".declared_sha256")
        if workspace:
            local = "data/raw/annotations/workspace1.jpg"
            require(item.get("available_local_copy") == local and item["declared_sha256"] == inputs[local],
                    "MISSING_SOURCES",loc,"local screenshot conflicts with its retained original")
        else:
            require(item.get("available_local_copy") is None,"MISSING_SOURCES",loc,"missing original JSON cannot be replaced by another copy")

    if book == "46006966":
        directory = originals[raw[0]]
        annotations = originals[raw[1]]
        check_book(directory.get("bookId"),book,"history.directory.bookId")
        check_book(annotations.get("bookId"),book,"history.manual-annotations.bookId")
        check_book(originals[raw[3]]["book"]["id"],book,"history.book-info.book.id")
        tree = directory["directory_data"]
        exported = originals[raw[2]].splitlines()
        require(len(exported) == 14,"REFERENCE_RECORDS","history.paper-questions-original","assigned export count differs")
        for row in exported:
            parse(row)
        origin,positions = raw[2],list(range(1,15))
        require(source.payload.metadata_page_count == originals[raw[3]]["book"]["page_count"],"METADATA_CONFLICT","history.book-info","metadata total differs")
        require(provenance["observation"].get("date") == originals[raw[4]]["date"],"OBSERVATION_CONFLICT","provenance.observation.date","historical date differs from archived session")
        validate_observation_source(provenance["observation"],inputs,book,raw[4])
        issues = []
        assets = {a.asset_id:a for a in source.payload.assets}
        by_viewer = {m["viewer_page"]:m for m in provenance["mappings"] if m["viewer_page"] is not None}
        for i,row in enumerate(annotations["annotations"]):
            check_book(row.get("file_id"),book,"history.annotations[{}].file_id".format(i))
            require(row.get("page_index") in by_viewer,"MAPPING_CONFLICT","history.annotations[{}].page_index".format(i),"annotation has no assigned original")
            asset = assets[by_viewer[row["page_index"]]["asset_id"]]
            bbox = [float(v) for v in row["rect_bbox"].split(",")]
            require(len(bbox) == 4 and all(math.isfinite(v) for v in bbox),"HISTORY_DATA","history.annotations[{}].rect_bbox".format(i),"historical box requires four finite coordinates")
            if not (0 <= bbox[0] < bbox[2] <= asset.width and 0 <= bbox[1] < bbox[3] <= asset.height):
                issues.append(dict(rect_id=row["rect_id"],asset_id=asset.asset_id,bbox=bbox,code="HISTORICAL_BOX_OUT_OF_BOUNDS",action="PRESERVED_UNMODIFIED_NOT_PROMOTED"))
        require(limitations.get("historical_box_issues") == issues,"HISTORY_DATA","limitations.historical_box_issues","outlier inventory conflicts with archived original boxes")
    else:
        by_viewer = {m["viewer_page"]:m for m in provenance["mappings"] if m["viewer_page"] is not None}
        for archive in raw[:2]:
            data = originals[archive]["data"]
            check_book(data.get("file_id"),book,"history."+archive+".file_id")
            viewer = int(re.search(r"page([0-9]+)\.json$",archive)[1])
            require(viewer in by_viewer,"MAPPING_CONFLICT","history."+archive,"response has no retained viewer/source mapping")
            pages = data.get("pages")
            require(isinstance(pages,list) and len(pages) == 1 and isinstance(pages[0],dict),
                    "MAPPING_CONFLICT","history."+archive+".pages","expected one archived source page")
            page = pages[0]
            loc = "history."+archive+".pages[0]"
            require(type(page.get("page_index")) is int and page["page_index"] == by_viewer[viewer]["source_index"],
                    "MAPPING_CONFLICT",loc+".page_index","archived response index conflicts with retained mapping")
            index = url_index(page.get("image"),book,loc+".image")
            require(index == page["page_index"],"MAPPING_CONFLICT",loc+".image","archived image URL index conflicts with response and retained mapping")
        check_book(originals[raw[3]]["data"]["id"],book,"history.book.data.id")
        check_book(originals[raw[4]]["data"]["file_id"],book,"history.metadata.file_id")
        tree = originals[raw[2]]["data"]["directory_data"]
        origin,positions = raw[2],["1792148510557"]
        require(source.payload.metadata_page_count == originals[raw[3]]["data"]["page_count"] == originals[raw[4]]["data"]["total_pages"],
                "METADATA_CONFLICT","history.metadata","archived totals conflict")
        require(provenance["observation"].get("archive_created_at") == originals[raw[5]]["created_at"],"OBSERVATION_CONFLICT","provenance.observation.archive_created_at","archive boundary differs")
        validate_observation_source(provenance["observation"],inputs,book,raw[5])
    expected_dirs,nodes = directories(tree,book)
    require([d.model_dump() for d in source.payload.directories] == expected_dirs,"HISTORY_DIRECTORY","directories","directory projection differs from archived tree")
    if book == "46007447":
        require(sum(str(n["id"]) == positions[0] for n in nodes) == 1,"REFERENCE_RECORDS","history.directory","A05 reference is missing or duplicated")
    require(limitations.get("reference_origin") == origin,"REFERENCE_RECORDS","limitations.reference_origin","reference origin conflicts with archived input")
    expected_refs = [dict(reference_id="reference-"+book+"-"+digest((book+":"+inputs[origin]+":"+str(p)).encode()),position=p) for p in positions]
    require(provenance.get("reference_records") == expected_refs,"REFERENCE_RECORDS","provenance.reference_records","reference identities/positions conflict with archived input")
    require(source.payload.scope_manifest == [r["reference_id"] for r in expected_refs],"REFERENCE_RECORDS","scope_manifest","public reference IDs differ from provenance records")
    require(limitations.get("reference_count") == len(expected_refs),"REFERENCE_RECORDS","limitations.reference_count","reference count differs")
