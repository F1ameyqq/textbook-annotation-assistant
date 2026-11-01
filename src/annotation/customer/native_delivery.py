"""Map native paper records to accepted readbacks, then use A26 rendering."""
from __future__ import annotations
import base64
import copy
import html
from html.parser import HTMLParser
from pathlib import Path
import shutil
from . import native_renderer as render
from .native_plan import require, _response
from .store import digest, encoded, byte_hash
from annotation.runtime.usense_live.native_export import records


def signature(record):
    return tuple(render.export_zone(record,z) for z in render.ZONES)+(record.get('tishi') or None,record.get('tihao') or None)


def targets(store,job):
    result=[]
    for candidate in job['candidates']:
        if not candidate.get('acceptance_ref'): continue
        accepted=store.get(candidate['acceptance_ref'])
        node=accepted['comparison']['new_node_id'];current=accepted['after']
        record=current['questions'][node];info=_response(record['info'])
        zones={}
        for zone in render.ZONES:
            value=_response(record['zones'][zone]);zones[zone]=render.normalized(value['ocr_result']) if value.get('success') is True else ''
        require(_response(record['zones']['knowledge_point']).get('success') is False,'原生纸卷格式未覆盖知识点分区。')
        result.append({'key':candidate['key'],'printed_number':candidate['printed_number'],'node_id':node,'info_id':info['id'],
            'zones':zones,'signature':tuple(zones.values())+(info.get('tishi') or None,info.get('tihao') or None),
            'allowed_images': [f['image_path'] for f in _response(record['annotations'])]})
    require(bool(result),'当前任务没有已读回的具体题目。')
    return result


class Images(HTMLParser):
    def __init__(self):super().__init__();self.urls=[]
    def handle_starttag(self,tag,attrs):
        if tag=='img':self.urls.append(dict(attrs).get('src'))
    def handle_startendtag(self,tag,attrs):self.handle_starttag(tag,attrs)


def match(raw,expected):
    parsed=records(raw);used=set();matches=[]
    for target in expected:
        choices=[(line,record) for line,record in parsed if signature(record)==tuple(target['signature'])]
        require(len(choices)==1 and choices[0][0] not in used,'平台导出记录不能唯一匹配已读回内容。')
        line,record=choices[0];used.add(line)
        matches.append({**copy.deepcopy(target),'line':line,'record':record})
    return matches


def build(store,job,export,transport):
    raw=Path(export['path']).read_bytes()
    require(byte_hash(raw)==export['sha256'],'导出原件改变。')
    matches=match(raw,targets(store,job))
    output=store.root/'native-deliveries'/job['id']/digest([export['sha256'],job['candidates']])
    output.mkdir(parents=True,exist_ok=False);assets=output/'assets';assets.mkdir()
    for name in ('tex-svg.js','MathJax-LICENSE'):shutil.copyfile(Path(__file__).parent/'assets'/name,assets/name)
    require(byte_hash((assets/'tex-svg.js').read_bytes())=='d4295dc33744836935c1399feece5159577b34c5c8ffb9f1c6324cd82e03a882','固定 MathJax 改变。')
    sections=[];formulas=[];image_receipts=[]
    for index,item in enumerate(matches,1):
        image_map={};zone_html=[]
        for zone in render.ZONES:
            text=render.export_zone(item['record'],zone);parser=Images();parser.feed(text)
            for url in parser.urls:
                require(url in item['allowed_images'],'导出图片未绑定独立读回题框。')
                if url not in image_map:
                    source=transport.download_original(url,allow_crop=True)
                    image_raw=Path(source['raw_path']).read_bytes()
                    from PIL import Image
                    import io
                    with Image.open(io.BytesIO(image_raw)) as picture:
                        picture.load();mime=Image.MIME.get(picture.format)
                    require(mime in {'image/jpeg','image/png','image/webp'},'原生图片嵌入格式不支持。')
                    image_map[url]={'base64':base64.b64encode(image_raw).decode(),'mime':mime,
                        'width':source['width'],'height':source['height'],'printed_question':index}
                    image_receipts.append(source)
            safe=render.FORMULA.sub(lambda m:html.escape(m.group(),quote=False),text)
            renderer=render.Content(image_map,index,zone);renderer.feed(safe);renderer.close()
            formulas.extend(renderer.formulas)
            zone_html.append('<section class="zone '+zone+'"><h3>'+html.escape(zone)+'</h3>'+''.join(renderer.parts)+'</section>')
        sections.append('<article><h2>第 '+html.escape(item['printed_number'])+' 题</h2>'+''.join(zone_html)+'</article>')
    config="window.MathJax={startup:{typeset:true},loader:{load:[]},tex:{packages:['base','ams']},svg:{fontCache:'local'},options:{enableMenu:false,enableAssistiveMml:false}};"
    page='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
    page+='<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; img-src data:; style-src \'unsafe-inline\'; script-src \'self\' \'unsafe-inline\'; font-src \'none\'; connect-src \'none\'">'
    page+='<title>'+html.escape(job['lesson'])+'</title><style>'+render.CSS+'</style><main><header><h1>'+html.escape(job['lesson'])+'</h1>'
    page+='<p>当前任务原生导出，与独立读回逐项匹配；不代表整书完成。</p></header>'+''.join(sections)+'</main><script>'+config+'</script><script src="assets/tex-svg.js"></script></html>'
    (output/'index.html').write_text(page,encoding='utf-8');(output/'paper-questions.jsonl').write_bytes(raw)
    (output/'mapping.json').write_bytes(encoded(matches));(output/'formulas.json').write_bytes(encoded(formulas))
    receipt={'schema':'CustomerNativeDelivery/v1','native_export':export,'mapped_count':len(matches),'images':image_receipts,
        'formula_count':len(formulas),'output':str(output),'visual_acceptance':'NOT_RUN','source': 'PLATFORM_NATIVE_EXPORT_MATCHED_TO_INDEPENDENT_READBACK'}
    receipt.update(observed_question_count=len(job['candidates']),remaining_unaccepted_count=sum(not q.get('acceptance_ref') for q in job['candidates']),
                   source_scope_complete=job.get('source_scope_complete',False))
    (output/'receipt.json').write_bytes(encoded(receipt))
    return receipt


def finish(store,identity,transport):
    job,head=store.job(identity);key=digest([identity,[q['acceptance_ref'] for q in job['candidates'] if q.get('acceptance_ref')]])
    old=store.operation('native-export',key)
    if old:
        require(old['state']=='COMPLETE','原生导出已有失败/未知记录，查看原件，不重新发送保存或导出。')
        receipt=store.get(old['output'])
        if job.get('native_export_ref')!=old['output']:
            job['native_export_ref']=old['output'];store.save_job(job,head,'NATIVE_EXPORT_REUSED')
        return check_display(store,identity)
    store.begin('native-export',key)
    try:
        exported=transport.export_native();receipt=build(store,job,exported,transport)
        ref=store.finish('native-export',key,'COMPLETE',receipt)
        job['native_export_ref']=ref;job['native_export_status']='MAPPED_AND_PACKAGED_VISUAL_NOT_RUN'
        store.save_job(job,head,'NATIVE_EXPORT_COMPLETE')
    except BaseException as exc:
        if store.operation('native-export',key)['state']=='INTENT':
            store.finish('native-export',key,'FAILED_NO_RETRY',{'type':type(exc).__name__,'message':str(exc)})
        raise
    return check_display(store,identity)


def check_display(store,identity,*,explicit_recheck=False,inspector=None):
    """Pure local check; a display failure cannot cause another platform export."""
    from .delivery_display import inspect_delivery
    job,head=store.job(identity)
    require(bool(job.get('native_export_ref')),'请先完成本任务原生交付。')
    receipt=store.get(job['native_export_ref']);output=Path(receipt['output'])
    base=job['native_export_ref']
    history=job.get('display_checks',[])
    matching=[row for row in history if row['delivery_ref']==base]
    if matching and not explicit_recheck:
        previous=store.get(matching[-1]['result_ref'])
        require(previous.get('status')=='AUTOMATED_DISPLAY_CHECK_PASSED' and previous.get('owned_os_release_confirmed') is True,
                '原生交付已保留；显示检查未通过。可点击本地显示复查，不会重新保存或导出。')
        return output
    from uuid import uuid4
    key=digest([base,uuid4().hex if explicit_recheck else 'first'])
    require(store.operation('display-check',key) is None,'此显示检查已有记录；保留原件，显式选择本地复查。')
    store.begin('display-check',key)
    try:
        result=(inspector or inspect_delivery)(output,store.root/'display-checks'/key)
        passed=result.get('status')=='AUTOMATED_DISPLAY_CHECK_PASSED' and result.get('owned_os_release_confirmed') is True
        ref=store.finish('display-check',key,'COMPLETE' if passed else 'FAILED_NO_RETRY',result)
        job.setdefault('display_checks',[]).append({'delivery_ref':base,'result_ref':ref})
        job['native_export_status']='MAPPED_PACKAGED_AND_AUTOMATED_DISPLAY_PASSED' if passed else 'MAPPED_PACKAGED_DISPLAY_FAILED'
        store.save_job(job,head,'NATIVE_DISPLAY_RESULT')
        require(passed,'原生交付已保留，显示检查未通过；查看原记录或显式本地复查。')
        return output
    except BaseException as exc:
        if store.operation('display-check',key)['state']=='INTENT':
            store.finish('display-check',key,'FAILED_NO_RETRY',{'type':type(exc).__name__,'message':str(exc)})
        raise
