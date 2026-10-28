"""Book/directory selection acquires official pages before preparation.

Current annotated frames provide seed pages, not a complete section boundary.
The selected bounded adjacent pages are reported as discovery coverage. Missing
question/answer ranges remain explicit and never imply whole-section completion.
"""
from __future__ import annotations
import copy
from pathlib import Path
import re
from urllib.parse import urlsplit

from .native_plan import _response, directory_rows, require
from .store import Hold, digest
from .transport import UsenseTransport


def catalog(flat, book):
    rows, _ = directory_rows(flat['directory'])
    frames = _response(flat['frames']); source = _response(flat['source'])
    require(type(frames) is list and source.get('file_id') == book
            and type(source.get('total_pages')) is int and 0 < source['total_pages'] <= 9999,
            '当前来源页库存或书籍不完整。')
    result = []
    for row in rows:
        if row['question']: continue
        descendant_nodes = [r for r in rows if r['question'] and r['path'][:len(row['path'])] == row['path']]
        orders = {r['node']['order_in_level'] for r in descendant_nodes}
        associated = [f for f in frames if f.get('order_in_level') in orders]
        require(all(f.get('file_id') == book and type(f.get('page_index')) is int
                    and 1 <= f['page_index'] <= source['total_pages'] for f in associated), '目录关联题框页码无效。')
        result.append({'directory_id': row['node']['id'], 'path': row['path'],
            'question_nodes': [r['node']['id'] for r in descendant_nodes],
            'seed_question_pages': sorted({f['page_index'] for f in associated if f.get('type') in ('question','choice')}),
            'seed_answer_pages': sorted({f['page_index'] for f in associated if f.get('type') in ('answer','analysis')}),
            'has_child_directories': any(r['parent'] == row['node']['id'] and not r['question'] for r in rows),
            'section_complete': False})
    return {'schema': 'CustomerBookCatalog/v1', 'book_id': book, 'total_pages': source['total_pages'],
            'directories': result, 'raw_snapshot': copy.deepcopy(flat)}


def read_catalog(store, settings, book, *, transport_factory=None):
    with store.book_lock(book):
        transport = (transport_factory or UsenseTransport)(store, settings, book)
        # A catalog refresh is an explicit read action, never a production retry.
        value = catalog(transport._capture(), book)
        value['processes'] = copy.deepcopy(transport.processes)
        ref = store.put(value)
        return {'catalog_ref': ref, **{k: v for k, v in value.items() if k != 'raw_snapshot'}}


def scope_plan(value, directory, *, question_pages=None, answer_pages=None, adjacent_pages=1):
    matches = [r for r in value['directories'] if r['directory_id'] == directory]
    require(len(matches) == 1 and not matches[0]['has_child_directories'], '请选择唯一末级目录。')
    selected = matches[0]
    require(type(adjacent_pages) is int and 0 <= adjacent_pages <= 2, '相邻探查页上限为两页。')
    def bounded(supplied, seeds):
        pages = supplied if supplied is not None else sorted({p + n for p in seeds for n in range(adjacent_pages + 1)
                                                             if p + n <= value['total_pages']})
        require(type(pages) is list and pages and len(pages) <= 8 and len(set(pages)) == len(pages)
                and all(type(p) is int and 1 <= p <= value['total_pages'] for p in pages),
                '该目录没有可推导的来源页，请在书中选择题页和答页范围。')
        return sorted(pages)
    questions = bounded(question_pages, selected['seed_question_pages'])
    answers = bounded(answer_pages, selected['seed_answer_pages'])
    require(not set(questions) & set(answers), '题目与答案来源同页，当前需处理混合布局异常。')
    require(len(questions) + len(answers) <= 8, '一次普通范围取源最多八页。')
    return {'schema': 'CustomerSourceScope/v1', 'book_id': value['book_id'], 'directory_id': directory,
            'directory_path': selected['path'], 'question_pages': questions, 'answer_pages': answers,
            'existing_node_ids': selected['question_nodes'], 'existing_node_replay': False,
            'source_scope_complete': False, 'selection_basis': 'DIRECTORY_FRAME_SEEDS_AND_BOUNDED_ADJACENT_PAGES',
            'maximum_api_gets': 3 + len(questions) + len(answers), 'maximum_original_gets': len(questions) + len(answers),
            'save_attempts': 0, 'ocr_attempts': 0}


def page_url(flat, book, number):
    data = _response(flat['page_' + str(number)])
    require(data.get('file_id') == book and type(data.get('pages')) is list and len(data['pages']) == 1,
            '当前来源页记录无效。')
    page = data['pages'][0]
    require(page.get('page_index') == number - 1, '平台来源页索引不一致。')
    url = page.get('image', ''); parsed = urlsplit(url)
    require(parsed.scheme == 'https' and not parsed.query and not parsed.fragment and not parsed.username
            and parsed.netloc.endswith('.aliyuncs.com') and '/' + book + '/' in parsed.path, '来源原图未绑定所选书籍。')
    return url


def validate_plan(plan):
    require(type(plan) is dict and plan.get('schema') == 'CustomerSourceScope/v1'
            and type(plan.get('book_id')) is str and re.fullmatch(r'[1-9][0-9]{0,31}',plan['book_id']), '来源计划书籍无效。')
    require(type(plan.get('directory_id')) is str and plan['directory_id']
            and type(plan.get('directory_path')) is list and plan['directory_path']
            and all(type(s) is str and s for s in plan['directory_path']), '来源计划目录无效。')
    for role in ('question','answer'):
        pages=plan.get(role+'_pages')
        require(type(pages) is list and pages and all(type(p) is int and 1<=p<=9999 for p in pages)
                and pages==sorted(set(pages)), '来源计划页范围无效。')
    pages=plan['question_pages']+plan['answer_pages']
    require(len(pages)<=8 and len(set(pages))==len(pages), '来源计划页重复或过多。')
    require(plan.get('maximum_api_gets') == 3+len(pages) and plan.get('maximum_original_gets') == len(pages)
            and type(plan.get('save_attempts')) is int and plan['save_attempts']==0
            and type(plan.get('ocr_attempts')) is int and plan['ocr_attempts']==0
            and plan.get('existing_node_replay') is False and plan.get('source_scope_complete') is False,
            '来源计划预算或边界不一致。')
    require(type(plan.get('existing_node_ids')) is list and all(type(n) is str and n for n in plan['existing_node_ids'])
            and len(set(plan['existing_node_ids']))==len(plan['existing_node_ids']), '原题身份列表无效。')
    return plan


def acquire(store, settings, plan, *, transport_factory=None):
    validate_plan(plan)
    book = plan['book_id']; key = digest(plan)
    with store.book_lock(book):
        old = store.operation('platform-source', key)
        if old:
            if old['state'] != 'COMPLETE': raise Hold('本范围取源曾失败或未知；保留原记录，不自动重试。')
            value = store.get(old['output'])
            from .source import verify_sources
            verify_sources(value['pages'])
            return value
        store.begin('platform-source', key)
        transport = None
        try:
            transport = (transport_factory or UsenseTransport)(store, settings, book)
            pages = plan['question_pages'] + plan['answer_pages']
            flat = transport._capture(pages=pages)
            actual = catalog(flat, book)
            check = scope_plan(actual, plan['directory_id'], question_pages=plan['question_pages'], answer_pages=plan['answer_pages'])
            require(check == plan, '目录身份或旧题库存已变化，停止取源并核对。')
            files = []
            for role in ('question', 'answer'):
                for number in plan[role + '_pages']:
                    item = transport.download_original(page_url(flat, book, number))
                    files.append({**item, 'role': role, 'viewer_page': number})
            value = {'schema': 'CustomerAcquiredSources/v1', 'plan': copy.deepcopy(plan), 'pages': files,
                     'snapshot_ref': store.put(flat), 'processes': copy.deepcopy(transport.processes),
                     'section_titles': [r['path'][-1] for r in actual['directories']],
                     'source_scope_complete': False, 'new_ocr_calls': 0, 'save_attempts': 0}
            store.finish('platform-source', key, 'COMPLETE', value)
            return value
        except BaseException as exc:
            if store.operation('platform-source',key)['state']=='INTENT':
                store.finish('platform-source', key, 'FAILED_NO_RETRY', {'type': type(exc).__name__, 'message': str(exc),
                    'native_output': str(transport.out) if transport else None, 'successors': 'NOT_RUN'})
            raise


def prepare_acquired(store, value, *, allow_local_ocr=False):
    from .prepare import prepare
    plan = value['plan']
    remember_pages(store,value)
    roles = {role: [p for p in value['pages'] if p['role'] == role] for role in ('question','answer')}
    bindings = {p['raw_sha256']: p['viewer_page'] for p in value['pages']}
    job = prepare(store, book=plan['book_id'], lesson=plan['directory_path'][-1],
        question_files=[p['raw_path'] for p in roles['question']], answer_files=[p['raw_path'] for p in roles['answer']],
        allow_local_ocr=allow_local_ocr, page_bindings=bindings, directory_path=plan['directory_path'],
        section_titles=value['section_titles'])
    with store.book_lock(plan['book_id']):
        job, head = store.job(job['id'])
        job['platform_source_ref'] = store.put(value)
        job.setdefault('source_scope_complete',False)
        store.save_job(job, head, 'PLATFORM_SOURCES_PREPARED')
    return job


def remember_pages(store,value):
    """Index already acquired originals once; no platform or recognition call."""
    from .source import verify_sources
    verify_sources(value['pages'])
    flat=store.get(value['snapshot_ref']);book=value['plan']['book_id']
    for page in value['pages']:
        url=page_url(flat,book,page['viewer_page'])
        require(page.get('book_id')==book and page.get('image_url')==url,'已取得原图的官方页绑定不一致。')
        key=digest([book,url]);old=store.operation('official-original',key)
        if old:
            require(old['state']=='COMPLETE' and store.get(old['output'])['raw_sha256']==page['raw_sha256'],'原图已有未知或不同记录。')
        else:store.record_read('official-original',key,page)
        key=digest([book,page['viewer_page']]);old=store.operation('official-page',key)
        record={'page':page,'page_metadata':flat['page_'+str(page['viewer_page'])],'snapshot_ref':value['snapshot_ref']}
        if old:
            require(old['state']=='COMPLETE' and store.get(old['output'])['page']['raw_sha256']==page['raw_sha256'],'平台页已有未知或不同原图。')
        else:store.record_read('official-page',key,record)


def prepare_section(store,settings,value,*,allow_local_ocr=False,maximum_additional_pages=4,transport_factory=None):
    """Continue the ordinary book/range entry until a heading or finite bound.

    Each absent adjacent page has one durable read operation. Old sources and
    recognition are reused before any new request. The output always states
    unresolved roles and never treats the discovery limit as a section end.
    """
    require(type(maximum_additional_pages) is int and 0<=maximum_additional_pages<=8,'相邻页探查预算无效。')
    value=copy.deepcopy(value);book=value['plan']['book_id'];extra=[]
    while True:
        job=prepare_acquired(store,value,allow_local_ocr=allow_local_ocr)
        if job['status'] in {'WAITING_SOURCE','FAILED_NO_RETRY'}:return job
        scope=store.get(job['section_scope_ref']) if job.get('section_scope_ref') else []
        last={}
        for entry in scope:
            page=entry['page']
            last[page['role']]=entry
        unresolved=[role for role in ('question','answer') if role not in last or last[role]['continuation_at_end']]
        if not unresolved or len(extra)>=maximum_additional_pages:
            with store.book_lock(book):
                job,head=store.job(job['id']);job['remaining_source_roles']=unresolved
                job['source_discovery']={'additional_pages':extra,'limit':maximum_additional_pages,
                    'status':'OBSERVED_SECTION_END' if not unresolved else 'BOUND_REACHED_END_UNKNOWN'}
                job['source_scope_complete']=not unresolved
                store.save_job(job,head,'SECTION_DISCOVERY_RESULT')
            return job
        require(job['platform_status']=='NOT_RUN' and job['metrics']['review_actions']==0,
                '来源范围已有审校或生产记录；保留原任务，不能替换为新范围。')
        role=unresolved[0];number=max(p['viewer_page'] for p in value['pages'] if p['role']==role)+1
        flat=store.get(value['snapshot_ref']);total=_response(flat['source'])['total_pages']
        if number>total:
            with store.book_lock(book):
                job,head=store.job(job['id']);job['remaining_source_roles']=unresolved
                job['source_discovery']={'additional_pages':extra,'limit':maximum_additional_pages,'status':'BOOK_END_SECTION_BOUNDARY_UNVERIFIED'}
                store.save_job(job,head,'SECTION_BOOK_EDGE')
            return job
        require(number not in {p['viewer_page'] for p in value['pages']},'题答范围相交，需处理混合页结构。')
        key=digest([book,number]);old=store.operation('official-page',key)
        with store.book_lock(book):
            if old:
                require(old['state']=='COMPLETE','相邻页已有失败或未知读取，不自动重试。')
                cached=store.get(old['output']);page=copy.deepcopy(cached['page'])
                flat['page_'+str(number)]=cached['page_metadata'];mode='EXISTING_SOURCE_CACHE'
            else:
                store.begin('official-page',key);transport=None
                try:
                    transport=(transport_factory or UsenseTransport)(store,settings,book)
                    incoming=transport._capture(pages=[number])
                    from annotation.runtime.usense_live.update import json_same
                    require(all(json_same(flat[name],incoming[name]) for name in ('directory','frames','source')),
                            '来源续页期间目录、题框或书籍库存变化；停止并保留原结果。')
                    flat['page_'+str(number)]=incoming['page_'+str(number)]
                    page=transport.download_original(page_url(flat,book,number));page['viewer_page']=number
                    value.setdefault('processes',[]).extend(copy.deepcopy(transport.processes))
                    store.finish('official-page',key,'COMPLETE',{'page':page,'page_metadata':flat['page_'+str(number)],
                        'snapshot_ref':store.put(flat),'processes':copy.deepcopy(transport.processes)})
                    mode='NEW_BOUNDED_PAGE_READ'
                except BaseException as exc:
                    if store.operation('official-page',key)['state']=='INTENT':
                        store.finish('official-page',key,'FAILED_NO_RETRY',{'type':type(exc).__name__,'message':str(exc),
                            'native_output':str(transport.out) if transport else None,'successors':'NOT_RUN'})
                    raise
            page['role']=role;value['pages'].append(page)
            value['pages'].sort(key=lambda p:(p['role']!='question',p['viewer_page']))
            value['snapshot_ref']=store.put(flat)
            value['continuation_from_job']=job['id']
            extra.append({'role':role,'viewer_page':number,'mode':mode,'source_sha256':page['raw_sha256']})
            value.setdefault('continuation_pages',[]).append(copy.deepcopy(extra[-1]))
