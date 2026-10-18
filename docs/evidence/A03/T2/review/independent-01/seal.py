"""Create-only export of necessary independent evidence; no business or SQL."""
import hashlib
import json
from pathlib import Path
import re
import shutil

H = Path(__file__).resolve().parent
R = H / 'c'
E = R / 'docs/evidence/A03/T2/execution'
I = E / 'validation/independent-01'
MAIN = Path('D:/1800')
OUT = MAIN / 'docs/evidence/A03/T2/review/independent-01'
REPORT = MAIN / 'docs/tasks/A03-T2-review-report.md'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load(path):
    return json.loads(path.read_bytes())

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write('\n')

def copy(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as stream:
        stream.write(source.read_bytes())
    assert sha(source) == sha(target)

def main():
    OUT.mkdir(parents=True, exist_ok=False)
    audit = load(H / 'audit.json')
    assert audit['status'] == 'FINITE_T2_ACCEPTED'
    for name in ('bootstrap.py', 'launch.py', 'audit.py', 'audit-r1.py', 'correct-audit.py', 'seal.py',
                 'validation-plan.json', 'static-review.md', 'materialization.json', 'audit.json',
                 'author-manifest-check.json', 'audit-first-failure.json', 'static-audit-correction.json'):
        copy(H / name, OUT / name)
    shutil.copytree(I, OUT / 'independent-run')
    shutil.copytree(E / 'launch/independent-01', OUT / 'driver-launch')
    shutil.copytree(E / 'import-processes', OUT / 'launch-imports')
    shutil.copytree(H / 'launches', OUT / 'outer-processes')
    externals = []
    for folder in sorted((H / 'static-processes').iterdir()):
        for file in sorted(folder.iterdir()):
            if file.name in ('preregistered.json', 'started.json', 'completed.json'):
                copy(file, OUT / 'static-processes' / folder.name / file.name)
            else:
                externals.append({'path': str(file), 'sha256': sha(file), 'bytes': file.stat().st_size,
                                  'reason': 'retain actual raw static Git streams in isolated directory; no duplicated historical package'})
    write(OUT / 'external-static-records.json', {'records': externals, 'raw_source_commit': audit['target']})
    folders = {p.parent for p in I.rglob('started.json')}
    folders |= {p.parent for p in (H / 'launches').rglob('started.json')}
    folders |= {p.parent for p in (H / 'static-processes').rglob('started.json')}
    folders.add(E / 'launch/independent-01')
    processes = []
    for folder in sorted(folders):
        start, end = load(folder / 'started.json'), load(folder / 'completed.json')
        assert start['pid'] == end['pid'] and not end.get('alive', False) and not end.get('timeout', False)
        processes.append({'folder': str(folder), 'started': start, 'completed': end})
    keeper = load(I / 'cases/H1/owner-release.json')
    assert all(not t['alive'] and t['error'] is None for t in keeper['keepers']['all_keeper_threads'])
    final = audit['independent']['stages'][-1]
    owner = final['owner']
    assert owner['owner'] is None and owner['pid'] is None and owner['lease'] == 0 and owner['phase'] == 'RELEASED'
    raw_final = []
    for kind, location in (('runtime', 'runtime/runtime.sqlite3'), ('target', 'target/target.sqlite3')):
        source = I / 'cases/H1' / location
        assert sha(source) == final['raw_databases'][kind]['sha256']
        sidecars = [str(source) + suffix for suffix in ('-journal', '-wal', '-shm') if Path(str(source) + suffix).exists()]
        assert not sidecars
        raw_final.append({'kind': kind, 'source': str(source), 'sha256': sha(source), 'sidecars': sidecars})
    write(OUT / 'final-release.json', {'all_registered_children_waited_and_reaped': True, 'registered_child_count': len(processes),
          'processes': processes, 'business_validation_chain_child_count': len(audit['independent_processes']),
          'business_validation_chain_all_exit0_no_timeout': True,
          'static_failures_preserved': [p for p in processes if p['completed']['exit_code'] != 0],
          'keeper_release': keeper, 'final_owner': owner, 'source_equals_after_report': raw_final,
          'SQL_reads_during_sealing': 0, 'machine_global_PID_scan': False, 'own_business_or_background_resources_remaining': False})
    broken = []
    for target in re.findall(r'\]\(([^)]+)\)', REPORT.read_text(encoding='utf-8')):
        if not (REPORT.parent / target).resolve().exists():
            broken.append(target)
    assert not broken, broken
    entries = []
    for file in sorted([p for p in OUT.rglob('*') if p.is_file()] + [REPORT]):
        entries.append({'path': file.relative_to(MAIN).as_posix(), 'bytes': file.stat().st_size, 'sha256': sha(file)})
    write(OUT / 'manifest.json', {'target': audit['target'], 'workflow': audit['workflow'],
          'conclusion': 'ACCEPTED_FIXED_C12_AND_H1_ONLY', 'product_baseline': '1330047dd29890dea0e433ff01b991f615bf78f4',
          'files': entries, 'excludes': ['docs/evidence/A03/T2/review/independent-01/manifest.json'],
          'external_static_records': 'external-static-records.json', 'A03_overall': 'REWORK', 'I01_released': False,
          'field_reset': 'NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION'})
    for item in entries:
        file = MAIN / item['path']
        assert file.stat().st_size == item['bytes'] and sha(file) == item['sha256']
    print(json.dumps({'conclusion': 'ACCEPTED_FIXED_C12_AND_H1_ONLY', 'files': len(entries),
          'report_sha256': sha(REPORT), 'manifest_sha256': sha(OUT / 'manifest.json'),
          'registered_children_completed': len(processes), 'preserved_static_failures': sum(p['completed']['exit_code'] != 0 for p in processes),
          'business_reruns': 0, 'broken_report_links': broken, 'output': str(OUT)}))

if __name__ == '__main__':
    main()
