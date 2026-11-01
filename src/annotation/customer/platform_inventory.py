"""Explicit read-only comparison of prepared source jobs with current native nodes.

The capture contains the book directory tree, question nodes, and native frame
inventory. A unique geometry match is an identity clue only: neither content
equivalence nor platform completion is inferred from it.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from html import escape
import json
import math
from pathlib import Path
from uuid import uuid4

from .native_plan import _response, directory_rows, require
from .store import encoded
from .transport import UsenseTransport


def _bbox(value):
    try:
        parts = value.split(',') if isinstance(value, str) else value
        box = tuple(float(part) for part in parts)
    except (TypeError, ValueError):
        raise ValueError('来源框坐标不是四个数字。') from None
    if len(box) != 4 or not all(math.isfinite(n) for n in box) or not (box[0] < box[2] and box[1] < box[3]):
        raise ValueError('来源框坐标无效。')
    return box


def _overlaps(a, b):
    return max(a[0], b[0]) < min(a[2], b[2]) and max(a[1], b[1]) < min(a[3], b[3])


def _local_questions(job, candidate):
    pages = {page['asset_id']: page for page in job['pages'] if page.get('kind') == 'image'}
    records = []
    for frame in candidate['frames']:
        if frame.get('zone') != 'question':
            continue
        page = pages.get(frame.get('asset_id'))
        if (not page or page.get('raw_sha256') != frame.get('source_sha256')
                or type(page.get('viewer_page')) is not int):
            raise ValueError('本地题干框缺少已绑定页码或原图身份。')
        records.append((page['viewer_page'], _bbox(frame.get('bbox'))))
    if not records:
        raise ValueError('本地来源实例缺少题干框。')
    return sorted(records)


def build_inventory(book, jobs, flat):
    """Classify local-to-native source geometry without changing either side."""
    require(type(book) is str and book.isdecimal() and type(jobs) is list, '书籍或本地任务无效。')
    rows, questions = directory_rows(flat['directory'])
    frames = _response(flat['frames'])
    source = _response(flat['source'])
    require(type(frames) is list and type(source) is dict and source.get('file_id') == book
            and type(source.get('total_pages')) is int and source['total_pages'] > 0,
            '当前书籍或题框库存不完整。')
    rect_ids = [frame.get('rect_id') for frame in frames if type(frame) is dict]
    require(len(rect_ids) == len(frames) and all(type(identity) is str and identity for identity in rect_ids)
            and len(set(rect_ids)) == len(rect_ids), '平台题框身份缺失或重复。')
    leaves = {row['node']['id']: row for row in rows if not row['question']
              and not any(child['parent'] == row['node']['id'] and not child['question'] for child in rows)}
    nodes_by_directory = defaultdict(list)
    by_order = {}
    for order, row in enumerate(questions, 1):
        nodes_by_directory[row['parent']].append(row)
        by_order[str(order)] = row
    geometry = defaultdict(list)
    for frame in frames:
        require(type(frame) is dict and frame.get('file_id') == book
                and type(frame.get('order_in_level')) is str
                and frame['order_in_level'] in by_order
                and frame.get('directory_id') == by_order[frame['order_in_level']]['parent']
                and type(frame.get('page_index')) is int
                and 1 <= frame['page_index'] <= source['total_pages'],
                '平台题框与本书题节点或来源页不一致。')
        if frame.get('type') == 'question':
            try:
                box = _bbox(frame.get('rect_bbox'))
            except ValueError as exc:
                require(False, '平台题干框无效：' + str(exc))
            geometry[by_order[frame['order_in_level']]['node']['id']].append((frame['page_index'], box))
    seen_directories = set()
    reports = []
    totals = {'exact': 0, 'ambiguous': 0, 'missing': 0}
    for job in jobs:
        require(job.get('book_id') == book and type(job.get('source_plan')) is dict,
                '本地任务不属于所选全书来源。')
        directory_id = job['source_plan'].get('scope_id')
        require(type(directory_id) is str and directory_id and directory_id not in seen_directories,
                '本地来源目录身份缺失或重复。')
        seen_directories.add(directory_id)
        native = leaves.get(directory_id)
        native_path = native['path'] if native else None
        local_path = job.get('directory_path')
        directory_status = ('MISSING' if native is None else
                            'EXACT_ID_AND_PATH' if native_path == local_path else 'ID_PATH_CONFLICT')
        native_nodes = nodes_by_directory[directory_id] if native else []
        candidates = []
        possible_owners = defaultdict(set)
        for candidate in job['candidates']:
            identity = candidate.get('source_instance_id')
            require(type(identity) is str and identity, '本地候选缺少来源实例身份。')
            item = {'source_instance_id': identity, 'candidate_key': candidate['key'],
                    'source_item_kind': candidate.get('source_item_kind'),
                    'printed_number': candidate.get('printed_number'),
                    'local_content_status': candidate.get('content_status'),
                    'local_platform_status': candidate.get('platform_status'),
                    'matching_basis': 'BOOK_DIRECTORY_ID_QUESTION_FRAME_PAGE_AND_ORIGINAL_PIXEL_BBOX',
                    'content_equivalence_checked': False,
                    'platform_completion_claim': False}
            try:
                local_frames = _local_questions(job, candidate)
            except ValueError as exc:
                local_frames = []
                item['local_geometry_issue'] = str(exc)
            exact, overlaps = [], []
            if native is not None and directory_status == 'EXACT_ID_AND_PATH' and local_frames:
                for row in native_nodes:
                    node_id = row['node']['id']
                    native_frames = sorted(geometry[node_id])
                    if native_frames == local_frames:
                        exact.append(node_id)
                    elif any(a[0] == b[0] and _overlaps(a[1], b[1])
                             for a in local_frames for b in native_frames):
                        overlaps.append(node_id)
                for node_id in set(exact + overlaps):
                    possible_owners[node_id].add(identity)
            item['exact_native_node_ids'] = exact
            item['overlapping_native_node_ids'] = overlaps
            candidates.append(item)
        matched_exact = set()
        for item in candidates:
            exact = item['exact_native_node_ids']
            possible = set(exact + item['overlapping_native_node_ids'])
            if (directory_status == 'EXACT_ID_AND_PATH' and len(exact) == 1
                    and not item['overlapping_native_node_ids']
                    and len(possible_owners[exact[0]]) == 1):
                item['correspondence'] = 'EXACT_GEOMETRY'
                item['reason'] = '唯一题节点的题干来源页与原像素框逐一相同；题答内容仍待核对。'
                matched_exact.add(exact[0])
                totals['exact'] += 1
            elif possible or item.get('local_geometry_issue') or directory_status == 'ID_PATH_CONFLICT':
                item['correspondence'] = 'AMBIGUOUS'
                item['reason'] = ('目录 ID 与路径不一致，须人工核对。' if directory_status == 'ID_PATH_CONFLICT' else
                                  item.get('local_geometry_issue') or '题干框仅相交或对应多个来源实例，须人工核对。')
                totals['ambiguous'] += 1
            else:
                item['correspondence'] = 'MISSING'
                item['reason'] = ('平台末级目录未找到。' if native is None else
                                  '当前目录题节点中未找到相同或相交的题干来源框。')
                totals['missing'] += 1
        reports.append({'job_id': job['id'], 'directory_id': directory_id,
                        'local_path': local_path, 'native_path': native_path,
                        'directory_status': directory_status,
                        'native_question_count': len(native_nodes),
                        'native_question_node_ids': [row['node']['id'] for row in native_nodes],
                        'native_nodes_without_exact_local_match': [row['node']['id'] for row in native_nodes
                                                                   if row['node']['id'] not in matched_exact],
                        'candidate_count': len(candidates), 'candidates': candidates})
    return {'schema': 'CustomerPlatformInventoryComparison/v1', 'book_id': book,
            'capture_kind': 'READ_ONLY_DIRECTORY_FRAMES_SOURCE',
            'platform_question_nodes': len(questions), 'platform_frames': len(frames),
            'source_candidates': sum(item['candidate_count'] for item in reports),
            'summary': totals, 'directories': reports,
            'platform_absence_proven': False, 'content_equivalence_checked': False,
            'platform_completion_claim': False, 'platform_actions': []}


def _html(report):
    summary = report['summary']
    rows = []
    for directory in report['directories']:
        path = ' / '.join(directory['local_path'] or [])
        detail_rows = ''.join('<tr><td><code>' + escape(item['source_instance_id'])
            + '</code></td><td>' + escape(str(item['printed_number'])) + '</td><td>'
            + escape(item['correspondence']) + '</td><td>'
            + escape(', '.join(item['exact_native_node_ids'] + item['overlapping_native_node_ids']))
            + '</td><td>' + escape(item['reason']) + '</td></tr>' for item in directory['candidates'])
        rows.append('<details><summary>' + escape(path) + ' · 目录 <code>'
            + escape(directory['directory_id']) + '</code> · 平台已有 '
            + str(directory['native_question_count']) + ' 个题节点 · 本地 '
            + str(directory['candidate_count']) + ' 条来源实例 · '
            + escape(directory['directory_status']) + '</summary><table><thead><tr><th>来源身份</th>'
            '<th>印刷题号</th><th>对应状态</th><th>平台题节点</th><th>原因</th></tr></thead><tbody>'
            + detail_rows + '</tbody></table></details>')
    return ('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
        '<title>平台当前库存只读核对</title><style>body{font:15px/1.6 system-ui;max-width:1200px;margin:30px auto;'
        'padding:0 20px;color:#17352d}h1{font-size:28px}p{color:#4d625c}details{padding:12px 0;border-bottom:1px solid #ddd}'
        'summary{cursor:pointer}table{border-collapse:collapse;width:100%;margin:12px 0}td,th{text-align:left;'
        'border-bottom:1px solid #ddd;padding:7px;vertical-align:top}code{overflow-wrap:anywhere}</style>'
        '<h1>平台当前库存只读核对</h1><p>书 ' + escape(report['book_id']) + ' · 平台题节点 '
        + str(report['platform_question_nodes']) + ' 个 · 本地来源实例 ' + str(report['source_candidates']) + ' 条</p>'
        '<p>原像素几何唯一对应 ' + str(summary['exact']) + ' 条；存在歧义 '
        + str(summary['ambiguous']) + ' 条；未找到对应 ' + str(summary['missing']) + ' 条。</p>'
        '<p><strong>本报告只比对当前目录、题节点和题干框的页码与原像素范围。</strong>'
        '未核对题答正文和当前原图字节；“唯一对应”不是平台完成确认，“未找到”也不证明平台不存在。'
        '本次没有保存、提交或删除。</p>' + ''.join(rows) + '</html>').encode('utf-8')


def read_inventory(store, settings, book, prepared, *, transport_factory=None):
    """One explicit live GET capture, then a local report. Never call a writer."""
    require(prepared.get('schema') == 'CustomerWholebookPreparation/v1'
            and prepared.get('book_id') == book, '请先通过产品入口准备本书来源课时。')
    job_ids = [item['job'] for item in prepared['results'] if item.get('job')]
    require(job_ids and len(job_ids) == len(set(job_ids)), '已准备课时任务身份缺失或重复。')
    with store.book_lock(book):
        transport = (transport_factory or UsenseTransport)(store, settings, book)
        flat = transport._capture()
        jobs = [store.job(identity)[0] for identity in job_ids]
        report = build_inventory(book, jobs, flat)
        report['captured_at'] = datetime.now(timezone.utc).isoformat()
        report['native_read_processes'] = len(transport.processes)
        folder = store.root / 'inventory-reports' / uuid4().hex
        folder.mkdir(parents=True)
        (folder / 'inventory.json').write_bytes(encoded(report))
        (folder / 'index.html').write_bytes(_html(report))
    return {'output': str(folder / 'index.html'), 'json': str(folder / 'inventory.json'),
            'summary': report['summary'], 'native_question_nodes': report['platform_question_nodes'],
            'platform_actions': [], 'platform_completion_claim': False}
