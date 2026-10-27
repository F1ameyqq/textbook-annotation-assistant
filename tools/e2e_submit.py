#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
bin/e2e_submit.py — 端到端第 2 步：一键识别 → order 闸门 → 提交 → 服务端回读

SOP 的两道硬闸门（缺一不可，2026-10-27 实测过它们拦下过真实错挂）：
  (a) 识别返回的 results[].question_order 必须全部等于预期题号，不等就重试一次，仍不等则中止不提交
  (b) 提交响应的 inserted 必须为 true 且 question_order 符合预期

用法：
    python bin/e2e_submit.py --expect 95 [--dry]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_cdp import LiveCDP  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / "data" / "derived" / "live"

HOOK = """() => {
  window.__cap2 = {ocr: null, commit: null};
  const OX = window.XMLHttpRequest;
  const op = OX.prototype.open, se = OX.prototype.send;
  OX.prototype.open = function (m, u) { this.__u = u; return op.apply(this, arguments); };
  OX.prototype.send = function (b) {
    this.addEventListener('load', () => {
      const u = String(this.__u || '');
      if (u.includes('batch-ocr-task')) window.__cap2.ocr = String(this.responseText).slice(0, 20000);
      if (u.includes('commit_unified_submit')) window.__cap2.commit =
        {req: typeof b === 'string' ? b.slice(0, 4000) : null, body: String(this.responseText).slice(0, 3000)};
    });
    return se.apply(this, arguments);
  };
  return 'hooked';
}"""

CLICK_TEXT = """(name) => {
  const vis = el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const cands = [...document.querySelectorAll('button, .el-button, span, div')]
    .filter(vis).filter(e => (e.innerText || '').trim() === name);
  if (!cands.length) return {ok: false, visible: false};
  const el = cands[cands.length - 1];
  el.click();
  return {ok: true, cls: String(el.className).slice(0, 40)};
}"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--expect", type=int, required=True)
    ap.add_argument("--dry", action="store_true", help="只识别核对，不提交")
    args = ap.parse_args()
    stamp = datetime.now().strftime("%H%M%S")

    with LiveCDP() as lv:
        st = lv.read_state()
        print("[state]", json.dumps(st, ensure_ascii=False))
        if st.get("cur") != str(args.expect):
            print(f"[中止] 当前题目 {st.get('cur')} ≠ 预期 {args.expect}")
            return 2
        c = st.get("counts") or {}
        if c.get("question") != 1:
            print(f"[中止] 题目框数 {c.get('question')} ≠ 1，先确认框画上了")
            return 2

        print("[hook]", lv.page.evaluate(HOOK))

        # ---- 一键识别（最多两次；第一次可能是上一题缓存）----
        ocr = None
        for attempt in (1, 2):
            lv.page.evaluate("() => { window.__cap2.ocr = null; }")
            print(f"[ocr] 第 {attempt} 次点击一键识别 …")
            print("      ", json.dumps(lv.page.evaluate(CLICK_TEXT, "一键识别"), ensure_ascii=False))
            for _ in range(60):            # 最多等 60 秒
                lv.page.wait_for_timeout(1000)
                ocr = lv.page.evaluate("() => window.__cap2.ocr")
                if ocr:
                    break
            if not ocr:
                print("      [警告] 60 秒内没拿到 batch-ocr-task 响应")
                continue
            try:
                data = json.loads(ocr)
            except Exception as e:
                print("      [警告] 响应不是 JSON:", e, ocr[:200])
                continue
            results = data.get("data", {}).get("results") or data.get("results") or []
            orders = sorted({str(r.get("question_order")) for r in results})
            print(f"      processed={data.get('data', {}).get('processed')} results={len(results)} orders={orders}")
            if orders == [str(args.expect)]:
                print("[闸门 a] ✅ 全部 order 都等于预期")
                break
            print("[闸门 a] ❌ order 不符，重试")
            ocr = None
        if not ocr:
            print("[中止] 识别未通过 order 闸门，不提交")
            return 3

        shot = LIVE / f"e2e_ocr_{stamp}.png"
        lv.page.screenshot(path=str(shot))
        print("[shot]", shot)

        # 打印识别出的文本，供人核对
        try:
            data = json.loads(ocr)
            for r in (data.get("data", {}).get("results") or []):
                txt = (r.get("ocr_result") or "").replace("\n", " ")[:160]
                print(f"      [{r.get('zone')}] {txt}")
        except Exception:
            pass

        if args.dry:
            print("[dry] 已停在提交前")
            return 0

        # ---- 提交 ----
        print("[submit] 点击提交修改 …")
        print("      ", json.dumps(lv.page.evaluate(CLICK_TEXT, "提交修改"), ensure_ascii=False))
        commit = None
        for _ in range(40):
            lv.page.wait_for_timeout(1000)
            commit = lv.page.evaluate("() => window.__cap2.commit")
            if commit:
                break
        if not commit:
            print("[中止] 40 秒内没拿到 commit_unified_submit 响应（未确认写入）")
            return 4
        try:
            body = json.loads(commit["body"])
        except Exception:
            print("[警告] 提交响应非 JSON:", commit["body"][:300])
            return 5
        d = body.get("data") or {}
        print("[响应]", json.dumps({k: d.get(k) for k in
                                   ("inserted", "question_order", "success", "append_at_global_end")},
                                  ensure_ascii=False))
        if d.get("inserted") is not True or str(d.get("question_order")) != str(args.expect):
            print("[闸门 b] ❌ inserted/order 不符 —— 立刻停下核查，不要继续录下一题")
            return 6
        print("[闸门 b] ✅ inserted=true 且 order 符合预期")

        # ---- 服务端回读 ----
        rb = lv.page.evaluate("""async (order) => {
          const raw = localStorage.getItem('user');
          const tok = raw ? JSON.parse(raw).access_token : null;
          const r = await fetch(`/qieti/api/annotate_pic/get_manual_annotations_unified_by_order_in_level/46007447/${order}`,
            {headers: {Authorization: 'Bearer ' + tok}});
          const j = await r.json(); const d = j.data || [];
          return {n: d.length, rows: d.map(x => ({type: x.type, page: x.page_index,
                  bbox: String(x.rect_bbox).slice(0, 60), dir: x.directory_id}))};
        }""", args.expect)
        print("[回读]", json.dumps(rb, ensure_ascii=False, indent=1))
        out = LIVE / f"e2e_result_{stamp}.json"
        out.write_text(json.dumps({"state": st, "ocr": json.loads(ocr), "commit": commit,
                                   "readback": rb}, ensure_ascii=False, indent=1), encoding="utf-8")
        print("[out]", out)
        return 0


if __name__ == "__main__":
    sys.exit(main())
