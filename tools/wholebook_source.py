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
parser.add_argument("--geometry-deps", type=Path, help="run character geometry using this rapidocr package directory")
parser.add_argument("--training2", type=Path, help="reviewed training question 2 source plan JSON")
parser.add_argument("--boundaries7", type=Path, help="reviewed seven-region boundary plan JSON")
parser.add_argument("--figures", type=Path, help="reviewed question figure binding plan JSON")
args = parser.parse_args()
if bool(args.training2) != bool(args.boundaries7):
    parser.error("--training2 and --boundaries7 must be supplied together")
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

def reconcile_sources(database, csv_path, geometry_dependencies=None):
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
    unique_explanation_heads=observe_unique_explanation_heads(database)
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
                observed_head=(sid,n,index) in unique_explanation_heads
                main_line=at_start and (x<=anchor_x+12 or observed_head)
                if main_line:
                    for m in raw_matches:
                        number=m['number']
                        if 0<number<=maximum and number not in seen_numbers:
                            if observed_head:m={**m,'reason':'UNIQUE_EXPLANATION_HEAD_IN_WINDOW'}
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
    add_reading_solution_candidates(database)
    if geometry_dependencies is not None:observe_answer_geometry(database,geometry_dependencies)
    merge_answer_geometry(database)
    add_reviewed_block_answers(database)
    store_answer_token_sources(database)
    for sid,iid,kind,label,sp,sr in database.execute("SELECT scope_id,item_id,kind,label,start_page,start_row FROM source_items WHERE role='question' AND kind IN ('QUESTION','READING_TASK','VARIANT')").fetchall():
        binding=database.execute('SELECT answer_item_id,block_key FROM reviewed_answer_block_bindings WHERE question_item_id=?',(iid,)).fetchone()
        answers=[(binding[0],)] if binding else database.execute("SELECT item_id FROM resolved_answer_items WHERE scope_id=? AND kind=? AND label=?",(sid,kind,label)).fetchall()
        question_count=database.execute("SELECT count(*) FROM source_items WHERE scope_id=? AND role='question' AND kind=? AND label=?",(sid,kind,label)).fetchone()[0]
        if binding:question_count=database.execute("SELECT count(*) FROM source_items i JOIN source_item_context c ON c.item_id=i.item_id WHERE i.scope_id=? AND i.role='question' AND i.kind=? AND i.label=? AND c.block_key=?",(sid,kind,label,binding[1])).fetchone()[0]
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
        if database.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='answer_geometry_merge_decisions'").fetchone() and database.execute("SELECT 1 FROM answer_geometry_merge_decisions WHERE scope_id=? AND printed_number=? AND status IN ('CONFLICTING_STRONG_SOURCE','MULTIPLE_SOURCE_GROUPS','UNLABELED_PHYSICAL_CONTINUATION')",(sid,label)).fetchone():reasons.append('GEOMETRY_SOURCE_CONFLICT_REVIEW')
        context=database.execute("SELECT block_key,origin FROM source_item_context WHERE item_id=?",(iid,)).fetchone()
        if context and context[0] in ('training','selftest'):reasons.append("ANSWER_BLOCK_CONTEXT_REVIEW")
        if context and context[1] in ('VISUAL_SOURCE_RECOVERY','LAYOUT_RECUT','SOURCE_REANCHORED'):reasons.append("RECOVERED_SOURCE_REGION_REVIEW")
        text=unicodedata.normalize("NFKC",pages[sp]["rows"][sr][1])
        if kind=="QUESTION" and not re.match(r"^\s*\d+[.、]\s*(?:[（(]|[A-Z]?[\u4e00-\u9fff]|\d+[\u4e00-\u9fff])",text):reasons.append("MATH_OR_UNCLEAR_ANCHOR_REVIEW")
        gaps=json.loads(database.execute("SELECT number_gaps FROM machine_counts WHERE scope_id=?",(sid,)).fetchone()[0])
        if kind=="QUESTION" and any(abs(int(label)-gap)==1 for gap in gaps):reasons.append("ADJACENT_TO_MISSING_NUMBER")
        status="READY_TO_PAIR" if not reasons else "CUSTOMER_REVIEW"
        detail={"kind":kind,"label":label,"question_fragments":cleaned.get(iid,[]),"answer_candidates":[a[0] for a in answers]}
        if database.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='question_figure_bindings'").fetchone():
            for zone,field in [('stem','stem_figure_regions'),('options','option_graphic_regions')]:
                detail[field]=[json.loads(r[0]) for r in database.execute('SELECT record_json FROM question_figure_bindings WHERE question_item_id=? AND zone=? ORDER BY page,figure_id',(iid,zone))]
        database.execute("INSERT INTO pairing_status VALUES(?,?,?,?,?,?)",(sid,iid,answers[0][0] if len(answers)==1 else None,status,";".join(reasons) or "UNIQUE_SOURCE_ANCHORS_SAME_SCOPE_KIND_LABEL",json.dumps(detail,ensure_ascii=False)))
    observe_choice_boundary_candidates(database)
    database.commit()
    with Path(csv_path).open(encoding="utf-8-sig",newline="") as f:rows=list(csv.DictReader(f));fieldnames=list(rows[0])
    extra=["已定位答案窗口","已定位答案锚点","可直接配对候选","需客户审校实例","装饰页脚排除行","图形选项待审组","缺口定位","原图恢复实例","栏目实例","几何答案分组","几何来源待审"]
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
        has_geometry=database.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='answer_geometry_links'").fetchone()
        row['几何答案分组']=database.execute('SELECT count(*) FROM answer_geometry_links g JOIN resolved_answer_items a ON a.item_id=g.answer_item_id WHERE a.scope_id=?',(sid,)).fetchone()[0] if has_geometry else 0
        row['几何来源待审']=database.execute("SELECT count(*) FROM answer_geometry_merge_decisions WHERE scope_id=? AND status!='MERGED'",(sid,)).fetchone()[0] if has_geometry else 0
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

def observe_unique_explanation_heads(database):
    import json,re,unicodedata,collections
    pages={n:(json.loads(raw),h) for n,raw,h in database.execute('SELECT page,rows_json,height FROM pages')};counts={(sid,label):count for sid,label,count in database.execute("SELECT scope_id,label,count(*) FROM source_items WHERE role='question' AND kind='QUESTION' GROUP BY scope_id,label")};blocked={sid for sid, in database.execute("SELECT DISTINCT i.scope_id FROM source_item_context c JOIN source_items i ON i.item_id=c.item_id WHERE c.block_key IN ('training','selftest')")}
    for sid,n,row in database.execute("SELECT scope_id,start_page,start_row FROM source_items WHERE role='question' AND kind='VARIANT'"):
        if pages[n][0][row][1].strip().startswith('变式训练'):blocked.add(sid)
    found=collections.defaultdict(dict)
    for sid,n,c,x0,y0,x1,y1 in database.execute('SELECT scope_id,page,column,x0,y0,x1,y1 FROM resolved_answer_windows').fetchall():
        if sid in blocked:continue
        for index,(box,text,score) in enumerate(pages[n][0]):
            t=unicodedata.normalize('NFKC',text);m=re.match(r'^\s*([1-9]\d?)[.、]\s*(?:解|证明)\s*[:：]',t)
            if not m or counts.get((sid,m[1]))!=1:continue
            b=[min(v[0] for v in box),min(v[1] for v in box),max(v[0] for v in box),max(v[1] for v in box)];inside=y0<=(b[1]+b[3])/2<y1;straddles=abs(y1-pages[n][1]*.95)<.01 and y0<=b[1]<y1<b[3]<=pages[n][1]
            if x0-8<=b[0] and b[2]<=x1+8 and (inside or straddles):found[(sid,m[1])][(n,index)]=(c,y0,y1,b,straddles)
    database.executescript('CREATE TABLE IF NOT EXISTS explanation_head_observations(scope_id TEXT,label TEXT,page INTEGER,row_index INTEGER,bbox_json TEXT,window_before_json TEXT,window_after_json TEXT,PRIMARY KEY(scope_id,label,page,row_index));DELETE FROM explanation_head_observations;')
    accepted=set()
    for (sid,label),positions in found.items():
        if len(positions)!=1:continue
        (n,index),(c,y0,y1,b,straddles)=next(iter(positions.items()));end=b[3]+1 if straddles else y1
        if straddles:database.execute('UPDATE resolved_answer_windows SET y1=? WHERE scope_id=? AND page=? AND column=? AND y0=?',(end,sid,n,c,y0))
        database.execute('INSERT INTO explanation_head_observations VALUES(?,?,?,?,?,?,?)',(sid,label,n,index,json.dumps(b),json.dumps([y0,y1]),json.dumps([y0,end])));accepted.add((sid,n,index))
    return accepted

def observe_choice_boundary_candidates(database):
    """Expose a witnessed choice-key boundary for review without approving numeric answers."""
    import json,re
    database.executescript('CREATE TABLE IF NOT EXISTS answer_choice_boundary_candidates(answer_item_id TEXT PRIMARY KEY,question_item_id TEXT,scope_id TEXT,label TEXT,page INTEGER,row_index INTEGER,raw_token TEXT,start_offset INTEGER,end_offset INTEGER,previous_question_item_id TEXT,previous_answer_item_id TEXT,source_sha256 TEXT,proof_json TEXT);DELETE FROM answer_choice_boundary_candidates;')
    rows=database.execute("SELECT scope_id,question_item_id,answer_item_id,details_json FROM pairing_status WHERE status='CUSTOMER_REVIEW' AND reason='ANSWER_MARKER_REQUIRES_REVIEW'").fetchall()
    for sid,qid,aid,detail_json in rows:
        detail=json.loads(detail_json)
        if detail['kind']!='QUESTION' or not aid:continue
        n=int(detail['label']);text,a,b,page,index=database.execute('SELECT raw_text,start_offset,end_offset,page,row_index FROM answer_marker_quality WHERE item_id=?',(aid,)).fetchone()
        if n<2 or '变式' in text or not text[b:].strip() or not re.fullmatch(str(n)+r'[.、．]',text[a:b]):continue
        previous=re.search(r'(?<!\d)'+str(n-1)+r'[.、．][A-D]$',text[:a])
        if previous is None:continue
        if database.execute("SELECT count(*) FROM source_items WHERE scope_id=? AND role='question' AND kind='QUESTION' AND label=?",(sid,str(n))).fetchone()[0]!=1:continue
        if database.execute("SELECT count(*) FROM resolved_answer_items WHERE scope_id=? AND kind='QUESTION' AND label=?",(sid,str(n))).fetchone()[0]!=1:continue
        prev=database.execute("SELECT p.question_item_id,p.answer_item_id,q.raw_text,q.page,q.row_index,q.start_offset,q.end_offset FROM pairing_status p JOIN source_items i ON i.item_id=p.question_item_id JOIN answer_marker_quality q ON q.item_id=p.answer_item_id WHERE p.scope_id=? AND p.status='READY_TO_PAIR' AND i.kind='QUESTION' AND i.label=?",(sid,str(n-1))).fetchall()
        if len(prev)!=1 or prev[0][2:5]!=(text,page,index) or prev[0][5:7]!=(previous.start(),previous.end()-1):continue
        source,raw=database.execute('SELECT sha,rows_json FROM pages WHERE page=?',(page,)).fetchone();box,original,score=json.loads(raw)[index]
        if original!=text:continue
        cx=sum(p[0] for p in box)/4;cy=sum(p[1] for p in box)/4
        windows=[list(w) for w in database.execute('SELECT column,x0,y0,x1,y1 FROM resolved_answer_windows WHERE scope_id=? AND page=?',(sid,page)) if w[1]<=cx<w[3] and w[2]<=cy<w[4]]
        if len(windows)!=1:continue
        proof={'rule':'READY_PREVIOUS_CHOICE_BOUNDARY','previous_choice':text[previous.start():previous.end()],'previous_span':[previous.start(),previous.end()],'current_span':[a,b],'raw_text':text,'window':windows[0],'original_row_bbox':box,'requires_review':True}
        database.execute('INSERT INTO answer_choice_boundary_candidates VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',(aid,qid,sid,str(n),page,index,text[a:b],a,b,prev[0][0],prev[0][1],source,json.dumps(proof,ensure_ascii=False)))
        detail['answer_boundary_candidate']=proof
        database.execute('UPDATE pairing_status SET details_json=? WHERE question_item_id=?',(json.dumps(detail,ensure_ascii=False),qid))

def apply_question_figure_bindings(database, plan_path):
    """Bind visually located regions by source question identity, including unlettered figures."""
    import json,hashlib
    from pathlib import Path
    raw=Path(plan_path).read_bytes();plan=json.loads(raw.decode('utf-8-sig'));sha=hashlib.sha256(raw).hexdigest()
    pages={n:(source,w,h) for n,source,w,h in database.execute('SELECT page,sha,width,height FROM pages')}
    for p in plan['source_images']:
        if pages[p['page']]!=(p['source_sha256'],p['width'],p['height']):raise ValueError('Figure source page differs')
    database.executescript('CREATE TABLE IF NOT EXISTS question_figure_bindings(figure_id TEXT PRIMARY KEY,scope_id TEXT,question_item_id TEXT,printed_question TEXT,zone TEXT,role TEXT,page INTEGER,column INTEGER,bbox_json TEXT,source_sha256 TEXT,source_width INTEGER,source_height INTEGER,label TEXT,figure_label TEXT,subquestion_refs_json TEXT,original_ocr_row_refs_json TEXT,visual_crop_checked INTEGER,assignment_basis TEXT,plan_sha TEXT,record_json TEXT);CREATE TABLE IF NOT EXISTS question_figure_scope_reviews(scope_id TEXT PRIMARY KEY,plan_sha TEXT,plan_json TEXT);')
    database.execute('DELETE FROM question_figure_bindings WHERE scope_id=?',(plan['scope_id'],))
    database.execute('INSERT OR REPLACE INTO question_figure_scope_reviews VALUES(?,?,?)',(plan['scope_id'],sha,json.dumps(plan,ensure_ascii=False)))
    for item in plan['items']:
        qid=item['question_item_id'];identity=database.execute("SELECT scope_id,label FROM source_items WHERE item_id=? AND role='question' AND kind='QUESTION'",(qid,)).fetchone()
        if identity!=(item['scope_id'],item['printed_question']):raise ValueError('Figure question identity differs')
        for region in [*item['stem_figure_regions'],*item['option_graphic_regions']]:
            source,w,h=pages[region['page']];x0,y0,x1,y1=region['bbox']
            if source!=region['source_sha256'] or not(0<=x0<x1<=w and 0<=y0<y1<=h):raise ValueError('Figure region is outside its source')
            fid=region.get('figure_id') or f"{qid}/option-graphic/{region['label']}"
            record={**region,'figure_id':fid,'question_item_id':qid,'scope_id':item['scope_id'],'assignment_basis':item['assignment_basis'],'position_note':item['position_note'],'plan_sha256':sha}
            refs=region.get('original_ocr_row_refs',[region['original_label_ocr_row']] if 'original_label_ocr_row' in region else [])
            database.execute('INSERT INTO question_figure_bindings VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(fid,item['scope_id'],qid,item['printed_question'],region['zone'],region['role'],region['page'],region['column'],json.dumps(region['bbox']),source,w,h,region.get('label'),region.get('figure_label'),json.dumps(region.get('subquestion_refs',[])),json.dumps(refs),int(region['visual_crop_checked']),item['assignment_basis'],sha,json.dumps(record,ensure_ascii=False)))
    database.commit()

def apply_source_region_updates(database, training_path, boundary_path):
    """Apply the supplied original-image regions to source instances."""
    import json,hashlib
    from pathlib import Path
    database.execute('CREATE TABLE IF NOT EXISTS source_review_inputs(name TEXT PRIMARY KEY,plan_sha TEXT,plan_json TEXT)')
    plans={}
    for name,path in [('training2',training_path),('boundaries7',boundary_path)]:
        raw=Path(path).read_bytes();plan=json.loads(raw.decode('utf-8-sig'));plans[name]=plan
        for p in plan['pages']:
            if database.execute('SELECT sha FROM pages WHERE page=?',(p['page'],)).fetchone()[0]!=p['source_sha256']:raise ValueError('Source region image differs')
        database.execute('INSERT OR REPLACE INTO source_review_inputs VALUES(?,?,?)',(name,hashlib.sha256(raw).hexdigest(),json.dumps(plan,ensure_ascii=False)))
    plan=plans['training2'];sid=plan['scope_id'];q=plan['question'];iid=f'{sid}/question/QUESTION/recovered/training/2'
    source_sha=database.execute('SELECT sha FROM pages WHERE page=?',(q['page'],)).fetchone()[0]
    fragments=[{'page':q['page'],'column':q['column'],'bbox':q['full_bbox'],'row_indices':q['original_ocr_rows'],'reviewed_region':True,'source_sha256':source_sha,'part':'full_question'}]
    record={'scope_id':sid,'printed_question':'2','subsection':q['subsection'],'start_page':q['page'],'start_bbox':q['start_bbox'],'fragments':fragments,'evidence':'VISUALLY_OBSERVED_ORIGINAL_IMAGE','block_key':'training'}
    sha=database.execute("SELECT plan_sha FROM source_review_inputs WHERE name='training2'").fetchone()[0]
    database.execute('INSERT OR REPLACE INTO source_items VALUES(?,?,?,?,?,?,?,?,?,?)',(sid,iid,'question','QUESTION','2',q['page'],q['original_ocr_rows'][0],q['page'],json.dumps(fragments,ensure_ascii=False),None))
    database.execute('INSERT OR REPLACE INTO source_item_context VALUES(?,?,?,?,?)',(iid,'training','变式训练','VISUAL_SOURCE_RECOVERY',json.dumps({'plan_sha':sha,'start_bbox':q['start_bbox']},ensure_ascii=False)))
    database.execute('INSERT OR REPLACE INTO source_recovery_records VALUES(?,?,?)',(iid,sha,json.dumps(record,ensure_ascii=False)))
    old=plan['old_question1_resegmentation'];old_iid=old['item_id']
    kept=[{'page':q['page'],'column':q['column'],'bbox':old['retain_bbox'],'row_indices':old['retain_rows'],'reviewed_region':True,'source_sha256':source_sha,'part':'full_question'}]
    database.execute('UPDATE source_items SET fragments_json=?,end_page=? WHERE item_id=?',(json.dumps(kept,ensure_ascii=False),q['page'],old_iid))
    updated={}
    for r in plans['boundaries7']['records']:
        updated[(r['item_id'],r['page'])]=r['corrected_full_region_bbox']
    for r in plans['boundaries7']['coupled_neighbor_adjustments']:
        updated[(r['item_id'],r['page'])]=r['corrected_bbox']
    for (target,page),region in updated.items():
        fragments=json.loads(database.execute('SELECT fragments_json FROM source_items WHERE item_id=?',(target,)).fetchone()[0])
        for f in fragments:
            center=(f['bbox'][0]+f['bbox'][2])/2
            if f['page']==page and region[0]<=center<region[2]:
                f.update(bbox=region,reviewed_region=True,source_sha256=database.execute('SELECT sha FROM pages WHERE page=?',(page,)).fetchone()[0]);f.setdefault('part','full_question')
        database.execute('UPDATE source_items SET fragments_json=? WHERE item_id=?',(json.dumps(fragments,ensure_ascii=False),target))
    kinds=dict(database.execute("SELECT kind,count(*) FROM source_items WHERE scope_id=? AND role='question' GROUP BY kind",(sid,)))
    blocks={}
    for block,label in database.execute("SELECT c.block_key,i.label FROM source_items i JOIN source_item_context c ON c.item_id=i.item_id WHERE i.scope_id=? AND i.kind='QUESTION'",(sid,)):blocks.setdefault(block,set()).add(int(label))
    gaps=sorted({n for nums in blocks.values() for n in set(range(1,max(nums,default=0)+1))-nums})
    database.execute('UPDATE machine_counts SET item_count=?,numbered=?,number_gaps=? WHERE scope_id=?',(sum(kinds.get(k,0) for k in ['QUESTION','READING_TASK','VARIANT']),kinds.get('QUESTION',0),json.dumps(gaps),sid))
    database.commit()

def add_reviewed_block_answers(database):
    import json,re
    database.executescript('CREATE TABLE IF NOT EXISTS reviewed_answer_block_bindings(question_item_id TEXT PRIMARY KEY,answer_item_id TEXT,block_key TEXT,record_json TEXT);DELETE FROM reviewed_answer_block_bindings;')
    if not database.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='source_review_inputs'").fetchone():return
    row=database.execute("SELECT plan_json FROM source_review_inputs WHERE name='training2'").fetchone()
    if not row:return
    plan=json.loads(row[0]);sid=plan['scope_id'];a=plan['answer'];s=plan['same_scope_selftest2']
    for block,page,index,bbox,indices,qid in [
        ('training',a['page'],a['shared_original_row'],a['full_bbox'],[a['shared_original_row'],*a['additional_original_rows']],f'{sid}/question/QUESTION/recovered/training/2'),
        ('selftest',s['answer_page'],s['answer_row'],s['answer_bbox'],[s['answer_row']],s['question_item_id'])]:
        rows=json.loads(database.execute('SELECT rows_json FROM pages WHERE page=?',(page,)).fetchone()[0]);text=rows[index][1];marker=re.search(r'(?<!\d)2[.、．]',text)
        if marker is None:raise ValueError('Observed block answer 2 marker missing')
        iid=f'{sid}/reviewed-block-answer/{block}/2';fragment={'page':page,'column':0,'row_indices':indices,'bbox':bbox,'reviewed_region':True,'answer_block_key':block,'requires_review':True,'text_spans':[{'row_index':index,'start':marker.start(),'end':len(text) if block=='training' else s['answer_original_text_span'][1]}]}
        database.execute('INSERT OR REPLACE INTO resolved_answer_items VALUES(?,?,?,?,?,?,?)',(sid,iid,'QUESTION','2',page,index,json.dumps([fragment],ensure_ascii=False)))
        database.execute('INSERT OR REPLACE INTO answer_marker_quality VALUES(?,?,?,?,?,?,?,?,?)',(iid,'REVIEW','VISUAL_SOURCE_BLOCK_ANSWER',marker.group(),marker.start(),marker.end(),text,page,index))
        database.execute('INSERT INTO reviewed_answer_block_bindings VALUES(?,?,?,?)',(qid,iid,block,json.dumps({'block_title':a['block_title'] if block=='training' else s['answer_block_title'],'source':'training2'},ensure_ascii=False)))
        database.execute('INSERT OR REPLACE INTO source_item_context VALUES(?,?,?,?,?)',(iid,block,'变式训练' if block=='training' else '复习自测','VISUAL_BLOCK_SOURCE',json.dumps({'question_item_id':qid,'source':'training2'},ensure_ascii=False)))

def store_answer_token_sources(database):
    """Keep source glyphs in raw_token and normalized spelling separately."""
    import unicodedata
    database.executescript('CREATE TABLE IF NOT EXISTS answer_marker_normalization(item_id TEXT PRIMARY KEY,normalized_token TEXT);DELETE FROM answer_marker_normalization;')
    for iid,a,b,text in database.execute('SELECT item_id,start_offset,end_offset,raw_text FROM answer_marker_quality').fetchall():
        token=text[a:b]
        database.execute('UPDATE answer_marker_quality SET raw_token=? WHERE item_id=?',(token,iid))
        database.execute('INSERT INTO answer_marker_normalization VALUES(?,?)',(iid,unicodedata.normalize('NFKC',token)))

def add_reading_solution_candidates(database):
    import json,re,unicodedata
    database.executescript('CREATE TABLE IF NOT EXISTS reading_answer_contexts(context_id TEXT PRIMARY KEY,scope_id TEXT,windows_json TEXT,rows_json TEXT);DELETE FROM reading_answer_contexts;')
    for sid,maximum in database.execute("SELECT scope_id,max(cast(label AS INTEGER)) FROM source_items WHERE role='question' AND kind='READING_TASK' GROUP BY scope_id").fetchall():
        windows=database.execute('SELECT page,column,x0,y0,x1,y1,title_rows_json FROM resolved_answer_windows WHERE scope_id=? ORDER BY page,column,y0',(sid,)).fetchall();rows=[]
        for n,c,x0,y0,x1,y1,title_rows in windows:
            headings=set(json.loads(title_rows));observed=json.loads(database.execute('SELECT rows_json FROM pages WHERE page=?',(n,)).fetchone()[0])
            for index,(box,text,score) in enumerate(observed):
                x=min(v[0] for v in box);cy=sum(v[1] for v in box)/4;cx=sum(v[0] for v in box)/4
                if x0<=cx<x1 and y0<=cy<y1 and index not in headings:rows.append((n,c,cy,x,index,text,[x0,y0,x1,y1]))
        bands=[]
        for r in sorted(rows):
            if bands and r[:2]==bands[-1][0][:2] and abs(r[2]-bands[-1][0][2])<=8:bands[-1].append(r)
            else:bands.append([r])
        started=False;expected=1;anchors=[]
        for band in bands:
            for n,c,cy,x,index,text,window in sorted(band,key=lambda r:r[3]):
                normalized=unicodedata.normalize('NFKC',text)
                prefix=re.match(r'^\s*解\s*[:：]\s*\(1\)',normalized)
                if not started:
                    if not prefix:continue
                    started=True
                if len(normalized)!=len(text):continue
                for m in re.finditer(r'\(([1-9]\d?)\)',normalized):
                    if int(m[1])==expected and expected<=maximum:
                        anchors.append((expected,n,c,index,text,m.start(),m.end(),window));expected+=1
            if expected>maximum:break
        if not anchors:continue
        context_id=f'{sid}/answer/shared-reading-context'
        database.execute('INSERT INTO reading_answer_contexts VALUES(?,?,?,?)',(context_id,sid,json.dumps(windows),json.dumps([{'page':n,'column':c,'row_index':i} for n,c,cy,x,i,t,w in rows])))
        previous=database.execute("SELECT item_id FROM resolved_answer_items WHERE scope_id=? AND kind='READING_TASK'",(sid,)).fetchall()
        for iid, in previous:database.execute('DELETE FROM answer_marker_quality WHERE item_id=?',(iid,))
        database.execute("DELETE FROM resolved_answer_items WHERE scope_id=? AND kind='READING_TASK'",(sid,))
        for number,n,c,index,text,a,b,window in anchors:
            iid=f'{sid}/reading-solution-answer/{number}';end=next((aa for nn,p,cc,ii,tt,aa,bb,ww in anchors if p==n and ii==index and aa>a),len(text))
            fragment={'page':n,'column':c,'row_indices':[index],'text_spans':[{'row_index':index,'start':a,'end':end}],'bbox':window,'shared_reading_context_id':context_id,'shared_answer_bbox':True,'anchor_only':True,'requires_review':True}
            database.execute('INSERT INTO resolved_answer_items VALUES(?,?,?,?,?,?,?)',(sid,iid,'READING_TASK',str(number),n,index,json.dumps([fragment],ensure_ascii=False)))
            normalized=unicodedata.normalize('NFKC',text);database.execute('INSERT INTO answer_marker_quality VALUES(?,?,?,?,?,?,?,?,?)',(iid,'REVIEW','READING_SOLUTION_SHARED_CONTEXT',normalized[a:b],a,b,text,n,index))

def observe_answer_geometry(database, dependency_path, target_rows=None):
    import json,re,sys,hashlib,statistics,unicodedata
    from pathlib import Path
    sys.path.insert(0,str(dependency_path))
    import numpy as np
    from PIL import Image
    import rapidocr_onnxruntime
    from rapidocr_onnxruntime import RapidOCR
    database.executescript('''CREATE TABLE IF NOT EXISTS answer_geometry_observations(observation_id TEXT PRIMARY KEY,scope_id TEXT,page INTEGER,row_index INTEGER,original_text TEXT,source_sha TEXT,crop_json TEXT,ocr_text TEXT,char_boxes_json TEXT,char_texts_json TEXT,char_scores_json TEXT,method_json TEXT,status TEXT,gaps_json TEXT);
    CREATE TABLE IF NOT EXISTS answer_geometry_groups(group_id TEXT PRIMARY KEY,observation_id TEXT,printed_number TEXT,text TEXT,bbox_json TEXT,char_span_json TEXT,status TEXT,proof_json TEXT);''')
    normalize=lambda t:unicodedata.normalize('NFKC',t)
    candidates={}
    for sid,n,row,text in database.execute('SELECT DISTINCT a.scope_id,q.page,q.row_index,q.raw_text FROM resolved_answer_items a JOIN answer_marker_quality q ON q.item_id=a.item_id').fetchall():
        t=normalize(text)
        if target_rows is not None and (n,row) not in set(target_rows):continue
        keys=re.findall(r'(?<!\d)[1-9]\d?[.、][A-G](?=\d|[^A-Za-z]|$)',t)
        if len(keys)>=2 and not re.search('解|证明|答案|答',t):candidates[(sid,n,row)]=text
    method={'engine':'rapidocr_onnxruntime','version':'1.4.4','observation_format':3,'device':'CPU','scale':2,'return_word_box':True,'crop_padding':[6,4,7,5],'gap_width_to_median_character':1.4,'ink_threshold':160,'maximum_white_column_ink_ratio':.02,'minimum_white_run_to_median_character':1.,'minimum_character_confidence':.85}
    package=Path(rapidocr_onnxruntime.__file__).parent
    method['models']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (package/'models').glob('*.onnx')}
    method_json=json.dumps(method,sort_keys=True);engine=None;images={};count=0
    for (sid,n,row),original in sorted(candidates.items(),key=lambda pair:(pair[0][1],pair[0][2],pair[0][0])):
        image_path,sha,w,h,rows_json=database.execute('SELECT image,sha,width,height,rows_json FROM pages WHERE page=?',(n,)).fetchone();box=json.loads(rows_json)[row][0]
        raw=[min(v[0] for v in box),min(v[1] for v in box),max(v[0] for v in box),max(v[1] for v in box)]
        oid=hashlib.sha256(json.dumps([sid,n,row,sha,original,method_json],ensure_ascii=False).encode()).hexdigest()
        if database.execute('SELECT 1 FROM answer_geometry_observations WHERE observation_id=?',(oid,)).fetchone():continue
        if engine is None:engine=RapidOCR(intra_op_num_threads=2,inter_op_num_threads=1,det_use_cuda=False,cls_use_cuda=False,rec_use_cuda=False,det_use_dml=False,cls_use_dml=False,rec_use_dml=False)
        if n not in images:images[n]=Image.open(image_path).convert('RGB')
        image=images[n];crop=[max(0,int(raw[0])-6),max(0,int(raw[1])-4),min(w,int(raw[2])+7),min(h,int(raw[3])+5)]
        roi=image.crop(tuple(crop));roi=roi.resize((roi.width*2,roi.height*2));recognized,_=engine(np.asarray(roi)[:,:,::-1].copy(),use_cls=False,text_score=0,return_word_box=True)
        matching=[r for r in recognized or [] if len(r)==6 and normalize(r[1])==normalize(original) and len(r[3])==len(r[4])==len(r[5])==len(r[1])]
        observation_method_json=method_json
        if not matching:
            pieces=[r for r in recognized or [] if len(r)==6 and len(r[3])==len(r[4])==len(r[5])==len(r[1]) and abs((min(v[1] for v in r[0])+max(v[1] for v in r[0]))/4+crop[1]-(raw[1]+raw[3])/2)<=max(8,(raw[3]-raw[1])*.6)]
            pieces.sort(key=lambda r:min(v[0] for v in r[0]))
            if pieces and normalize(''.join(r[1] for r in pieces))==normalize(original):
                pts=[v for r in pieces for v in r[0]];x0=min(v[0] for v in pts);y0=min(v[1] for v in pts);x1=max(v[0] for v in pts);y1=max(v[1] for v in pts)
                matching=[[[[x0,y0],[x1,y0],[x1,y1],[x0,y1]],''.join(r[1] for r in pieces),min(r[2] for r in pieces),[b for r in pieces for b in r[3]],[c for r in pieces for c in r[4]],[s for r in pieces for s in r[5]]]]
                observation_method_json=json.dumps({**method,'detector_regions':[{'text':r[1],'bbox':[[float(x)/2+crop[0],float(y)/2+crop[1]] for x,y in r[0]],'confidence':float(r[2])} for r in pieces]},ensure_ascii=False)
        if not matching:
            database.execute('INSERT INTO answer_geometry_observations VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(oid,sid,n,row,original,sha,json.dumps(crop),json.dumps([r[1] for r in recognized or []],ensure_ascii=False),'[]','[]','[]',method_json,'OCR_TEXT_REVIEW','[]'));database.commit();continue
        r=min(matching,key=lambda r:abs((min(v[1] for v in r[0])+max(v[1] for v in r[0]))/4+crop[1]-(raw[1]+raw[3])/2))
        chars=r[4];scores=[float(s) for s in r[5]];char_boxes=[[[float(x)/2+crop[0],float(y)/2+crop[1]] for x,y in b] for b in r[3]]
        if any(len(normalize(c))!=1 for c in chars) or len(normalize(original))!=len(original):status='NORMALIZATION_REVIEW';breaks=[];gaps=[]
        else:
            widths=[max(v[0] for v in b)-min(v[0] for v in b) for b in char_boxes];median=statistics.median(widths);gray=np.asarray(image.convert('L'));breaks=[];gaps=[]
            for i in range(1,len(chars)):
                previous=char_boxes[i-1];current=char_boxes[i];left=max(v[0] for v in previous);right=min(v[0] for v in current);gap=right-left
                if gap<max(4,median*1.4):continue
                top=min(min(v[1] for v in previous),min(v[1] for v in current));bottom=max(max(v[1] for v in previous),max(v[1] for v in current));gap_box=[int(left)+1,max(0,int(top)),int(right)-1,min(h,int(bottom)+1)];pixels=gray[gap_box[1]:gap_box[3],gap_box[0]:gap_box[2]];ink=float((pixels<160).mean()) if pixels.size else 1.
                white=(pixels<160).mean(axis=0)<=.02 if pixels.size else [];best_a=best_b=run_a=0
                for column,is_white in enumerate(white):
                    if not is_white:run_a=column+1
                    elif column+1-run_a>best_b-best_a:best_a,best_b=run_a,column+1
                white_width=best_b-best_a;passed=white_width>=max(4,median);gaps.append({'before_character':i,'width':gap,'median_char_width':median,'bbox':gap_box,'ink_ratio':ink,'white_run_bbox':[gap_box[0]+best_a,gap_box[1],gap_box[0]+best_b,gap_box[3]],'white_run_width':white_width,'passed':passed})
                if passed:breaks.append(i)
            status='PIXEL_GROUPS_OBSERVED'
        database.execute('INSERT INTO answer_geometry_observations VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(oid,sid,n,row,original,sha,json.dumps(crop),r[1],json.dumps(char_boxes),json.dumps(chars,ensure_ascii=False),json.dumps(scores),observation_method_json,status,json.dumps(gaps)))
        groups=[];bounds=[0,*breaks,len(chars)]
        for a,b in zip(bounds,bounds[1:]):
            text=''.join(chars[a:b]);m=re.match(r'^([1-9]\d?)[.、．]',normalize(text))
            if m:groups.append({'number':m[1],'a':a,'b':b})
            elif groups:groups[-1]['b']=b
        numbers=[int(g['number']) for g in groups];ordered=len(groups)>=2 and numbers==sorted(set(numbers))
        windows=database.execute('SELECT x0,y0,x1,y1 FROM resolved_answer_windows WHERE scope_id=? AND page=?',(sid,n)).fetchall();within=any(x0-8<=raw[0] and raw[2]<=x1+8 and y0<=(raw[1]+raw[3])/2<y1 for x0,y0,x1,y1 in windows)
        for j,g in enumerate(groups):
            a,b=g['a'],g['b'];text=''.join(chars[a:b]);boxes=char_boxes[a:b];gb=[min(v[0] for box in boxes for v in box),min(v[1] for box in boxes for v in box),max(v[0] for box in boxes for v in box),max(v[1] for box in boxes for v in box)];body=re.sub(r'^[1-9]\d?[.、．]','',normalize(text),count=1).strip();strong=status=='PIXEL_GROUPS_OBSERVED' and ordered and within and bool(body) and min(scores[a:b])>=.85 and not re.search(r'\d+\.\d+',body) and not re.search(r'[A-G][1-9]\d?[.、]',body)
            proof={'original_char_span':[a,b],'left_gap':next((gap for gap in gaps if gap['before_character']==a),None),'right_gap':next((gap for gap in gaps if gap['before_character']==b),None),'at_row_start':a==0,'at_row_end':b==len(chars),'group_numbers_observed':numbers,'within_answer_window':within,'minimum_confidence':min(scores[a:b]),'font_height':statistics.median(max(v[1] for v in box)-min(v[1] for v in box) for box in boxes)}
            database.execute('INSERT INTO answer_geometry_groups VALUES(?,?,?,?,?,?,?,?)',(f'{oid}/group/{j+1}',oid,g['number'],text,json.dumps(gb),json.dumps([a,b]),'VERIFIED_PIXEL_GAP' if strong else 'GEOMETRY_REVIEW',json.dumps(proof)))
        database.commit();count+=1;print(f'GEOMETRY page={n} row={row} groups={len(groups)} status={status}',flush=True)
    return count

def merge_answer_geometry(database):
    import json,re,unicodedata
    if not database.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='answer_geometry_groups'").fetchone():return
    database.executescript('CREATE TABLE IF NOT EXISTS answer_geometry_links(answer_item_id TEXT PRIMARY KEY,group_id TEXT,observation_id TEXT);CREATE TABLE IF NOT EXISTS answer_geometry_merge_decisions(group_id TEXT PRIMARY KEY,scope_id TEXT,printed_number TEXT,status TEXT,existing_answer_id TEXT);DELETE FROM answer_geometry_links;DELETE FROM answer_geometry_merge_decisions;')
    candidates=database.execute("SELECT g.group_id,g.observation_id,g.printed_number,g.text,g.bbox_json,g.char_span_json,g.proof_json,o.scope_id,o.page,o.row_index,o.original_text FROM answer_geometry_groups g JOIN answer_geometry_observations o ON o.observation_id=g.observation_id WHERE g.status='VERIFIED_PIXEL_GAP' AND o.rowid=(SELECT max(newer.rowid) FROM answer_geometry_observations newer WHERE newer.scope_id=o.scope_id AND newer.page=o.page AND newer.row_index=o.row_index)").fetchall()
    counts={}
    for candidate in candidates:counts[(candidate[7],candidate[2])]=counts.get((candidate[7],candidate[2]),0)+1
    for gid,oid,label,text,bbox,span,proof,sid,n,row,original in candidates:
        existing=database.execute("SELECT item_id FROM resolved_answer_items WHERE scope_id=? AND kind='QUESTION' AND label=?",(sid,label)).fetchall()
        if len(existing)>1:continue
        chars,gaps=database.execute('SELECT char_texts_json,gaps_json FROM answer_geometry_observations WHERE observation_id=?',(oid,)).fetchone();chars=json.loads(chars);a,b=json.loads(span);cuts=[g['before_character'] for g in json.loads(gaps) if g['passed'] and a<g['before_character']<b]
        unlabeled=any(not re.match(r'^\([1-9]\d?\)',unicodedata.normalize('NFKC',''.join(chars[cut:b]))) for cut in cuts)
        if unlabeled:
            database.execute('INSERT INTO answer_geometry_merge_decisions VALUES(?,?,?,?,?)',(gid,sid,label,'UNLABELED_PHYSICAL_CONTINUATION',existing[0][0] if existing else None));continue
        baseline=database.execute('SELECT a.item_id,a.start_page,a.start_row,q.strength FROM resolved_answer_items a JOIN answer_marker_quality q ON q.item_id=a.item_id WHERE a.scope_id=? AND a.kind=\'QUESTION\' AND a.label=?',(sid,label)).fetchall()
        conflict=bool(baseline and baseline[0][3]=='STRONG' and baseline[0][1:3]!=(n,row))
        multi=counts[(sid,label)]>1 and not (baseline and baseline[0][3]=='STRONG' and baseline[0][1:3]==(n,row))
        if conflict or multi:
            database.execute('INSERT INTO answer_geometry_merge_decisions VALUES(?,?,?,?,?)',(gid,sid,label,'CONFLICTING_STRONG_SOURCE' if conflict else 'MULTIPLE_SOURCE_GROUPS',baseline[0][0] if baseline else None));continue
        if existing:
            iid=existing[0][0];database.execute('DELETE FROM resolved_answer_items WHERE item_id=?',(iid,));database.execute('DELETE FROM answer_marker_quality WHERE item_id=?',(iid,))
        iid=f'{sid}/geometry-answer/{gid}';a,b=json.loads(span);geometry_proof=json.loads(proof);fragment={'page':n,'column':next((c for c,x0,x1 in database.execute('SELECT column,x0,x1 FROM resolved_answer_windows WHERE scope_id=? AND page=?',(sid,n)) if x0<=(json.loads(bbox)[0]+json.loads(bbox)[2])/2<x1),0),'row_indices':[row],'text_spans':[{'row_index':row,'start':a,'end':b}],'bbox':json.loads(bbox),'geometry_observation_id':oid,'geometry_group_id':gid,'observation_text':text,'original_row_text':original,'geometry_proof':geometry_proof}
        database.execute('INSERT INTO resolved_answer_items VALUES(?,?,?,?,?,?,?)',(sid,iid,'QUESTION',label,n,row,json.dumps([fragment],ensure_ascii=False)))
        normalized=unicodedata.normalize('NFKC',text);m=re.match(r'([1-9]\d?)[.、]',normalized)
        database.execute('INSERT INTO answer_marker_quality VALUES(?,?,?,?,?,?,?,?,?)',(iid,'STRONG','GEOMETRY_WHITE_GAP',m.group(),0,m.end(),text,n,row));database.execute('INSERT INTO answer_geometry_links VALUES(?,?,?)',(iid,gid,oid))
        database.execute('INSERT INTO answer_geometry_merge_decisions VALUES(?,?,?,?,?)',(gid,sid,label,'MERGED',iid))

if args.recoveries:
    apply_reviewed_regions(db,args.recoveries.expanduser().resolve(strict=True))
if args.training2:
    apply_source_region_updates(db,args.training2.expanduser().resolve(strict=True),args.boundaries7.expanduser().resolve(strict=True))
if args.figures:
    apply_question_figure_bindings(db,args.figures.expanduser().resolve(strict=True))
reconcile_sources(db, output, args.geometry_deps.expanduser().resolve(strict=True) if args.geometry_deps else None)
