"""Build a source database from retained whole-book images and OCR."""
import argparse
import json
import re
import sqlite3
import sys
import time
import unicodedata
from pathlib import Path

def scan_answer_markers(text, reading=False):
    import re,unicodedata
    normalized=unicodedata.normalize("NFKC",text)
    pattern=r"(?<!\d)\((?P<n>[1-9]\d?)\)" if reading else r"(?<!\d)(?P<n>[1-9]\d?)[.、]"
    found=list(re.finditer(pattern,normalized))
    choice=lambda m:bool(re.match(r"[A-G](?=\d|[^A-Za-z]|$)",normalized[m.end():]))
    chain=sum(choice(m) for m in found)>=2
    markers=[]; explanation_body=False
    for i,m in enumerate(found):
        if explanation_body:continue
        at_start=not normalized[:m.start()].strip()
        tail=normalized[m.end():]
        if re.match(r"\s*(?:解|证明|答案|答)",tail):explanation_body=True
        explained=bool(re.match(r"\s*(?:解|证明|答案|答|\(1\))",tail))
        segment=normalized[m.end():found[i+1].start() if i+1<len(found) else len(normalized)].strip()
        single_key=bool(re.fullmatch(r"[A-G]",segment))
        strong=(reading and at_start) or (not reading and (single_key or (at_start and explained) or chain and (choice(m) or explained)))
        reason="READING_HEAD" if reading and strong else "SINGLE_CHOICE_KEY" if single_key else "EXPLANATION_HEAD" if at_start and explained else "CHOICE_KEY_CHAIN" if chain and strong else "NUMERIC_OR_INLINE_AMBIGUITY"
        if not reading and not chain and re.match(r"\d+(?:\.\d+)?\s*[=<>]",tail):
            continue
        markers.append({"number":int(m['n']),"start":m.start(),"end":m.end(),"strong":strong,"reason":reason,"token":m.group(),"at_start":at_start})
    return markers

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--cache", type=Path, required=True, help="folder containing mapping-seed.json, image-manifest.json, images and OCR")
parser.add_argument("--inventory", type=Path, required=True, help="current-directory-inventory.json")
parser.add_argument("--database", type=Path, required=True, help="SQLite database to build or resume")
parser.add_argument("--output", type=Path, required=True, help="machine inventory CSV to write")
parser.add_argument("--deps", type=Path, help="optional rapidocr_onnxruntime package directory")
parser.add_argument("--recoveries", type=Path, help="reviewed original-image recovery plan JSON")
args = parser.parse_args()
ROOT = Path(__file__).resolve().parent
if args.deps:
    sys.path.insert(0, str(args.deps.expanduser().resolve(strict=True)))
CACHE = args.cache.expanduser().resolve(strict=True)
INVENTORY = args.inventory.expanduser().resolve(strict=True)
DB = args.database.expanduser().resolve()
DB.parent.mkdir(parents=True, exist_ok=True)
OUTPUT = args.output.expanduser().resolve()
read = lambda p: json.loads(p.read_text(encoding="utf-8-sig"))
db = sqlite3.connect(DB)
db.executescript("""
CREATE TABLE IF NOT EXISTS pages(page INTEGER PRIMARY KEY, sha TEXT, image TEXT, width INTEGER, height INTEGER, method TEXT, seconds REAL, rows_json TEXT);
CREATE TABLE IF NOT EXISTS scopes(id TEXT PRIMARY KEY, path TEXT, question_pages TEXT, answer_pages TEXT, known_items TEXT, complete INTEGER);
CREATE TABLE IF NOT EXISTS anchors(page INTEGER, row_index INTEGER, kind TEXT, label TEXT, x REAL, y REAL, text TEXT, score REAL, PRIMARY KEY(page,row_index));
""")
mapping = read(CACHE / "mapping-seed.json")
for s in mapping["directories"]:
    db.execute("INSERT OR REPLACE INTO scopes VALUES(?,?,?,?,?,?)", (
        s["directory_id"], json.dumps(s["path"], ensure_ascii=False),
        json.dumps(s.get("question_pages", [])), json.dumps(s.get("answer_pages", [])),
        json.dumps(s.get("recognized_items", []), ensure_ascii=False), int(s.get("complete_enumeration", False))))
db.commit()
engine = None
images = read(CACHE / "image-manifest.json")["pages"]
for p in images:
    n = p["viewer_page"]
    if db.execute("SELECT 1 FROM pages WHERE page=?", (n,)).fetchone():
        continue
    old = read(CACHE / f"ocr/page-{n:03d}.json")
    image_path = CACHE / "images" / f"viewer-{n:03d}.jpg"
    if not image_path.is_file():
        image_path = Path(p["path"])
    if not image_path.is_file():
        raise FileNotFoundError(image_path)
    t = time.monotonic()
    if old["observation"] == "WHOLE_PAGE_RAPIDOCR_CPU":
        rows = old["rows"]
        method = "REUSED_FULL_PAGE"
    else:
        if engine is None:
            from rapidocr_onnxruntime import RapidOCR
            engine = RapidOCR(intra_op_num_threads=2, inter_op_num_threads=1,
                              det_use_cuda=False, cls_use_cuda=False, rec_use_cuda=False,
                              det_use_dml=False, cls_use_dml=False, rec_use_dml=False)
        result, _ = engine(str(image_path), use_det=True, use_cls=False, use_rec=True, text_score=0)
        rows = [[[list(map(float, point)) for point in box], str(text), float(score)]
                for box, text, score in (result or [])]
        method = "FULL_PAGE_RAPIDOCR_CPU"
    seconds = time.monotonic() - t
    db.execute("INSERT INTO pages VALUES(?,?,?,?,?,?,?,?)", (
        n, p["sha256"], str(image_path), p["width"], p["height"], method, seconds,
        json.dumps(rows, ensure_ascii=False)))
    for i, (box, text, score) in enumerate(rows):
        text = unicodedata.normalize("NFKC", text)
        x = min(v[0] for v in box)
        y = min(v[1] for v in box)
        match = re.match(r"^\s*(\d{1,2})\s*[.、．](?!\d)", text)
        kind, label = None, ""
        if match and y > 120 and y < p["height"] - 70:
            kind, label = "NUMBER_CANDIDATE", match[1]
        elif re.search(r"变式|变题|例\s*[1-9一二三四五六七八九]|第\s*\d+\s*课时|参考答案|周测|单元.*卷", text):
            kind, label = "HEADING_OR_VARIANT", text[:60]
        if kind:
            db.execute("INSERT OR REPLACE INTO anchors VALUES(?,?,?,?,?,?,?,?)", (
                n, i, kind, label, x, y, text, score))
    db.commit()
    done = db.execute("SELECT count(*) FROM pages").fetchone()[0]
    print(f"{done}/214 page={n} rows={len(rows)} {method} seconds={seconds:.1f}", flush=True)
inventory = read(INVENTORY)
leaves = {s["id"] for s in inventory["directories"] if s["subdirectories"] == 0}
db.executescript("""
CREATE TABLE IF NOT EXISTS scope_summary(id TEXT PRIMARY KEY, label TEXT, kind TEXT, question_pages TEXT, answer_pages TEXT, numeric_labels TEXT, printed_max INTEGER, variant_markers INTEGER, known_questions INTEGER, worked_examples INTEGER, answer_heading_candidates TEXT);
DELETE FROM scope_summary;
""")
scopes = [s for s in mapping["directories"] if s["directory_id"] in leaves]
leaf_pages = {p for s in scopes for p in s.get("question_pages", [])}
parent_only = [s for s in mapping["directories"]
               if s["directory_id"] not in leaves and set(s.get("question_pages", [])) - leaf_pages]
for s in parent_only:
    s = dict(s)
    s["question_pages"] = sorted(set(s["question_pages"]) - leaf_pages)
    s["parent_only"] = True
    scopes.append(s)
scopes += mapping["unbound_scopes"]
for s in scopes:
    pages = s.get("question_pages", [])
    candidates, variants = [], 0
    for page in pages:
        row = db.execute("SELECT rows_json,width,height FROM pages WHERE page=?", (page,)).fetchone()
        if not row:
            continue
        rows, width, height = json.loads(row[0]), row[1], row[2]
        for box, text, score in rows:
            text = unicodedata.normalize("NFKC", text)
            x, y = min(p[0] for p in box), min(p[1] for p in box)
            if not 120 < y < height - 70:
                continue
            column_width = width / (3 if width > height else 2)
            at_column_start = x % column_width < column_width * 0.28
            m = re.match(r"^\s*(\d{1,2})\s*[.、．(]", text)
            if m and 0 < int(m[1]) < 60 and at_column_start:
                candidates.append(int(m[1]))
            if "变式" in text and "教材" not in text:
                variants += 1
    items = s.get("recognized_items", [])
    known = sum(i.get("kind") != "WORKED_EXAMPLE" for i in items) if s.get("complete_enumeration") else None
    examples = sum(i.get("kind") == "WORKED_EXAMPLE" for i in items)
    db.execute("INSERT INTO scope_summary VALUES(?,?,?,?,?,?,?,?,?,?,?)", (
        s.get("directory_id") or s["scope_id"], " / ".join(s.get("path", [s.get("label", "")])),
        ("PARENT_SOURCE" if s.get("parent_only") else "LEAF") if s.get("directory_id") else "EXTRA_PAPER", json.dumps(pages),
        json.dumps(s.get("answer_pages", [])), json.dumps(sorted(set(candidates))),
        max(candidates, default=0), variants, known, examples,
        json.dumps(s.get("answer_heading_candidates", []), ensure_ascii=False)))
db.commit()
def title_key(text):
    text = unicodedata.normalize('NFKC', text)
    text = re.sub(r'^\s*(?:第[一二三四五六七八九十0-9]+[章节课时]+|[0-9]+)\s*', '', text)
    return ''.join(c for c in text if c.isalnum())
import csv

db.executescript("""
CREATE TABLE IF NOT EXISTS scope_windows(scope_id TEXT,role TEXT,page INTEGER,column INTEGER,x0 REAL,y0 REAL,x1 REAL,y1 REAL,start_observed INTEGER,source_title TEXT,PRIMARY KEY(scope_id,role,page,column,y0));
DROP TABLE IF EXISTS source_items;
CREATE TABLE source_items(scope_id TEXT,item_id TEXT,role TEXT,kind TEXT,label TEXT,start_page INTEGER,start_row INTEGER,end_page INTEGER,fragments_json TEXT,material_id TEXT,PRIMARY KEY(scope_id,item_id));
CREATE TABLE IF NOT EXISTS machine_counts(scope_id TEXT PRIMARY KEY,item_count INTEGER,numbered INTEGER,reading_tasks INTEGER,variants INTEGER,examples INTEGER,number_gaps TEXT);
DELETE FROM scope_windows;
DELETE FROM source_items;
DELETE FROM machine_counts;
""")
page_data = {p: {"rows": json.loads(rows), "width": w, "height": h}
             for p, rows, w, h in db.execute("SELECT page,rows_json,width,height FROM pages")}
scope_id = lambda s: s.get("directory_id") or s["scope_id"]

def alias(s):
    label = s.get("path", [s.get("label", "")])[-1].split("——")[0]
    label = re.sub(r"\[.*?\]", "", label)
    label = re.sub(r"(?:解题技巧|分类强化|重点强化|教材回归)专练.*$", "", label).strip()
    return title_key(label)

def header(s, n):
    target = alias(s)
    rows = page_data[n]["rows"]
    candidates = []
    for i, (box, text, score) in enumerate(rows):
        if re.match(r"^\s*\d+[.．、]", text):
            continue
        key = title_key(text)
        y0, y1 = min(p[1] for p in box), max(p[1] for p in box)
        if key == target or len(target) >= 5 and key.startswith(target) and len(key) <= len(target) + 16:
            candidates.append((y0, y1, i, text))
    return min(candidates, default=None)

ordered = sorted([s for s in scopes if s.get("question_pages")],
                 key=lambda s: (min(s["question_pages"]), header(s, min(s["question_pages"])) or (0,)))
question_pages = {p for s in ordered for p in s["question_pages"]}
for index, s in enumerate(ordered):
    sid = scope_id(s)
    start_page = min(s["question_pages"])
    start = None if not s.get("directory_id") else header(s, start_page)
    end_page = max(question_pages) + 1
    end_y = 0
    if index + 1 < len(ordered):
        following = ordered[index + 1]
        end_page = min(following["question_pages"])
        following_header = header(following, end_page) if following.get("directory_id") else None
        end_y = following_header[0] if following_header and following_header[0] > 200 else 0
        if end_page > max(s["question_pages"]) + 1 or not s.get("directory_id"):
            end_page, end_y = max(s["question_pages"]) + 1, 0
    for n in sorted(question_pages):
        if not start_page <= n <= end_page:
            continue
        p = page_data[n]
        y0 = start[1] if n == start_page and start else 0
        y1 = end_y if n == end_page else p["height"] * .95
        if y1 <= y0:
            continue
        columns = 3 if p["width"] > p["height"] else 2
        for column in range(columns):
            db.execute("INSERT INTO scope_windows VALUES(?,?,?,?,?,?,?,?,?,?)", (
                sid, "question", n, column, column*p["width"]/columns, y0,
                (column+1)*p["width"]/columns, y1, int(bool(start)),
                start[3] if start else "PAGE_RANGE_START"))

# Answer headings carry across columns and pages; an observed heading ends the previous section.
active, active_title = None, ""
answer_pages = list(range(173,189)) + list(range(209,213))
for n in answer_pages:
    p = page_data[n]
    if n == 209:
        active = None
    columns = 3 if p["width"] > p["height"] else 2
    headers = {}
    for s in ordered:
        found = header(s, n)
        if found:
            box = p["rows"][found[2]][0]
            column = min(columns-1, int(sum(v[0] for v in box)/4 / (p["width"]/columns)))
            headers.setdefault(column, []).append((found, scope_id(s)))
    for column in range(columns):
        y0 = 0
        def answer_window(y1):
            if active is not None and y1 > y0:
                db.execute("INSERT OR REPLACE INTO scope_windows VALUES(?,?,?,?,?,?,?,?,?,?)", (
                    active,"answer",n,column,column*p["width"]/columns,y0,
                    (column+1)*p["width"]/columns,y1,1,active_title))
        for found, sid in sorted(headers.get(column, [])):
            answer_window(found[0])
            active, active_title = sid, found[3]
            y0 = found[1]
        answer_window(p["height"]*.95)

count_rows = []
for s in ordered:
    sid = scope_id(s)
    reading = "阅读" in s.get("path", [s.get("label", "")])[-1]
    windows = db.execute("SELECT page,column,x0,y0,x1,y1 FROM scope_windows WHERE scope_id=? AND role='question' ORDER BY page,column,y0", (sid,)).fetchall()
    items, current, seen, prior = [], None, set(), 0
    material_id = f"{sid}/question/MATERIAL/1" if reading else None
    for n, column, x0, y0, x1, y1 in windows:
        selected = []
        for i, (box,text,score) in enumerate(page_data[n]["rows"]):
            x, y = min(v[0] for v in box), min(v[1] for v in box)
            cx = sum(v[0] for v in box)/4
            if x0 <= cx < x1 and y0 <= y < y1:
                selected.append((y,x,i,text,box))
        for y,x,i,text,box in sorted(selected):
            normalized = unicodedata.normalize("NFKC",text)
            m = re.match(r"^\s*\((\d{1,2})\)",normalized) if reading else re.match(r"^\s*(\d{1,2})\s*[.、]",normalized)
            kind, label = None, None
            at_margin = x-x0 < (x1-x0)*.28
            if m and at_margin and 0 < int(m[1]) < 60:
                number = int(m[1])
                if number > prior and number not in seen:
                    kind, label = ("READING_TASK" if reading else "QUESTION"), str(number)
                    seen.add(number); prior = number
            elif "题图" not in normalized and re.match(r"^\s*[【\[]?变式[】\]1-9一二三四五六七八九\s:：]*",normalized):
                kind, label = "VARIANT", f"{prior}:variant:{sum(i['kind']=='VARIANT' for i in items)+1}"
            elif re.match(r"^\s*[【\[]?例\s*[1-9一二三四五六七八九]",normalized):
                kind, label = "WORKED_EXAMPLE", f"example:{len(items)}"
            if kind:
                current = {"kind":kind,"label":label,"start_page":n,"start_row":i,"end_page":n,"fragments":[]}
                items.append(current)
            if current is None:
                if not reading:
                    continue
                current = {"kind":"MATERIAL","label":"shared","start_page":n,"start_row":i,"end_page":n,"fragments":[]}
                items.append(current)
            fragments = current["fragments"]
            if not fragments or (fragments[-1]["page"],fragments[-1]["column"]) != (n,column):
                fragments.append({"page":n,"column":column,"row_indices":[],"bbox":[x,y,max(v[0] for v in box),max(v[1] for v in box)]})
            fragment=fragments[-1]; fragment["row_indices"].append(i)
            b=fragment["bbox"]; b[0]=min(b[0],x); b[1]=min(b[1],y)
            b[2]=max(b[2],max(v[0] for v in box)); b[3]=max(b[3],max(v[1] for v in box))
            current["end_page"] = n
    for i,item in enumerate(items):
        item_id = material_id if item["kind"] == "MATERIAL" else f"{sid}/question/{item['kind']}/{i+1}"
        db.execute("INSERT INTO source_items VALUES(?,?,?,?,?,?,?,?,?,?)", (
            sid,item_id,"question",item["kind"],item["label"],item["start_page"],item["start_row"],item["end_page"],json.dumps(item["fragments"],ensure_ascii=False),material_id if item["kind"]=="READING_TASK" else None))
    counts={kind:sum(i["kind"]==kind for i in items) for kind in ["QUESTION","READING_TASK","VARIANT","WORKED_EXAMPLE"]}
    gaps=sorted(set(range(1,max(seen,default=0)+1))-seen)
    total=sum(counts[k] for k in ["QUESTION","READING_TASK","VARIANT"])
    db.execute("INSERT INTO machine_counts VALUES(?,?,?,?,?,?,?)", (sid,total,counts["QUESTION"],counts["READING_TASK"],counts["VARIANT"],counts["WORKED_EXAMPLE"],json.dumps(gaps)))
    label=" / ".join(s.get("path",[s.get("label","")]))
    count_rows.append([sid,label,total,counts["QUESTION"],counts["READING_TASK"],counts["VARIANT"],counts["WORKED_EXAMPLE"],json.dumps(gaps),json.dumps(s["question_pages"]),db.execute("SELECT count(*) FROM scope_windows WHERE scope_id=? AND role='answer'",(sid,)).fetchone()[0]])

for s,row_summary in zip(ordered,count_rows):
    sid=scope_id(s); reading="阅读" in s.get("path",[s.get("label","")])[-1]
    items,current,prior=[],None,0
    labels=[int(r[0]) for r in db.execute("SELECT label FROM source_items WHERE scope_id=? AND role='question' AND kind IN ('QUESTION','READING_TASK')",(sid,))]
    maximum=max(labels,default=0)
    answer_seen=set()
    for n,column,x0,y0,x1,y1 in db.execute("SELECT page,column,x0,y0,x1,y1 FROM scope_windows WHERE scope_id=? AND role='answer' ORDER BY page,column,y0",(sid,)).fetchall():
        selected=[]
        for i,(box,text,score) in enumerate(page_data[n]["rows"]):
            cx=sum(v[0] for v in box)/4; y=min(v[1] for v in box)
            if x0<=cx<x1 and y0<=y<y1:selected.append((y,min(v[0] for v in box),i,text,box))
        for y,x,i,text,box in sorted(selected):
            normalized=unicodedata.normalize("NFKC",text)
            scanned=scan_answer_markers(text,reading)
            matches=[]
            if scanned and scanned[0]['at_start']:
                for marker in scanned:
                    number=marker['number']
                    if 0<number<=maximum and number not in answer_seen:
                        matches.append((number,marker['start'],marker['end']));answer_seen.add(number)
            if re.match(r"^\s*[【\[]?例\s*[1-9一二三四五六七八九]",normalized):
                current={"kind":"WORKED_EXAMPLE","label":f"example:{len(items)}","start_page":n,"start_row":i,"end_page":n,"fragments":[]};items.append(current)
            accepted=[]
            for match in matches:
                prior=match[0];accepted.append(match)
            segments=[(None,0,len(text))] if not accepted else [(m,m[1],accepted[j+1][1] if j+1<len(accepted) else len(text)) for j,m in enumerate(accepted)]
            for match,a,b in segments:
                if match:
                    current={"kind":"READING_TASK" if reading else "QUESTION","label":str(match[0]),"start_page":n,"start_row":i,"end_page":n,"fragments":[]};items.append(current)
                if current is None:continue
                fragments=current["fragments"]
                if not fragments or (fragments[-1]["page"],fragments[-1]["column"])!=(n,column):
                    fragments.append({"page":n,"column":column,"row_indices":[],"text_spans":[],"bbox":[x,y,max(v[0] for v in box),max(v[1] for v in box)]})
                f=fragments[-1];f["row_indices"].append(i);f["text_spans"].append({"row_index":i,"start":a,"end":b})
                f["bbox"]=[min(f["bbox"][0],x),min(f["bbox"][1],y),max(f["bbox"][2],max(v[0] for v in box)),max(f["bbox"][3],max(v[1] for v in box))]
                current["end_page"]=n
    for i,item in enumerate(items):
        db.execute("INSERT INTO source_items VALUES(?,?,?,?,?,?,?,?,?,?)",(sid,f"{sid}/answer/{item['kind']}/{i+1}","answer",item["kind"],item["label"],item["start_page"],item["start_row"],item["end_page"],json.dumps(item["fragments"],ensure_ascii=False),None))
    cross_page=db.execute("SELECT count(*) FROM source_items WHERE scope_id=? AND role='question' AND end_page>start_page",(sid,)).fetchone()[0]
    split=db.execute("SELECT count(DISTINCT page) FROM scope_windows WHERE scope_id=? AND role='question' AND (y0>200 OR y1<(SELECT height*.9 FROM pages WHERE pages.page=scope_windows.page))",(sid,)).fetchone()[0]
    used={(p,r) for (fragments,) in db.execute("SELECT fragments_json FROM source_items WHERE scope_id=? AND role='question'",(sid,)) for f in json.loads(fragments) for p,r in [(f['page'],i) for i in f['row_indices']]}
    unassigned=set()
    for n,column,x0,y0,x1,y1 in db.execute("SELECT page,column,x0,y0,x1,y1 FROM scope_windows WHERE scope_id=? AND role='question'",(sid,)):
        for anchor_page,anchor_row,x,y in db.execute("SELECT page,row_index,x,y FROM anchors WHERE page=? AND kind='NUMBER_CANDIDATE'",(n,)):
            if x0<=x<x1 and y0<=y<y1 and (n,anchor_row) not in used:unassigned.add((n,anchor_row))
    known=db.execute("SELECT known_questions FROM scope_summary WHERE id=?",(sid,)).fetchone()[0]
    pending=row_summary[2] if known is None else abs(row_summary[2]-known)
    row_summary.extend([len(items),split,cross_page,len(unassigned),known,pending])
db.commit()
output = OUTPUT
output.parent.mkdir(parents=True, exist_ok=True)
with output.open("w",encoding="utf-8-sig",newline="") as stream:
    writer=csv.writer(stream)
    writer.writerow(["目录ID","目录","机器候选数","编号题","阅读任务","变式","例题另列","题号缺口","目录原页范围","答案窗口数","答案锚点数","同页分段页数","跨页候选数","未归属题号候选数","可确认题数_既有逐项枚举","待判候选或计数差异"])
    writer.writerows(count_rows)
print(f"DONE pages=214 scopes={len(ordered)} source_items={sum(r[2] for r in count_rows)} {DB} {output}",flush=True)

def reconcile_sources(database, csv_path):
    """Add source resolutions without changing the in-use source_items snapshot."""
    import csv, json, re, unicodedata
    from pathlib import Path
    pages={n:{"rows":json.loads(raw),"w":w,"h":h} for n,raw,w,h in database.execute("SELECT page,rows_json,width,height FROM pages")}
    scopes={sid:{"label":label,"qpages":json.loads(qp),"apages":json.loads(ap)} for sid,label,qp,ap in database.execute("SELECT id,label,question_pages,answer_pages FROM scope_summary")}
    active_ids={r[0] for r in database.execute("SELECT scope_id FROM machine_counts")}
    scopes={k:v for k,v in scopes.items() if k in active_ids}
    database.executescript("""
    CREATE TABLE IF NOT EXISTS source_exclusions(scope_id TEXT,role TEXT,page INTEGER,row_index INTEGER,reason TEXT,bbox_json TEXT,text TEXT,PRIMARY KEY(scope_id,role,page,row_index));
    CREATE TABLE IF NOT EXISTS graphic_option_candidates(scope_id TEXT,question_item_id TEXT,page INTEGER,label TEXT,row_index INTEGER,label_bbox_json TEXT,candidate_bbox_json TEXT,status TEXT,PRIMARY KEY(question_item_id,page,row_index));
    CREATE TABLE IF NOT EXISTS source_issues(scope_id TEXT,issue_type TEXT,label TEXT,page INTEGER,row_index INTEGER,details_json TEXT,PRIMARY KEY(scope_id,issue_type,label,page,row_index));
    CREATE TABLE IF NOT EXISTS resolved_answer_windows(scope_id TEXT,page INTEGER,column INTEGER,x0 REAL,y0 REAL,x1 REAL,y1 REAL,title_rows_json TEXT,title TEXT,PRIMARY KEY(scope_id,page,column,y0));
    CREATE TABLE IF NOT EXISTS resolved_answer_items(scope_id TEXT,item_id TEXT,kind TEXT,label TEXT,start_page INTEGER,start_row INTEGER,fragments_json TEXT,PRIMARY KEY(item_id));
    CREATE TABLE IF NOT EXISTS pairing_status(scope_id TEXT,question_item_id TEXT,answer_item_id TEXT,status TEXT,reason TEXT,details_json TEXT,PRIMARY KEY(question_item_id));
    CREATE TABLE IF NOT EXISTS answer_marker_quality(item_id TEXT PRIMARY KEY,strength TEXT,reason TEXT,raw_token TEXT,start_offset INTEGER,end_offset INTEGER,raw_text TEXT,page INTEGER,row_index INTEGER);
    CREATE TABLE IF NOT EXISTS source_item_context(item_id TEXT PRIMARY KEY,block_key TEXT,block_label TEXT,origin TEXT,evidence_json TEXT);
    CREATE TABLE IF NOT EXISTS source_recovery_records(item_id TEXT PRIMARY KEY,plan_sha TEXT,record_json TEXT);
    DELETE FROM source_exclusions;
    DELETE FROM graphic_option_candidates;
    DELETE FROM source_issues;
    DELETE FROM resolved_answer_windows;
    DELETE FROM resolved_answer_items;
    DELETE FROM pairing_status;
    DELETE FROM answer_marker_quality;
    """)
    bbox=lambda box:[min(p[0] for p in box),min(p[1] for p in box),max(p[0] for p in box),max(p[1] for p in box)]
    decorations=re.compile(r"^(?:[ABC]?基础题|[ABC]?中档题|[ABC]?综合题|重难点突破|考点针对练|针对训练|变式训练|综合训练|知识点\d*|易错点)")
    excluded={}; graphics=set(); cleaned={}
    for sid,iid,role,kind,label,fragments in database.execute("SELECT scope_id,item_id,role,kind,label,fragments_json FROM source_items").fetchall():
        kept=[]; letters=[]; texts=[]
        for f in json.loads(fragments):
            p=pages[f["page"]]; indices=[]
            for index in f["row_indices"]:
                box,text,score=p["rows"][index]; b=bbox(box); t=unicodedata.normalize("NFKC",text).strip();reason=None
                if decorations.match(t):reason="DECORATION_HEADER"
                elif re.fullmatch(r"\d{1,3}",t) and b[1]>p["h"]*.94 and (b[0]<p["w"]*.13 or b[2]>p["w"]*.87):reason="PAGE_FOOTER"
                elif re.fullmatch(r"(?:变式题图|第\d+题图)",t):reason="FIGURE_CAPTION"
                if reason:
                    excluded[(sid,role,f["page"],index)]=reason
                    database.execute("INSERT OR REPLACE INTO source_exclusions VALUES(?,?,?,?,?,?,?)",(sid,role,f["page"],index,reason,json.dumps(b),text))
                else:
                    indices.append(index);texts.append((f["page"],index,t,b))
                    if role=="question" and re.fullmatch(r"[ABCD]",t):letters.append((f["page"],index,t,b,f))
            if indices:
                boxes=[bbox(p["rows"][i][0]) for i in indices]
                kept.append({**f,"row_indices":indices,"bbox":f['bbox'] if f.get('reviewed_region') else [min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes)]})
        cleaned[iid]=kept
        for n in {l[0] for l in letters}:
            group=[l for l in letters if l[0]==n]
            if len(group)!=4 or {l[2] for l in group}!={"A","B","C","D"}:continue
            group.sort(key=lambda l:(round(l[3][1]/32),l[3][0]));bands=[]
            for l in group:
                if bands and abs(bands[-1][0][3][1]-l[3][1])<35:bands[-1].append(l)
                else:bands.append([l])
            bands=[sorted(b,key=lambda l:l[3][0]) for b in bands]
            grid=[l[2] for band in bands for l in band]==list("ABCD") and len({len(b) for b in bands})==1
            first_y=min(l[3][1] for l in group)
            stem_bottom=max((b[3] for pn,ri,t,b in texts if pn==n and len(t)>8 and b[3]<first_y),default=min(l[4]["bbox"][1] for l in group))
            for band_index,band in enumerate(bands):
                y0=stem_bottom if band_index==0 else max(l[3][3] for l in bands[band_index-1])
                y1=max(l[3][3] for l in band)
                for j,l in enumerate(band):
                    pn,ri,letter,lb,f=l;p=pages[pn];columns=3 if p["w"]>p["h"] else 2;cw=p["w"]/columns;column=f["column"]
                    x0=column*cw if j==0 else (band[j-1][3][0]+band[j-1][3][2]+lb[0]+lb[2])/4
                    x1=(column+1)*cw if j+1==len(band) else (band[j+1][3][0]+band[j+1][3][2]+lb[0]+lb[2])/4
                    proposal=[x0,y0,x1,y1] if grid else None
                    database.execute("INSERT INTO graphic_option_candidates VALUES(?,?,?,?,?,?,?,?)",(sid,iid,pn,letter,ri,json.dumps(lb),json.dumps(proposal),"GRID_REGION_REVIEW" if grid else "BARE_LABEL_GROUP_REVIEW"))
                    graphics.add(iid)
    for sid,gaps in database.execute("SELECT scope_id,number_gaps FROM machine_counts WHERE number_gaps!='[]'").fetchall():
        block_numbers={}
        for block,label in database.execute("SELECT c.block_key,i.label FROM source_item_context c JOIN source_items i ON i.item_id=c.item_id WHERE i.scope_id=? AND i.kind='QUESTION'",(sid,)):
            block_numbers.setdefault(block,set()).add(int(label))
        if len(block_numbers)>1:
            for block,numbers in block_numbers.items():
                for label in sorted(set(range(1,max(numbers,default=0)+1))-numbers):
                    database.execute('INSERT INTO source_issues VALUES(?,?,?,?,?,?)',(sid,'BLOCK_NUMBERING_REVIEW',f'{block}/{label}',scopes[sid]['qpages'][0],-1,json.dumps({'block_key':block,'observed_labels':sorted(numbers),'action':'REVIEW_ORIGINAL_BLOCK_WITHOUT_BORROWING_SAME_NUMBER_FROM_OTHER_BLOCK'},ensure_ascii=False)))
            continue
        for label in json.loads(gaps):
            found=[]
            for n in scopes[sid]["qpages"]:
                for index,(box,text,score) in enumerate(pages[n]["rows"]):
                    if re.match(r"^\s*"+str(label)+r"\s*[.、．]",text):found.append((n,index,text,bbox(box)))
            if found:
                for n,index,text,b in found:
                    strong=bool(re.match(r"^\s*\d+[.、．]\s*(?:[（(]|[A-Z]?[\u4e00-\u9fff])",text))
                    issue="GAP_ANCHOR_OBSERVED" if strong else "NUMERIC_TEXT_REVIEW"
                    database.execute("INSERT INTO source_issues VALUES(?,?,?,?,?,?)",(sid,issue,str(label),n,index,json.dumps({"text":text,"bbox":b,"action":"REVIEW_READING_ORDER_OR_COLUMN"},ensure_ascii=False)))
            else:
                neighbors=database.execute("SELECT item_id,label,start_page,start_row FROM source_items WHERE scope_id=? AND role='question' AND kind='QUESTION' AND label IN (?,?)",(sid,str(label-1),str(label+1))).fetchall()
                database.execute("INSERT INTO source_issues VALUES(?,?,?,?,?,?)",(sid,"NUMBER_NOT_OCR",str(label),scopes[sid]["qpages"][0],-1,json.dumps({"source_pages":scopes[sid]["qpages"],"neighbor_items":neighbors,"action":"REVIEW_ORIGINAL_IMAGE"},ensure_ascii=False)))
    def key(text):
        text=unicodedata.normalize("NFKC",text).replace("探究","探索").replace("百分位数数值表","百分位数值表")
        text=re.sub(r"^\s*(?:第[一二三四五六七八九十0-9]+[章节课时]+|[0-9]+)\s*","",text)
        return ''.join(c for c in text if c.isalnum())
    aliases={}
    for sid,s in scopes.items():
        label=unicodedata.normalize("NFKC",s["label"].split(" / ")[-1]).split("——")[0]
        label=re.sub(r"\[.*?\]","",label)
        label=re.sub(r"(?:解题技巧|分类强化|重点强化|教材回归)专练.*$|周测小卷?$","",label).strip()
        values=[key(label)]
        if "回顾与思考" in label and ")" in label:values.append(key(label.partition(chr(41))[0]))
        aliases[sid]=[v for v in values if v]
    answer_pages=list(range(173,189))+list(range(209,213)); all_headers={}
    for n in answer_pages:
        p=pages[n];columns=3 if p["w"]>p["h"] else 2;cw=p["w"]/columns;headers=[]
        by_col={c:[] for c in range(columns)}
        for index,(box,text,score) in enumerate(p["rows"]):
            b=bbox(box);c=min(columns-1,int((b[0]+b[2])/2/cw));by_col[c].append((b[1],index,text,b))
        for c,rows in by_col.items():
            rows.sort()
            for j,(y,index,text,b) in enumerate(rows):
                if re.match(r"^\s*\d+[.、．]",text):continue
                candidates=[(text,b,[index])]
                if j+1<len(rows) and 0<rows[j+1][0]-y<48:
                    ny,ni,nt,nb=rows[j+1];candidates.append((text+nt,[min(b[0],nb[0]),b[1],max(b[2],nb[2]),max(b[3],nb[3])],[index,ni]))
                matches=[]
                for txt,bb,indices in candidates:
                    k=key(txt)
                    for sid,targets in aliases.items():
                        for target in targets:
                            if k==target or len(target)>=5 and k.startswith(target) and len(k)<=len(target)+16 or "教材" in txt and k.startswith(target) and len(target)>=4:
                                matches.append((len(target),sid,txt,bb,indices))
                if matches:
                    matches.sort(key=lambda m:m[0],reverse=True);best=matches[0]
                    if len({m[1] for m in matches if m[0]==best[0]})==1:
                        _,sid,txt,bb,indices=best;headers.append((c,bb[1],bb[3],sid,txt,indices))
        all_headers[n]=headers
    active=None;title="";title_rows=[]
    for n in answer_pages:
        p=pages[n];columns=3 if p["w"]>p["h"] else 2;cw=p["w"]/columns
        if n==209:active=None
        for c in range(columns):
            y0=0;title_rows=[]
            def window(y1):
                if active is not None and y1>y0:database.execute("INSERT OR REPLACE INTO resolved_answer_windows VALUES(?,?,?,?,?,?,?,?,?)",(active,n,c,c*cw,y0,(c+1)*cw,y1,json.dumps(title_rows),title))
            for col,top,bottom,sid,txt,indices in sorted(h for h in all_headers[n] if h[0]==c):
                window(top);active=sid;title=txt;title_rows=indices;y0=bottom
            window(p["h"]*.95)
    for sid,s in scopes.items():
        labels=[int(r[0]) for r in database.execute("SELECT label FROM source_items WHERE scope_id=? AND role='question' AND kind IN ('QUESTION','READING_TASK')",(sid,))];maximum=max(labels,default=0);items=[];current=None;seen_numbers=set()
        reading="阅读" in s["label"].split(" / ")[-1]
        for n,c,x0,y0,x1,y1,heading_rows in database.execute("SELECT page,column,x0,y0,x1,y1,title_rows_json FROM resolved_answer_windows WHERE scope_id=? ORDER BY page,column,y0",(sid,)).fetchall():
            rows=[];heading_rows=set(json.loads(heading_rows))
            for index,(box,text,score) in enumerate(pages[n]["rows"]):
                b=bbox(box);cx=(b[0]+b[2])/2;cy=(b[1]+b[3])/2
                if x0<=cx<x1 and y0<=cy<y1 and index not in heading_rows and not decorations.match(text):rows.append((b[1],b[0],index,text,b))
            starters=[]
            for y,x,index,text,b in rows:
                t=unicodedata.normalize("NFKC",text)
                m=re.match(r"^\s*\((\d{1,2})\)" if reading else r"^\s*(\d{1,2})[.、]",t)
                if m and 0<int(m[1])<=maximum:starters.append(x)
            anchor_x=min(starters,default=x0)
            for y,x,index,text,b in sorted(rows):
                normalized=unicodedata.normalize("NFKC",text);matches=[]
                raw_matches=scan_answer_markers(text,reading)
                first=raw_matches[0] if raw_matches else None
                at_start=first is not None and first['at_start']
                main_line=at_start and x<=anchor_x+12
                if main_line:
                    for m in raw_matches:
                        number=m['number']
                        if 0<number<=maximum and number not in seen_numbers:
                            matches.append((number,m['start'],m['end'],m));seen_numbers.add(number)
                segments=[(None,0,len(text))] if not matches else [(m,m[1],matches[j+1][1] if j+1<len(matches) else len(text)) for j,m in enumerate(matches)]
                for m,a,z in segments:
                    if m:current={"kind":"READING_TASK" if reading else "QUESTION","label":str(m[0]),"page":n,"row":index,"fragments":[],"marker":m[3],"raw_text":text};items.append(current)
                    if current is None:continue
                    current["fragments"].append({"page":n,"column":c,"row_indices":[index],"text_spans":[{"row_index":index,"start":a,"end":z}],"bbox":b})
        for j,item in enumerate(items):
            iid=f"{sid}/resolved-answer/{item['kind']}/{j+1}"
            database.execute("INSERT INTO resolved_answer_items VALUES(?,?,?,?,?,?,?)",(sid,iid,item["kind"],item["label"],item["page"],item["row"],json.dumps(item["fragments"],ensure_ascii=False)))
            m=item['marker'];database.execute("INSERT INTO answer_marker_quality VALUES(?,?,?,?,?,?,?,?,?)",(iid,"STRONG" if m['strong'] else "REVIEW",m['reason'],m['token'],m['start'],m['end'],item['raw_text'],item['page'],item['row']))
    for sid,iid,kind,label,sp,sr in database.execute("SELECT scope_id,item_id,kind,label,start_page,start_row FROM source_items WHERE role='question' AND kind IN ('QUESTION','READING_TASK','VARIANT')").fetchall():
        answers=database.execute("SELECT item_id FROM resolved_answer_items WHERE scope_id=? AND kind=? AND label=?",(sid,kind,label)).fetchall()
        question_count=database.execute("SELECT count(*) FROM source_items WHERE scope_id=? AND role='question' AND kind=? AND label=?",(sid,kind,label)).fetchone()[0]
        reasons=[]
        if len(answers)!=1:reasons.append("MISSING_OR_MULTIPLE_ANSWER_ANCHORS")
        elif database.execute("SELECT strength FROM answer_marker_quality WHERE item_id=?",(answers[0][0],)).fetchone()[0]!="STRONG":reasons.append("ANSWER_MARKER_REQUIRES_REVIEW")
        if len(answers)==1:
            answer_fragments=json.loads(database.execute("SELECT fragments_json FROM resolved_answer_items WHERE item_id=?",(answers[0][0],)).fetchone()[0])
            for fragment in answer_fragments:
                for span in fragment.get("text_spans",[]):
                    raw=pages[fragment['page']]['rows'][span['row_index']][1][span['start']:span['end']]
                    if re.search(r"\d+\.\d+\.\d+",raw):reasons.append("UNSPLIT_NUMERIC_CHAIN_REVIEW")
            reasons=list(dict.fromkeys(reasons))
        if question_count!=1:reasons.append("DUPLICATE_QUESTION_IDENTITY")
        if iid in graphics:reasons.append("GRAPHIC_OPTIONS_REQUIRE_REVIEW")
        if not cleaned.get(iid):reasons.append("NO_BODY_AFTER_EXCLUSIONS")
        context=database.execute("SELECT block_key,origin FROM source_item_context WHERE item_id=?",(iid,)).fetchone()
        if context and context[0] in ('training','selftest'):reasons.append("ANSWER_BLOCK_CONTEXT_REVIEW")
        if context and context[1] in ('VISUAL_SOURCE_RECOVERY','LAYOUT_RECUT','SOURCE_REANCHORED'):reasons.append("RECOVERED_SOURCE_REGION_REVIEW")
        text=unicodedata.normalize("NFKC",pages[sp]["rows"][sr][1])
        if kind=="QUESTION" and not re.match(r"^\s*\d+[.、]\s*(?:[（(]|[A-Z]?[\u4e00-\u9fff]|\d+[\u4e00-\u9fff])",text):reasons.append("MATH_OR_UNCLEAR_ANCHOR_REVIEW")
        gaps=json.loads(database.execute("SELECT number_gaps FROM machine_counts WHERE scope_id=?",(sid,)).fetchone()[0])
        if kind=="QUESTION" and any(abs(int(label)-gap)==1 for gap in gaps):reasons.append("ADJACENT_TO_MISSING_NUMBER")
        status="READY_TO_PAIR" if not reasons else "CUSTOMER_REVIEW"
        detail={"kind":kind,"label":label,"question_fragments":cleaned.get(iid,[]),"answer_candidates":[a[0] for a in answers]}
        database.execute("INSERT INTO pairing_status VALUES(?,?,?,?,?,?)",(sid,iid,answers[0][0] if len(answers)==1 else None,status,";".join(reasons) or "UNIQUE_SOURCE_ANCHORS_SAME_SCOPE_KIND_LABEL",json.dumps(detail,ensure_ascii=False)))
    database.commit()
    with Path(csv_path).open(encoding="utf-8-sig",newline="") as f:rows=list(csv.DictReader(f));fieldnames=list(rows[0])
    extra=["已定位答案窗口","已定位答案锚点","可直接配对候选","需客户审校实例","装饰页脚排除行","图形选项待审组","缺口定位","原图恢复实例","栏目实例"]
    for field in extra:
        if field not in fieldnames:fieldnames.append(field)
    for row in rows:
        sid=row["目录ID"]
        m=database.execute("SELECT item_count,numbered,reading_tasks,variants,examples,number_gaps FROM machine_counts WHERE scope_id=?",(sid,)).fetchone()
        if m:
            for field,value in zip(['机器候选数','编号题','阅读任务','变式','例题另列','题号缺口'],m):row[field]=value
            known=row.get('可确认题数_既有逐项枚举','');row['待判候选或计数差异']=abs(m[0]-int(known)) if known else m[0]
        row.update(dict(zip(extra,[database.execute("SELECT count(*) FROM resolved_answer_windows WHERE scope_id=?",(sid,)).fetchone()[0],database.execute("SELECT count(*) FROM resolved_answer_items WHERE scope_id=?",(sid,)).fetchone()[0],database.execute("SELECT count(*) FROM pairing_status WHERE scope_id=? AND status='READY_TO_PAIR'",(sid,)).fetchone()[0],database.execute("SELECT count(*) FROM pairing_status WHERE scope_id=? AND status='CUSTOMER_REVIEW'",(sid,)).fetchone()[0],database.execute("SELECT count(*) FROM source_exclusions WHERE scope_id=?",(sid,)).fetchone()[0],database.execute("SELECT count(DISTINCT question_item_id) FROM graphic_option_candidates WHERE scope_id=?",(sid,)).fetchone()[0],';'.join(f"{t}:{lab}@{p}/{i}" for t,lab,p,i in database.execute("SELECT issue_type,label,page,row_index FROM source_issues WHERE scope_id=?",(sid,)))])))
        row['原图恢复实例']=database.execute('SELECT count(*) FROM source_recovery_records r JOIN source_items i ON i.item_id=r.item_id WHERE i.scope_id=?',(sid,)).fetchone()[0]
        row['栏目实例']=';'.join(f'{block}:{count}' for block,count in database.execute('SELECT c.block_key,count(*) FROM source_item_context c JOIN source_items i ON i.item_id=c.item_id WHERE i.scope_id=? GROUP BY c.block_key',(sid,)))
    with Path(csv_path).open("w",encoding="utf-8-sig",newline="") as f:writer=csv.DictWriter(f,fieldnames);writer.writeheader();writer.writerows(rows)
    print("RECONCILED",database.execute("SELECT status,count(*) FROM pairing_status GROUP BY status").fetchall(),flush=True)

def apply_reviewed_regions(database, plan_path):
    import json,re,hashlib
    from pathlib import Path
    plan_bytes=Path(plan_path).read_bytes();plan=json.loads(plan_bytes.decode('utf-8-sig'));plan_sha=hashlib.sha256(plan_bytes).hexdigest()
    pages={n:{'rows':json.loads(raw),'sha':sha,'w':w,'h':h} for n,raw,sha,w,h in database.execute('SELECT page,rows_json,sha,width,height FROM pages')}
    for p in plan['pages']:
        if pages[p['page']]['sha']!=p['source_sha256']:raise ValueError('Recovery image hash differs from source page')
    database.executescript('CREATE TABLE IF NOT EXISTS source_item_context(item_id TEXT PRIMARY KEY,block_key TEXT,block_label TEXT,origin TEXT,evidence_json TEXT);CREATE TABLE IF NOT EXISTS source_recovery_records(item_id TEXT PRIMARY KEY,plan_sha TEXT,record_json TEXT);')
    reset_scope='dir-1792063578574-xrojh8iro'
    records=list(plan['items'])+list(plan.get('additional_tail_items',[]))
    for s in plan.get('additional_same_subsection_instances',[]):
        records.append({**s,'start_page':s['page'],'start_bbox':s['bbox'],'fragments':[{'page':s['page'],'column':s['column'],'part':'full_question','bbox':s['bbox'],'row_indices':s['row_indices'],'source_sha256':pages[s['page']]['sha']}],'evidence':'VISUALLY_OBSERVED_ORIGINAL_IMAGE'})
    for finding in plan.get('structural_findings',[]):
        for region in finding.get('repair_regions',[]):
            sid=finding['scope_id'];label=region['label'];iid=database.execute("SELECT item_id FROM source_items WHERE scope_id=? AND role='question' AND kind='QUESTION' AND label=?",(sid,label)).fetchone()[0]
            n=region['page'];b=region['bbox'];indices=[]
            for i,(box,text,score) in enumerate(pages[n]['rows']):
                cx=sum(v[0] for v in box)/4;cy=sum(v[1] for v in box)/4
                if b[0]<=cx<b[2] and b[1]<=cy<b[3]:indices.append(i)
            records.append({'scope_id':sid,'printed_question':label,'subsection':'原图重切','start_page':n,'column':region['column'],'start_bbox':b,'fragments':[{'page':n,'column':region['column'],'bbox':b,'row_indices':indices,'source_sha256':pages[n]['sha'],'part':'full_question'}],'existing_item_id':iid,'evidence':'VISUALLY_OBSERVED_ORIGINAL_IMAGE'})
    assigned={};prepared=[];affected=set()
    for record in records:
        sid=record['scope_id'];affected.add(sid);label=str(record['printed_question']);block='selftest' if sid==reset_scope else 'main'
        iid=record.get('existing_item_id') or f'{sid}/question/QUESTION/recovered/{block}/{label}'
        fragments=[]
        for f in record['fragments']:
            if f['source_sha256']!=pages[f['page']]['sha']:raise ValueError('Recovery fragment image mismatch')
            indices=[int(i) for i in f['row_indices']];fragments.append({**f,'row_indices':indices,'reviewed_region':True})
            for i in indices:assigned[(sid,f['page'],i)]=iid
        n=record['start_page'];b=record['start_bbox'];candidates=[]
        for f in fragments:
            if f['page']!=n:continue
            for i in f['row_indices']:
                box,text,score=pages[n]['rows'][i];cx=sum(v[0] for v in box)/4;cy=sum(v[1] for v in box)/4
                if b[0]<=cx<b[2] and b[1]<=cy<b[3]:candidates.append((min(v[1] for v in box),i))
        start_row=min(candidates)[1] if candidates else fragments[0]['row_indices'][0]
        prepared.append((iid,sid,label,n,start_row,fragments,block,record))
    # Keep each observed OCR row in one question instance after an explicit reassignment.
    for sid,iid,fragments in database.execute("SELECT scope_id,item_id,fragments_json FROM source_items WHERE role='question'").fetchall():
        if sid not in affected:continue
        kept=[]
        for f in json.loads(fragments):
            indices=[i for i in f['row_indices'] if assigned.get((sid,f['page'],i),iid)==iid]
            if not indices:continue
            boxes=[pages[f['page']]['rows'][i][0] for i in indices]
            kept.append({**f,'row_indices':indices,'bbox':[min(v[0] for box in boxes for v in box),min(v[1] for box in boxes for v in box),max(v[0] for box in boxes for v in box),max(v[1] for box in boxes for v in box)]})
        database.execute('UPDATE source_items SET fragments_json=?,end_page=? WHERE item_id=?',(json.dumps(kept,ensure_ascii=False),max((f['page'] for f in kept),default=database.execute('SELECT start_page FROM source_items WHERE item_id=?',(iid,)).fetchone()[0]),iid))
    for iid,sid,label,n,start_row,fragments,block,record in prepared:
        database.execute('INSERT OR REPLACE INTO source_items VALUES(?,?,?,?,?,?,?,?,?,?)',(sid,iid,'question','QUESTION',label,n,start_row,max(f['page'] for f in fragments),json.dumps(fragments,ensure_ascii=False),None))
        database.execute('INSERT OR REPLACE INTO source_item_context VALUES(?,?,?,?,?)',(iid,block,record.get('subsection',''),'VISUAL_SOURCE_RECOVERY',json.dumps({'plan_sha':plan_sha,'start_bbox':record['start_bbox'],'evidence':record['evidence']},ensure_ascii=False)))
        database.execute('INSERT OR REPLACE INTO source_recovery_records VALUES(?,?,?)',(iid,plan_sha,json.dumps(record,ensure_ascii=False)))
    # The printed self-test restarts at 1, independently of the preceding variant training.
    for iid,kind,n,row in database.execute("SELECT item_id,kind,start_page,start_row FROM source_items WHERE scope_id=? AND role='question'",(reset_scope,)).fetchall():
        text=pages[n]['rows'][row][1]
        if kind=='VARIANT' and text.strip()=='变式训练':database.execute("UPDATE source_items SET kind='DECORATION' WHERE item_id=?",(iid,));continue
        if kind!='QUESTION':continue
        box=pages[n]['rows'][row][0];col=int(sum(v[0] for v in box)/4/(pages[n]['w']/2));y=min(v[1] for v in box)
        block='selftest' if n>126 or n==126 and (col==1 or y>=397) else 'training'
        old=database.execute('SELECT origin,evidence_json FROM source_item_context WHERE item_id=?',(iid,)).fetchone()
        database.execute('INSERT OR REPLACE INTO source_item_context VALUES(?,?,?,?,?)',(iid,block,'复习自测' if block=='selftest' else '变式训练',old[0] if old else 'OBSERVED_COLUMN_BLOCK',old[1] if old else json.dumps({'block_start':[126,0,397]})))
    # Correct a weak numeric/decimal anchor only when its existing source contains the same real label.
    for sid in affected:
        for iid,label,n,row,raw in database.execute("SELECT item_id,label,start_page,start_row,fragments_json FROM source_items WHERE scope_id=? AND role='question' AND kind='QUESTION'",(sid,)).fetchall():
            if database.execute('SELECT 1 FROM source_recovery_records WHERE item_id=?',(iid,)).fetchone():continue
            text=pages[n]['rows'][row][1]
            strong=lambda t:bool(re.match(r'^\s*'+re.escape(label)+r'[.、．]\s*(?:[（(]|[A-Z]?[\u4e00-\u9fff])',t))
            if strong(text):continue
            matches=[]
            for f in json.loads(raw):
                for i in f['row_indices']:
                    box,t,score=pages[f['page']]['rows'][i]
                    if strong(t):matches.append((f['page'],f['column'],min(v[1] for v in box),i))
            if matches:
                page,col,y,index=min(matches);database.execute('UPDATE source_items SET start_page=?,start_row=? WHERE item_id=?',(page,index,iid));database.execute('INSERT OR REPLACE INTO source_item_context VALUES(?,?,?,?,?)',(iid,'main','真实同号源锚','SOURCE_REANCHORED',json.dumps({'old_anchor':[n,row],'new_anchor':[page,index]})))
    # Return text preceding a corrected anchor to its actual preceding question.
    reanchored=database.execute("SELECT i.scope_id,i.item_id,i.start_page,i.start_row,i.fragments_json FROM source_items i JOIN source_item_context c ON c.item_id=i.item_id WHERE c.origin='SOURCE_REANCHORED'").fetchall()
    for sid,iid,n,row,raw in reanchored:
        anchors=[]
        for other,p,r in database.execute("SELECT item_id,start_page,start_row FROM source_items WHERE scope_id=? AND role='question' AND kind='QUESTION'",(sid,)):
            box=pages[p]['rows'][r][0];c=int(sum(v[0] for v in box)/4/(pages[p]['w']/2));anchors.append(((p,c,min(v[1] for v in box)),other))
        anchor=next(a for a,other in anchors if other==iid);remaining=[];transfers=[]
        for f in json.loads(raw):
            keep=[]
            for index in f['row_indices']:
                box=pages[f['page']]['rows'][index][0];position=(f['page'],f['column'],min(v[1] for v in box))
                if position<anchor:
                    preceding=[(a,other) for a,other in anchors if a<=position and other!=iid]
                    if preceding:transfers.append((max(preceding)[1],f['page'],f['column'],index));continue
                keep.append(index)
            if keep:
                boxes=[pages[f['page']]['rows'][i][0] for i in keep];bounds=[min(v[0] for b in boxes for v in b),min(v[1] for b in boxes for v in b),max(v[0] for b in boxes for v in b),max(v[1] for b in boxes for v in b)]
                remaining.append({**f,'row_indices':keep,'bbox':bounds})
        database.execute('UPDATE source_items SET fragments_json=?,end_page=? WHERE item_id=?',(json.dumps(remaining,ensure_ascii=False),max((f['page'] for f in remaining),default=n),iid))
        for target,p,c,index in transfers:
            fragments=json.loads(database.execute('SELECT fragments_json FROM source_items WHERE item_id=?',(target,)).fetchone()[0]);f=next((f for f in fragments if f['page']==p and f['column']==c),None)
            if f is None:f={'page':p,'column':c,'row_indices':[],'bbox':[0,0,0,0]};fragments.append(f)
            f['row_indices']=sorted(set([*f['row_indices'],index]),key=lambda i:min(v[1] for v in pages[p]['rows'][i][0]));boxes=[pages[p]['rows'][i][0] for i in f['row_indices']];f['bbox']=[min(v[0] for b in boxes for v in b),min(v[1] for b in boxes for v in b),max(v[0] for b in boxes for v in b),max(v[1] for b in boxes for v in b)]
            database.execute('UPDATE source_items SET fragments_json=? WHERE item_id=?',(json.dumps(fragments,ensure_ascii=False),target))
    # The last test paper is printed in two columns on all four source images.
    sid='unit-volume-205';items=database.execute("SELECT item_id,start_page,start_row,fragments_json FROM source_items WHERE scope_id=? AND role='question' AND kind='QUESTION'",(sid,)).fetchall();anchors=[]
    for iid,n,row,raw in items:
        box=pages[n]['rows'][row][0];x=sum(v[0] for v in box)/4;y=min(v[1] for v in box);anchors.append(((n,int(x/(pages[n]['w']/2)),y),iid))
    anchors.sort();pool={iid:[] for _,iid in anchors};protected={}
    for iid,ss,label,n,row,fragments,block,record in prepared:
        if ss==sid:
            pool[iid]=fragments
            for f in fragments:
                for index in f['row_indices']:protected[(f['page'],index)]=iid
    for n in range(205,209):
        p=pages[n];cw=p['w']/2;database.execute("DELETE FROM scope_windows WHERE scope_id=? AND role='question' AND page=?",(sid,n))
        for c in range(2):database.execute('INSERT INTO scope_windows VALUES(?,?,?,?,?,?,?,?,?,?)',(sid,'question',n,c,c*cw,0,(c+1)*cw,p['h']*.95,1,'ORIGINAL_IMAGE_TWO_COLUMNS'))
        for index,(box,text,score) in enumerate(p['rows']):
            if (n,index) in protected:continue
            x=sum(v[0] for v in box)/4;y=min(v[1] for v in box);c=min(1,int(x/cw));eligible=[(a,iid) for a,iid in anchors if a<=(n,c,y)]
            if not eligible or y>=p['h']*.95:continue
            iid=max(eligible)[1];f=next((f for f in pool[iid] if f['page']==n and f['column']==c and not f.get('reviewed_region')),None)
            if f is None:f={'page':n,'column':c,'row_indices':[],'bbox':[c*cw,y,(c+1)*cw,y]};pool[iid].append(f)
            f['row_indices'].append(index)
    for iid,fragments in pool.items():
        for f in fragments:
            if f.get('reviewed_region') or not f['row_indices']:continue
            boxes=[pages[f['page']]['rows'][i][0] for i in f['row_indices']];f['bbox']=[min(v[0] for box in boxes for v in box),min(v[1] for box in boxes for v in box),max(v[0] for box in boxes for v in box),max(v[1] for box in boxes for v in box)]
        database.execute('UPDATE source_items SET fragments_json=?,end_page=? WHERE item_id=?',(json.dumps(fragments,ensure_ascii=False),max(f['page'] for f in fragments),iid))
        if not database.execute('SELECT 1 FROM source_item_context WHERE item_id=?',(iid,)).fetchone():database.execute('INSERT INTO source_item_context VALUES(?,?,?,?,?)',(iid,'main','期末试卷双栏','LAYOUT_RECUT',json.dumps({'columns':2,'pages':[205,206,207,208]})))
    for sid in affected:
        kinds=dict(database.execute("SELECT kind,count(*) FROM source_items WHERE scope_id=? AND role='question' GROUP BY kind",(sid,)).fetchall());blocks={}
        for iid,label in database.execute("SELECT item_id,label FROM source_items WHERE scope_id=? AND role='question' AND kind='QUESTION'",(sid,)):
            context=database.execute('SELECT block_key FROM source_item_context WHERE item_id=?',(iid,)).fetchone();blocks.setdefault(context[0] if context else 'main',set()).add(int(label))
        gaps=sorted({n for nums in blocks.values() for n in set(range(1,max(nums,default=0)+1))-nums});count=sum(kinds.get(k,0) for k in ['QUESTION','READING_TASK','VARIANT'])
        database.execute('UPDATE machine_counts SET item_count=?,numbered=?,reading_tasks=?,variants=?,examples=?,number_gaps=? WHERE scope_id=?',(count,kinds.get('QUESTION',0),kinds.get('READING_TASK',0),kinds.get('VARIANT',0),kinds.get('WORKED_EXAMPLE',0),json.dumps(gaps),sid))
    database.commit();print('RECOVERED',len(prepared),'records',len(affected),'scopes',plan_sha,flush=True)

if args.recoveries:
    apply_reviewed_regions(db,args.recoveries.expanduser().resolve(strict=True))
reconcile_sources(db, output)
