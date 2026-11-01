"""Fill only absent native zones of an unambiguously existing source question."""
import copy,math
from urllib.parse import urlsplit
from .store import digest
from .native_plan import _response,require,source_key,ZONES
from annotation.runtime.usense_live.update import json_same


def locate(current,candidate):
    frames=_response(current['frames']);hits=set()
    for frame in candidate['frames']:
        if frame['zone']!='question':continue
        page=current['pages'][frame['source_sha256']]['viewer_page'];a=frame['bbox']
        for old in frames:
            if old['type']!='question' or old['page_index']!=page:continue
            b=[float(v) for v in old['rect_bbox'].split(',')]
            require(len(b)==4 and all(math.isfinite(v) for v in b),'既有题框坐标无效。')
            if max(a[0],b[0])<min(a[2],b[2]) and max(a[1],b[1])<min(a[3],b[3]):hits.add(old['order_in_level'])
    if not hits:return None
    require(len(hits)==1,'题干来源与多个已有题相交，先核对。')
    order=next(iter(hits));rows=[(node,record) for node,record in current['questions'].items() if _response(record['info'])['order_in_level']==order]
    require(len(rows)==1,'已有题身份不唯一。')
    return {'node_id':rows[0][0],'record':rows[0][1],'order':int(order)}


def bound_frames(current,candidate,record):
    """Return a one-to-one binding to existing native source frames."""
    oldframes=_response(record['annotations']);matched=[];used=set()
    for frame in candidate['frames']:
        source=current['pages'].get(frame['source_sha256'])
        require(source is not None and source['sha256']==frame['source_sha256'] and source['dimensions']==frame['source_dimensions'],
                '候选来源字节或尺寸未绑定当前页面。')
        matches=[]
        for old in oldframes:
            if old['type']!=frame['zone'] or old.get('content_type')!=frame.get('content_type','text') or old['page_index']!=source['viewer_page']:continue
            a=frame['bbox'];b=[float(v) for v in old['rect_bbox'].split(',')]
            require(len(b)==4 and all(math.isfinite(v) for v in b),'既有来源框坐标无效。')
            if frame.get('content_type')=='image':fits=all(abs(x-y)<.001 for x,y in zip(a,b))
            else:fits=b[0]-1<=a[0]<a[2]<=b[2]+1 and b[1]-1<=a[1]<a[3]<=b[3]+1
            if fits:matches.append(old)
        require(len(matches)==1 and matches[0]['rect_id'] not in used,'候选文字或题图没有一一对应的原生来源框。')
        bound=matches[0]
        original=urlsplit(source.get('image_url',''));image=urlsplit(bound.get('image_path',''))
        require(source.get('book_id')==current['book_id'] and original.scheme=='https'
                and not original.query and not original.fragment and not original.username
                and original.netloc.endswith('.aliyuncs.com') and '/'+current['book_id']+'/' in original.path
                and not image.fragment and image._replace(query='').geturl()==original.geturl(),
                '原生来源框的图片地址与已验证原图身份不一致。')
        if frame.get('content_type')=='image':
            x1,y1,x2,y2=frame['bbox']
            require(image.query==f'x-oss-process=image/crop,x_{x1},y_{y1},w_{x2-x1},h_{y2-y1}',
                    '原生题图实际裁剪地址与候选像素范围不一致。')
        used.add(matches[0]['rect_id']);matched.append(matches[0])
    require(used=={f['rect_id'] for f in oldframes},'原生题还包含候选未核对的来源框。')
    return matched


def make(current,candidate,lesson,target):
    from .rich_content import zone_html
    from .native_plan import directory_rows
    match=locate(current,candidate);require(match is not None,'没有唯一既有题。')
    record=match['record'];oldframes=_response(record['annotations']);submissions=[]
    require(all(f['directory_id']==target['node']['id'] for f in oldframes),'已有题不属于所选课时。')
    require(not any(f.get('content_type')=='image' for f in candidate['frames']),'已有题补齐只复用原框；新增题图需单独几何修订。')
    for zone,text in candidate['zones'].items():
        native=[f for f in oldframes if f['type']==zone]
        require(bool(native),'已有题缺少本分区题框，不能冒充新增题处理。')
        for frame in [f for f in candidate['frames'] if f['zone']==zone]:
            page=current['pages'][frame['source_sha256']]['viewer_page'];a=frame['bbox']
            contains=[]
            for old in native:
                b=[float(v) for v in old['rect_bbox'].split(',')]
                if old['page_index']==page and b[0]-1<=a[0]<a[2]<=b[2]+1 and b[1]-1<=a[1]<a[3]<=b[3]+1:contains.append(old)
            require(len(contains)==1,'候选正文来源没有完全落在唯一原题框内。')
        value=zone_html(text);old=_response(record['zones'][zone])
        if old['success']:
            require(old['ocr_result']==value,'已有正文不同；仅补空分区，不能覆盖原内容。')
        else:submissions.append({'zone':zone,'ocr_result':value,'rect_ids':[f['rect_id'] for f in native],'question_order':match['order']})
    require(bool(submissions),'已有题内容相同，应走只读复用。')
    info=_response(record['info']);_,questions=directory_rows(current['directory'])
    payload={'file_id':current['book_id'],'target_directory_id':target['node']['id'],'question_order':match['order'],
        'is_new_question_insertion':False,'insert_after_order':None,'annotations_upsert':[],'annotations_delete_rect_ids':[],
        'ocr_submissions':submissions,'ocr_delete_zones':[],
        'question_info':{k:copy.deepcopy(info[k]) for k in ('tishi','tilei','tihao')},'created_by':None}
    result={'schema':'CustomerNativeExistingFillPlan/v1','book_id':current['book_id'],'key':source_key(current['book_id'],candidate),
        'candidate':copy.deepcopy(candidate),'before':copy.deepcopy(current),'lesson':lesson,'new_order':match['order'],
        'target_node':match['node_id'],'target_info_id':info['id'],'before_count':len(questions),'before_frame_count':len(_response(current['frames'])),
        'payload':payload,'write_authorized':False,'automatic_retry':False}
    result['hash']=digest(result);return result


def decode(plan,receipt):
    expected={'code':0,'message':'success','data':{'inserted':False,'question_order':plan['new_order'],
        'inserted_question_node':None,'success':True,'append_at_global_end':False}}
    require(json_same(receipt,expected),'已有题补齐回执未知；禁止重发。')
    return {'ok':True,'node_id':plan['target_node'],'new_order':plan['new_order'],'inserted':False}


def compare(plan,after,receipt,*,runtime_actor_hashes=None,send_window=None):
    from .native_plan import validate_current,send_window_bounds,CLOCK_TOLERANCE_SECONDS
    from annotation.runtime.usense_live.lesson_insert import _native_time
    decode(plan,receipt);validate_current(after)
    expected=copy.deepcopy(plan['before']);node=plan['target_node']
    before=expected['questions'][node];actual=after['questions'][node]
    adjustments=[]
    for submission in plan['payload']['ocr_submissions']:
        zone=submission['zone'];value=_response(actual['zones'][zone]);old=before['zones'][zone]
        require(list(value) in [['rect_ids','ocr_result','success'],['success','ocr_result','rect_ids']],
                '新建分区字段集合或键序不在已知有限格式。')
        desired={'rect_ids':submission['rect_ids'],'ocr_result':submission['ocr_result'],'success':True}
        require(all(json_same(value[k],desired[k]) for k in desired),'补齐分区内容或题框关联不一致。')
        before['zones'][zone]={**old,'data':{k:desired[k] for k in value}}
        adjustments.append({'zone':zone,'actual_key_order':list(value)})
    oldtime=before['info']['data'].get('updated_at');newtime=actual['info']['data'].get('updated_at')
    if oldtime!=newtime:
        require(send_window is not None,'缺少实际发送窗口，无法接受时间变化。')
        start,end=send_window_bounds(send_window);prior,now=_native_time(oldtime),_native_time(newtime)
        require(prior<now and start<=now<=end,'已有题时间变化不在发送窗口。')
        before['info']['data']['updated_at']=newtime
    require(json_same(expected,after),'已有题补齐改变了题数、原框、其他正文或未知字段。')
    return {'match':True,'new_node_id':node,'new_info_id':plan['target_info_id'],'existing_node_filled':True,'inserted':False,
        'old_questions_preserved':plan['before_count']-1,'old_frames_preserved':plan['before_frame_count'],
        'new_zone_key_orders':adjustments,'readback_hash':digest(after),
        'native_clock_tolerance_seconds':CLOCK_TOLERANCE_SECONDS if send_window is not None else None,
        'runtime_actor_and_send_window_checked':runtime_actor_hashes is not None and send_window is not None}
