"""Read-only R12-R1 delivery audit. No product import, SQL, or functional run."""
import hashlib
import io
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path('D:/1800')
WORK = Path('C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800')
BASE = '394fe51f5ed14c5ed312073a20faac0f5cbb9990'
CODE = '7694490ef25539d131b863bdcb2b21531c69dfae'
TARGET = '6affc61d2ab0b1f0d96bb2497c5ae969ebaf1df2'
E = 'docs/evidence/A03/execution/P2-R12-R1-unknown-projection/'
EX = 'examples/a03/P2-R12-R1-unknown-projection/'
REPORT = 'docs/tasks/A03-P2-R12-R1-unknown-projection-report.md'
MANIFEST = E + 'manifest.json'
RELEASE = E + 'sealing/process-release-proof.json'
PROFILE = 'src/annotation/contracts/a03_native/data/profile.json'
ADOPTION = 'src/annotation/contracts/a03_native/data/adoption.json'
PRODUCT = ['src/annotation/runtime/storage/__init__.py',
           'src/annotation/runtime/storage/native.py']
ALLOWED = set(PRODUCT + [PROFILE, ADOPTION])


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(*args, cwd=ROOT, data=None):
    return subprocess.run(['git', '-c', 'core.longpaths=true', *args], cwd=cwd,
                          input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          check=True, timeout=60).stdout


def blobs(ref, paths):
    paths = sorted(paths)
    data = ''.join(ref + ':' + p + '\n' for p in paths).encode('utf-8')
    stream = io.BytesIO(git('cat-file', '--batch', data=data))
    result = {}
    for path in paths:
        header = stream.readline().split()
        assert len(header) == 3 and header[1] == b'blob', (path, header)
        result[path] = stream.read(int(header[2]))
        assert stream.read(1) == b'\n'
    assert stream.read() == b''
    return result


def tree(ref):
    return {p.decode('utf-8'): meta.decode('ascii') for row in
            git('ls-tree', '-r', '-z', ref).split(b'\0') if row
            for meta, p in [row.split(b'\t', 1)]}


def main():
    root_head = git('rev-parse', 'HEAD').decode().strip()
    assert git('rev-parse', 'HEAD', cwd=WORK).decode().strip() == TARGET
    assert not git('status', '--porcelain=v1', cwd=WORK).strip()
    git('merge-base', '--is-ancestor', BASE, CODE)
    git('merge-base', '--is-ancestor', CODE, TARGET)
    bt, ct, tt = tree(BASE), tree(CODE), tree(TARGET)
    modified = {p for p in bt if tt.get(p) != bt[p]}
    added = set(tt) - set(bt)
    assert modified == ALLOWED, sorted(modified)
    assert all(tt.get(p) == value for p, value in ct.items())
    assert all(p.startswith((E, EX)) or p in
               {REPORT, 'tests/test_a03_p2_r12_r1_unknown_projection.py'} for p in added)
    assert all(p.startswith(E) or p == REPORT for p in set(tt) - set(ct))
    raw = blobs(TARGET, {MANIFEST})
    manifest = json.loads(raw[MANIFEST])
    assert manifest['base'] == BASE and manifest['candidate_code_commit'] == CODE
    assert set(manifest['excluded']) == {MANIFEST}
    assert set(manifest['files']) | {MANIFEST} == modified | added
    raw.update(blobs(TARGET, manifest['files']))
    for p, digest in manifest['files'].items():
        assert sha(raw[p]) == digest, ('manifest', p)
    for p, data in raw.items():
        assert (WORK / p).read_bytes() == data, ('worktree', p)
    expected = {
        REPORT: '457d0f85e491ae9cefa757475918c6766cd527179b99aa3b07de06611db5e133',
        MANIFEST: 'b280ef782ee85f2c7f92485debc316a6bfae0902b078894e555df59afe904867',
        RELEASE: '6dd2da06a5212db39eaac95437dea5f44bc1e07072bbcb8a2ddc22f6cf1eced4',
    }
    for p, digest in expected.items():
        assert sha(raw[p]) == digest, ('expected', p)

    base_raw = blobs(BASE, ALLOWED)
    before, after = json.loads(base_raw[PROFILE]), json.loads(raw[PROFILE])
    bp, ap = dict(before['implementation_pins']), dict(after['implementation_pins'])
    pin_keys = {'@annotation/' + p.split('src/annotation/', 1)[1] for p in PRODUCT}
    assert set(bp) == set(ap)
    assert {p for p in bp if bp[p] != ap[p]} == pin_keys
    for p in PRODUCT:
        key = '@annotation/' + p.split('src/annotation/', 1)[1]
        assert bp[key] == sha(base_raw[p]) and ap[key] == sha(raw[p])
    before['implementation_pins'] = after['implementation_pins']
    assert before == after
    ba, ta = json.loads(base_raw[ADOPTION]), json.loads(raw[ADOPTION])
    assert ba['profile_sha256'] == sha(base_raw[PROFILE])
    assert ta['profile_sha256'] == sha(raw[PROFILE])
    ba['profile_sha256'] = ta['profile_sha256']
    assert ba == ta

    inputs = json.loads(raw[EX + 'inputs.json'])
    source_raw = blobs(CODE, inputs['files'])
    source_checkout_eol_differences = []
    for p, digest in inputs['files'].items():
        checkout = (WORK / p).read_bytes()
        assert sha(checkout) == digest, ('execution source index', p)
        if sha(source_raw[p]) != digest:
            assert source_raw[p].replace(b'\r\n', b'\n') == checkout.replace(b'\r\n', b'\n'), ('non-EOL difference', p)
            source_checkout_eol_differences.append({'path': p, 'raw_git_sha256': sha(source_raw[p]),
                                                    'execution_checkout_sha256': digest,
                                                    'raw_size': len(source_raw[p]), 'checkout_size': len(checkout)})
        assert ct[p] == tt[p], ('source frozen', p)
    raw_exports = 0
    for p in raw:
        marker = '/raw-git/'
        if marker in p:
            ref, source_path = p.split(marker, 1)[1].split('/', 1)
            assert raw[p] == blobs(ref, {source_path})[source_path], ('raw export', p)
            raw_exports += 1

    captures = []
    for p in sorted(raw):
        if '/captures/' not in p or not p.endswith('/capture.json'):
            continue
        capture = json.loads(raw[p])
        assert capture['cross_database_atomic'] is False
        assert capture['SQL_reads_only_retained_immutable_copies'] is True
        assert len(capture['records']) == 2
        for record in capture['records']:
            binary = raw[record['retained']]
            assert len(binary) == record['size']
            assert sha(binary) == record['sha256'] == record['source_sha256_after_copy']
            assert binary.startswith(b'SQLite format 3\x00')
            assert record['sequential_non_atomic'] is True
            assert record['writer_in_business_call'] is False
        captures.append({'capture': p, 'sha256': sha(raw[p]), 'stage': capture['stage'],
                         'records': [{k: r[k] for k in ['retained', 'sha256', 'size',
                                                       'kind', 'keeper_alive']}
                                     for r in capture['records']]})
    assert len(captures) == 6
    release = json.loads(raw[RELEASE])
    assert release['count'] == len(release['processes']) == 23
    assert release['all_own_Popen_reaped'] is True
    processes = []
    for record in release['processes']:
        p = record['completion']
        completion, start = json.loads(raw[p]), json.loads(raw[record['start']])
        assert record['pid'] == completion['pid'] == start['pid']
        assert completion['alive'] is record['alive'] is False
        assert completion['timeout'] is record['timeout'] is False
        assert completion['exit_code'] == record['exit_code']
        directory = p.rsplit('/', 1)[0] + '/'
        streams = {}
        for kind in ['stdout', 'stderr']:
            candidates = [directory + kind + ext for ext in ['.txt', '.bin']
                          if directory + kind + ext in raw]
            assert len(candidates) == 1, (p, kind, candidates)
            streams[kind] = {'path': candidates[0], 'sha256': sha(raw[candidates[0]])}
            if kind + '_sha256' in completion:
                assert completion[kind + '_sha256'] == streams[kind]['sha256']
            if kind + '_sha256' in record:
                assert record[kind + '_sha256'] == streams[kind]['sha256']
        processes.append({'completion': p, 'pid': record['pid'],
                          'exit_code': record['exit_code'], 'streams': streams})
    nonzero = [p for p in processes if p['exit_code'] != 0]
    assert len(nonzero) == 2
    assert all(p['exit_code'] == 1 and
               ('/U1-execute/' in p['completion'] or '/watchdogs/U1/' in p['completion'])
               for p in nonzero)
    functional = [p for p in processes if '/validation/author-01/' in p['completion']]
    assert len(functional) == 5
    matrix = json.loads(raw[E + 'validation/author-01/matrix.json'])
    failure = json.loads(raw[E + 'failure-summary.json'])
    assert failure['functional_reruns'] == 0
    assert failure['same_round_product_or_driver_corrections'] == 0
    assert failure['U1_reconcile'] == 'NOT_RUN'
    assert failure['retained_SQLite_binary_count'] == 12
    assert b'MISSING_REFERENCE' in raw[E + 'validation/author-01/processes/U1-execute/stderr.txt']
    outcome = {
        'checked_at': datetime.now(timezone.utc).isoformat(), 'root_head_before': root_head,
        'base': BASE, 'candidate_code_commit': CODE, 'target': TARGET,
        'executor_worktree_clean': True, 'outcome': 'FROZEN_DELIVERY_VERIFIED_REVIEW_PENDING',
        'base_tree_entries': len(bt), 'protected_unchanged_entries': len(bt) - len(ALLOWED),
        'modified_existing': sorted(modified), 'added_files': len(added),
        'manifest_members': len(manifest['files']), 'manifest_self_excluded': True,
        'raw_git_and_worktree_bytes_match': True, 'candidate_source_frozen': True,
        'source_index_members': len(source_raw), 'raw_git_exports_verified': raw_exports,
        'source_index_byte_boundary': 'Execution checkout, with explicit raw Git comparisons below.',
        'source_checkout_eol_differences': source_checkout_eol_differences,
        'first_audit_error': 'delivery-preflight-first-error.json; corrected raw-Git-only assumption after checking prepare_static.py read_bytes provenance.',
        'only_two_implementation_pins_and_profile_digest_changed': True,
        'artifacts': expected, 'capture_audit': captures,
        'release_records': processes, 'functional_process_count': len(functional),
        'matrix_author_only': matrix, 'functional_reruns': 0,
        'archive_error_preserved_sha256': sha(raw[E + 'first-archive-error.txt']),
        'metadata_correction_sha256': sha(raw[E + 'metadata-correction.json']),
        'scope': 'Frozen raw bytes, trees, pins, inputs, captures and historical release records only.',
        'not_done': ['SQL inspection', 'product imports', 'functional replay', 'independent acceptance',
                     'integration', 'B confirmation', 'platform operation', 'push'],
        'limitations': ['Per-database sequential copies; no cross-database atomic snapshot.',
                       'Historical process completion records checked; no present PID scan.',
                       'Persisted effects and complete receipt/issue/report semantics require independent review.'],
    }
    path = Path(__file__).with_name('r12-r1-delivery-preflight.json')
    path.write_bytes((json.dumps(outcome, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    print(json.dumps({'audit': str(path), 'sha256': sha(path.read_bytes()),
                      'members': len(manifest['files']), 'captures': len(captures),
                      'release_records': len(processes), 'outcome': outcome['outcome']}))


if __name__ == '__main__':
    main()
