"""Partition retained dense OCR only at observed blank pixel gutters.

No recognizer, new text, or per-character coordinates are created. Text slices
retain their coarse source span and the old observed number-token anchors.
"""
import copy
import math
import re


def partition(page, lines, details):
    if page['kind']!='image' or page['role']!='answer':return details,[]
    from PIL import Image
    import numpy as np
    with Image.open(page['raw_path']) as image:ink=np.asarray(image.convert('L'))<160
    output=list(details);records=[]
    for line in lines:
        if not line.get('location'):continue
        marks=list(re.finditer(r'(\d{1,2})[.．、]',line['text']))
        if len(marks)<2 or line['text'][:marks[0].start()].strip():continue
        numbers=[int(m[1]) for m in marks]
        if not all(b==a+1 for a,b in zip(numbers,numbers[1:])):continue
        texts=[line['text'][m.end():marks[i+1].start() if i+1<len(marks) else len(line['text'])].strip()
               for i,m in enumerate(marks)]
        if not all(re.fullmatch(r'[A-G]|[0-9]+',text) for text in texts):continue
        tokens=sorted([t for t in details if t.get('parent_line_id')==line['line_id']],key=lambda t:t['bbox'][0])
        if len(tokens)!=len(marks) or any(not re.fullmatch(re.escape(m[1])+r'[.．、]?',t['text'].strip()) for t,m in zip(tokens,marks)):continue
        x1,y1,x2,y2=[int(v) for v in line['bbox']];cuts=[]
        for left,right in zip(tokens,tokens[1:]):
            lo,hi=math.ceil(left['bbox'][2]),math.floor(right['bbox'][0])
            if hi-lo<5:break
            blank=~ink[y1:y2,lo:hi].any(axis=0);runs=[];start=None
            for i,empty in enumerate([*blank,False]):
                if empty and start is None:start=i
                if not empty and start is not None:
                    if i-start>=3:runs.append((start,i))
                    start=None
            runs.sort(key=lambda r:r[1]-r[0],reverse=True)
            if not runs or len(runs)>1 and runs[0][1]-runs[0][0]<=runs[1][1]-runs[1][0]:break
            cut=lo+sum(runs[0])//2
            # The left number alone cannot count as an answer. There must be
            # ink after its observed anchor, before the separating gutter.
            if not ink[y1:y2,math.ceil(left['bbox'][2])+2:lo+runs[0][0]].any():break
            cuts.append(cut)
        if len(cuts)!=len(marks)-1:continue
        bounds=[x1,*cuts,x2];derived=[]
        for i,(mark,token) in enumerate(zip(marks,tokens)):
            end=marks[i+1].start() if i+1<len(marks) else len(line['text'])
            item=copy.deepcopy(token);item.update(line_id=line['line_id']+'/pixel-partition/'+str(i),
                text=line['text'][mark.start():end],bbox=[bounds[i],y1,bounds[i+1],y2],
                score=min(line.get('score',line.get('confidence',0)),token.get('score',token.get('confidence',0))),
                derivation={'kind':'COARSE_TEXT_SPAN_AND_OBSERVED_PIXEL_GUTTER','parent_line_id':line['line_id'],
                    'coarse_text_span':[mark.start(),end],'anchor_line_id':token['line_id'],
                    'source_sha256':page['raw_sha256'],'new_model_calls':0})
            derived.append(item)
        output=[t for t in output if t.get('parent_line_id')!=line['line_id']]+derived
        records.append({'parent_line_id':line['line_id'],'original_tokens':tokens,'derived_tokens':derived})
    return output,records
