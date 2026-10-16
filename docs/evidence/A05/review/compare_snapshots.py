"""Independent A05 comparison; reads evidence only, writes review evidence only."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'AGENTS.md').is_file())
OUT = ROOT / 'docs/evidence/A05/review'
BASE = ROOT / 'docs/evidence/A05/baseline'

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def records(data):
    rows = data['data'] if isinstance(data, dict) else data
    return {r['rect_id']: {k:v for k,v in r.items() if k != 'user_id'} for r in rows}

def tree(data):
    return data['data']['directory_data']

def flatten(nodes, parent=None):
    rows = []
    for node in nodes:
        rows.append((node, parent))
        rows.extend(flatten(node.get('children', []), node['id']))
    return rows

def pruned(nodes, keep):
    result = []
    for node in nodes:
        if node['id'] not in keep:
            continue
        row = dict(node)
        if 'children' in row:
            row['children'] = pruned(row['children'], keep)
        result.append(row)
    return result

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--annotations')
    p.add_argument('--directory')
    p.add_argument('--label', default='baseline')
    args = p.parse_args()
    manifest = read(BASE / 'manifest.json')
    old = records(read(BASE / 'annotations.json'))
    old_tree = tree(read(BASE / 'directory.json'))
    old_nodes = flatten(old_tree)
    old_ids = {node['id'] for node, _ in old_nodes}
    result = {'label': args.label, 'baseline_file_hash_matches': {n:digest(BASE/n)==h for n,h in manifest['files_sha256'].items()},
        'baseline_rect_count':len(old), 'baseline_question_count':len({(r['directory_id'],r['order_in_level']) for r in old.values()}),
        'baseline_directory_node_count':len(old_nodes), 'baseline_question_node_count':sum(bool(r.get('isQuestion')) for r,_ in old_nodes)}
    if args.annotations:
        new = records(read(args.annotations))
        missing = sorted(old.keys()-new.keys())
        changed = {key:{field:{'before':old[key].get(field),'after':new[key].get(field)} for field in old[key].keys()|new[key].keys()
                        if old[key].get(field)!=new[key].get(field) or (field in old[key])!=(field in new[key])}
                   for key in old.keys() & new.keys() if old[key] != new[key]}
        added = [new[key] for key in sorted(new.keys()-old.keys())]
        result.update({'annotations_source':str(Path(args.annotations).relative_to(ROOT)).replace('\\','/'), 'annotations_sha256':digest(args.annotations),
            'rect_count':len(new),'missing_old_rect_ids':missing,'changed_old_rects':changed,'old_rects_exactly_unchanged':not missing and not changed,
            'added_rects':added,'added_rect_count':len(added),
            'question_count':len({(r['directory_id'],r['order_in_level']) for r in new.values()}),
            'added_question_keys':sorted({(r['directory_id'],r['order_in_level']) for r in added})})
    if args.directory:
        new_tree = tree(read(args.directory))
        new_nodes = flatten(new_tree)
        added_nodes = [{'node':node,'parent_id':parent} for node,parent in new_nodes if node['id'] not in old_ids]
        result.update({'directory_source':str(Path(args.directory).relative_to(ROOT)).replace('\\','/'), 'directory_sha256':digest(args.directory),
            'directory_old_tree_exactly_unchanged_after_pruning_additions':pruned(new_tree,old_ids)==old_tree,
            'added_directory_nodes':added_nodes,'added_directory_node_count':len(added_nodes),
            'missing_old_directory_ids':sorted(old_ids-{node['id'] for node,_ in new_nodes})})
    (OUT / ('comparison-' + args.label + '.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('added_rects','added_directory_nodes','baseline_file_hash_matches')},ensure_ascii=True))

if __name__ == '__main__':
    main()
