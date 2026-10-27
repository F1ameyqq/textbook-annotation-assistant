#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
tools/parallel_probe.py — 「标注平台能否多会话并行」只读探针（v2）

回答三个问题（全程只读，不提交、不画框、不调用任何写接口）：
  1. 本账号能看到几本书（页面内 GET /qieti/api/claim_book/books）
  2. 同一 token 能否同时开两个持久化会话（各自 profile 目录），能不能各自选书/翻页
  3. 一边操作后另一边的 counts / 当前题目 / 页码框 / 画布 是否被带动
     —— 这是"指针滞后"是否跨会话的判据

v2 修正（v1 教训）：
  * 页码输入框的 val 才是"会话当前显示第几页"的权威信号，画布指纹会因异步重绘读到空白（hash="0"）
  * 画布指纹改为整幅网格采样 + 稳定性轮询（连续两次相同才算稳定）
  * 只有 dblclick 加载题目后 counts 才非零，所以跨会话影响必须用"加载题目"这一段来测
  * 新增写请求审计：记录本次运行里所有非 GET 请求路径，证明没有写操作

用法：
    python tools/parallel_probe.py --mode books --profiles work-default
    python tools/parallel_probe.py --profiles work-default,par-b --book 46007447

必需环境（否则 playwright 起不来）：
    export TMP="$PWD/bin/tmp/pw" TEMP="$PWD/bin/tmp/pw"

安全：token 只报长度/存在性，绝不打印/落盘；只发 GET，非 GET 全部记录在案。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bin"))

from live import TARGET, Live  # noqa: E402

OUT_DEFAULT = ROOT / "data" / "derived" / "live" / "parallel_probe.json"
BOOKS_API = "/qieti/api/claim_book/books"
BOOKS_FALLBACK = ("https://www.usense.com" + BOOKS_API
                  + "?page=1&pageSize=50&status_list=1,2,3,4,5,6,7,8,9")

T0 = time.time()


def stamp() -> float:
    return round(time.time() - T0, 2)


def clock() -> str:
    return datetime.now().strftime("%H:%M:%S")


# ------------------------------------------------------------------ JS
# 平台把登录态存成 localStorage['user'] 这一个 JSON（内部字段 access_token），
# 不是独立 key 'user.access_token' —— 两种都兼容，只返回值给 fetch 用，不落盘。
JS_TOKEN = """() => {
  const info = {present: false, len: 0, source: null, url: location.href,
                keys: [], user_len: 0, login_page: /\\/qieti\\/login/.test(location.href)};
  try {
    info.keys = Object.keys(localStorage).sort();
    const u = localStorage.getItem('user');
    info.user_len = u ? u.length : 0;
    let t = localStorage.getItem('user.access_token');
    if (t) info.source = 'key:user.access_token';
    else if (u) {
      try {
        const o = JSON.parse(u);
        t = (o && (o.access_token || (o.user && o.user.access_token))) || null;
        if (t) info.source = 'json:user.access_token';
      } catch (e) { info.parse_err = String(e); }
    }
    if (typeof t === 'string') {
      t = t.trim();
      if (t.length >= 2 && t[0] === '"' && t[t.length - 1] === '"') t = t.slice(1, -1);
      info.present = !!t;
      info.len = t.length;
    }
  } catch (e) { info.err = String(e); }
  return info;
}"""

JS_RAW_TOKEN = """() => {
  try {
    let t = localStorage.getItem('user.access_token');
    if (!t) {
      const u = localStorage.getItem('user');
      if (u) { const o = JSON.parse(u); t = (o && (o.access_token || (o.user && o.user.access_token))) || null; }
    }
    if (typeof t === 'string') {
      t = t.trim();
      if (t.length >= 2 && t[0] === '"' && t[t.length - 1] === '"') t = t.slice(1, -1);
    }
    return t || null;
  } catch (e) { return null; }
}"""

# 整幅网格采样指纹：hash + 非白像素占比（判断画布是"空白"还是"渲染了内容"）
JS_FP = """([idx, stride]) => {
  const cs = document.querySelectorAll('canvas.pdf-canvas');
  const c = cs[idx];
  if (!c) return null;
  const g = c.getContext('2d');
  const W = c.width, H = c.height;
  const st = Math.max(1, Math.round(W * H / 20000));
  let h = 0, nonwhite = 0, n = 0, err = null;
  try {
    const d = g.getImageData(0, 0, W, H).data;
    const step = 4 * st;
    for (let i = 0; i < d.length; i += step) {
      n++;
      const r = d[i], gg = d[i + 1], b = d[i + 2];
      if (r < 240 || gg < 240 || b < 240) nonwhite++;
      h = (h * 31 + r + gg * 7 + b * 13) >>> 0;
    }
  } catch (e) { err = String(e); }
  return {w: W, h: H, hash: h.toString(16), nonwhite: n ? +(nonwhite / n).toFixed(4) : null,
          samples: n, err: err};
}"""

JS_INPUTS = """() => {
  const vis = el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  return [...document.querySelectorAll('input')].filter(vis).map((e, i) => {
    const r = e.getBoundingClientRect();
    return {i: i, ph: e.placeholder || '', x: Math.round(r.x), y: Math.round(r.y),
            w: Math.round(r.width), val: e.value};
  });
}"""

JS_FETCH = """async ([url, hname, hval]) => {
  const headers = {'Content-Type': 'application/json', 'Accept': 'application/json'};
  if (hname && hval) headers[hname] = hval;
  try {
    const r = await fetch(url, {method: 'GET', headers: headers, credentials: 'include'});
    const text = await r.text();
    let body = null;
    try { body = JSON.parse(text); } catch (e) { body = null; }
    return {status: r.status, ok: r.ok, body: body, text_len: text.length,
            text_head: body ? '' : text.slice(0, 300)};
  } catch (e) {
    return {status: -1, ok: false, body: null, err: String(e)};
  }
}"""

# 双击目录树节点加载题目（节点文本可能带徽标前缀，按 token 匹配）
JS_LOAD = """(label) => {
  const norm = s => (s || '').replace(/\\s+/g, ' ').trim();
  const num = String(label).split(' ')[0];
  const nodes = [...document.querySelectorAll('.el-tree-node__content')];
  const hit = nodes.find(n => norm(n.innerText).split(' ').includes(num));
  if (!hit) {
    return {ok: false, total: nodes.length,
            sample: nodes.map(n => norm(n.innerText)).slice(0, 10)};
  }
  hit.dispatchEvent(new MouseEvent('dblclick', {bubbles: true, cancelable: true, view: window}));
  return {ok: true, text: norm(hit.innerText)};
}"""


def books_summary(body) -> dict:
    """从书籍列表响应里抽 id/名称/状态；丢弃任何人员字段。"""
    rows: list[dict] = []

    def walk(x):
        if isinstance(x, dict):
            if "id" in x and any(k in x for k in ("title", "book_name", "name")):
                keep = {}
                for k in ("id", "title", "book_name", "name", "status", "page_count",
                          "question_count", "processing_status", "duplicateCheckStatus"):
                    if k in x:
                        keep[k] = x[k]
                rows.append(keep)
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(body)
    uniq, seen = [], set()
    for r in rows:
        key = str(r.get("id"))
        if key in seen:
            continue
        seen.add(key)
        uniq.append(r)
    total = None
    if isinstance(body, dict):
        for k in ("total", "count", "total_count"):
            if isinstance(body.get(k), int):
                total = body[k]
                break
            data = body.get("data")
            if isinstance(data, dict) and isinstance(data.get(k), int):
                total = data[k]
                break
    return {"rows": uniq, "n": len(uniq), "total_field": total,
            "code": body.get("code") if isinstance(body, dict) else None,
            "msg": (body.get("message") or body.get("msg")) if isinstance(body, dict) else None}


class Sess:
    """一个会话：所有 playwright 调用都串行投递到它自己的单线程执行器。"""

    def __init__(self, label: str, profile: str, book: str, headless: bool = True):
        self.label = label
        self.profile = profile
        self.book = book
        self.headless = headless
        self.ex = ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"sess-{label}")
        self.lv: Live | None = None
        self.auth: dict | None = None        # {"name","value"} — 只在内存
        self.books_url: str | None = None
        self.errors: list[dict] = []         # >=400 的 API 响应
        self.dialogs: list[str] = []
        self.non_get: list[dict] = []        # 写请求审计
        self.get_count = 0
        self._lock = threading.Lock()

    def call(self, fn, *a, **kw):
        return self.ex.submit(fn, *a, **kw)

    # ---------------- 会话内动作 ----------------
    def boot(self) -> dict:
        t = time.time()
        self.lv = Live(headless=self.headless, profile=self.profile)
        self.lv.__enter__()
        page = self.lv.page
        page.on("dialog", self._on_dialog)

        def on_req(req):
            try:
                u = req.url
                if "/qieti/api/" not in u:
                    return
                if req.method == "GET":
                    with self._lock:
                        self.get_count += 1
                else:
                    with self._lock:
                        if len(self.non_get) < 200:
                            self.non_get.append({"t": stamp(), "method": req.method,
                                                 "path": u.split("?")[0]})
                for k, v in (req.headers or {}).items():
                    kl = k.lower()
                    if kl in ("authorization", "access-token", "x-access-token", "token",
                              "satoken", "x-token") and v and len(v) >= 20:
                        with self._lock:
                            if self.auth is None:
                                self.auth = {"name": k, "value": v}
                if BOOKS_API in u:
                    with self._lock:
                        self.books_url = u
            except Exception:
                pass

        def on_resp(resp):
            try:
                if "/qieti/api/" in resp.url and resp.status >= 400:
                    with self._lock:
                        if len(self.errors) < 60:
                            self.errors.append({"t": stamp(), "path": resp.url.split("?")[0],
                                                "status": resp.status,
                                                "method": resp.request.method})
            except Exception:
                pass

        page.on("request", on_req)
        page.on("response", on_resp)
        self.lv.open()
        picked = self.lv.select_book(self.book)
        snap = self.snapshot("boot")
        return {"ok": True, "elapsed": round(time.time() - t, 2),
                "select_book": picked, "snapshot": snap,
                "auth_header_name": self.auth["name"] if self.auth else None,
                "books_url_seen": bool(self.books_url)}

    def _on_dialog(self, d):
        try:
            self.dialogs.append((d.message or "")[:200])
            d.dismiss()
        except Exception:
            pass

    def token_info(self) -> dict:
        return self.lv.page.evaluate(JS_TOKEN)

    def page_inputs(self) -> dict:
        """题目区/答案区各自的页码框 val —— 会话"正在显示第几页"的权威信号。"""
        ins = self.lv.page.evaluate(JS_INPUTS)
        cands = [i for i in ins if not i["ph"] and i["y"] < 120 and i["w"] <= 60]
        cands.sort(key=lambda i: i["x"])
        out = {"raw": [{"ph": i["ph"], "val": i["val"], "x": i["x"]} for i in cands]}
        if len(cands) >= 2:
            out["q"] = cands[0]["val"]
            out["a"] = cands[1]["val"]
        return out

    def _fp_stable(self, idx: int, max_s: float = 6.0) -> dict:
        """整幅指纹，连续两次相同才算稳定（避开异步重绘读到空白）。"""
        page = self.lv.page
        tries, prev = 0, None
        t0 = time.time()
        while time.time() - t0 < max_s:
            tries += 1
            fp = page.evaluate(JS_FP, [idx, 1])
            if fp is not None and prev is not None and fp.get("hash") == prev.get("hash"):
                fp["stable"] = True
                fp["tries"] = tries
                return fp
            prev = fp
            page.wait_for_timeout(350)
        if prev is None:
            return {"err": "no canvas"}
        prev["stable"] = False
        prev["tries"] = tries
        return prev

    def snapshot(self, tag: str) -> dict:
        page = self.lv.page
        try:
            tok = page.evaluate(JS_TOKEN)
        except Exception as e:
            tok = {"err": str(e)}
        st = self.lv.read_state()
        pin = self.page_inputs()
        qfp = self._fp_stable(0)
        afp = self._fp_stable(1)
        return {"t": stamp(), "clock": clock(), "tag": tag, "url": page.url,
                "has_token": bool(tok.get("present")), "token_len": tok.get("len", 0),
                "token_source": tok.get("source"),
                "login_page": bool(tok.get("login_page")),
                "page_q": pin.get("q"), "page_a": pin.get("a"),
                "counts": st.get("counts"), "cur": st.get("cur"), "type": st.get("type"),
                "body_head": (st.get("head") or "")[:120],
                "q": {k: qfp.get(k) for k in ("w", "h", "hash", "nonwhite", "stable", "tries")} if qfp else None,
                "a": {k: afp.get(k) for k in ("w", "h", "hash", "nonwhite", "stable", "tries")} if afp else None}

    def fetch_books(self, tag: str = "books") -> dict:
        tok = self.token_info()
        raw = self.lv.page.evaluate(JS_RAW_TOKEN) if tok.get("present") else None
        if isinstance(raw, str):
            raw = raw.strip() or None
        url = self.books_url or BOOKS_FALLBACK
        variants = []
        if self.auth:
            variants.append(("captured:" + self.auth["name"], self.auth["name"], self.auth["value"]))
        if raw:
            variants.append(("bearer", "Authorization", "Bearer " + raw))
        variants.append(("cookie-only", None, None))

        tries = []
        for name, hn, hv in variants:
            r = self.lv.page.evaluate(JS_FETCH, [url, hn, hv])
            body = r.get("body")
            summ = books_summary(body) if body is not None else None
            ok = r.get("status") == 200 and (summ is None or summ.get("code") in (0, None))
            tries.append({"variant": name, "status": r.get("status"), "ok": ok,
                          "text_len": r.get("text_len"), "text_head": r.get("text_head", ""),
                          "summary": summ})
            if ok:
                break
        best = tries[-1]
        qk = sorted({kv.split("=")[0] for kv in url.split("?")[1].split("&") if kv}) if "?" in url else []
        return {"t": stamp(), "tag": tag, "url_path": url.split("?")[0], "url_query_keys": qk,
                "token": {"present": tok.get("present"), "len": tok.get("len"),
                          "source": tok.get("source"), "keys": tok.get("keys"),
                          "login_page": tok.get("login_page")},
                "variants_tried": [t["variant"] for t in tries],
                "used": best["variant"], "status": best["status"], "ok": best["ok"],
                "books": best.get("summary"), "attempts": tries}

    def goto(self, panel: str, page_no: int, start_at: float | None = None) -> dict:
        if start_at:
            while time.time() < start_at:
                time.sleep(0.01)
        t = time.time()
        res = self.lv.goto_page(panel, page_no)
        res["wall"] = round(time.time() - t, 2)
        snap = self.snapshot(f"after_goto_{panel}_{page_no}")
        res["snapshot"] = snap
        # ui_page 是权威判据（Live.goto_page 的 changed 用 40x40 小块指纹，会漏判）
        key = "page_q" if panel == "q" else "page_a"
        res["ui_page"] = snap.get(key)
        res["ui_page_ok"] = str(snap.get(key)) == str(page_no)
        return res

    def load_question(self, label: str, timeout_s: float = 40.0,
                      settle_s: float = 8.0, start_at: float | None = None) -> dict:
        """双击目录树加载题目。两段等待：
        1) 当前题目切到目标题号；
        2) 状态栏 counts 连续两次相同（加载是异步的，早读会读到上一题/空值）。
        """
        if start_at:
            while time.time() < start_at:
                time.sleep(0.01)
        t = time.time()
        target = str(label).split(" ")[0]
        pre = self.lv.read_state()
        node = self.lv.page.evaluate(JS_LOAD, label)
        if not node.get("ok"):
            return {"ok": False, "node": node, "wall": round(time.time() - t, 2)}

        st, cur = pre, pre.get("cur")
        while time.time() - t < timeout_s and cur != target:
            self.lv.page.wait_for_timeout(400)
            st = self.lv.read_state()
            cur = st.get("cur")
        cur_ok = cur == target

        t2, prev, stable, polls = time.time(), st.get("counts"), False, 0
        while time.time() - t2 < settle_s:
            self.lv.page.wait_for_timeout(700)
            st = self.lv.read_state()
            polls += 1
            if polls >= 2 and st.get("counts") == prev:
                stable = True
                break
            prev = st.get("counts")
        waited = round(time.time() - t, 2)
        counts = st.get("counts")
        return {"ok": bool(cur_ok and stable), "node": node, "waited": waited,
                "cur_ok": cur_ok, "counts_stable": stable, "polls": polls,
                "pre_cur": pre.get("cur"), "cur": cur, "counts": counts,
                "snapshot": self.snapshot(f"after_load_{label}")}

    def close(self) -> dict:
        try:
            if self.lv is not None:
                self.lv.__exit__(None, None, None)
            return {"closed": True}
        except Exception as e:
            return {"closed": False, "err": str(e)}
        finally:
            self.ex.shutdown(wait=False)

    def reap(self) -> dict:
        return {"errors": list(self.errors), "dialogs": list(self.dialogs),
                "non_get_requests": list(self.non_get), "api_get_count": self.get_count}


def resolve_profile(spec: str) -> str:
    p = Path(spec)
    if p.is_dir():
        return str(p.resolve())
    alt = ROOT / "bin" / "browser-profiles" / spec
    if alt.is_dir():
        return str(alt.resolve())
    raise SystemExit(f"[fatal] profile 目录不存在: {spec}")


def diff_snap(ref: dict, now_snap: dict) -> dict:
    """另一会话是否被带动：页码框（权威）/counts/当前题目/画布指纹 四项。"""
    def fp(d, k):
        return (d.get(k) or {})

    return {
        "page_q_same": ref.get("page_q") == now_snap.get("page_q"),
        "page_a_same": ref.get("page_a") == now_snap.get("page_a"),
        "counts_same": ref.get("counts") == now_snap.get("counts"),
        "cur_same": ref.get("cur") == now_snap.get("cur"),
        "q_hash_same": fp(ref, "q").get("hash") == fp(now_snap, "q").get("hash"),
        "a_hash_same": fp(ref, "a").get("hash") == fp(now_snap, "a").get("hash"),
        "affected": not (ref.get("page_q") == now_snap.get("page_q")
                         and ref.get("page_a") == now_snap.get("page_a")
                         and ref.get("counts") == now_snap.get("counts")
                         and ref.get("cur") == now_snap.get("cur")),
        "ref": {"page_q": ref.get("page_q"), "page_a": ref.get("page_a"),
                "counts": ref.get("counts"), "cur": ref.get("cur"),
                "q_hash": fp(ref, "q").get("hash"), "q_nonwhite": fp(ref, "q").get("nonwhite")},
        "now": {"page_q": now_snap.get("page_q"), "page_a": now_snap.get("page_a"),
                "counts": now_snap.get("counts"), "cur": now_snap.get("cur"),
                "q_hash": fp(now_snap, "q").get("hash"),
                "q_nonwhite": fp(now_snap, "q").get("nonwhite")},
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["books", "parallel"], default="parallel")
    ap.add_argument("--profiles", default="work-default,par-b")
    ap.add_argument("--book", default="46007447")
    ap.add_argument("--qpage-a", type=int, default=28)
    ap.add_argument("--qpage-b", type=int, default=100)
    ap.add_argument("--qpage-a2", type=int, default=60)
    ap.add_argument("--qpage-b2", type=int, default=140)
    ap.add_argument("--load-a", default="30", help="A 会话 dblclick 加载的题号")
    ap.add_argument("--load-b", default="12", help="B 会话 dblclick 加载的题号")
    ap.add_argument("--load-same", default="64", help="两会话并发加载的同一题号")
    ap.add_argument("--soak-s", type=float, default=0.0, help="并发巡检时长（秒），0=跳过")
    ap.add_argument("--step-s", type=float, default=30.0, help="巡检间隔（秒）")
    ap.add_argument("--headful", action="store_true")
    ap.add_argument("--out", default=str(OUT_DEFAULT))
    args = ap.parse_args()

    headless = not args.headful
    out_path = Path(args.out)
    if args.mode == "books" and out_path == Path(OUT_DEFAULT):
        # 避免 books 模式覆盖 parallel 模式的完整证据
        out_path = out_path.with_name("parallel_probe_books.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    events: list[dict] = []

    def log(phase: str, **kw):
        ev = {"t": stamp(), "clock": clock(), "phase": phase, **kw}
        events.append(ev)
        body = json.dumps(kw, ensure_ascii=False)
        print(f"[{ev['clock']} +{ev['t']:>7.2f}s] {phase}: {body[:800]}", flush=True)
        try:
            persist()          # 每步落盘：中途被打断也留下已测证据
        except Exception:
            pass
        return ev

    def persist():
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    specs = [s.strip() for s in args.profiles.split(",") if s.strip()]
    profiles = [resolve_profile(s) for s in specs]
    report: dict = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "target": TARGET, "book": args.book, "mode": args.mode,
        "profiles": profiles, "headless": headless,
        "env": {"TMP": os.environ.get("TMP"), "TEMP": os.environ.get("TEMP")},
        "events": events,
    }
    log("start", profiles=[Path(p).name for p in profiles], book=args.book,
        tmp=report["env"]["TMP"])

    # ------------------------------ books 模式 ------------------------------
    if args.mode == "books":
        s = Sess("a", profiles[0], args.book, headless)
        try:
            boot = s.call(s.boot).result()
            report["sessions"] = {"a": {"profile": profiles[0], "boot": boot}}
            bs = boot["snapshot"]
            log("boot_a", ok=boot["ok"], elapsed=boot["elapsed"], page_q=bs["page_q"],
                cur=bs["cur"], counts=bs["counts"], auth=boot["auth_header_name"])
            bk = s.call(s.fetch_books).result()
            report["books"] = {"a": bk}
            rows = ((bk.get("books") or {}).get("rows") or [])
            log("books", ok=bk["ok"], used=bk["used"], n=(bk.get("books") or {}).get("n"),
                total=(bk.get("books") or {}).get("total_field"),
                rows=[(r.get("id"), r.get("title") or r.get("name"), r.get("status"),
                       r.get("page_count"), r.get("question_count")) for r in rows])
            report["verdict"] = {"book_count": (bk.get("books") or {}).get("n"),
                                 "second_book_available": ((bk.get("books") or {}).get("n") or 0) > 1}
        finally:
            report.setdefault("sessions", {}).setdefault("a", {})["reap"] = s.call(s.reap).result()
            report["sessions"]["a"]["close"] = s.call(s.close).result()
            persist()
            print(f"[out] {out_path}")
        return 0

    # ---------------------------- parallel 模式 ----------------------------
    if len(profiles) < 2:
        raise SystemExit("[fatal] parallel 模式需要两个 profile: --profiles a,b")
    A = Sess("a", profiles[0], args.book, headless)
    B = Sess("b", profiles[1], args.book, headless)
    report["sessions"] = {"a": {"profile": profiles[0]}, "b": {"profile": profiles[1]}}
    try:
        # P1 并发启动 + 各自选同一本书
        fa, fb = A.call(A.boot), B.call(B.boot)
        try:
            boot_a = fa.result(timeout=200)
        except Exception:
            boot_a = {"ok": False, "err": traceback.format_exc()[-800:]}
        try:
            boot_b = fb.result(timeout=200)
        except Exception:
            boot_b = {"ok": False, "err": traceback.format_exc()[-800:]}
        report["sessions"]["a"]["boot"] = boot_a
        report["sessions"]["b"]["boot"] = boot_b
        for lbl, bt in (("a", boot_a), ("b", boot_b)):
            sn = bt.get("snapshot") or {}
            log(f"boot_{lbl}", ok=bt.get("ok"), elapsed=bt.get("elapsed"),
                page_q=sn.get("page_q"), page_a=sn.get("page_a"), cur=sn.get("cur"),
                counts=sn.get("counts"), q_nonwhite=(sn.get("q") or {}).get("nonwhite"),
                auth=bt.get("auth_header_name"), err=(bt.get("err") or "")[:160])
        if not (boot_a.get("ok") and boot_b.get("ok")):
            raise SystemExit("[fatal] 至少一个会话启动/选书失败")

        base_a = boot_a["snapshot"]
        base_b = boot_b["snapshot"]

        # P2 两边各自读书籍列表（token 是否双活 + 能看到几本书）
        ka, kb = A.call(A.fetch_books, "books_a"), B.call(B.fetch_books, "books_b")
        bk_a, bk_b = ka.result(), kb.result()
        report["books"] = {"a": bk_a, "b": bk_b}
        for lbl, bk in (("a", bk_a), ("b", bk_b)):
            rows = ((bk.get("books") or {}).get("rows") or [])
            log(f"books_{lbl}", ok=bk["ok"], used=bk["used"], status=bk["status"],
                token={"present": bk["token"]["present"], "len": bk["token"]["len"],
                       "source": bk["token"]["source"]},
                n=(bk.get("books") or {}).get("n"),
                total=(bk.get("books") or {}).get("total_field"),
                rows=[(r.get("id"), r.get("title") or r.get("name"), r.get("status"),
                       r.get("page_count"), r.get("question_count")) for r in rows])

        # P3 串行交叉：A 翻页 → 立刻读 B
        r_a1 = A.call(A.goto, "q", args.qpage_a).result()
        sa1 = r_a1.get("snapshot") or {}
        sb1 = B.call(B.snapshot, "after_a_goto").result()
        report["phase_A_goto"] = {"goto": r_a1, "b_now": sb1, "b_affected": diff_snap(base_b, sb1)}
        d1 = report["phase_A_goto"]["b_affected"]
        log("A_goto_alone", page=args.qpage_a, ui_page_a=sa1.get("page_q"),
            changed=r_a1["changed"], a_counts=sa1.get("counts"),
            b_page_q=sb1.get("page_q"), b_counts=sb1.get("counts"),
            b_affected=d1["affected"], b_page_q_same=d1["page_q_same"],
            b_counts_same=d1["counts_same"], b_q_hash_same=d1["q_hash_same"])

        # P4 串行交叉：B 翻页 → 立刻读 A
        r_b1 = B.call(B.goto, "q", args.qpage_b).result()
        sb1b = r_b1.get("snapshot") or {}
        sa2 = A.call(A.snapshot, "after_b_goto").result()
        report["phase_B_goto"] = {"goto": r_b1, "a_now": sa2, "a_affected": diff_snap(sa1, sa2)}
        d2 = report["phase_B_goto"]["a_affected"]
        log("B_goto_alone", page=args.qpage_b, ui_page_b=sb1b.get("page_q"),
            changed=r_b1["changed"], b_counts=sb1b.get("counts"),
            a_page_q=sa2.get("page_q"), a_counts=sa2.get("counts"),
            a_affected=d2["affected"], a_page_q_same=d2["page_q_same"],
            a_counts_same=d2["counts_same"], a_q_hash_same=d2["q_hash_same"])

        # P5 A 加载题目（dblclick，异步）→ 立刻读 B：指针滞后是否跨会话的关键段
        lq_a = A.call(A.load_question, args.load_a).result()
        sa3 = lq_a.get("snapshot") or {}
        sb2 = B.call(B.snapshot, "after_a_load").result()
        report["phase_A_load"] = {"load": lq_a, "b_now": sb2, "b_affected": diff_snap(sb1b, sb2)}
        d3 = report["phase_A_load"]["b_affected"]
        log("A_load_question", label=args.load_a, ok=lq_a.get("ok"),
            waited=lq_a.get("waited"), a_counts=sa3.get("counts"), a_cur=sa3.get("cur"),
            b_counts=sb2.get("counts"), b_cur=sb2.get("cur"),
            b_affected=d3["affected"], b_counts_same=d3["counts_same"],
            b_cur_same=d3["cur_same"], b_q_hash_same=d3["q_hash_same"])

        # P6 B 加载另一题 → 立刻读 A（反向）
        lq_b = B.call(B.load_question, args.load_b).result()
        sb3 = lq_b.get("snapshot") or {}
        sa4 = A.call(A.snapshot, "after_b_load").result()
        report["phase_B_load"] = {"load": lq_b, "a_now": sa4, "a_affected": diff_snap(sa3, sa4)}
        d4 = report["phase_B_load"]["a_affected"]
        log("B_load_question", label=args.load_b, ok=lq_b.get("ok"),
            waited=lq_b.get("waited"), b_counts=sb3.get("counts"), b_cur=sb3.get("cur"),
            a_counts=sa4.get("counts"), a_cur=sa4.get("cur"),
            a_affected=d4["affected"], a_counts_same=d4["counts_same"],
            a_cur_same=d4["cur_same"], a_q_hash_same=d4["q_hash_same"])

        # P7 真并发：两边同时翻到不同页
        start = time.time() + 0.6
        fa2 = A.call(A.goto, "q", args.qpage_a2, start)
        fb2 = B.call(B.goto, "q", args.qpage_b2, start)
        ra2, rb2 = fa2.result(), fb2.result()
        sa5 = A.call(A.snapshot, "after_concurrent").result()
        sb4 = B.call(B.snapshot, "after_concurrent").result()
        report["phase_concurrent"] = {"a_goto": ra2, "b_goto": rb2, "a_after": sa5, "b_after": sb4}
        log("concurrent_goto", page_a=args.qpage_a2, page_b=args.qpage_b2,
            a={"ui_page": sa5.get("page_q"), "ui_ok": ra2.get("ui_page_ok"),
               "changed_flag": ra2["changed"], "wall": ra2["wall"],
               "counts": sa5.get("counts"), "q_nonwhite": (sa5.get("q") or {}).get("nonwhite")},
            b={"ui_page": sb4.get("page_q"), "ui_ok": rb2.get("ui_page_ok"),
               "changed_flag": rb2["changed"], "wall": rb2["wall"],
               "counts": sb4.get("counts"), "q_nonwhite": (sb4.get("q") or {}).get("nonwhite")},
            ui_pages_differ=sa5.get("page_q") != sb4.get("page_q"))

        # P8 并发加载同一题（同一本书同一题，两边同时双击加载 → 读一致性）
        start3 = time.time() + 0.6
        fa4 = A.call(A.load_question, args.load_same, 40.0, 8.0, start3)
        fb4 = B.call(B.load_question, args.load_same, 40.0, 8.0, start3)
        la4, lb4 = fa4.result(), fb4.result()
        sa6 = A.call(A.snapshot, "after_same_load").result()
        sb5 = B.call(B.snapshot, "after_same_load").result()
        counts_equal = sa6.get("counts") == sb5.get("counts")
        report["phase_same_load"] = {
            "label": args.load_same, "a_load": la4, "b_load": lb4,
            "a_after": sa6, "b_after": sb5, "counts_equal": counts_equal,
            "cross": diff_snap(sa6, sb5)}
        log("concurrent_same_question", label=args.load_same,
            a={"ok": la4.get("ok"), "waited": la4.get("waited"), "counts": sa6.get("counts"),
               "cur": sa6.get("cur"), "page_a": sa6.get("page_a")},
            b={"ok": lb4.get("ok"), "waited": lb4.get("waited"), "counts": sb5.get("counts"),
               "cur": sb5.get("cur"), "page_a": sb5.get("page_a")},
            counts_equal=counts_equal)

        # P9 并发巡检：两边各自反复读同一接口，看会不会被踢/被限流
        soak: list[dict] = []
        if args.soak_s > 0:
            t_end = time.time() + args.soak_s
            i = 0
            while time.time() < t_end:
                time.sleep(max(5.0, args.step_s))
                i += 1
                fa5 = A.call(A.fetch_books, f"soak_{i}")
                fb5 = B.call(B.fetch_books, f"soak_{i}")
                ba5, bb5 = fa5.result(), fb5.result()
                sa7 = A.call(A.snapshot, f"soak_{i}").result()
                sb6 = B.call(B.snapshot, f"soak_{i}").result()
                row = {"i": i, "t": stamp(),
                       "a": {"ok": ba5["ok"], "status": ba5["status"],
                             "token_len": ba5["token"]["len"],
                             "login": ba5["token"]["login_page"],
                             "page_q": sa7.get("page_q"), "cur": sa7.get("cur")},
                       "b": {"ok": bb5["ok"], "status": bb5["status"],
                             "token_len": bb5["token"]["len"],
                             "login": bb5["token"]["login_page"],
                             "page_q": sb6.get("page_q"), "cur": sb6.get("cur")}}
                soak.append(row)
                log("soak", **row)
        report["soak"] = {"seconds": args.soak_s, "checks": soak}

        # P10 收尾：两边 token 是否仍双活
        ka2 = A.call(A.fetch_books, "books_final_a")
        kb2 = B.call(B.fetch_books, "books_final_b")
        bk_a2, bk_b2 = ka2.result(), kb2.result()
        fin_a = A.call(A.snapshot, "final").result()
        fin_b = B.call(B.snapshot, "final").result()
        report["final"] = {"books_a": bk_a2, "books_b": bk_b2, "a": fin_a, "b": fin_b}
        log("final_tokens",
            a={"ok": bk_a2["ok"], "status": bk_a2["status"],
               "token_len": bk_a2["token"]["len"], "login_page": bk_a2["token"]["login_page"],
               "url": fin_a["url"], "ui_page": fin_a.get("page_q")},
            b={"ok": bk_b2["ok"], "status": bk_b2["status"],
               "token_len": bk_b2["token"]["len"], "login_page": bk_b2["token"]["login_page"],
               "url": fin_b["url"], "ui_page": fin_b.get("page_q")})

        n_books = ((bk_a2.get("books") or {}).get("n")
                   or (bk_a.get("books") or {}).get("n") or 0)
        cross_influence = bool(
            report["phase_A_goto"]["b_affected"]["affected"]
            or report["phase_B_goto"]["a_affected"]["affected"]
            or report["phase_A_load"]["b_affected"]["affected"]
            or report["phase_B_load"]["a_affected"]["affected"])
        report["verdict"] = {
            "book_count_visible": n_books,
            "second_book_available": n_books > 1,
            "two_sessions_booted": True,
            "token_valid_in_both_at_end": bool(bk_a2["ok"] and bk_b2["ok"]),
            "token_len_a": bk_a2["token"]["len"], "token_len_b": bk_b2["token"]["len"],
            "cross_session_any_influence": cross_influence,
            "cross_after_other_goto": bool(report["phase_A_goto"]["b_affected"]["affected"]
                                           or report["phase_B_goto"]["a_affected"]["affected"]),
            "cross_after_other_load": bool(report["phase_A_load"]["b_affected"]["affected"]
                                           or report["phase_B_load"]["a_affected"]["affected"]),
            "concurrent_goto_ok": bool(ra2.get("ui_page_ok") and rb2.get("ui_page_ok")
                                       and sa5.get("page_q") != sb4.get("page_q")),
            "same_question_concurrent_counts_equal": bool(counts_equal),
            "soak_checks": len(soak),
            "soak_all_checks_ok": (all(c["a"]["ok"] and c["b"]["ok"] for c in soak)
                                   if soak else None),
            "a_final": {"ui_page": fin_a.get("page_q"), "counts": fin_a.get("counts"),
                        "cur": fin_a.get("cur")},
            "b_final": {"ui_page": fin_b.get("page_q"), "counts": fin_b.get("counts"),
                        "cur": fin_b.get("cur")},
        }
        log("verdict", **report["verdict"])
    except SystemExit:
        raise
    except Exception:
        report["error"] = traceback.format_exc()[-2000:]
        log("error", err=report["error"][-600:])
    finally:
        for lbl, s in (("a", A), ("b", B)):
            try:
                report["sessions"][lbl]["reap"] = s.call(s.reap).result(timeout=60)
            except Exception:
                pass
            try:
                report["sessions"][lbl]["close"] = s.call(s.close).result(timeout=90)
            except Exception as e:
                report["sessions"][lbl]["close"] = {"err": str(e)}
        persist()
        print(f"[out] {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
