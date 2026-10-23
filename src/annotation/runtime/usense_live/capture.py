"""Real native GET capture; decoded HTTP entity bytes retained without OCR edits."""
import asyncio
import base64
from datetime import datetime, timezone
import json

from .config import capture_endpoints
from .core import (ORIGIN, TARGET, load_binding, owned_readonly_context, require, sha, utc, write_new, record_exception)

FETCH = r"""async path => {
 const stored=localStorage.getItem('user');
 if(!stored)return {status:'LOGIN_REQUIRED'};
 let user;try{user=JSON.parse(stored);}catch(e){return {status:'LOGIN_REQUIRED'};}
 if(!user||typeof user.access_token!=='string'||!user.access_token)return {status:'LOGIN_REQUIRED'};
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),20000);
 try{
  const response=await fetch(path,{method:'GET',headers:{Authorization:'Bearer '+user.access_token,Accept:'application/json'},
   cache:'no-store',redirect:'error',credentials:'same-origin',signal:controller.signal});
  const bytes=new Uint8Array(await response.arrayBuffer());
  if(bytes.length>12000000)throw Error('RESPONSE_TOO_LARGE');
  let binary='';for(let i=0;i<bytes.length;i+=32768)binary+=String.fromCharCode(...bytes.subarray(i,i+32768));
  return {status:response.status,content_type:response.headers.get('content-type'),body_base64:btoa(binary)};
 }finally{clearTimeout(timer);}
}"""


async def capture(config_path, config_sha256):
    binding = load_binding(config_path, config_sha256)
    endpoints = capture_endpoints(binding)
    result = {"schema": "UsenseNativeCapture/v1", "book_id": "46007447", "status": "NOT_STARTED",
              "config_sha256": config_sha256, "run_id": binding.data["run_id"], "save_attempts": 0,
              "transport": binding.data["transport"],
              "document_mode": "LOCAL_INERT_SAME_ORIGIN_DOCUMENT", "viewer_rendered": False,
              "body_encoding": "FETCH_ARRAYBUFFER_HTTP_ENTITY_BYTES", "captures": {}, "release": None}
    owner = owned_readonly_context(binding)
    phase = "CONTEXT_ENTER"
    try:
        async with owner:
            phase = "INERT_NAVIGATION"
            await owner.page.route(TARGET, lambda route: route.fulfill(status=200, content_type="text/html",
                body='<!doctype html><title>Usense program collector</title><link rel="icon" href="data:,">'))
            await owner.navigate()
            for name, path in endpoints.items():
                phase = "GET_" + name
                binding.check()
                remaining = (utc(binding.data["expires_at"])-datetime.now(timezone.utc)).total_seconds()
                require(remaining > 0, "CAPTURE_WINDOW_EXPIRED")
                response = await asyncio.wait_for(owner.page.evaluate(FETCH, path), timeout=min(30, remaining))
                if response["status"] == "LOGIN_REQUIRED":
                    result["status"] = "LOGIN_REQUIRED"
                    break
                body = base64.b64decode(response.pop("body_base64"), validate=True)
                require(len(body) <= 12000000, "RESPONSE_TOO_LARGE")
                with (binding.output / (name + ".json")).open("xb") as stream:
                    stream.write(body)
                response.update(bytes=len(body), sha256=sha(body), observed_at=datetime.now(timezone.utc).isoformat(),
                    filename=name + ".json", request_counts={layer: owner.policy.counts.get((layer, ORIGIN+path), 0)
                                                               for layer in ("context", "native")})
                result["captures"][name] = response
                require(response["status"] == 200, "CAPTURE_HTTP_FAILURE")
                require(not owner.policy.blocked and all(n == 1 for n in response["request_counts"].values()),
                        "CAPTURE_DUAL_GUARD_UNPROVEN")
                parsed = json.loads(body)
                require(isinstance(parsed, dict) and type(parsed.get("code")) is int and parsed["code"] == 0,
                        "CAPTURE_BUSINESS_FAILURE")
            else:
                result["status"] = "NATIVE_GETS_CAPTURED"
    except BaseException as exc:
        result["status"] = "CAPTURE_FAILED_NO_RETRY"
        if binding.output.exists():
            startup = getattr(owner, "startup_phase", "READY")
            result["error"] = record_exception(binding.output, "capture-error", exc, startup if startup != "READY" else phase)
        else:
            result["error"] = {"type": type(exc).__name__, "code": getattr(exc, "code", "CAPTURE_ERROR")}
    finally:
        if owner is not None:
            result["release"] = owner.release
        result["finished_at"] = datetime.now(timezone.utc).isoformat()
        if binding.output.exists():
            write_new(binding.output / "capture-summary.json", result)
    return result
