"""Standalone, non-executing review of recorded region OCR and alternatives."""
import base64
from html import escape
import json
from pathlib import Path
from PIL import Image


def render_region_report(draft, crop_path):
    p=draft['payload'];e=lambda v:escape(str(v),quote=True)
    parts=['<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>区域自动草稿候选对照</title><style>body{font:16px/1.65 system-ui,sans-serif;background:#f4f6fa;color:#192334;margin:0}main{max-width:1100px;margin:28px auto;padding:24px;background:white}h1{font-size:27px}h2{margin-top:32px}pre,code{font:14px/1.55 Consolas,monospace;white-space:pre-wrap;overflow-wrap:anywhere}pre{padding:14px;background:#f1f4f8}table{border-collapse:collapse;width:100%}td,th{padding:10px;border:1px solid #d3dbe5;text-align:left;vertical-align:top}.hold{padding:14px;background:#fff0c9}img{width:100%;height:auto}summary{cursor:pointer;font-weight:600;margin:15px 0}.selected{background:#e4ecff}</style><main><h1>自动草稿与来源候选</h1><p class="hold">HOLD · 全部未核准。候选数量、两遍一致和来源检查均不是内容准确率；此报告不修改计划或网站。</p>']
    parts.append('<p>'+e(draft['book_id'])+' · '+e(draft['artifact_id'])+'</p>')
    # The existing fixed PNG is embedded unchanged, never uploaded or redrawn.
    encoded=base64.b64encode(Path(crop_path).read_bytes()).decode('ascii')
    with Image.open(crop_path) as original:mime=Image.MIME.get(original.format,'application/octet-stream')
    parts.append('<h2>原始裁片</h2><img alt="原始来源裁片" src="data:'+e(mime)+';base64,'+encoded+'">')
    parts.append('<h2>当前自动首稿</h2><p>首稿使用固定规则，可能漏字、错字或错序。下方保留整式原始结果及派生组合，复制 LaTeX 后可在离线复核界面的文字段中修订。</p>')
    for i,row in enumerate(p['rows'],1):
        parts.append('<h3>第'+str(i)+'行</h3><pre>'+e(''.join(r['text'] for r in row['runs']))+'</pre>')
    parts.append('<h2>正文核心 / 上下文 / 整行后备的原始 OCR</h2>')
    for unit in p['archives']['observations']['payload']['units']:
        parts.append('<details><summary>'+e(unit['kind'])+' · '+e(unit['source_bbox'])+'</summary>')
        for variant in unit['variants']:
            parts.append('<p>'+e(variant['variant_id'])+' · '+e(variant['source_bbox'])+'</p><pre>'+e(json.dumps(variant['raw_ocr_result'],ensure_ascii=False))+'</pre>')
        parts.append('</details>')
    parts.append('<h2>分式候选</h2><p>WHOLE 是一次模型观察的原始 LaTeX；DERIVED 是同一来源分式内带引用的分量组合，不是一次完整 CPU 输出。固定首选只用浅蓝标记，仍未核准。</p>')
    for i,fraction in enumerate(p['fractions'],1):
        parts.append('<details><summary>F'+str(i)+' · '+e(fraction['fraction_id'])+'</summary><table><tr><th>类型 / 引用</th><th>原样 LaTeX（可选择复制）</th></tr>')
        for candidate in fraction['whole_candidates']+fraction['composed_candidates']:
            chosen=' class="selected"' if candidate['candidate_id']==fraction['draft_candidate_id'] else ''
            parts.append('<tr'+chosen+'><td>'+e(candidate['kind'])+'<br>'+e(candidate['candidate_id'])+'</td><td><code>'+e(candidate['latex'])+'</code></td></tr>')
        parts.append('</table></details>')
    parts.append('<h2>未决来源与组装风险</h2><pre>'+e(json.dumps(p['risks'],ensure_ascii=False,indent=2))+'</pre></main></html>')
    return ''.join(parts)
