"""Finite stdlib schema interpreter. Not JSON Schema conformance certification."""
from datetime import datetime
import json
import re

class Rejected(ValueError):
    def __init__(self,code,path):self.code=code;self.path=path;super().__init__(code+' at '+path)
def need(v,code,path):
    if not v:raise Rejected(code,path)
KEYS={'$schema','$id','$comment','$defs','$ref','title','description','discriminator','type','properties','propertyNames','required','additionalProperties','anyOf','oneOf','const','enum','pattern','format','minLength','minItems','maxItems','minimum','maximum','exclusiveMinimum','items','uniqueItems','minProperties'}
def audit(s):
    need(not set(s)-KEYS,'SCHEMA_KEYWORDS',str(set(s)-KEYS))
    for k in ('properties','$defs'):
        for v in s.get(k,{}).values():audit(v)
    for k in ('oneOf','anyOf'):
        for v in s.get(k,[]):audit(v)
    for k in ('items','propertyNames','additionalProperties'):
        if isinstance(s.get(k),dict):audit(s[k])
def validate(v,s,doc=None,path='$'):
    doc=s if doc is None else doc
    if '$ref' in s:
        need(s['$ref'].startswith('#/'),'SCHEMA_EXTERNAL_REF',path)
        target=doc
        for k in s['$ref'][2:].split('/'):target=target[k.replace('~1','/').replace('~0','~')]
        validate(v,target,doc,path)
    for k in ('oneOf','anyOf'):
        if k in s:
            n=0
            for sub in s[k]:
                try:validate(v,sub,doc,path);n+=1
                except Rejected:pass
            need(n==1 if k=='oneOf' else n>0,'SHAPE_'+k,path)
    if 'const' in s:need(v==s['const'] and ((type(v)is bool)==(type(s['const'])is bool)),'SHAPE_CONST',path)
    if 'enum' in s:need(v in s['enum'],'SHAPE_ENUM',path)
    if 'type' in s:
        types={'object':isinstance(v,dict),'array':isinstance(v,list),'string':isinstance(v,str),'integer':type(v)is int,'number':type(v)in(int,float),'boolean':type(v)is bool,'null':v is None}
        need(types[s['type']],'SHAPE_TYPE',path)
    if isinstance(v,dict):
        need(set(s.get('required',[]))<=set(v),'SHAPE_REQUIRED',path)
        need(len(v)>=s.get('minProperties',0),'SHAPE_MIN_PROPERTIES',path)
        props=s.get('properties',{})
        for k,x in v.items():
            if 'propertyNames' in s:validate(k,s['propertyNames'],doc,path)
            if k in props:validate(x,props[k],doc,path+'/'+k)
            elif s.get('additionalProperties') is False:raise Rejected('SHAPE_EXTRA',path+'/'+k)
            elif isinstance(s.get('additionalProperties'),dict):validate(x,s['additionalProperties'],doc,path+'/'+k)
    if isinstance(v,list):
        need(s.get('minItems',0)<=len(v)<=s.get('maxItems',len(v)),'SHAPE_ITEMS',path)
        if s.get('uniqueItems'):need(len({json.dumps(x,sort_keys=True) for x in v})==len(v),'SHAPE_UNIQUE',path)
        if 'items' in s:
            for i,x in enumerate(v):validate(x,s['items'],doc,path+'/'+str(i))
    if isinstance(v,str):
        need(len(v)>=s.get('minLength',0),'SHAPE_LENGTH',path)
        if 'pattern' in s:need(re.search(s['pattern'],v) is not None,'SHAPE_PATTERN',path)
        if 'format' in s:
            need(s['format']=='date-time','SCHEMA_FORMAT',path)
            try:need(datetime.fromisoformat(v.replace('Z','+00:00')).tzinfo is not None,'SHAPE_TIME',path)
            except ValueError:raise Rejected('SHAPE_TIME',path)
    if type(v)in(int,float):
        for k,valid in [('minimum',lambda x:v>=x),('maximum',lambda x:v<=x),('exclusiveMinimum',lambda x:v>x)]:
            if k in s:need(valid(s[k]),'SHAPE_'+k,path)
