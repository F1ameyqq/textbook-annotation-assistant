"""Offline allowlist extraction only. Never copy TLS session text into delivery."""
import base64
import hashlib
import json
from pathlib import Path
import re
import ssl
from datetime import datetime, timezone

OUT = Path('D:/1800-worktrees/a14-tls-diagnostic/execution-output')
PRIVATE = Path('D:/1800/.local/stages/a14-tls-diagnostic')

def save(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')

def main():
    process = json.loads((OUT / 'process-result.json').read_text(encoding='utf-8'))
    streams = {n: (PRIVATE / ('s_client.' + n + '.bin')).read_bytes() for n in ('stdout', 'stderr')}
    for n, raw in streams.items():
        assert len(raw) == process['streams'][n]['bytes']
        assert hashlib.sha256(raw).hexdigest() == process['streams'][n]['sha256']
    combined = streams['stdout'] + b'\n' + streams['stderr']
    pem_blocks = re.findall(rb'-----BEGIN CERTIFICATE-----\r?\n([A-Za-z0-9+/=\r\n]+)-----END CERTIFICATE-----', combined)
    certs, hashes, order = [], {}, []
    for block in pem_blocks:
        der = base64.b64decode(re.sub(rb'\s', b'', block), validate=True)
        fingerprint = hashlib.sha256(der).hexdigest()
        if fingerprint in hashes:
            order.append(hashes[fingerprint])
            continue
        index = len(certs) + 1
        name = 'certificate-%02d.pem' % index
        b64 = base64.b64encode(der).decode('ascii')
        pem = '-----BEGIN CERTIFICATE-----\n' + '\n'.join(b64[i:i+64] for i in range(0, len(b64), 64)) + '\n-----END CERTIFICATE-----\n'
        (OUT / name).write_bytes(pem.encode('ascii'))
        decoded = ssl._ssl._test_decode_cert(str(OUT / name))
        dns = [v for k, v in decoded.get('subjectAltName', []) if k == 'DNS']
        try:
            ssl.match_hostname({'subjectAltName': tuple(('DNS', d) for d in dns)}, 'www.usense.com')
            covered = True
        except ssl.CertificateError:
            covered = False
        observed = datetime.fromisoformat(process['launch_utc']).timestamp()
        before, after = ssl.cert_time_to_seconds(decoded['notBefore']), ssl.cert_time_to_seconds(decoded['notAfter'])
        certs.append({'index': index, 'path': name, 'der_sha256': fingerprint,
                      'pem_sha256': hashlib.sha256(pem.encode('ascii')).hexdigest(),
                      'subject': decoded['subject'], 'issuer': decoded['issuer'],
                      'dns_subject_alt_names': dns, 'san_covers_www_usense_com': covered,
                      'not_before_utc': datetime.fromtimestamp(before, timezone.utc).isoformat(),
                      'not_after_utc': datetime.fromtimestamp(after, timezone.utc).isoformat(),
                      'within_validity_at_observation': before <= observed <= after,
                      'note': 'Server-sent public certificate; showcerts does not establish a validated chain.'})
        hashes[fingerprint] = index
        order.append(index)
    errors = sorted({int(m) for m in re.findall(rb'verify error:num=(\d+)', combined)})
    returns = sorted({int(m) for m in re.findall(rb'Verify return code:\s*(\d+)', combined)})
    codes = set(errors + returns)
    if not certs:
        category = 'NO_CERTIFICATE_EVIDENCE'
    elif 62 in codes:
        category = 'HOSTNAME_MISMATCH'
    elif codes - {0}:
        category = 'CHAIN/TRUST_ERROR' if codes.intersection({2, 3, 7, 9, 10, 18, 19, 20, 21, 24, 27, 28}) else 'UNKNOWN'
    elif codes == {0} and process.get('exit_code') == 0:
        category = 'STRICT_TLS_VERIFIED_THIS_PATH_ONLY'
    elif process.get('timeout') or process.get('exit_code') != 0:
        category = 'TRANSPORT_ERROR'
    else:
        category = 'UNKNOWN'
    result = {'extraction_mode': 'OFFLINE_ALLOWLIST_NO_NETWORK', 'category': category,
              'observed_verify_error_codes': errors, 'observed_verify_return_codes': returns,
              'raw_pem_occurrences': len(pem_blocks), 'unique_public_certificates': len(certs),
              'certificate_occurrence_order': order, 'certificates': certs,
              'server_sent_certificates_only': True, 'validated_chain_not_inferred_from_showcerts': True,
              'session_values_exported': False, 'raw_text_exported': False,
              'stream_hashes': {n: {'size': len(b), 'sha256': hashlib.sha256(b).hexdigest()} for n, b in streams.items()},
              'leaf_san_covers_www_usense_com': certs[0]['san_covers_www_usense_com'] if certs else None,
              'root_cause': 'UNKNOWN; no attribution to website, proxy interception, Windows/Edge trust, authentication or book access'}
    save(OUT / 'public-certificate-results.json', result)
    print(json.dumps({'category': category, 'verify_error_codes': errors, 'verify_return_codes': returns,
                      'unique_public_certificates': len(certs),
                      'leaf_san_covers_target': result['leaf_san_covers_www_usense_com'],
                      'leaf_dns_SAN': certs[0]['dns_subject_alt_names'] if certs else []}, ensure_ascii=False))

if __name__ == '__main__':
    main()
