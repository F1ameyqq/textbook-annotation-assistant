"""Export a self-contained, read-only local chapter review page. No network assets."""
from pathlib import Path
import argparse, base64, html, io, json, re
from PIL import Image
import build_chapter_workspace_b as model

esc=lambda value:html.escape(str(value),quote=True)

def mathml(text):
    text=text.replace(r'\times','×');pos=0
    def group():
        nonlocal pos
        if pos<len(text) and text[pos]=='{':pos+=1;return parse(True)
        ch=text[pos:pos+1];pos+=len(ch);return '<mi>'+esc(ch)+'</mi>'
    def parse(nested=False):
        nonlocal pos
        parts=[]
        while pos<len(text):
            ch=text[pos]
            if ch=='}' and nested:pos+=1;break
            if text.startswith(r'\frac',pos):
                pos+=5;numerator=group();denominator=group()
                token='<mfrac>'+numerator+denominator+'</mfrac>'
            elif ch in '^_':
                pos+=1;value=group();base=parts.pop() if parts else '<mi></mi>'
                tag='msup' if ch=='^' else 'msub';parts.append('<'+tag+'>'+base+value+'</'+tag+'>');continue
            elif ch=='{':pos+=1;token=parse(True)
            elif ch.isdigit():
                m=re.match(r'\d+(?:\.\d+)?',text[pos:]);s=m.group();pos+=len(s);token='<mn>'+s+'</mn>'
            else:
                pos+=1;tag='mi' if ch.isalpha() else 'mo';token='<'+tag+'>'+esc(ch)+'</'+tag+'>'
            parts.append(token)
        return '<mrow>'+''.join(parts)+'</mrow>'
    return '<math xmlns="http://www.w3.org/1998/Math/MathML" aria-label="'+esc(text)+'">'+parse()+'</math>'

def runs_html(runs):
    return ''.join(mathml(r['text']) if r['format']=='latex' else '<span class="blank">________</span>' if r['format']=='blank' else esc(r['text']) for r in runs)

def crop_uri(raw,box):
    with Image.open(io.BytesIO(raw)) as image:
        crop=image.crop(box);out=io.BytesIO();crop.save(out,format='PNG')
    return 'data:image/png;base64,'+base64.b64encode(out.getvalue()).decode('ascii')

def render(view,inputs):
    audit=model.audit_workspace(view,inputs)
    model.need(audit['source_and_structure_accepted'],'UNVERIFIED_WORKSPACE')
    p=view['payload'];*_,images=model.prepare(inputs)
    pieces=['''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>第一章离线内容复核</title><style>body{font:16px/1.75 system-ui,sans-serif;background:#f5f6fa;color:#243047;margin:0}main{max-width:1100px;margin:auto;padding:28px}h1,h2{line-height:1.4}section,details.item{background:white;border:1px solid #dce2ec;border-radius:12px;padding:20px;margin:18px 0}summary{cursor:pointer;font-weight:600}small,.note{color:#64718b}input{width:95%;padding:12px;border:1px solid #bec8d9;border-radius:8px;font-size:16px}.warn{background:#fff3d6;padding:14px;border-radius:8px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}.source{max-width:100%;height:auto;border:1px solid #ddd}math{font-size:1.15em;margin:0 .12em}p{overflow-wrap:anywhere}.answer{background:#f3f7ff;padding:12px;margin-top:10px}.blank{border-bottom:1px solid #718099}a{color:#245caf}table{border-collapse:collapse;width:100%}td,th{padding:8px;border-bottom:1px solid #ddd;text-align:left}@media(max-width:750px){.grid{display:block}main{padding:12px}}</style><main>
<h1>第一章离线内容复核</h1><p class="warn">当前是局部来源下的待核对草稿。42个题目候选不是整章题数；模型核图与机器检查不等于人工验收。本页只读，不连接标注网站。</p>''']
    pieces.append('<p>42个题目候选 · 66份原答案 · 1份共享材料／3个任务 · 3份新增任务答案草稿</p><p>5条旧来源已有答案草稿，14条尚无当前候选；原账本19条保持历史状态。</p>')
    q16=p['q16_relationship'];q=q16['question_snapshot'];a=q16['answer_snapshot']
    pieces.append('<section id="q16-review"><h2>Q16 · 一定是直角三角形吗</h2><p class="note">三个小问与答案的来源候选；未选定、待独立内容核对。</p><div class="grid"><div><h3>题目</h3>')
    for b in q['blocks']:pieces.append('<p>'+('（'+esc(b['label'])+'）' if b.get('label') else '')+runs_html(b['runs'])+'</p>')
    pieces.append('<a href="#source-viewer-15">查看题页原图</a></div><div><h3>当前答案</h3>')
    for line in a['content_fragments']:pieces.append('<p>'+runs_html(line['runs'])+'</p>')
    pieces.append('<img class="source" alt="Q16答案原像素裁片" src="'+crop_uri(images['viewer-173'],[579,263,1084,367])+'"><p><a href="#source-viewer-173">查看答案页原图</a></p></div></div><h3>11个分式逐槽核对</h3><p class="note">本轮模型核图与当前公式一致，未取得独立人工签核。</p><table><tr><th>槽位</th><th>当前公式</th><th>源像素</th></tr>')
    for slot in p['q16_formula_review']:
        pieces.append('<tr><td>'+esc(slot['slot'])+'</td><td>'+mathml(slot['expected_latex'])+'</td><td><img alt="'+esc(slot['slot'])+'原像素" style="min-height:40px;image-rendering:auto" src="'+crop_uri(images['viewer-173'],slot['source_bbox'])+'"></td></tr>')
    pieces.append('</table></section><section><h2>漫话勾股世界 · 三个任务答案草稿</h2><p><a href="#source-viewer-13">查看共享材料与三个任务的原题页</a></p>')
    for number,draft in enumerate(p['material_answer_drafts'],1):
        pieces.append('<h3>任务（'+str(number)+'）</h3><p class="note">来源补全的模型草稿，配对未选定。</p>')
        for region in draft['source_regions']:
            if region['content_type']=='text':pieces.append('<p>'+runs_html(region['runs'])+'</p>')
            pieces.append('<details><summary>'+('答案图形' if region['content_type']=='image' else '查看这一段的源像素')+'</summary><img class="source" alt="任务'+str(number)+'来源裁片" src="'+crop_uri(images['viewer-173'],region['bbox_xyxy'])+'"></details>')
    pieces.append('</section><section><h2>当前题目候选索引</h2><p class="note">按原分支保留。相同印刷题号可属于不同章节位置，请结合来源查看。</p><input id="search" aria-label="搜索题号、文字或来源" placeholder="搜索题号、文字或来源"><div id="question-list">')
    answers={row['answer_id']:row['native'] for row in p['legacy_answers']}
    for row in p['questions']:
        native=row['native'];text=native.get('text','')
        if not text:text=' '.join(b.get('text',''.join(r.get('text','')for r in b.get('runs',[]))) for b in native.get('blocks',native.get('fragments',[])))
        path=native.get('section_path',native.get('source_question_archive',{}).get('section_path',[]))
        title=' / '.join(path)+' · '+str(native.get('printed_number','未编号'))
        search=' '.join([title,text,row['question_id'],native['asset_id']])
        pieces.append('<details class="item" data-search="'+esc(search)+'"><summary>'+esc(title)+'</summary><small>'+esc(native['asset_id'])+' · 待核对</small>')
        if row['question_id']==model.QID:pieces.append('<p><a href="#q16-review">打开上方三小问题答对照</a></p>')
        elif native.get('blocks'):
            for block in native['blocks']:
                if block['role']=='figure':pieces.append('<img class="source" alt="题目图形" src="'+crop_uri(images[native['asset_id']],block['bbox'])+'">')
                else:pieces.append('<p>'+runs_html(block.get('runs',[]))+'</p>')
        else:pieces.append('<p>'+esc(text)+'</p>')
        if native.get('selected_answer_id') in answers:pieces.append('<div class="answer">原分支答案候选：'+esc(answers[native['selected_answer_id']]['text'])+'</div>')
        pieces.append('<p><a href="#source-'+esc(native['asset_id'])+'">查看来源原图</a></p></details>')
    pieces.append('</div></section><section><h2>八张现有原图</h2><p class="note">这是已收子集，不能证明首章边界或完整页数。</p>')
    for item in p['source_inventory']['verified_local_assets']:
        aid=item['asset_id'];uri='data:image/jpeg;base64,'+base64.b64encode(images[aid]).decode('ascii')
        pieces.append('<details id="source-'+esc(aid)+'"><summary>'+esc(aid)+' · 印刷页观察'+str(item['printed_page_model_visual'])+'</summary><img class="source" alt="'+esc(aid)+'完整原图" src="'+uri+'"></details>')
    pieces.append('''</section><p class="note">离线复核页面 · 2026-10-20 · 所有来源、版本及风险随交付包保存。没有保存或提交标注功能。</p></main><script>document.getElementById('search').addEventListener('input',e=>{const s=e.target.value.toLowerCase();document.querySelectorAll('#question-list .item').forEach(x=>{x.hidden=!x.dataset.search.toLowerCase().includes(s)})});document.querySelectorAll('a[href^="#"]').forEach(a=>a.addEventListener('click',()=>{const target=document.getElementById(a.getAttribute('href').slice(1));if(target&&target.tagName==='DETAILS')target.open=true}));</script></html>''')
    return ''.join(pieces)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--workspace',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();view=model.unique_object(args.workspace.read_bytes());page=render(view,model.load_inputs())
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_bytes(page.encode('utf-8'))
    print(json.dumps({'output':str(args.out),'bytes':args.out.stat().st_size,'readonly':True,'network_assets':0}))

if __name__=='__main__':main()
