"""Single customer entry. No arguments opens ordinary file/range selection."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import threading
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from annotation.customer.store import Store, Hold, encoded
from annotation.customer.prepare import prepare, resume
from annotation.customer.review import CustomerReviewWorkspace
from annotation.customer.production import export_local, produce, reconcile


def default_workspace():
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "TextbookProduction"


def settings(store):
    path = store.root / "settings.json"
    value = json.loads(path.read_bytes()) if path.exists() else {"platform_enabled": False}
    if getattr(store, 'customer_start_mode', False):
        # The delivered GUI starts work only on explicit customer actions.
        # Retain the original developer settings file and spent authority; an
        # old preparation window is not the customer's new manual operation.
        value.pop('authorization_reference', None)
        value.pop('expires_at', None)
        installed=packaged_runtime()
        if installed:
            value.setdefault('runtime',{}).update(installed)
    return value


def packaged_runtime():
    """Read the delivered local runtime binding; never download or initialize."""
    runtime=ROOT/'runtime'/'customer-runtimes.json'
    if not runtime.is_file():return None
    from annotation.customer.store import byte_hash
    installed=json.loads(runtime.read_bytes())
    for name in ('text_python','formula_python'):
        item=installed.get(name)
        if item:
            if not isinstance(item,dict) or not item.get('path') or not item.get('sha256'):
                raise Hold('随包运行时缺少文件身份。')
            target=Path(item['path'])
            if not target.is_file() or byte_hash(target.read_bytes())!=item['sha256']:
                raise Hold('随包本地运行时已改变，请保留当前任务。')
    return installed


def configure_first_use(store, *, existing_profile=None, enable_platform=False, approved_known_certificate=False):
    path = store.root / "settings.json"
    if path.exists():
        raise Hold("首次配置已存在。使用原配置和登录目录；不能用新配置替换未对账任务。")
    if existing_profile is None:
        environment = store.root / "environment"
        environment.mkdir(exist_ok=False)
        profile = environment / "dedicated-profile"; profile.mkdir()
        (environment / "usense-existing-ledger").mkdir()
    else:
        profile = Path(existing_profile).resolve()
        if not (profile.parent / "usense-existing-ledger").is_dir():
            raise Hold("所选登录目录的原账本不存在；不能创建空账本代替。")
        from annotation.runtime.usense_live.core import profile_identity
        profile_identity(str(profile))
    value = {"schema": "CustomerDeployment/v1", "profile": str(profile), "platform_enabled": enable_platform,
             "tls_reference": "customer-first-setup-exact-known-certificate" if approved_known_certificate else None, "proxy_server": None}
    installed=packaged_runtime()
    if installed:
        value['runtime']=installed
    with path.open("xb") as stream:
        stream.write(encoded(value))
    return value


def open_review(store, identity, *, block=True):
    from annotation.recognition.content_review_server import make_server
    server = make_server(CustomerReviewWorkspace(store, identity,settings_provider=lambda:settings(store)))
    url = "http://127.0.0.1:" + str(server.server_address[1])
    webbrowser.open(url)
    if block:
        print("本地审校：" + url + "；按 Ctrl+C 关闭。", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
    else:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
    return server


def wizard(store):
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    root = tk.Tk(); root.title("教辅 · 材料准备与生产"); root.geometry("840x760")
    frame = ttk.Frame(root, padding=18); frame.pack(fill="both", expand=True)
    ttk.Label(frame, text="选择材料与范围，然后准备", font=("Microsoft YaHei UI", 17)).pack(anchor="w")
    ttk.Label(frame, text="图片使用本地识别。异常在现有审校页面处理；已成功任务直接复用。", wraplength=780).pack(anchor="w", pady=(4, 14))
    fields = {}
    for key, label, default in (("book", "书籍编号", ""), ("lesson", "课时名称（与平台末级目录相同）", ""),
            ("question_pages", "题目材料页范围（按选择顺序）", "全部"), ("answer_pages", "答案材料页范围", "全部"),
            ("question_first_page", "题目首张对应书中页码（离线可留空）", ""),
            ("answer_first_page", "答案首张对应书中页码（离线可留空）", "")):
        row = ttk.Frame(frame); row.pack(fill="x", pady=3)
        ttk.Label(row, text=label, width=39).pack(side="left")
        value = tk.StringVar(value=default); fields[key] = value
        ttk.Entry(row, textvariable=value).pack(side="left", fill="x", expand=True)
    files = {"question": [], "answer": []}
    for role, label in (("question", "选择题目材料"), ("answer", "选择答案材料")):
        row = ttk.Frame(frame); row.pack(fill="x", pady=5)
        selected_label = ttk.Label(row, text="尚未选择", wraplength=570)
        def choose(role=role, selected_label=selected_label):
            selected = filedialog.askopenfilenames(title="按阅读顺序选择材料", filetypes=[("图片或 UTF-8 文字", "*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff *.txt")])
            if selected:
                files[role] = list(selected)
                selected_label.configure(text=" → ".join(Path(p).name for p in selected))
        ttk.Button(row, text=label, command=choose).pack(side="left", padx=(0, 8)); selected_label.pack(side="left")
    local_ocr = tk.BooleanVar(value=False)
    ttk.Checkbutton(frame, text="允许对没有缓存的新图片运行本地 OCR（没有远端付费调用）", variable=local_ocr).pack(anchor="w", pady=8)
    status = tk.StringVar(value="离线准备可以直接开始。首次平台配置与登录只需在本机完成一次。")
    ttk.Label(frame, textvariable=status, wraplength=780).pack(anchor="w", pady=8)
    jobs = ttk.Treeview(frame, columns=("book", "lesson", "status"), show="headings", height=7)
    for key, title, width in (("book", "书籍", 110), ("lesson", "课时", 330), ("status", "状态", 300)):
        jobs.heading(key, text=title); jobs.column(key, width=width)
    jobs.pack(fill="both", expand=True)
    servers, active = [], {"busy": False}

    def refresh():
        chosen = jobs.selection()
        jobs.delete(*jobs.get_children())
        with store.connect() as db:
            rows = db.execute("SELECT id FROM jobs ORDER BY rowid DESC").fetchall()
        for (identity,) in rows:
            job, _ = store.job(identity)
            jobs.insert("", "end", iid=identity, values=(job["book_id"], job["lesson"], job["status"] + " / " + job["platform_status"]))
        if chosen and jobs.exists(chosen[0]): jobs.selection_set(chosen[0])

    def selected():
        if not jobs.selection(): raise Hold("请先选择下方已有任务。")
        return jobs.selection()[0]

    def task(function, success):
        if active["busy"]: return
        active["busy"] = True; status.set("正在处理；本次工作原件和状态会保留。")
        def work():
            try:
                result = function()
                root.after(0, lambda: finish(result, None))
            except BaseException as exc:
                message = str(exc)
                root.after(0, lambda: finish(None, message))
        def finish(result, error):
            active["busy"] = False; refresh()
            if error:
                status.set(error); messagebox.showerror("本次已停止", error)
            else:
                success(result)
        threading.Thread(target=work, daemon=False).start()

    def prepare_action():
        values = {key: value.get().strip() for key, value in fields.items()}
        try:
            for key in ("question_first_page", "answer_first_page"):
                values[key] = int(values[key]) if values[key] else None
        except ValueError:
            messagebox.showerror("页码无效", "书中页码请填写正整数。"); return
        values.update(question_files=list(files["question"]), answer_files=list(files["answer"]), allow_local_ocr=local_ocr.get())
        def done(job):
            jobs.selection_set(job["id"])
            status.set(job["status"] + "：" + job.get("last_message", "已生成候选与来源框；可审校、导出或启动生产。"))
            if job["status"] == "NEEDS_REVIEW": servers.append(open_review(store, job["id"], block=False))
        task(lambda: prepare(store, **values), done)

    def platform_action():
        book = fields['book'].get().strip()
        if not book.isdigit(): messagebox.showerror('书籍编号', '先填写书籍编号。'); return
        from annotation.customer.platform_source import read_catalog, scope_plan, acquire, prepare_section
        def catalog_ready(value):
            dialog = tk.Toplevel(root); dialog.title('选择平台课时范围'); dialog.geometry('820x480')
            listing = ttk.Treeview(dialog, columns=('path','q','a'), show='headings')
            for key,label,width in [('path','平台目录',490),('q','已有题页线索',120),('a','已有答页线索',120)]:
                listing.heading(key,text=label); listing.column(key,width=width)
            listing.pack(fill='both',expand=True,padx=12,pady=12)
            for row in value['directories']:
                if not row['has_child_directories']:
                    listing.insert('', 'end', iid=row['directory_id'], values=(' / '.join(row['path']),
                        ','.join(map(str,row['seed_question_pages'])), ','.join(map(str,row['seed_answer_pages']))))
            ttk.Label(dialog,text='程序从目录题框发现来源，复用缓存并有界向后探查章节结束；空目录可填写普通书中页范围。',wraplength=780).pack()
            qrange, arange = tk.StringVar(), tk.StringVar()
            for label,var in [('题页范围（留空自动）',qrange),('答页范围（留空自动）',arange)]:
                row=ttk.Frame(dialog);row.pack(fill='x',padx=12,pady=3)
                ttk.Label(row,text=label,width=28).pack(side='left');ttk.Entry(row,textvariable=var).pack(side='left',fill='x',expand=True)
            def start():
                try:
                    if not listing.selection(): raise Hold('请选择课时目录。')
                    from annotation.customer.source import page_numbers
                    current = store.get(value['catalog_ref'])
                    plan = scope_plan(current,listing.selection()[0],
                        question_pages=page_numbers(qrange.get(),current['total_pages']) if qrange.get().strip() else None,
                        answer_pages=page_numbers(arange.get(),current['total_pages']) if arange.get().strip() else None)
                    allow = local_ocr.get(); dialog.destroy()
                    def run(): return prepare_section(store,settings(store),acquire(store,settings(store),plan),allow_local_ocr=allow)
                    def done(job):
                        jobs.selection_set(job['id']);status.set(job['status']+'：'+job.get('last_message','当前范围已准备；来源完整范围仍须检查。'))
                        if job['status']=='NEEDS_REVIEW': servers.append(open_review(store,job['id'],block=False))
                    task(run,done)
                except Exception as exc: messagebox.showerror('范围无法开始',str(exc))
            ttk.Button(dialog,text='取得来源并准备',command=start).pack(pady=10)
            status.set('目录已读取，请选择末级课时。')
        task(lambda:read_catalog(store,settings(store),book),catalog_ready)

    def action(kind):
        try:
            identity = selected()
            if kind == "review": servers.append(open_review(store, identity, block=False))
            elif kind == "export": webbrowser.open((export_local(store, identity) / "index.html").as_uri())
            elif kind == "resume":
                allow = local_ocr.get()
                def continue_prepare():
                    job,_=store.job(identity)
                    if job.get('platform_source_ref'):
                        from annotation.customer.platform_source import prepare_section
                        return prepare_section(store,settings(store),store.get(job['platform_source_ref']),allow_local_ocr=allow)
                    return resume(store,identity,allow_local_ocr=allow)
                task(continue_prepare,lambda job:status.set(job['status']+'：'+job.get('last_message','准备完成')))
            elif kind == "produce":
                job, _ = store.job(identity)
                from annotation.customer.selection import select
                dialog=tk.Toplevel(root);dialog.title('选择本次生产题目');dialog.geometry('720x440')
                ttk.Label(dialog,text='书籍 '+job['book_id']+' · '+job['lesson']+'\n只生产本次选择；已完成记录直接复用。其余异常及整节未完成状态会保留。',wraplength=680).pack(padx=12,pady=12)
                listing=ttk.Treeview(dialog,columns=('number','content','platform'),show='headings',selectmode='extended')
                for key,label,width in [('number','题号',90),('content','内容状态',260),('platform','平台状态',300)]:
                    listing.heading(key,text=label);listing.column(key,width=width)
                listing.pack(fill='both',expand=True,padx=12)
                ready=[]
                for candidate in job['candidates']:
                    listing.insert('','end',iid=candidate['key'],values=(candidate['printed_number'],candidate['content_status'],candidate['platform_status']))
                    try: select(store,job,[candidate['key']]);ready.append(candidate['key'])
                    except Hold: pass
                if ready:listing.selection_set(ready)
                def begin_selected():
                    keys=list(listing.selection())
                    try: select(store,store.job(identity)[0],keys)
                    except Exception as exc:messagebox.showerror('所选范围未准备好',str(exc));return
                    dialog.destroy()
                    task(lambda:produce(store,identity,settings(store),selected_keys=keys),lambda output:(status.set('所选题目已读回，原生交付与自动显示检查完成；其余范围状态保留。'),webbrowser.open((output/'index.html').as_uri())))
                ttk.Button(dialog,text='保存所选题目并独立读回',command=begin_selected).pack(pady=12)
            elif kind == 'display':
                from annotation.customer.native_delivery import check_display
                task(lambda:check_display(store,identity,explicit_recheck=True),lambda output:(status.set('本地显示复查通过；未调用平台保存或导出。'),webbrowser.open((output/'index.html').as_uri())))
            elif kind == "reconcile":
                task(lambda: reconcile(store, identity, settings(store)), lambda output: status.set("只读对账完成；原 UNKNOWN 记录已保留。后继尚未执行。"))
        except Exception as exc:
            messagebox.showerror("无法继续", str(exc))

    def setup():
        try:
            if not messagebox.askokcancel("首次配置", "保存本机平台配置并启用明确点击后的平台操作。登录仍由你在可见 Edge 中完成。"):
                return
            existing = None
            if messagebox.askyesno("已有运行记录", "这台电脑是否已有本项目专用登录目录与原账本？\n选择“是”以复用原目录；新客户选择“否”。"):
                existing = filedialog.askdirectory(title="选择原专用登录目录（不复制或替换）")
                if not existing: return
            exact_cert = messagebox.askyesno("连接证书", "是否允许本程序已有记录的 Usense 指定证书例外？\n仅绑定那一张证书和指定主机；不关闭通用证书校验。不确定时选择“否”。")
            configure_first_use(store, existing_profile=existing, enable_platform=True, approved_known_certificate=exact_cert)
            status.set("首次配置完成。点击登录，在可见 Edge 中自行登录。")
        except Exception as exc: messagebox.showerror("配置未完成", str(exc))

    def login():
        book = fields["book"].get().strip()
        if not book.isdigit(): messagebox.showerror("书籍编号", "先填写书籍编号。"); return
        from annotation.customer.transport import UsenseTransport
        def execute():
            with store.book_lock(book): return UsenseTransport(store, settings(store), book).login()
        task(execute, lambda result: status.set("登录步骤结束；登录状态以随后当前书籍采集为准。"))

    row = ttk.Frame(frame); row.pack(fill="x", pady=12)
    for label, callback in (("准备材料", prepare_action), ("继续准备", lambda: action("resume")),
            ("异常审校", lambda: action("review")), ("导出本地结果", lambda: action("export")),
            ("启动生产", lambda: action("produce")), ("刷新", refresh)):
        ttk.Button(row, text=label, command=callback).pack(side="left", padx=3)
    row = ttk.Frame(frame); row.pack(fill="x")
    ttk.Button(row, text="首次配置", command=setup).pack(side="left", padx=3)
    ttk.Button(row, text="首次登录 / 登录失效", command=login).pack(side="left", padx=3)
    ttk.Button(row, text="从平台选课时并准备", command=platform_action).pack(side="left", padx=3)
    ttk.Button(row, text="未知保存只读对账", command=lambda: action("reconcile")).pack(side="left", padx=3)
    ttk.Button(row, text="本地显示复查", command=lambda: action("display")).pack(side="left", padx=3)
    def close():
        if active["busy"]:
            messagebox.showinfo("任务进行中", "请等待本次记录与释放完成，再关闭窗口。"); return
        for server in servers: server.shutdown(); server.server_close()
        root.destroy()
    root.protocol("WM_DELETE_WINDOW", close)
    refresh(); root.mainloop()


def _offline_settings():
    return {'platform_enabled': False, 'runtime': {'text_python': sys.executable,
                                                   'formula_inference_activated': False}}


def _offline_network():
    import socket
    connect = socket.socket.connect
    connect_ex = socket.socket.connect_ex

    def local_connect(self, address, *args):
        if not isinstance(address, tuple) or address[0] not in {'127.0.0.1', '::1', 'localhost'}:
            raise RuntimeError('离线审校仅使用本地服务，不连接外网。')
        return connect(self, address, *args)

    def local_connect_ex(self, address, *args):
        if not isinstance(address, tuple) or address[0] not in {'127.0.0.1', '::1', 'localhost'}:
            raise RuntimeError('离线审校仅使用本地服务，不连接外网。')
        return connect_ex(self, address, *args)

    socket.socket.connect = local_connect
    socket.socket.connect_ex = local_connect_ex


def _offline_database(root, workspace, expected_sha256):
    from contextlib import closing
    import hashlib
    import sqlite3
    original = root / 'data' / 'source.sqlite'
    if hashlib.sha256(original.read_bytes()).hexdigest() != expected_sha256:
        raise ValueError('包内题源数据库与随包记录不一致。')
    database = workspace / 'source-local.sqlite'
    with closing(sqlite3.connect(original.as_uri() + '?mode=ro', uri=True)) as source:
        pages = source.execute('SELECT page FROM pages ORDER BY page').fetchall()
        images = []
        for (number,) in pages:
            image = root / 'data' / 'images' / f'viewer-{number:03d}.jpg'
            if not image.is_file():
                raise FileNotFoundError(image)
            images.append((str(image), number))
        with closing(sqlite3.connect(database)) as target:
            source.backup(target)
            with target:
                target.executemany('UPDATE pages SET image=? WHERE page=?', images)
    return database, len(pages)


def _offline_portal(store, result, root, bundle, report, *, self_test=False):
    from html import escape
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from urllib.parse import parse_qs, urlsplit
    import webbrowser
    import urllib.request
    from annotation.customer.review import CustomerReviewWorkspace
    from annotation.recognition.content_review_server import make_server
    jobs = {}
    for item in result['results']:
        job, _ = store.job(item['job'])
        jobs[job['id']] = job
    review_servers = {}
    lock = threading.Lock()
    rows = ''.join('<tr data-job="' + identity + '"><td>' + escape(job['lesson'])
                   + '</td><td>' + str(len(job['candidates'])) + '</td><td>待审校</td><td>'
                   + '<a target="_blank" href="/review?job=' + identity + '">打开审校</a> · '
                   + '<a target="_blank" href="/export?job=' + identity + '">导出</a></td></tr>'
                   for identity, job in jobs.items())
    scope_count = len(jobs)
    candidate_count = sum(len(job['candidates']) for job in jobs.values())
    page_count = report['pages']
    page = ('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
            '<title>全书离线审校 · 46007447</title><style>'
            'body{margin:36px auto;padding:0 24px;max-width:1100px;font:16px/1.7 system-ui;color:#18352f;background:#f5f8f6}'
            'h1{font-size:30px;margin-bottom:8px}p{color:#50655e}table{width:100%;border-collapse:collapse;background:white}'
            'td,th{text-align:left;padding:12px 16px;border-bottom:1px solid #dce7e1}th{background:#e7f0eb}'
            'a{color:#16664e}small{display:block;margin:12px 0 24px;color:#6f5730}</style>'
            f'<h1>全书离线审校</h1><p>书 {bundle["book_id"]} · {page_count} 页材料 · {scope_count} 节 · {candidate_count} 个候选</p>'
            '<p>选择课时打开审校，可查看原图、修改候选并导出。材料和修改均保存在解压后的文件夹。</p>'
            '<small>候选待审校，请逐题核对题干、选项及答案。</small>'
            '<table><thead><tr><th>课时</th><th>候选</th><th>状态</th><th>操作</th></tr></thead><tbody>'
            + rows + '</tbody></table></html>').encode('utf-8')
    preview = root / 'data' / 'graphic-preview.html'
    if bundle.get('graphic_preview_sha256'):
        preview_body = preview.read_bytes()
        page = page.replace(b'<table>', '<p><a target="_blank" href="/graphic-preview">查看21题图形选项预览</a></p><table>'.encode('utf-8'), 1)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, body, content_type='text/html; charset=utf-8', download=None):
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            if download:
                self.send_header('Content-Disposition', 'attachment; filename="' + download + '"')
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            parsed = urlsplit(self.path)
            if parsed.path == '/':
                self.send(page)
                return
            if parsed.path == '/graphic-preview' and bundle.get('graphic_preview_sha256'):
                self.send(preview_body)
                return
            identity = parse_qs(parsed.query).get('job', [''])[0]
            if identity not in jobs:
                self.send_error(404)
                return
            if parsed.path == '/review':
                with lock:
                    if identity not in review_servers:
                        review = make_server(CustomerReviewWorkspace(store, identity, settings_provider=_offline_settings))
                        threading.Thread(target=review.serve_forever, daemon=True).start()
                        review_servers[identity] = review
                    review = review_servers[identity]
                self.send_response(302)
                self.send_header('Location', 'http://127.0.0.1:' + str(review.server_address[1]))
                self.end_headers()
            elif parsed.path in {'/export', '/download'}:
                try:
                    output = Path(export_local(store, identity))
                    if parsed.path == '/export':
                        self.send(('<!doctype html><meta charset="utf-8"><h1>课时已导出</h1><p>'
                                   + escape(jobs[identity]['lesson']) + '</p><a href="/download?job=' + identity
                                   + '&amp;kind=html">下载 HTML</a> · <a href="/download?job=' + identity
                                   + '&amp;kind=json">下载 JSON</a>').encode('utf-8'))
                    else:
                        kind = parse_qs(parsed.query).get('kind', ['html'])[0]
                        name = 'job.json' if kind == 'json' else 'index.html'
                        self.send((output / name).read_bytes(), 'application/octet-stream', name)
                except Exception as exc:
                    self.send_error(500, str(exc))
            else:
                self.send_error(404)

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    server.daemon_threads = True
    url = 'http://127.0.0.1:' + str(server.server_address[1])
    try:
        if self_test:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(url, timeout=15) as response:
                body = response.read()
                if response.status != 200 or body.count(b'data-job=') != len(jobs):
                    raise RuntimeError('离线审校列表课时数不正确。')
            report['portal'] = {'http_status': 200, 'rows': len(jobs)}
            if bundle.get('graphic_preview_sha256'):
                with opener.open(url + '/graphic-preview', timeout=15) as response:
                    body = response.read()
                    if response.status != 200:
                        raise RuntimeError('图形选项预览未按包内原件打开。')
                    report['graphic_preview'] = {'http_status': 200, 'articles': body.count(b'<article'),
                                                 'images': body.count(b'<img')}
            identity = next(iter(jobs))
            with opener.open(url + '/review?job=' + identity, timeout=20) as response:
                body = response.read()
                if response.status != 200 or len(body) < 100:
                    raise RuntimeError('课时审校页面未打开。')
                report['review_page'] = {'http_status': 200, 'bytes': len(body)}
            with opener.open(url + '/export?job=' + identity, timeout=20) as response:
                response.read()
            output = Path(export_local(store, identity))
            if not all((output / name).is_file() for name in ['index.html', 'job.json']):
                raise RuntimeError('样例导出文件不完整。')
            report.update(status='PASS', sample_export=str(output))
        else:
            print('离线审校已打开：' + url + '。关闭此窗口可结束本地服务。', flush=True)
            webbrowser.open(url)
            server.serve_forever()
    finally:
        if self_test:
            server.shutdown()
            thread.join(timeout=5)
        server.server_close()
        for review in review_servers.values():
            review.shutdown()
            review.server_close()


def start_offline_bundle(*, self_test=False):
    import time
    import urllib.request
    from collections import Counter
    from annotation.customer.wholebook import prepare_book
    root = ROOT.parent
    _offline_network()
    workspace = root / 'workspace'
    workspace.mkdir(exist_ok=True)
    bundle = json.loads((root / 'bundle.json').read_text(encoding='utf-8'))
    started = time.perf_counter()
    database, page_count = _offline_database(root, workspace, bundle['source_database_sha256'])
    store = Store(workspace)
    result = prepare_book(store, database, book=bundle['book_id'],
        graphic_review=root / 'data' / 'graphic-review.json',
        graphic_review_sha256=bundle['graphic_review_sha256'])
    (workspace / 'offline-results.json').write_bytes(encoded(result))
    for item in result['results']:
        if not item.get('job'):
            raise RuntimeError(item.get('message') or str(item))
    graphic_counts = Counter()
    for item in result['results']:
        job, _ = store.job(item['job'])
        for candidate in job['candidates']:
            for proposal in candidate.get('graphic_option_proposals', []):
                graphic_counts[proposal['display_status']] += 1
    report = {'status': 'STARTED', 'root': str(root), 'python': sys.executable,
              'derived_database': str(database), 'pages': page_count,
              'scopes': len(result['results']),
              'candidates': sum(item.get('candidates', 0) for item in result['results']),
              'graphic_proposals': dict(graphic_counts),
              'new_model_calls': result['new_model_calls'],
              'platform_actions': result['platform_actions']}
    _offline_portal(store, result, root, bundle, report, self_test=self_test)
    if self_test:
        report['wall_seconds'] = time.perf_counter() - started
        (workspace / 'startup-result.json').write_bytes(encoded(report))
        print(json.dumps(report, ensure_ascii=True), flush=True)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=default_workspace())
    parser.add_argument('--customer-deployment', action='store_true',
                        help='交付 GUI：显式点击开始，原设置文件中的开发验收窗口仅保留历史')
    sub = parser.add_subparsers(dest="command")
    p = sub.add_parser('offline', help='打开包内材料的本地审校')
    p.add_argument('--self-test', action='store_true')
    p = sub.add_parser("prepare")
    p.add_argument("--book", required=True); p.add_argument("--lesson", required=True)
    p.add_argument("--questions", nargs="+", required=True); p.add_argument("--answers", nargs="*", default=[])
    for name in ("question-pages", "answer-pages"): p.add_argument("--" + name, default="全部")
    for name in ("question-first-page", "answer-first-page"): p.add_argument("--" + name, type=int)
    p.add_argument("--local-ocr", action="store_true")
    for name in ("resume", "review", "export", "produce", "reconcile", "display"):
        p = sub.add_parser(name); p.add_argument("job")
        if name == "resume": p.add_argument("--local-ocr", action="store_true")
        if name == 'produce': p.add_argument('--questions',nargs='+',help='本次明确选择的印刷题号')
    p = sub.add_parser("setup"); p.add_argument("--existing-profile", type=Path); p.add_argument("--enable-platform", action="store_true")
    p.add_argument("--approved-known-certificate", action="store_true")
    p = sub.add_parser('platform'); p.add_argument('--book',required=True);p.add_argument('--directory',required=True)
    p.add_argument('--question-pages');p.add_argument('--answer-pages');p.add_argument('--local-ocr',action='store_true')
    p = sub.add_parser('import-cache');p.add_argument('evidence',type=Path);p.add_argument('--member')
    p = sub.add_parser('wholebook', help='复用全书 OCR 数据库，按来源窗口离线准备与审校')
    p.add_argument('--database', required=True, type=Path); p.add_argument('--book', required=True)
    p.add_argument('--scopes', nargs='+', help='仅准备所选目录；省略时准备所有普通双栏课时')
    p.add_argument('--graphic-review', type=Path); p.add_argument('--graphic-review-sha256')
    a = parser.parse_args(argv)
    if a.customer_deployment and a.command is not None:
        raise Hold('客户交付模式只用于图形入口，不能作为开发命令的授权覆盖。')
    if a.command == 'offline':
        return start_offline_bundle(self_test=a.self_test)
    store = Store(a.workspace)
    store.customer_start_mode = a.customer_deployment
    if a.command is None: wizard(store); return 0
    if a.command == "prepare":
        result = prepare(store, book=a.book, lesson=a.lesson, question_files=a.questions, answer_files=a.answers,
                         question_pages=a.question_pages, answer_pages=a.answer_pages, allow_local_ocr=a.local_ocr,
                         question_first_page=a.question_first_page, answer_first_page=a.answer_first_page)
    elif a.command == "resume": result = resume(store, a.job, allow_local_ocr=a.local_ocr)
    elif a.command == "review": open_review(store, a.job); return 0
    elif a.command == "export": result = {"output": str(export_local(store, a.job))}
    elif a.command == "produce":
        keys=None
        if a.questions:
            job,_=store.job(a.job)
            if len(a.questions)!=len(set(a.questions)) or any(sum(q['printed_number']==n for q in job['candidates'])!=1 for n in a.questions):
                raise Hold('所选印刷题号不存在、重复或不唯一。')
            keys=[q['key'] for q in job['candidates'] if q['printed_number'] in a.questions]
        result = {"output": str(produce(store, a.job, settings(store),selected_keys=keys))}
    elif a.command == 'display':
        from annotation.customer.native_delivery import check_display
        result={'output':str(check_display(store,a.job,explicit_recheck=True))}
    elif a.command == "reconcile": result = {"output": str(reconcile(store, a.job, settings(store)))}
    elif a.command == 'platform':
        from annotation.customer.platform_source import read_catalog, scope_plan, acquire, prepare_section
        from annotation.customer.source import page_numbers
        current = read_catalog(store,settings(store),a.book)
        plan = scope_plan(store.get(current['catalog_ref']),a.directory,
            question_pages=page_numbers(a.question_pages,current['total_pages']) if a.question_pages else None,
            answer_pages=page_numbers(a.answer_pages,current['total_pages']) if a.answer_pages else None)
        result = prepare_section(store,settings(store),acquire(store,settings(store),plan),allow_local_ocr=a.local_ocr)
    elif a.command == 'import-cache':
        from annotation.customer.recognition_cache import import_evidence
        result = import_evidence(store,a.evidence,member=a.member)
    elif a.command == 'wholebook':
        from annotation.customer.wholebook import prepare_book
        result = prepare_book(store,a.database,book=a.book,scope_ids=a.scopes,
                              graphic_review=a.graphic_review,graphic_review_sha256=a.graphic_review_sha256)
    else: result = configure_first_use(store, existing_profile=a.existing_profile, enable_platform=a.enable_platform,
                                       approved_known_certificate=a.approved_known_certificate)
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"status": "STOPPED", "message": str(exc), "automatic_retry": False}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2)
