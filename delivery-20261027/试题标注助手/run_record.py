#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
run_record.py — 交付形态的「课时录入」（模拟客户环境：一条命令跑完，浏览器可见）

客户视角：双击 → 选课时 → 自动跑完 → 出报告。中间不需要人操作，只在屏幕上看着。

本脚本做四件事：
  1. 离线测量该课时所在页（源图从 OSS 直取，不需要登录）
  2. 接管已开着的可见 Edge（CDP 9222），选中课时目录、翻到正确页
  3. 逐题：画题干框 → 一键识别 → order 闸门 → 提交 → 服务端回读
  4. 输出逐题耗时表 + 总表（报告/课时_<dir>.md）

安全闸门（缺一不可）：
  - 识别返回的 results[].question_order 全部等于预期题号
  - 提交响应 question_order 符合预期
  - 每题提交后立即回读

用法：
    python run_record.py --book 46007447 --qpage 34 --lesson "第2课时 二次根式的化简及加减运算" \
        --start 2 --count 9 [--dry]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
for cand in (HERE / "tools", HERE.parent / "tools", HERE.parent.parent / "tools"):
    if (cand / "page_measure.py").exists():
        sys.path.insert(0, str(cand))
        break
sys.path.insert(0, str(HERE))

import page_measure as pm  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CFG = {"book": "46007447", "oss": "https://oss-ef-bd-2026-gz.oss-cn-guangzhou.aliyuncs.com/upload_images",
       "page_offset": -1}


# ------------------------------------------------------------------ 浏览器
def open_browser():
    from live_cdp import LiveCDP
    lv = LiveCDP()
    lv.__enter__()
    if not lv.canvases():
        lv.select_book(CFG["book"])
    return lv


CLICK_NODE = """(label) => {
  const norm = s => (s || '').replace(/\\s+/g, ' ').trim();
  const hit = [...document.querySelectorAll('.el-tree-node__content')]
    .find(n => norm(n.innerText) === label);
  if (!hit) return {ok: false};
  hit.click();                       // 单击=选中目录
  return {ok: true};
}"""

CLICK_TEXT = """(name) => {
  const vis = el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const c = [...document.querySelectorAll('button, .el-button, span, div')]
    .filter(vis).filter(e => (e.innerText || '').trim() === name);
  if (!c.length) return {ok: false};
  c[c.length - 1].click();
  return {ok: true};
}"""

HOOK = """() => {
  window.__capR = {ocr: null, commit: null};
  const OX = window.XMLHttpRequest;
  const op = OX.prototype.open, se = OX.prototype.send;
  OX.prototype.open = function (m, u) { this.__u = u; return op.apply(this, arguments); };
  OX.prototype.send = function (b) {
    this.addEventListener('load', () => {
      const u = String(this.__u || '');
      if (u.includes('batch-ocr-task')) window.__capR.ocr = String(this.responseText).slice(0, 20000);
      if (u.includes('commit_unified_submit')) window.__capR.commit = String(this.responseText).slice(0, 3000);
    });
    return se.apply(this, arguments);
  };
  return 'hooked';
}"""

READBACK = """async (order) => {
  const raw = localStorage.getItem('user'); const tok = JSON.parse(raw).access_token;
  const r = await fetch(`/qieti/api/annotate_pic/get_manual_annotations_unified_by_order_in_level/46007447/${order}`,
    {headers: {Authorization: 'Bearer ' + tok}});
  const j = await r.json(); const d = j.data || [];
  return {n: d.length, types: d.map(x => x.type), pages: d.map(x => x.page_index)};
}"""


def drag(lv, ox, oy, p1, p2, steps=16, pause=0.45):
    lv.page.mouse.move(ox + p1[0], oy + p1[1])
    time.sleep(pause)
    lv.page.mouse.down()
    time.sleep(pause)
    lv.page.mouse.move(ox + p2[0], oy + p2[1], steps=steps)
    time.sleep(pause)
    lv.page.mouse.up()
    time.sleep(1.0)


OPEN_SELECT = """() => {
  const vis = el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const s = [...document.querySelectorAll('.el-select')].filter(vis)[0];
  if (!s) return {ok: false};
  const r = s.getBoundingClientRect();
  return {ok: true, x: Math.round(r.x + r.width / 2), y: Math.round(r.y + r.height / 2)};
}"""

PICK_ITEM = """(name) => {
  const vis = el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const items = [...document.querySelectorAll('.el-select-dropdown__item')].filter(vis);
  const hit = items.find(e => (e.innerText || '').trim() === name);
  if (!hit) return {ok: false, options: items.map(e => (e.innerText || '').trim())};
  for (const t of ['mousedown', 'mouseup', 'click'])
    hit.dispatchEvent(new MouseEvent(t, {bubbles: true, cancelable: true, view: window}));
  return {ok: true};
}"""

TYPE_TEXT = """() => {
  const m = document.body.innerText.replace(/\s+/g, ' ').match(/题型[:：]\s*(\S{0,8})/);
  return m ? m[1] : null;
}"""


def ensure_type(lv, want: str) -> str:
    """没选题型就先选；返回当前题型显示。不选题型平台会拒绝提交（不发请求）。"""
    cur = lv.page.evaluate(TYPE_TEXT)
    if cur and cur != "请选择题型":
        return cur
    sel = lv.page.evaluate(OPEN_SELECT)
    if not sel.get("ok"):
        return cur or "?"
    lv.page.mouse.click(sel["x"], sel["y"])
    lv.page.wait_for_timeout(900)
    lv.page.evaluate(PICK_ITEM, want)
    lv.page.wait_for_timeout(1000)
    return lv.page.evaluate(TYPE_TEXT)



def draw_box(lv, role: str, css, expect_q: int, tries: int = 3) -> bool:
    """
    画一个框并校验 counts 恰好 +1（question 区）。
    失败重试：换起手方向（右下→左上），避免落在已有框的 handle 上（SOP #26）。
    """
    for i in range(tries):
        lv.page.evaluate(CLICK_TEXT, role)
        lv.page.wait_for_timeout(1200)
        before = (lv.read_state().get("counts") or {}).get("question", 0)
        if i % 2 == 0:
            drag(lv, lv.canvases()[0]["x"], lv.canvases()[0]["y"],
                 (css[0], css[1]), (css[2], css[3]))
        else:
            drag(lv, lv.canvases()[0]["x"], lv.canvases()[0]["y"],
                 (css[2], css[3]), (css[0], css[1]))
        after = (lv.read_state().get("counts") or {}).get("question", 0)
        if after == before + 1:
            return True
        print(f"    画框未生效（{before}→{after}），重试 {i + 2}/{tries}")
    return False


def measure_page(img: Path):
    import cv2
    import numpy as np
    import page_measure as pm
    from rapidocr_onnxruntime import RapidOCR
    bgr = cv2.imdecode(np.frombuffer(img.read_bytes(), np.uint8), cv2.IMREAD_COLOR)
    H, W = bgr.shape[:2]
    mask = pm.ink_mask(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY))
    panels = pm.column_windows(mask)
    rows = [pm.row_segments(mask, x1, x2, 0, H) for x1, x2 in panels]
    res, _ = RapidOCR()(bgr)
    atoms = [{"text": str(it[1]), "score": float(it[2]) if len(it) > 2 else 0.0,
              "x1": int(min(p[0] for p in it[0])), "y1": int(min(p[1] for p in it[0])),
              "x2": int(max(p[0] for p in it[0])), "y2": int(max(p[1] for p in it[0]))}
             for it in (res or [])]
    qs, _ = pm.build_questions(panels, rows, atoms, H)
    return W, H, qs, atoms


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", default=CFG["book"])
    ap.add_argument("--qpage", type=int, required=True)
    ap.add_argument("--lesson", required=True)
    ap.add_argument("--start", type=int, default=1, help="从第几题开始（1-based）")
    ap.add_argument("--count", type=int, default=10, help="连做几题")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--fix", action="append", default=[],
                    help="覆盖某个题的测量框，格式 qnum:x1,y1,x2,y2（源图像素）")
    args = ap.parse_args()
    CFG["book"] = args.book

    out_dir = HERE / "报告"
    out_dir.mkdir(parents=True, exist_ok=True)
    cache = out_dir / "_源图"
    cache.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    t_all = time.time()
    # ---------- 1. 取源图 + 测量 ----------
    n = args.qpage + CFG["page_offset"]
    img = cache / f"{args.book}_p{args.qpage}.jpg"
    t0 = time.time()
    if not img.exists() or img.stat().st_size < 10_000:
        url = f"{CFG['oss']}/{args.book}/{args.book}_page_{n}.jpg"
        req = urllib.request.Request(url, headers={"User-Agent": "record/1.0"})
        img.write_bytes(urllib.request.urlopen(req, timeout=60).read())
    t_dl = time.time() - t0

    t0 = time.time()
    W, H, qs, atoms = measure_page(img)
    t_meas = time.time() - t0
    print(f"[测量] 源图 {W}x{H}，题块 {len(qs)} 个，耗时 {t_meas:.1f}s（下载 {t_dl:.1f}s）")
    if not qs:
        print("[中止] 本页没测出题块")
        return 2

    for spec in args.fix:
        qn, coords = spec.split(":")
        vals = [int(v) for v in coords.split(",")]
        for q in qs:
            if q["num"] == int(qn):
                q["bbox"] = vals
                print(f"[覆盖] Q{qn} 框 → {vals}")

    # ---------- 2. 接管浏览器 ----------
    lv = open_browser()
    print("[浏览器]", json.dumps(lv.goto_page("q", args.qpage), ensure_ascii=False))
    print("[目录]", json.dumps(lv.page.evaluate(CLICK_NODE, args.lesson), ensure_ascii=False))
    lv.page.wait_for_timeout(2000)
    st = lv.read_state()
    print("[初始状态]", json.dumps(st, ensure_ascii=False))
    lv.page.evaluate(HOOK)

    canv = lv.canvases()[0]
    k = W / canv["w"]
    pad = (canv["h"] - H / k) / 2
    ox, oy = canv["x"], canv["y"]
    print(f"[几何] canvas {canv['w']}x{canv['h']}  k={k:.4f}  pad={pad:.2f}")

    # ---------- 3. 逐题 ----------
    rows_out = []
    for q in qs:
        num = q["num"]
        if num < args.start or num >= args.start + args.count:
            continue
        tq = time.time()
        b = q["bbox"]
        css = [b[0] / k, b[1] / k + pad, b[2] / k, b[3] / k + pad]
        # 源图往内收 2px，抵消实测的 −5px 系统残差
        css = [css[0] + 2, css[1] + 2, css[2] - 2, css[3] - 2]
        # 平台硬约束：拖拽位移 < ~12 CSS px 会被当成单击，一个框都不产生（SOP #23）。
        # 小面积题块（如只有一行题干）必须撑到至少 16px 高 / 24px 宽。
        MIN_H, MIN_W = 16.0, 24.0
        if css[3] - css[1] < MIN_H:
            mid = (css[1] + css[3]) / 2
            css[1], css[3] = mid - MIN_H / 2, mid + MIN_H / 2
        if css[2] - css[0] < MIN_W:
            mid = (css[0] + css[2]) / 2
            css[0], css[2] = mid - MIN_W / 2, mid + MIN_W / 2

        st = lv.read_state()
        c0 = st.get("counts") or {}
        if sum(c0.values()) != 0:
            print(f"    [清理] 检测到残留框 {c0}，先 reload 清场")
            lv.page.reload(wait_until="load")
            lv.page.wait_for_timeout(7000)
            if not lv.canvases():
                lv.select_book(CFG["book"])
            lv.goto_page("q", args.qpage)
            lv.page.evaluate(CLICK_NODE, args.lesson)
            lv.page.wait_for_timeout(1500)
            lv.page.evaluate(HOOK)      # reload 会清掉 window.__capR，必须重装
            st = lv.read_state()
        expect = int(st["cur"]) if st.get("cur") else None
        print(f"\n--- Q{num} (预期 order {expect}) 源图框 {b} → css "
              f"({css[0]:.0f},{css[1]:.0f})-({css[2]:.0f},{css[3]:.0f})")

        lv.page.evaluate(HOOK)          # 兜底：确保钩子在位
        if not draw_box(lv, "题目(Q)", css, num):
            print("    [中止] 连续 3 次没画出框 —— 为避免错位，停止本次运行")
            rows_out.append({"q": num, "status": "draw_failed"})
            break
        st_after = lv.read_state()
        print(f"    画框后 counts={st_after.get('counts')}")

        # 选题型（不选则提交被静默拦下，2026-10-27 实测）
        n_opt = len(pm.options_in_block(atoms, b))
        want_type = "选择" if n_opt >= 2 else "填空"
        got_type = ensure_type(lv, want_type)
        print(f"    题型={got_type}（推断 {want_type}，选项 {n_opt} 个）")

        # 识别 + 闸门
        ocr_ok, ocr_res = False, None
        for attempt in (1, 2):
            lv.page.evaluate("() => { window.__capR.ocr = null; }")
            lv.page.evaluate(CLICK_TEXT, "一键识别")
            for _ in range(40):
                lv.page.wait_for_timeout(700)
                ocr_res = lv.page.evaluate("() => window.__capR.ocr")
                if ocr_res:
                    break
            if not ocr_res:
                continue
            data = json.loads(ocr_res)
            res = (data.get("data") or {}).get("results") or []
            orders = sorted({str(r.get("question_order")) for r in res})
            if orders == [str(expect)]:
                ocr_ok = True
                break
            print(f"    [闸门a] order 不符 {orders} ≠ [{expect}]，重试")
        if not ocr_ok:
            print("    [中止] 识别闸门未过，不提交")
            rows_out.append({"q": num, "status": "gate_a_failed"})
            continue

        if args.dry:
            print("    [dry] 停在提交前")
            rows_out.append({"q": num, "status": "dry", "sec": round(time.time() - tq, 1)})
            continue

        # 提交
        lv.page.evaluate("() => { window.__capR.commit = null; }")
        lv.page.evaluate(CLICK_TEXT, "提交修改")
        commit = None
        for _ in range(40):
            lv.page.wait_for_timeout(700)
            commit = lv.page.evaluate("() => window.__capR.commit")
            if commit:
                break
        if not commit:
            toast = lv.page.evaluate("""() => {
              const t = [...document.querySelectorAll('.el-message, .el-message-box, .el-notification')]
                .map(e => (e.innerText || '').replace(/\s+/g, ' ').trim()).filter(Boolean);
              return t.slice(0, 3);
            }""")
            print(f"    [中止] 没拿到提交响应；页面提示={toast}")
            rows_out.append({"q": num, "status": "no_commit_resp", "toast": toast})
            print("    [中止本次运行] 未提交的框会堆在同一题上，必须先清场再重跑")
            break
        body = json.loads(commit)
        d = body.get("data") or {}
        ok = str(d.get("question_order")) == str(expect)
        rb = lv.page.evaluate(READBACK, expect)
        sec = round(time.time() - tq, 1)
        print(f"    提交 inserted={d.get('inserted')} order={d.get('question_order')} | "
              f"回读 {rb} | 本题 {sec}s")
        rows_out.append({"q": num, "order": expect, "inserted": d.get("inserted"),
                         "readback": rb, "sec": sec,
                         "status": "ok" if ok else "order_mismatch"})
        lv.page.wait_for_timeout(800)

    # ---------- 4. 报告 ----------
    total = round(time.time() - t_all, 1)
    okn = sum(1 for r in rows_out if r.get("status") == "ok")
    md = out_dir / f"课时_{stamp}.md"
    lines = [f"# 课时录入报告 {stamp}", "",
             f"- 书 {args.book} / 题目页 {args.qpage} / 课时「{args.lesson}」",
             f"- 测量：{len(qs)} 题块，{t_meas:.1f}s（源图下载 {t_dl:.1f}s）",
             f"- 录入：成功 {okn}/{len(rows_out)} 题，总耗时 {total:.1f}s", "",
             "| 题 | order | 耗时(s) | 状态 | 回读 |", "|---|---|---|---|---|"]
    for r in rows_out:
        lines.append(f"| Q{r.get('q')} | {r.get('order', '-')} | {r.get('sec', '-')} | "
                     f"{r.get('status')} | {r.get('readback', '-')} |")
    lines += ["", "## 成本", "",
              f"- 本题时总耗时 {total:.1f}s；纯测量 {t_meas:.1f}s（这部分**零 token**）",
              "- 交付工具运行时不消耗模型 token（无 LLM 参与）", ""]
    md.write_text("\n".join(lines), encoding="utf-8")
    (out_dir / f"课时_{stamp}.json").write_text(
        json.dumps({"page": args.qpage, "lesson": args.lesson, "t_measure": t_meas,
                    "t_total": total, "rows": rows_out}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    print(f"\n[完成] 成功 {okn}/{len(rows_out)}，总 {total:.1f}s")
    print(f"[报告] {md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
