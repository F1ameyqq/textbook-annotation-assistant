"""Bounded live acquisition; page adaptation stays on the platform side."""
from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

from annotation.runtime.browser.guard import BrowserSafetyError, BOOK_ID, VIEWER_PAGES
from annotation.runtime.browser.session import HeadlessSession


def now():
    return datetime.now(timezone.utc).isoformat()


def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def _business(result):
    if result.get("error") == "TIMEOUT":
        raise BrowserSafetyError("TIMEOUT", "fetch")
    if result.get("http_status") in (401, 403):
        raise BrowserSafetyError("LOGIN_REQUIRED", "fetch")
    body = result.get("body")
    if isinstance(body, dict) and body.get("code") in (401, 403, "401", "403"):
        raise BrowserSafetyError("LOGIN_REQUIRED", "fetch")
    if result.get("http_status") != 200 or not isinstance(body, dict) or body.get("code") != 0:
        raise BrowserSafetyError("RESOURCE_FAILED", "fetch")
    return body


def get_business(session, endpoint):
    allowed, category = session.policy.decide("GET", "https://www.usense.com" + endpoint)
    if not allowed:
        session.audit.record("GET", category, False)
        raise BrowserSafetyError("REQUEST_BLOCKED", "fetch")
    # Tokens remain entirely inside the protected page. They are neither returned
    # from evaluate nor included in browser diagnostics/audit/serialized evidence.
    try:
        result = session.page.evaluate("""async ([path,timeout]) => {
          const user = JSON.parse(localStorage.getItem('user') || '{}');
          if (!user.access_token) return {http_status:401};
          const target = new URL(path,location.origin);
          if(target.pathname==='/qieti/api/claim_book/books'){
            // Mirror the existing UI's account filter inside the page. Account
            // identity must not leave evaluate or enter evidence/command args.
            target.searchParams.set('username',user.username || '');
            target.searchParams.set('role',user.role || '');
            target.searchParams.set('is_admin',String(user.role==='admin'));
            target.searchParams.set('status_list',['admin','delivery_admin'].includes(user.role)
              ? '标注中,返修,待审核,复审,待交付,问题书籍,无法入库,重复' : '标注中,返修,待审核,复审');
          }
          const controller = new AbortController();
          const timer = setTimeout(()=>controller.abort(),timeout);
          try {
            const response = await fetch(target,{method:'GET',redirect:'error',signal:controller.signal,
              headers:{Authorization:'Bearer '+user.access_token}});
            return {http_status:response.status,body:await response.json()};
          } catch(error) {
            return {error:controller.signal.aborted?'TIMEOUT':'RESOURCE_FAILED'};
          } finally {clearTimeout(timer);}
        }""", [endpoint, session.timeout_ms])
    except Exception:
        raise BrowserSafetyError("RESOURCE_FAILED", "fetch") from None
    return _business(result)


def _subset(row, keys):
    result = {}
    for key in keys:
        if key not in row:
            continue
        value = row[key]
        if key == "rect_bbox" and isinstance(value, list):
            if len(value) != 4 or any(type(v) not in (int, float) or not math.isfinite(v) for v in value):
                raise BrowserSafetyError("RESOURCE_FAILED", "collect")
        elif type(value) not in (str, int, float, bool, type(None)) or (type(value) is float and not math.isfinite(value)):
            # A key whitelist alone cannot sanitize unexpected nested objects.
            raise BrowserSafetyError("RESOURCE_FAILED", "collect")
        result[key] = value
    return result


def _book(body):
    found = []
    def walk(value):
        if isinstance(value, dict):
            if str(value.get("id")) == BOOK_ID:
                found.append(_subset(value, ("id", "title", "page_count", "question_count", "status", "updated_at")))
            else:
                for child in value.values():
                    walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
    walk(body.get("data"))
    # The platform may expose the same list as records/books/list. Equal aliases
    # describe one target; conflicting aliases remain a target failure.
    unique = {json.dumps(row, sort_keys=True, ensure_ascii=False): row for row in found}
    if len(unique) != 1:
        error = BrowserSafetyError("TARGET_MISMATCH", "collect")
        error.safe_details = {"matched_target_rows":len(found),"unique_target_rows":len(unique)}
        raise error
    return next(iter(unique.values()))


def _directory(body):
    def node(value):
        if not isinstance(value, dict):
            raise BrowserSafetyError("RESOURCE_FAILED", "collect")
        result = _subset(value, ("id", "label", "isQuestion", "order_in_level"))
        if "children" in value:
            result["children"] = [node(child) for child in value["children"]]
        return result
    try:
        return {"code": 0, "data": {"directory_data": [node(n) for n in body["data"]["directory_data"]]}}
    except (KeyError, TypeError):
        raise BrowserSafetyError("RESOURCE_FAILED", "collect") from None


def _annotations(body):
    keys = ("type", "rect_id", "file_id", "belong_to_level", "order_in_level", "rect_bbox",
            "page_index", "parent_rect_id", "directory_id", "content_type", "is_pre_annotation")
    if not isinstance(body.get("data"), list):
        raise BrowserSafetyError("RESOURCE_FAILED", "collect")
    return {"code": 0, "data": [_subset(row, keys) for row in body["data"]]}


def sanitized_capture(capture):
    """Package only the bounded input schema, even for offline caller inputs."""
    result = _subset(capture, ("capture_version", "evidence_mode", "provenance", "observed_at", "complete"))
    book = capture["book"]
    if "code" in book:
        book = book["data"]
    result["book"] = _subset(book, ("id", "title", "page_count", "question_count", "status", "updated_at"))
    result["directory"] = _directory(capture["directory"])
    result["annotations"] = _annotations(capture["annotations"])
    result["source_metadata"] = {"code":0,"data":_subset(capture["source_metadata"]["data"],
                               ("file_id","total_pages","annotation_type","source","manifest_exists"))}
    result["pages"] = []
    for page in capture["pages"]:
        raw = page["source_response"]["data"]
        result["pages"].append({"viewer_page":page["viewer_page"],"asset_path":page["asset_path"],
            "download_status":page["download_status"],
            "mapping_evidence":_subset(page["mapping_evidence"],("viewer_page","source_index","original_loaded")),
            "source_response":{"code":0,"data":{"file_id":raw["file_id"],"pages":[
                _subset(p,("image","page_index")) for p in raw["pages"]]}}})
    return result


def _current(session):
    return {"book": _book(get_business(session, "/qieti/api/claim_book/books?page=1&pageSize=10&id=" + BOOK_ID)),
            "directory": _directory(get_business(session, "/qieti/api/annotate_ocr/directory/get?file_id=" + BOOK_ID)),
            "annotations": _annotations(get_business(session, "/qieti/api/annotate_pic/get_manual_annotations_unified/" + BOOK_ID))}


def _jump(page, zone_index, viewer_page):
    if viewer_page not in VIEWER_PAGES or zone_index not in (0, 1):
        raise BrowserSafetyError("REQUEST_BLOCKED", "navigate")
    zone = page.locator(".pdf-zone").nth(zone_index)
    control = zone.locator(".section-title input").first
    control.fill(str(viewer_page))
    control.press("Enter")


def _canvas_proof(page, zone_index, source_index, image_url):
    """Observe props and painted pixels; no general coordinate implementation.

    Vue props identify the actual page resource independently from a URL jump.
    Canvas content and a clipped screenshot supply the visible-load evidence.
    """
    script = """([zone,index,url]) => {
      const el=document.querySelectorAll('.pdf-zone')[zone];
      const canvas=el && el.querySelector('canvas');
      if(!canvas || !canvas.width || !canvas.height) return null;
      let vm=canvas.__vueParentComponent, matched=null;
      while(vm){if(vm.type && vm.type.__name==='PdfViewerWithDivUnified'){matched=vm;break;}vm=vm.parent;}
      if(!matched){
        // Production Vue may omit the per-element devtools pointer. Traverse
        // only mounted VNodes, returning only this viewer's bounded page props.
        const seen=new Set(), stack=[document.querySelector('#app')?._vnode];
        while(stack.length){const node=stack.pop();if(!node || typeof node!=='object' || seen.has(node))continue;
          seen.add(node);const component=node.component;
          if(component && component.type?.__name==='PdfViewerWithDivUnified'
             && component.props.zone===(zone===0?'question_zone':'answer_zone')){matched=component;break;}
          if(component?.subTree)stack.push(component.subTree);
          if(Array.isArray(node.children))stack.push(...node.children);
          if(node.suspense?.activeBranch)stack.push(node.suspense.activeBranch);
        }
      }
      if(!matched || !Array.isArray(matched.props.pages) || matched.props.pages.length!==1) return null;
      const pg=matched.props.pages[0];
      if(pg.page_index!==index || pg.image!==url) return null;
      if(!performance.getEntriesByName(url).some(entry=>entry.responseEnd>0)) return null;
      const ctx=canvas.getContext('2d'), data=ctx.getImageData(0,0,canvas.width,canvas.height).data;
      let dark=0,light=0;
      for(let i=0;i<data.length;i+=64){if(data[i+3] && data[i]<160) dark++;if(data[i+3] && data[i]>220) light++;}
      if(dark<20 || light<20) return null;
      const box=canvas.getBoundingClientRect();
      return {source_index:pg.page_index,resource_matches:true,resource_timing_loaded:true,canvas_width:canvas.width,canvas_height:canvas.height,
        css_rect:{x:box.x,y:box.y,width:box.width,height:box.height},dark_samples:dark,light_samples:light,
        data_url:canvas.toDataURL('image/png')};
    }"""
    page.wait_for_function(script, arg=[zone_index, source_index, image_url], timeout=30000)
    # Allow the current render's image decode/draw callbacks to complete before
    # retaining the visible canvas. This does not assert geometric correctness.
    page.evaluate("() => new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))")
    result = page.evaluate(script, [zone_index, source_index, image_url])
    data_url = result.pop("data_url")
    return result, base64.b64decode(data_url.split(",", 1)[1], validate=True)


def _original(session, url, path):
    session.policy.register_image(url)
    allowed, category = session.policy.decide("GET", url)
    if not allowed:
        raise BrowserSafetyError("REQUEST_BLOCKED", "download")
    session.audit.record("GET", category, True)
    try:
        response = session.context.request.get(url, timeout=30000, max_redirects=0, max_retries=0)
        session.audit.record("GET", category, True, response.status)
        if response.status != 200:
            raise BrowserSafetyError("RESOURCE_FAILED", "download")
        content = response.body()
        from PIL import Image
        import io
        with Image.open(io.BytesIO(content)) as image:
            image.verify()
        path.write_bytes(content)
    except BrowserSafetyError:
        raise
    except Exception as exc:
        raise BrowserSafetyError("TIMEOUT" if type(exc).__name__ == "TimeoutError" else "RESOURCE_FAILED", "download") from None


def collect_live(output, login_root, *, ignore_https_errors=False, coordinate_refs=None):
    """Acquire exactly pages 14, 15 and 173, close, then return portable capture.

    Output must be new, retaining incomplete evidence on any failure. Never
    retries login or a business request and never overwrites an earlier run.
    """
    output = Path(output)
    if output.exists():
        raise BrowserSafetyError("OUTPUT_EXISTS", "prepare")
    output.mkdir(parents=True)
    (output / "assets").mkdir()
    (output / "evidence").mkdir()
    session_options={"ignore_https_errors":ignore_https_errors}
    if coordinate_refs is not None:
        from .viewer_observation import DRAW_OBSERVER
        session_options['init_script']=DRAW_OBSERVER
    session = HeadlessSession(login_root, **session_options)
    geometry_status='NOT_REQUESTED' if coordinate_refs is None else 'A01_BOUND_REFERENCE_CHECKS_REQUESTED'
    stage = "collect"
    operation = "open_session"
    capture = None
    try:
        with session:
            page = session.page
            operation = "open_book_picker"
            page.get_by_role("button", name="选择书籍", exact=True).click()
            operation = "locate_target_book"
            row = page.locator(".el-table__row").filter(has_text=BOOK_ID)
            row.wait_for(state="visible", timeout=30000)
            operation = "select_target_book"
            row.get_by_role("button", name="选择", exact=True).click()
            page.get_by_text(BOOK_ID, exact=False).first.wait_for(state="visible", timeout=30000)
            operation = "read_current_state"
            before = _current(session)
            source = get_business(session, "/qieti/api/annotate_pic/pre_annotation_source/" + BOOK_ID + "?annotationType=mr_pre")
            source_metadata = {"code": 0, "data": _subset(source["data"],
                               ("file_id", "total_pages", "annotation_type", "source", "manifest_exists"))}
            capture = {"capture_version": "a04.readonly.v1", "evidence_mode": "OBSERVED", "provenance": "LIVE",
                       "observed_at": now(), "complete": False, **before, "source_metadata": source_metadata, "pages": [],
                       "geometry_dependency": geometry_status}
            for viewer_page, zone_index in ((14, 0), (173, 1), (15, 0)):
                operation = "read_source_page"
                raw = get_business(session, f"/qieti/api/annotate_pic/pre_annotation/{BOOK_ID}?pageNum={viewer_page}&annotationType=mr_pre")
                data = raw.get("data", {})
                pages = data.get("pages", [])
                if str(data.get("file_id")) != BOOK_ID or len(pages) != 1:
                    raise BrowserSafetyError("TARGET_MISMATCH", "collect")
                pg = pages[0]
                source_index = pg.get("page_index")
                if type(source_index) is not int:
                    raise BrowserSafetyError("RESOURCE_FAILED", "collect")
                url = pg.get("image")
                asset = f"assets/page-{viewer_page}.jpg"
                operation = "download_original"
                _original(session, url, output / asset)
                operation = "navigate_viewer_page"
                _jump(page, zone_index, viewer_page)
                operation = "verify_painted_original"
                proof, canvas_bytes = _canvas_proof(page, zone_index, source_index, url)
                canvas_path = f"evidence/canvas-{viewer_page}.png"
                (output / canvas_path).write_bytes(canvas_bytes)
                page.locator(".pdf-zone").nth(zone_index).screenshot(path=str(output / f"evidence/viewer-{viewer_page}.png"))
                capture["pages"].append({"viewer_page": viewer_page,
                    "source_response": {"code":0,"data":{"file_id":BOOK_ID,**_subset(data,("source",)),
                        "pages":[{"image":f"original:viewer-{viewer_page}","page_index":source_index,"blocks":[]}]}},
                    "asset_path":asset,"download_status":200,
                    "mapping_evidence":{"viewer_page":viewer_page,"source_index":source_index,"original_loaded":True, **proof},
                    "canvas_path":canvas_path})
                if coordinate_refs is not None:
                    from .coordinate_probe import probe_page
                    from annotation.delivery.usense_readonly.coordinates import CoordinateError
                    operation='coordinate_reference_check'
                    try:
                        probe_page(page,output,viewer_page,zone_index,source_index,coordinate_refs)
                    except CoordinateError as coordinate_error:
                        failure=BrowserSafetyError('COORDINATE_FAILED','verify')
                        failure.safe_details={'coordinate_code':coordinate_error.code}
                        raise failure from None
            # Explicit return to page14; verify identity and visible canvas again.
            pg14 = next(p for p in capture["pages"] if p["viewer_page"] == 14)
            operation = "return_body_page"
            raw14 = get_business(session, f"/qieti/api/annotate_pic/pre_annotation/{BOOK_ID}?pageNum=14&annotationType=mr_pre")
            _jump(page, 0, 14)
            proof, _ = _canvas_proof(page, 0, pg14["mapping_evidence"]["source_index"], raw14["data"]["pages"][0]["image"])
            save_json(output / "evidence/navigation.json", {"at":now(),"sequence":[14,15,14],"answer_page":173,
                       "return_verified":True,"return_proof":proof,"protected_viewer_verified":session._helper.verify_viewer(page),
                       "target_book_confirmed":BOOK_ID,"geometry_status":geometry_status})
            after = _current(session)
            if before != after:
                save_json(output / "evidence/state-change.json", {"at":now(),"detected":True})
                raise BrowserSafetyError("STALE_STATE", "collect")
            capture["observed_at"] = now()
            save_json(output / "evidence/read-only-state.json", {"at":now(),"before_after_equal":True,
                       "frame_count":len(after["annotations"]["data"]),"book_question_count":after["book"].get("question_count"),
                       "business_state_sha256":hashlib.sha256(json.dumps(after,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),
                       "state_comparison_scope":"allowlisted book, complete directory and complete frame records"})
        # Publish a complete capture only after successful context/lease release.
        capture["complete"] = True
        save_json(output / "capture.json", capture)
        return capture
    except Exception as exc:
        code = exc.code if isinstance(exc, BrowserSafetyError) else ("TIMEOUT" if type(exc).__name__ == "TimeoutError" else "COLLECT_FAILED")
        if capture is not None and not (output / "capture.json").exists():
            capture["complete"] = False
            save_json(output / "capture-incomplete.json", capture)
        save_json(output / "evidence/failure.json", {"at":now(),"code":code,"stage":getattr(exc,"stage",stage),
                   "operation":operation,"complete":False,"details":getattr(exc,"safe_details",None)})
        raise BrowserSafetyError(code, getattr(exc,"stage",stage)) from None
    finally:
        save_json(output / "evidence/network-audit.json", session.audit.records)
        save_json(output / "evidence/session-release.json", {"at":now(),**session.report()})
