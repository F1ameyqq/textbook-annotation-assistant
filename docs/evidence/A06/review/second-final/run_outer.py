"""Wait for the once-only final delta driver and preserve process releases."""
import datetime
import json
import os
import sys
from review_tools import ROOT, dump, run

def main():
    logs = ROOT / 'outer'
    logs.mkdir(exist_ok=False)
    # Separate timeout for the outer record is managed by running each bounded child;
    # generator and the two consumer calls are sequential in the driver.
    rc, stdout, stderr, record = run('independent-driver', [sys.executable, '-B', ROOT / 'independent_run.py'], ROOT, logs)
    summary_path = ROOT / 'run-summary.json'
    summary = json.loads(summary_path.read_bytes()) if summary_path.exists() else {}
    records = summary.get('processes', []) + [record]
    dump(ROOT / 'release.json', dict(status='RELEASED' if all(r['process_reaped'] for r in records) else 'INCOMPLETE',
        outer_pid=os.getpid(), driver_pid=record['pid'], driver_exit_code=rc,
        all_recorded_children_reaped=all(r['process_reaped'] for r in records),
        synchronous_process_records=records, total_process_records=len(records), background_processes_started=0,
        platform_sessions_started=0, B_code_or_database_calls=0,
        finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    print(stdout.decode('utf-8'), end='')
    if stderr:
        print(stderr.decode('utf-8'), file=sys.stderr, end='')
    return rc

if __name__ == '__main__':
    raise SystemExit(main())
