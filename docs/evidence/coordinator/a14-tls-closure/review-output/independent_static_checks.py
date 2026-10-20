"""A14 fixed-file review only. Never import author code or open a connection."""
import ast
import base64
import hashlib
import json
from pathlib import Path
import re
import ssl
from datetime import datetime, timezone, timedelta
from decimal import Decimal

ROOT = Path('D:/1800-worktrees/a14-tls-review')
OUT = ROOT / 'review-output'
EX = ROOT / 'execution-output'

def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def digest(path):
    raw = path.read_bytes()
    return {'size': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

def save(name, obj):
    with (OUT / name).open('x', encoding='utf-8', newline='\n') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write('\n')

def require(condition, name):
    if not condition:
        raise AssertionError(name)

baseline = load(OUT / 'input-precheck.json')
require(len(baseline['inputs']) == 23, 'fixed 23 inputs')
for item in baseline['inputs']:
    require(digest(ROOT / item['path']) == {k: item[k] for k in ('size', 'sha256')}, item['path'])
expected_set = {x['path'] for x in baseline['inputs']}
actual_set = {p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*')
              if p.is_file() and OUT not in p.parents}
require(actual_set == expected_set, 'no missing or extra fixed input files')
require(not any(p.is_symlink() or (p.stat().st_file_attributes & 1024)
                for p in ROOT.rglob('*') if OUT not in p.parents), 'no input reparse/symlink')

manifest = load(EX / 'raw-output-manifest.json')
require(len(manifest['members']) == 18, '18 nonself author manifest members')
require({x['path'] for x in manifest['members']} ==
        {Path(x).name for x in expected_set if x.startswith('execution-output/') and
         x != 'execution-output/raw-output-manifest.json'}, 'complete author member set')
for item in manifest['members']:
    require(digest(EX / item['path']) == {k: item[k] for k in ('size', 'sha256')}, item['path'])

intent = load(EX / 'launch-intent.json')
preflight = load(EX / 'preflight.json')
audit = load(EX / 'archive-audit.json')
proc = load(EX / 'process-result.json')
outer = load(EX / 'wrapper-os-release.json')
public = load(EX / 'public-certificate-results.json')
author = load(EX / 'report.json')
private_hashes = load(EX / 'private-raw-hash-manifest.json')
prior = load(ROOT / 'prior-A13-review/report.json')

expected_argv = [intent['openssl_path'], 's_client', '-connect', 'www.usense.com:443',
                 '-servername', 'www.usense.com', '-verify_hostname', 'www.usense.com',
                 '-verify_return_error', '-showcerts', '-prexit', '-CAfile', intent['ca_path'],
                 '-proxy', '127.0.0.1:7897', '-no_ign_eof']
require(intent['tls_argv'] == expected_argv, 'strict exact argv')
require(intent['target'] == 'www.usense.com:443' and intent['sni'] ==
        intent['verify_hostname'] == 'www.usense.com', 'fixed target binding')
require(intent['strict_verify'] is True, 'strict verification flag')
require(intent['proxy'] == preflight['proxy'], 'proxy metadata binding')
require(intent['bindings'] == preflight['bindings'], 'all preflight bindings')
proxy = intent['proxy']
require(proxy['enabled'] and not proxy['pac_present'] and not proxy['authentication_syntax_present']
        and proxy['host'] == '127.0.0.1' and proxy['port'] == 7897, 'fixed proxy boundary')
for row in audit['frozen_bindings']:
    require(row['expected'] == row['observed'] == intent['bindings'][row['path']] and
            row['matches'], 'audit binding consistency')
for name in ('tls_wrapper.py', 'launch_once.py'):
    require(digest(EX / name) == intent['bindings'][
        'D:/1800-worktrees/a14-tls-diagnostic/execution-output/' + name], 'frozen code binding')
for key, path in [('preflight.json_raw', EX / 'preflight.json'),
                  ('static-review.json_raw', EX / 'static-review.json'),
                  ('task_raw', ROOT / 'standards/A14-single-tls-certificate-diagnostic.md')]:
    require(digest(path) == intent[key], 'intent content binding: ' + key)
require(digest(EX / 'launch-intent.json') == author['freeze']['launch_intent'], 'report intent binding')

sources = {}
ast_results = {}
for name in ('tls_wrapper.py', 'launch_once.py', 'extract_public_evidence.py', 'seal_delivery.py'):
    src = (EX / name).read_text(encoding='utf-8')
    sources[name] = src
    tree = ast.parse(src, filename=name)
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
    popens = [n for n in calls if isinstance(n.func, ast.Attribute) and n.func.attr == 'Popen']
    ast_results[name] = {
        'ast_valid': True,
        'Popen_lines': [n.lineno for n in popens],
        'Popen_literal_shell_false': all(any(k.arg == 'shell' and isinstance(k.value, ast.Constant)
            and k.value.value is False for k in n.keywords) for n in popens),
        'functions': {n.name: n.lineno for n in tree.body if isinstance(n, ast.FunctionDef)},
        'lines_of_interest': [{'line': i, 'text': line.strip()} for i, line in enumerate(src.splitlines(), 1)
            if any(s in line for s in ('start = float', 'deadline = start', 'time.perf_counter() >= wait_cutoff',
                'p.wait(timeout=', 'except subprocess.TimeoutExpired', 'UNKNOWN_AT_22',
                'time.perf_counter() < deadline', 'p.kill()', 'p._handle.Close()',
                'launch-claim.json', 'wrapper-claim.json', "Path(path).open('x'", 'time.perf_counter() - start'))]
    }
    require(ast_results[name]['Popen_literal_shell_false'], name + ' shell=False')
require(len(ast_results['tls_wrapper.py']['Popen_lines']) == 1 and
        len(ast_results['launch_once.py']['Popen_lines']) == 1 and
        not ast_results['extract_public_evidence.py']['Popen_lines'] and
        not ast_results['seal_delivery.py']['Popen_lines'], 'one declared launch per layer, no extraction launches')
require(not re.search(r'\b(?:p|proc|process)\.stdin\.write\s*\(', sources['tls_wrapper.py']), 'no application stdin write')
require("Path(path).open('x'" in sources['tls_wrapper.py'] and
        "w.save(w.PRIVATE / 'launch-claim.json'" in sources['launch_once.py'] and
        "save(PRIVATE / 'wrapper-claim.json'" in sources['tls_wrapper.py'], 'exclusive claims in fixed code')

observed = datetime.fromisoformat(proc['launch_utc'])
certs = []
for idx, supplied in enumerate(public['certificates'], 1):
    path = EX / ('certificate-%02d.pem' % idx)
    raw = path.read_bytes()
    match = re.fullmatch(rb'-----BEGIN CERTIFICATE-----\n([A-Za-z0-9+/=\n]+)-----END CERTIFICATE-----\n', raw)
    require(bool(match), 'only canonical public certificate PEM')
    der = base64.b64decode(re.sub(rb'\s', b'', match.group(1)), validate=True)
    decoded = ssl._ssl._test_decode_cert(str(path))
    dns = [value for kind, value in decoded.get('subjectAltName', ()) if kind == 'DNS']
    before = datetime.fromtimestamp(ssl.cert_time_to_seconds(decoded['notBefore']), timezone.utc)
    after = datetime.fromtimestamp(ssl.cert_time_to_seconds(decoded['notAfter']), timezone.utc)
    row = {'index': idx, 'path': path.name, 'der_sha256': hashlib.sha256(der).hexdigest(),
           'pem_sha256': hashlib.sha256(raw).hexdigest(), 'subject': decoded['subject'],
           'issuer': decoded['issuer'], 'dns_subject_alt_names': dns,
           'not_before_utc': before.isoformat(), 'not_after_utc': after.isoformat(),
           'within_validity_at_observation': before <= observed <= after}
    # JSON canonicalization only converts tuples to lists; raw inputs stay untouched.
    row = json.loads(json.dumps(row))
    for key in row:
        require(row[key] == supplied[key], 'independent PEM field: %d/%s' % (idx, key))
    row['matches_author_public_fields'] = True
    certs.append(row)
require(len(certs) == 4 and len({r['der_sha256'] for r in certs}) == 4, 'four distinct certificates')
require(certs[0]['dns_subject_alt_names'] == ['qt.lingshubao.cn'], 'leaf exact sole DNS SAN')
require('www.usense.com' not in certs[0]['dns_subject_alt_names'], 'target absent from leaf SAN')
require(observed > datetime.fromisoformat(certs[0]['not_after_utc']), 'leaf validity ended before observation')
issuer_links = [{'from': i+1, 'to': i+2, 'issuer_equals_next_subject': certs[i]['issuer'] == certs[i+1]['subject']}
                for i in range(3)]
require(all(r['issuer_equals_next_subject'] for r in issuer_links), 'public issuer/subject naming sequence')
require(public['observed_verify_error_codes'] == [62] and public['observed_verify_return_codes'] == [62]
        and public['category'] == 'HOSTNAME_MISMATCH' and proc['exit_code'] == 1, 'published strict failure consistency')

secret_patterns = [rb'-----BEGIN (?:RSA |EC |ENCRYPTED )?PRIVATE KEY-----',
                   rb'Session-ID\s*:\s*[0-9a-fA-F]{8,}', rb'Master-Key\s*:\s*[0-9a-fA-F]{8,}',
                   rb'(?mi)^\s*(?:CLIENT_RANDOM|CLIENT_HANDSHAKE_TRAFFIC_SECRET|SERVER_HANDSHAKE_TRAFFIC_SECRET|CLIENT_TRAFFIC_SECRET_0|SERVER_TRAFFIC_SECRET_0)\s+[0-9a-f]+\s+[0-9a-f]+',
                   rb'(?mi)^\s*TLS session ticket:\s*\n\s*0000\s*-']
secret_scan = []
for rel in sorted(expected_set):
    raw = (ROOT / rel).read_bytes()
    hits = [i for i, pat in enumerate(secret_patterns) if re.search(pat, raw)]
    require(not hits, 'unexpected secret value pattern in public fixed input: ' + rel)
    secret_scan.append({'path': rel, 'secret_value_pattern_matches': 0})
require(not set(intent['tls_argv']).intersection({'-keylogfile', '-sess_out', '-trace', '-msg', '-reconnect',
        '-proxy_user', '-proxy_pass'}), 'no secret-export/reconnect/proxy credential options')

hash_by_name = {x['private_basename']: {k: x[k] for k in ('size', 'sha256')} for x in private_hashes['members']}
for name in ('stdout', 'stderr'):
    expected = {'size': proc['streams'][name]['bytes'], 'sha256': proc['streams'][name]['sha256']}
    require(expected == public['stream_hashes'][name] == hash_by_name['s_client.'+name+'.bin'], 'stream hash consistency')
    require(outer['wrapper_'+name] == hash_by_name['wrapper.'+name+'.bin'], 'wrapper stream hash consistency')

require(proc['tls_process_launches'] == proc['tls_handshake_intents'] == outer['wrapper_launches'] == 1, 'declared single launches')
require(proc['target_http_requests'] == proc['stdin_bytes_written'] == proc['browser_profile_login_business_actions'] == 0, 'declared zero business/HTTP')
require(not proc['timeout'] and not outer['timeout'] and proc['first_failure'] is None, 'finite transport supervisor no timeout')
require(proc['process_creation']['creation_filetime'] == proc['process_exit']['creation_filetime'] and
        proc['process_exit']['exit_filetime'] > proc['process_creation']['creation_filetime'] and
        proc['process_creation']['exit_filetime'] == 0, 'TLS exact retained-handle identity')
require(outer['creation']['creation_filetime'] == outer['exit']['creation_filetime'] and
        outer['exit']['exit_filetime'] > outer['creation']['creation_filetime'] and
        outer['creation']['exit_filetime'] == 0, 'wrapper exact retained-handle identity')
require(proc['wait_signaled'] and outer['wait_signaled'] and proc['readers_joined'], 'wait and joined readers')
require(all(x['closed'] and x['post_close']['invalid_handle_confirmed'] and x['post_close']['winerror'] == 6
            for k,x in proc['release'].items() if k != 'process_handle'), 'pipe release evidence')
require(proc['release']['process_handle']['close_called'] and
        proc['release']['process_handle']['handle'] == proc['process_handle'] and
        proc['release']['process_handle']['post_close']['invalid_handle_confirmed'], 'TLS handle closed')
require(outer['handle_close_called'] and outer['handle_post_close']['invalid_handle_confirmed'] and
        outer['redirect_files_closed'], 'wrapper handle/file release')
require(all(x['eof_observed'] and x['file_closed'] and x['reader_error_type'] is None
            for x in proc['streams'].values()), 'private drain EOF/file close metadata')
require(outer['creation']['creation_filetime'] < proc['process_creation']['creation_filetime'] <
        proc['process_exit']['exit_filetime'] < outer['exit']['exit_filetime'], 'OS lifetime nesting')
timing = {
    'wrapper_os_lifetime_ms': str(Decimal(outer['exit']['exit_filetime'] - outer['creation']['creation_filetime']) / Decimal(10000)),
    'tls_os_lifetime_ms': str(Decimal(proc['process_exit']['exit_filetime'] - proc['process_creation']['creation_filetime']) / Decimal(10000)),
    'parent_same_process_elapsed_ms': outer['elapsed_ms_to_wrapper_observed_exit'],
    'child_relative_launch_ms': proc['launch_elapsed_ms'],
    'child_relative_release_ms': proc['elapsed_ms_at_release'],
    'finite_exit_below_22s': outer['elapsed_ms_to_wrapper_observed_exit'] < 22000,
    'general_shared_deadline_accepted': False,
    'outer_timeout_path': 'records UNKNOWN and closes its wrapper handle; no timeout termination of wrapper/descendants',
    'child_finally_path': 'exact-child kill is conditional on local perf_counter being before inherited deadline',
    'unexecuted_branches': 'No timeout/late-cleanup negative control run; no new execution authorized'
}
require(proc['launch_elapsed_ms'] == -4.862 and author['timing']['general_22_second_guard_accepted'] is False, 'timing finding retained')
require(outer['exit_code'] == 0 and timing['finite_exit_below_22s'], 'finite wrapper exit only')
require(datetime.fromisoformat(intent['frozen_utc']) < datetime.fromisoformat(outer['started_utc']) < observed,
        'intent precedes finite execution')
require(prior['release_evidence']['wrapper_self']['os_exit_identity_status'] == 'UNKNOWN', 'prior A13 UNKNOWN preserved')

result = {'status': 'PASS_FIXED_PUBLIC_FACTS_AND_FINITE_RELEASE_WITH_DEADLINE_LIMITATION',
          'input_count': 23, 'input_bytes': baseline['total_bytes'], 'author_manifest_nonself': 18,
          'extra_or_missing_inputs': [], 'input_reparse_or_symlinks': False,
          'author_wrapper_imports_or_executions': 0, 'network_connections': 0, 'private_raw_reads': 0,
          'local_PEM_parse_mode': 'stdlib ssl local decode plus independent base64/DER SHA256; no external parser process',
          'local_PEM_parses': 4, 'ast_results': ast_results,
          'exact_tls_argv': expected_argv, 'proxy': proxy,
          'binary_CA_limit': 'Fixed recorded hashes checked across intent/preflight/archive-audit and guard source; installed executable/CA bytes not in 23-input package and not reread.',
          'certificates': certs, 'public_issuer_name_links': issuer_links,
          'chain_signatures_or_trust_not_verified': True,
          'private_stream_hash_consistency': True, 'private_claim_contents_not_read': True,
          'published_error_code': 62, 'error_code_origin': 'fixed sanitized extraction; underlying private stdout/stderr not independently reopened',
          'secret_value_scan': secret_scan, 'tls_release_metadata_accepted': True,
          'wrapper_release_metadata_accepted': True, 'timing': timing,
          'A13_wrapper_OS_exit_identity': 'UNKNOWN',
          'count_proof_boundary': 'One declared frozen launch path and one exact TLS/wrapper lifetime; no independent OS/network census or private-claim content audit.'}
save('independent-checks.json', result)
print(json.dumps({'status': result['status'], 'inputs': 23, 'bytes': baseline['total_bytes'],
                  'certificates': len(certs), 'leaf_SAN': certs[0]['dns_subject_alt_names'],
                  'leaf_not_after': certs[0]['not_after_utc'], 'timing': timing}, ensure_ascii=False, indent=2))
