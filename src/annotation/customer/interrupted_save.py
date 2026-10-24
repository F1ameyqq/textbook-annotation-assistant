"""Recover a killed customer's durable INTENT from its own immutable writer files.

This is local evidence recovery, never save acceptance or permission to resend.
The ordinary read-only reconcile action is the only caller.
"""
from pathlib import Path
from datetime import datetime
import copy
import json

from annotation.runtime.usense_live.update import loads, json_same
from .native_plan import require
from .prepare import utcnow, candidate_hash
from .store import byte_hash, encoded
from . import wire


def _time(value):
    parsed=datetime.fromisoformat(value)
    require(parsed.utcoffset() is not None,'原运行时间缺少时区。')
    return parsed


def _arg(argv,name):
    require(argv.count(name)==1 and argv.index(name)+1<len(argv),'原 writer 参数不完整或重复。')
    return argv[argv.index(name)+1]


def _bound_file(path,expected):
    raw=path.read_bytes();require(byte_hash(raw)==expected,'原 writer 证据字节已改变。')
    return raw


def _envelope_same(left,right):
    # Application result envelopes use different serializer key ordering in
    # stdout and execution-result.json. Preserve all values, JSON types, and
    # array ordering; original bytes remain bound separately.
    return json.dumps(left,sort_keys=True,ensure_ascii=False,allow_nan=False)==json.dumps(right,sort_keys=True,ensure_ascii=False,allow_nan=False)


def validate_writer(store,job,plan,wire_path,process_path,settings):
    folder=wire_path.parent.parent.resolve()
    require(folder.parent==(store.root/'native').resolve() and process_path.resolve().parent==folder
        and wire_path.resolve().parent.parent==folder,
            '中断保存证据不属于原工作目录。')
    process_raw=process_path.read_bytes();process=loads(process_raw)
    require(process.get('owned_os_release_confirmed') is True and process.get('exit_code')==0
            and process.get('job_active_processes_after')==0 and not process.get('errors'),'原 writer 进程释放未证。')
    require(process.get('observed_processes') and all(p.get('exit_signaled') is True and p.get('handle_closed') is True
            for p in process['observed_processes']),'原 writer 持有身份退出未证。')
    argv=process['argv'];require(len(argv)==19 and argv[1:3]==['-I','-B']
        and Path(argv[3]).name=='run_usense_live.py' and argv[4]=='--insert-writer','原进程不是 writer。')
    require(Path(_arg(argv,'--plan')).resolve()==wire_path.resolve(),'原 writer 计划路径不一致。')
    original_wire=loads(_bound_file(wire_path,_arg(argv,'--plan-sha256')))
    wire.validate_insert_plan(original_wire)
    require(json_same(original_wire['product'],plan),'原 writer 未绑定当前中断计划。')
    config_path=Path(_arg(argv,'--config')).resolve()
    require(config_path.parent==folder,'原配置路径不一致。')
    config=loads(_bound_file(config_path,_arg(argv,'--sha256')))
    require(config['book_id']==job['book_id'] and Path(config['output_root']).resolve()==folder
        and Path(config['profile']['directory']).resolve()==Path(settings['profile']).resolve(),
        '原 writer 的书籍、输出或原登录目录不同。')
    require(Path(_arg(argv,'--ledger-root')).resolve()==Path(settings['profile']).resolve().parent/'usense-existing-ledger',
        '原保存账本目录不同。')
    require(_arg(argv,'--authorization-reference')==config['authorization_reference'],'原授权引用不同。')
    stdout_path=process_path.with_name(process_path.name.removesuffix('.process.json')+'.stdout')
    stdout=_bound_file(stdout_path,process['stdout']['sha256'])
    require(len(stdout)==process['stdout']['bytes'],'原 writer stdout 长度不同。')
    writer=loads(stdout.decode('utf-8').strip().splitlines()[-1])
    run_id=writer['run_id'];require(isinstance(run_id,str) and Path(run_id).name==run_id,'原 writer 身份无效。')
    run=folder/run_id
    require(run.resolve().parent==folder,'原 writer 输出路径越界。')
    require(_envelope_same(writer,loads((run/'execution-result.json').read_bytes())),'原 writer 输出和原结果不一致。')
    require(writer['book_id']==job['book_id']==plan['book_id'] and writer['run_id']==config['run_id']
        and writer['ledger_key']=='customer-'+plan['key'] and writer['plan_sha256']==original_wire['plan_sha256']
        and writer['plan_file_sha256']==byte_hash(wire_path.read_bytes())
        and writer['config_sha256']==byte_hash(config_path.read_bytes())
        and writer['authorization_reference']==config['authorization_reference'], '原 writer 身份或计划摘要不同。')
    require(writer['status']=='INSERT_RECEIPT_REQUIRES_INDEPENDENT_ALL23_READBACK'
        and type(writer['post_attempts']) is int and writer['post_attempts']==1 and writer['http_status']==200
        and writer['post_layers']=={'context':1,'native':1}
        and writer['release']['context_runtime_release_confirmed'] is True,'原唯一保存回执或运行时释放未证。')
    require(_time(process['started_at'])<=_time(writer['send_intent_at'])<=_time(writer['finished_at'])<=_time(process['finished_at']),
        '原 writer 发送窗口不在原持有进程内。')
    receipt_raw=_bound_file(run/'native-receipt.json',writer['receipt_sha256']);receipt=loads(receipt_raw)
    wire.decode_receipt(original_wire,receipt)
    send=loads((run/'send-intent.json').read_bytes())
    for key in ('run_id','book_id','ledger_key','plan_sha256','plan_file_sha256','config_sha256','native_body_sha256','runtime_actor_hashes','send_intent_at'):
        require(_envelope_same(send.get(key),writer.get(key)),'原发送意图与回执不一致。')
    require(send['status']=='SEND_INTENT_RECORDED' and send['post_attempts']==1,'原发送意图不完整。')
    ref={'record':str(process_path.resolve()),'sha256':byte_hash(process_raw),
        'started_at':process['started_at'],'finished_at':process['finished_at']}
    return {'receipt':receipt,'writer':writer,'processes':[ref]}


def recover(store,job,plan,candidate,settings):
    """Return an UNKNOWN record from local raw files; does not write the Store."""
    require(candidate['pending_plan_ref']==byte_hash(encoded(plan))
        and candidate_hash(candidate)==candidate_hash(plan['candidate']),
        '当前中断计划摘要不一致。')
    root=(store.root/'native').resolve();matches=[]
    for wire_path in root.glob('*/write-'+plan['key']+'/plan.json'):
        folder=wire_path.parent.parent
        for process_path in folder.glob('writer-*.process.json'):
            process=loads(process_path.read_bytes());argv=process.get('argv',[])
            if '--plan' in argv and Path(_arg(argv,'--plan')).resolve()==wire_path.resolve():
                matches.append((wire_path,process_path))
    require(len(matches)==1,'没有唯一完整的原 writer 记录；保留 INTENT，不能重发或新读。')
    wire_path,process_path=matches[0];sent=validate_writer(store,job,plan,wire_path,process_path,settings)
    folder=wire_path.parent.parent.resolve();writer_end=_time(sent['processes'][0]['finished_at'])
    following=[]
    for path in folder.glob('read-*.process.json'):
        record=loads(path.read_bytes())
        if _time(record['started_at'])>=writer_end:
            following.append((path,record))
    following.sort(key=lambda pair:pair[1]['started_at'])
    prefix=[];interrupted=[];broken=False
    for path,record in following:
        ref={'record':str(path.resolve()),'sha256':byte_hash(path.read_bytes()),'started_at':record['started_at'],'finished_at':record['finished_at']}
        if record.get('owned_os_release_confirmed') is not True or record.get('exit_code')!=0:broken=True
        (interrupted if broken else prefix).append(ref)
    # Preserve every original raw file, including a killed capture without a
    # process.json. These hashes are provenance only, never readback acceptance.
    raw_files=[]
    for path in sorted(folder.rglob('*')):
        if not path.is_file():continue
        require(path.resolve().is_relative_to(folder),'原运行证据路径越界。')
        raw=path.read_bytes();raw_files.append({'path':str(path.resolve()),'sha256':byte_hash(raw),'bytes':len(raw)})
    return {'type':'InterruptedCustomerProduction','message':'Original process died after durable intent. Original writer receipt recovered locally; not save acceptance.',
        'at':utcnow(),'plan_ref':candidate['pending_plan_ref'],'sent':sent,
        'processes':copy.deepcopy(sent['processes'])+prefix,'native_output':str(folder),
        'interrupted_receipt_recovered':True,'original_operation':{'state':'INTENT','output':None},
        'interrupted_capture_processes':interrupted,'original_native_raw_files':raw_files,
        'fresh_reconcile_only_if_retained_readback_incomplete':True,'new_platform_calls':0,'new_save_attempts':0}
