"""Reconstruct the original post-save capture, without a new platform call.

The immutable UNKNOWN operation binds process-record hashes. Those records bind
stdout and the exact capture config; stdout binds every captured response byte.
Incomplete or changed retained reads hold rather than trigger another request.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from annotation.runtime.usense_live.config import endpoints
from annotation.runtime.usense_live.update import loads, json_same
from .native_plan import require, directory_rows
from .store import byte_hash
from .wire import snapshot


def _time(value):
    parsed = datetime.fromisoformat(value)
    require(parsed.utcoffset() is not None, '原进程时间缺少时区。')
    return parsed


def reconstruct(store, job, plan, unknown):
    """Return complete prior fresh readback, or None if no read was launched."""
    sent = unknown['sent']
    prefix = sent.get('processes', [])
    processes = unknown.get('processes', [])
    require(prefix and len(processes) >= len(prefix)
            and json_same(processes[:len(prefix)], prefix), '原保存与后续进程链不一致。')
    following = processes[len(prefix):]
    if not following:
        return None
    folder = Path(unknown['native_output']).resolve()
    require(folder.is_relative_to((store.root / 'native').resolve()), '原读回路径不属于当前工作目录。')
    prior_end = _time(prefix[-1]['finished_at'])
    require(prior_end >= _time(sent['writer']['finished_at']), '读回前原 writer 释放时间不一致。')
    numbers = sorted({p['viewer_page'] for p in job['pages'] if p['kind'] == 'image'})
    flat, bindings, scopes, run_ids = {}, [], None, set()
    for index, process in enumerate(following):
        record_path = Path(process['record']).resolve()
        require(record_path.parent == folder and record_path.name.endswith('.process.json'), '原进程记录路径不一致。')
        raw = record_path.read_bytes()
        require(byte_hash(raw) == process['sha256'], '原读回进程记录已改变。')
        record = loads(raw)
        require(record.get('owned_os_release_confirmed') is True and record.get('exit_code') == 0,
                '原读回进程失败或释放未证。')
        start, end = _time(process['started_at']), _time(process['finished_at'])
        require(prior_end <= start <= _time(record['started_at']) <= _time(record['finished_at']) <= end
                and end <= _time(unknown['at']), '原读回不是保存释放后的完整串行进程。')
        prior_end = end
        argv = record['argv']
        require(len(argv) == 9 and argv[1:3] == ['-I', '-B'] and argv[4:6] == ['capture', '--config']
                and argv[7] == '--sha256', '原后续进程不是只读采集。')
        config_path = Path(argv[6]).resolve()
        require(config_path.parent == folder, '原采集配置路径已变化。')
        config_raw = config_path.read_bytes()
        require(byte_hash(config_raw) == argv[8], '原采集配置字节已改变。')
        config = loads(config_raw)
        require(config['operation'] == 'READONLY_CAPTURE' and config['book_id'] == job['book_id'] == plan['book_id']
                and Path(config['output_root']).resolve() == folder
                and config['authorization_reference'] == sent['writer']['authorization_reference'], '原读回配置不属于这次保存。')
        run_id = config['run_id']
        require(type(run_id) is str and Path(run_id).name == run_id and run_id not in run_ids
                and run_id != sent['writer']['run_id'], '原读回上下文身份重复。')
        run_ids.add(run_id)
        stdout_path = record_path.with_name(record_path.name.removesuffix('.process.json') + '.stdout')
        stdout = stdout_path.read_bytes()
        require(len(stdout) == record['stdout']['bytes'] and byte_hash(stdout) == record['stdout']['sha256'], '原读回 stdout 字节已改变。')
        summary = loads(stdout.decode('utf-8').strip().splitlines()[-1])
        summary_path = folder / run_id / 'capture-summary.json'
        require(json_same(summary, loads(summary_path.read_bytes())), '原读回摘要与进程输出不同。')
        require(summary['run_id'] == run_id and summary['book_id'] == job['book_id']
                and summary['config_sha256'] == argv[8] and summary['status'] == 'NATIVE_GETS_CAPTURED'
                and summary['save_attempts'] == 0 and summary['release']['context_runtime_release_confirmed'] is True,
                '原读回摘要或释放不完整。')
        incoming = {}
        for name, descriptor in summary['captures'].items():
            require(descriptor['filename'] == name + '.json' and Path(name).name == name, '原响应文件名无效。')
            capture_path = folder / run_id / descriptor['filename']
            body = capture_path.read_bytes()
            require(byte_hash(body) == descriptor['sha256'] and len(body) == descriptor['bytes']
                    and descriptor['status'] == 200 and descriptor['request_counts'] == {'context': 1, 'native': 1}
                    and start <= _time(descriptor['observed_at']) <= end, '原读回响应字节、次数或时点未证。')
            incoming[name] = loads(body)
        if index == 0:
            require(set(incoming) == set(endpoints((), (), source=True, book_id=job['book_id'])), '原首个库存采集范围不符。')
            count = len(directory_rows(incoming['directory'])[1])
            scopes = [((), ())] + [(range(first, min(first + 6, count + 1)), ()) for first in range(1, count + 1, 6)]
            scopes += [((), numbers[first:first + 8]) for first in range(0, len(numbers), 8)]
            require(len(following) <= len(scopes), '原读回进程数超过完整范围。')
        orders, pages = scopes[index]
        require(set(incoming) == set(endpoints(orders, pages, source=True, book_id=job['book_id'])), '原读回分批范围不完整。')
        for name, value in incoming.items():
            require(name not in flat or json_same(flat[name], value), '原分批读回期间库存变化。')
            flat[name] = value
        bindings.append({'process': process, 'config_sha256': argv[8], 'run_id': run_id,
                         'stdout_sha256': byte_hash(stdout), 'summary_sha256': byte_hash(summary_path.read_bytes()),
                         'captures': {name: d['sha256'] for name, d in summary['captures'].items()}})
    if len(following) < len(scopes):
        require(unknown.get('interrupted_receipt_recovered') is True
                and unknown.get('fresh_reconcile_only_if_retained_readback_incomplete') is True,
                '原读回不完整，不能用部分响应解除未知保存。')
        # The recovered INTENT retains every original partial raw file. The
        # explicit ordinary reconcile action performs one new full read only;
        # it never fills gaps with stale pre-save values or invokes a writer.
        return None
    after = snapshot(flat, job['book_id'], plan['before']['pages'])
    return {'after': after, 'processes': following, 'bindings': bindings,
            'new_platform_reads': 0, 'origin': 'ORIGINAL_FRESH_POST_WRITER_PROCESSES'}
