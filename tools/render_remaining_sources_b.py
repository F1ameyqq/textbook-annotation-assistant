"""Render the versioned source-processing overlay and pending acceptance list, read-only."""
from pathlib import Path
import argparse,json
import process_remaining_sources_b as processing
import render_chapter_workspace_b as prior

def render(view,inputs):
    processing.need(processing.audit_processing(view,inputs)['source_and_structure_accepted'],'PROCESSING_AUDIT_FAILED')
    p=view['payload'];parent=p['base_workspace'];*_,images=processing.base.prepare(inputs)
    page=prior.render(parent,inputs)
    old='5条旧来源已有答案草稿，14条尚无当前候选；原账本19条保持历史状态。'
    processing.need(page.count(old)==1,'PARENT_SUMMARY_ANCHOR')
    page=page.replace(old,'5条已有题页来源已组装为3份任务答案草稿；其余14条已组装为8份答案证据，题页仍未匹配。原账本19条保持历史状态。')
    page=page.replace('<title>第一章离线内容复核</title>','<title>第一章来源处理与待验收复核</title>')
    parts=['<section id="remaining-sources"><h2>剩余14条来源：8份答案证据</h2><p class="warn">这8份只有答案来源，尚未找到对应题页，没有创建题目或选定配答。表格列的意义也须待题页确认。</p><input id="source-search" aria-label="搜索来源与待验收项" placeholder="搜索例题、训练、来源行或待验收项">']
    for candidate in p['answer_evidence_candidates']:
        source=candidate['source'];name=candidate['source_local_id'];rows=' / '.join(r['line_id']for r in candidate['raw_rows'])
        text=' '.join([name,source['label'],rows]+[c['value']for c in source['cells']]+[r['text']for r in source['runs']])
        parts.append('<details class="source-item" data-filter="'+prior.esc(text)+'"><summary>'+prior.esc(name+' · '+source['label'])+'</summary><p class="note">原行：'+prior.esc(rows)+'。待独立核图和题页匹配，源窗口不是平台精确框。</p>')
        if source['cells']:
            parts.append('<table><tr>'+''.join('<th>位置'+str(c['cell_index'])+'（列义待确认）</th>'for c in source['cells'])+'</tr><tr>'+''.join('<td>'+prior.mathml(c['value'])+'</td>'for c in source['cells'])+'</tr></table>')
        else:parts.append('<p>'+prior.runs_html(source['runs'])+'</p>')
        box=source['region']['bbox']
        parts.append('<img class="source" style="width:'+str((box[2]-box[0])*2)+'px;max-width:100%;image-rendering:pixelated" alt="'+prior.esc(name)+'原像素（显示放大2倍）" src="'+prior.crop_uri(images['viewer-173'],box)+'"><p>仍需：对应题页与独立内容复核。</p></details>')
    parts.append('</section><section id="acceptance-list"><h2>Q16与阅读任务：18项待验收问题</h2><p class="note">每项绑定当前内容范围。这里没有自动核准按钮；独立核对、差异处置及复核记录完成后，才讨论相应范围验收。</p>')
    for item in p['acceptance_queue']['items']:
        parts.append('<details class="acceptance-item" data-filter="'+prior.esc(item['issue_id']+' '+item['label']+' '+item['required_action'])+'"><summary>'+prior.esc(item['issue_id']+' · '+item['label'])+'</summary><p>'+prior.esc(item['required_action'])+'</p><p class="note">来源：'+prior.esc('、'.join(item['source_asset_ids']))+'；当前：已有模型核图记录，独立复核待完成。<br>内容范围摘要：'+prior.esc(item['subject_sha256'])+'</p></details>')
    parts.append('</section>')
    anchor='<section><h2>当前题目候选索引</h2>'
    processing.need(page.count(anchor)==1,'PARENT_INSERTION_ANCHOR');page=page.replace(anchor,''.join(parts)+anchor)
    script="document.getElementById('source-search').addEventListener('input',e=>{const s=e.target.value.toLowerCase();document.querySelectorAll('.source-item,.acceptance-item').forEach(x=>x.hidden=!x.dataset.filter.toLowerCase().includes(s))});"
    page=page.replace('</script>',script+'</script>')
    return page

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--workspace',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();view=processing.base.unique_object(args.workspace.read_bytes());page=render(view,processing.load_inputs())
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_bytes(page.encode('utf-8'))
    print(json.dumps(dict(output=str(args.out),bytes=args.out.stat().st_size,readonly=True)))

if __name__=='__main__':main()
