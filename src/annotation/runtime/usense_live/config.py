"""Portable configuration and observed GET endpoint construction."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
import tempfile
from urllib.parse import parse_qsl, urlsplit
import uuid

from .core import (APPROVED_CERT_DER, APPROVED_SPKI, LOGIN, ORIGIN, SCHEMA,
                   TARGET, canonical, freeze, require)

ZONES = ("question", "choice", "answer", "analysis", "knowledge_point")


def endpoints(orders=(), pages=(), *, source=False):
    orders, pages = list(orders), list(pages)
    require(len(orders) <= 6 and len(set(orders)) == len(orders) and
            all(type(n) is int and 1 <= n <= 9999 for n in orders), "ORDERS_ONE_BATCH_MAX_SIX")
    require(len(pages) <= 8 and len(set(pages)) == len(pages) and
            all(type(n) is int and 0 <= n <= 9999 for n in pages), "SOURCE_PAGES_MAX_EIGHT")
    result = {"directory": "/qieti/api/annotate_ocr/directory/get?file_id=46007447",
              "frames": "/qieti/api/annotate_pic/get_manual_annotations_unified/46007447"}
    if source:
        result["source"] = "/qieti/api/annotate_pic/pre_annotation_source/46007447?annotationType=mr_pre"
    for order in orders:
        result[f"q{order}_annotations"] = f"/qieti/api/annotate_pic/get_manual_annotations_unified_by_order_in_level/46007447/{order}"
        result[f"q{order}_info"] = f"/qieti/api/annotate_pic/get_question_info/46007447/{order}"
        for zone in ZONES:
            result[f"q{order}_{zone}"] = f"/qieti/api/verify_annotation/get-ocr-annotation?file_id=46007447&question_order={order}&zone={zone}"
    for page in pages:
        result[f"page_{page}"] = f"/qieti/api/annotate_pic/pre_annotation/46007447?pageNum={page}&annotationType=mr_pre"
    require(len(result) < 64, "GET_BATCH_TOO_LARGE")
    return result


def capture_endpoints(binding):
    """Recognize only current observed templates; never trust arbitrary filenames."""
    require(binding.data["operation"] == "READONLY_CAPTURE" and binding.data["static_get"] ==
            {"mode": "DISABLED", "max_requests": 0}, "INERT_CAPTURE_CONFIG_REQUIRED")
    observed = {}
    orders, pages, source = set(), set(), False
    for row in binding.data["allowed_get"]:
        if row["url"] == TARGET:
            continue
        require(row["resource_types"] == ["fetch", "xhr"] and row["max_requests"] == 1, "CAPTURE_ONE_GET_PER_URL")
        url = row["url"]
        require(url.startswith(ORIGIN + "/"), "CAPTURE_ORIGIN")
        relative = url[len(ORIGIN):]
        p = urlsplit(relative)
        query = dict(parse_qsl(p.query))
        m = re.fullmatch(r"/qieti/api/annotate_pic/(?:get_manual_annotations_unified_by_order_in_level|get_question_info)/46007447/([1-9][0-9]{0,3})", p.path)
        if m:
            orders.add(int(m[1]))
        elif p.path == "/qieti/api/verify_annotation/get-ocr-annotation" and query.get("question_order", "").isdigit():
            orders.add(int(query["question_order"]))
        elif p.path == "/qieti/api/annotate_pic/pre_annotation/46007447" and query.get("pageNum", "").isdigit():
            pages.add(int(query["pageNum"]))
        elif p.path == "/qieti/api/annotate_pic/pre_annotation_source/46007447":
            source = True
        observed[relative] = row
    expected = endpoints(sorted(orders), sorted(pages), source=source)
    require(set(observed) == set(expected.values()), "CAPTURE_ENDPOINT_SET_INCOMPLETE_OR_UNOBSERVED")
    return expected


def configure(*, profile, output_root, config_path, coordinator, executor, reviewer,
              authorization_reference, orders=(), pages=(), source=False, login=False,
              tls_approval_reference=None, proxy_server=None, seconds=600, now=None):
    require(type(seconds) is int and 30 <= seconds <= 900, "WINDOW_SECONDS_30_TO_900")
    current = now or datetime.now(timezone.utc)
    prefix = "usense-login-" if login else "usense-readonly-"
    run = prefix + current.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:8]
    target = LOGIN if login else TARGET
    rules = [{"url": target, "resource_types": ["document"], "max_requests": 1}]
    if login:
        require(not list(orders) and not list(pages) and not source, "LOGIN_HAS_NO_BUSINESS_READS")
        for path in ("/qieti/api/user_login/profile", "/qieti/api/user_login/config/permissions",
                     "/qieti/api/user_login/config/teams", "/qieti/version.json"):
            rules.append({"url": ORIGIN + path, "resource_types": ["xhr", "fetch"], "max_requests": 2})
    else:
        rules += [{"url": ORIGIN + path, "resource_types": ["fetch", "xhr"], "max_requests": 1}
                  for path in endpoints(orders, pages, source=source).values()]
    tls = {"mode": "STRICT"}
    if tls_approval_reference is not None:
        require(isinstance(tls_approval_reference, str) and bool(tls_approval_reference.strip()), "EXPLICIT_TLS_APPROVAL_REFERENCE_REQUIRED")
        tls = {"mode": "USER_APPROVED_EXACT_CERT", "origin": ORIGIN, "leaf_der_sha256": APPROVED_CERT_DER,
               "spki_sha256_base64": APPROVED_SPKI, "approval_reference": tls_approval_reference}
    data = {"schema": "UsenseLiveManualLoginConfig/v1" if login else SCHEMA,
        "book_id": "46007447", "operation": "MANUAL_LOGIN_ONLY" if login else "READONLY_CAPTURE", "run_id": run,
        "actors": {"coordinator": coordinator, "executor": executor, "reviewer": reviewer},
        "target_url": target, "profile": {"directory": str(Path(profile).resolve()), "fingerprint": None,
                                          "usage": "DEDICATED_PROJECT"},
        "output_root": str(Path(output_root).resolve()), "not_before": (current-timedelta(seconds=1)).isoformat(),
        "expires_at": (current+timedelta(seconds=seconds-1)).isoformat(), "headless": not login,
        "allowed_get": rules, "static_get": {"mode": "SAME_ORIGIN_ASSETS" if login else "DISABLED",
                                               "max_requests": 32 if login else 0},
        "tls": tls, "transport": {"mode": "DIRECT" if proxy_server is None else "HTTP_CONNECT_PROXY", "proxy_server": proxy_server},
        "implementation_sha256": None, "authorization_reference": authorization_reference}
    out = Path(config_path).resolve()
    require(out.parent.is_dir(), "CONFIG_PARENT_REQUIRED")
    with tempfile.NamedTemporaryFile(dir=out.parent, suffix=".draft.json", delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(canonical(data))
    try:
        return freeze(temporary, out)
    finally:
        temporary.unlink()
