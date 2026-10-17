# -*- coding: utf-8 -*-
"""Raw nested child logging only; preserve capture/text behavior for the caller."""
from datetime import datetime,timezone
import hashlib
import json
import locale
import os
from pathlib import Path
import subprocess
import time

OUT=Path(__file__).resolve().parents[1]
def write(p,v):
    with p.open('x',encoding='utf8',newline='\n')as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
def install(label):
    original=subprocess.Popen;directory=OUT/'nested'/label;directory.mkdir(parents=True,exist_ok=False);records=[]
    class LoggedPopen(original):
        def __init__(self,args,*positional,**kwargs):
            self.log_dir=directory/('child-%02d'%(len(records)+1));self.log_dir.mkdir()
            self.streams=[(self.log_dir/n).open('xb')for n in ['stdout.log','stderr.log']]
            self.was_text=bool(kwargs.get('text')or kwargs.get('universal_newlines')or kwargs.get('encoding')or kwargs.get('errors'))
            self.encoding_requested=kwargs.pop('encoding',None)or locale.getpreferredencoding(False);self.errors_requested=kwargs.pop('errors',None)or'strict'
            kwargs.pop('text',None);kwargs.pop('universal_newlines',None)
            if os.name=='nt':kwargs['creationflags']=kwargs.get('creationflags',0)|subprocess.CREATE_NO_WINDOW
            self.record={'argv':args,'cwd':str(kwargs.get('cwd')or os.getcwd()),'maximum_timeout_seconds':30,
              'registered_at':datetime.now(timezone.utc).isoformat(),'parent_input_index_sha256':hashlib.sha256((OUT/'input-index.json').read_bytes()).hexdigest(),
              'environment':'not serialized','raw_streams_opened_before_spawn':True}
            write(self.log_dir/'registration.json',self.record);self.tick=time.monotonic();self.logged=False
            super().__init__(args,*positional,**kwargs);self.record['pid']=self.pid
            write(self.log_dir/'started.json',{'pid':self.pid,'started_at':datetime.now(timezone.utc).isoformat()});records.append(self)
        def communicate(self,input=None,timeout=None):
            if isinstance(input,str):input=input.encode(self.encoding_requested,self.errors_requested)
            effective=30 if timeout is None else min(timeout,30)
            try:result=super().communicate(input=input,timeout=effective);timed_out=False
            except subprocess.TimeoutExpired:
                self.kill();result=super().communicate();timed_out=True
            if not self.logged:
                for f,body in zip(self.streams,result):
                    if body is not None:f.write(body)
                    f.close()
                self.record.update(exit_code=self.returncode,alive=self.poll()is None,timed_out=timed_out,
                  effective_timeout_seconds=effective,elapsed_seconds=round(time.monotonic()-self.tick,3),finished_at=datetime.now(timezone.utc).isoformat())
                write(self.log_dir/'completion.json',self.record);self.logged=True
            if timed_out:raise subprocess.TimeoutExpired(self.args,effective,output=result[0],stderr=result[1])
            if self.was_text:return tuple(b.decode(self.encoding_requested,self.errors_requested).replace('\r\n','\n').replace('\r','\n')if b is not None else None for b in result)
            return result
    subprocess.Popen=LoggedPopen
    return records,lambda:setattr(subprocess,'Popen',original)
