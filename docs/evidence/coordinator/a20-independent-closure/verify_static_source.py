"""Read the one authorized captured Script; emit hashes and finite facts only."""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
SOURCE = Path('D:/1800/.local/stages/a17-excluded-static-live/static-assets/1-d0a5ebce18bc92d7643662ecec2d078bb295214111e7cb32688f0b88e05bed41.bin')
EXPECTED = 'd0a5ebce18bc92d7643662ecec2d078bb295214111e7cb32688f0b88e05bed41'
raw = SOURCE.read_bytes()
assert len(raw) == 3065996 and hashlib.sha256(raw).hexdigest() == EXPECTED
needles = {
    'same_origin_login_prefix': b'Ui="/qieti/api/user_login"',
    'JSON_client': b'gn=Bo.create({headers:{"Content-Type":"application/json"}})',
    'official_POST_two_keys': b'async function Pze(e,t){const n=await gn.post(`${Ui}/login`,{username:e,password:t});return Hn(n.data)}',
    'numeric_Hn_success_and_unwrapped_rule': b'function Hn(e,t={}){if(e&&typeof e.code=="number"){if(e.code!==0&&e.code!==200)throw new Error(e.message||"Error");const n=e.data;return t.wrapKey&&Array.isArray(n)?{[t.wrapKey]:n}:n}return e}',
    'UI_calls_official_login': b'const v=await Pze(t.value,a.value);localStorage.setItem',
    'UI_consumes_credential_then_SPA_push': b'access_token:v.access_token})),l.push("/")',
    'wrapper': b'class:"login-wrapper"',
    'form': b'yFe={class:"login-container"},bFe={class:"login-form glass-panel"}',
    'username': b'type:"text",id:"username"',
    'password': b'type:"password",id:"password"',
    'official_button_handler': b'C("button",{onClick:c[4]||(c[4]=d=>s()),class:"login-button"}',
    '401_only_once_branch': b'if(e.response&&e.response.status===401&&!t._retry){t._retry=!0;',
    'refresh_is_POST': b'await Bo.post(`${tee}${Ui}/refresh-token/`,{}',
    'resends_original': b't.headers.Authorization=`Bearer ${v.access_token}`,gn(t)',
    'login_route': b'path:"/login",name:"login"',
}
offsets = {}
for name, needle in needles.items():
    at = raw.find(needle)
    assert at >= 0, 'MISSING_STATIC_FACT_' + name
    offsets[name] = at
sessions = {}
for suffix in (b'/profile', b'/config/permissions', b'/config/teams'):
    needle = b'gn.get(`${Ui}' + suffix + b'`'
    at = raw.find(needle)
    assert at >= 0, 'MISSING_FIXED_SESSION_GET'
    sessions[suffix.decode()] = {'method': 'GET', 'offset': at}
redirects = [v.start() for v in re.finditer(re.escape(b'window.location.href="/qieti/login"'), raw)]
assert redirects == [1068547, 1069023]
actual_path = ROOT / 'docs/evidence/A19/navigation-evidence/live-delivery/raw/current-state.json'
actual_raw = actual_path.read_bytes()
actual = json.loads(actual_raw)
assets = actual['static_assets']
assert len(assets) == 1 and assets[0]['sha256'] == EXPECTED and assets[0]['size'] == len(raw)
result = {'task': 'A20', 'result': 'STATIC_ORIGINAL_SOURCE_VERIFIED',
    'source_path': str(SOURCE), 'source_sha256': EXPECTED, 'source_size': len(raw),
    'offset_basis': 'ZERO_BASED_UTF8_BYTES', 'facts': offsets, 'fixed_session_GETs': sessions,
    'login_redirect_offsets': redirects, 'matches_A19_captured_Script': True,
    'A19_report_sha256': hashlib.sha256(actual_raw).hexdigest(),
    'script_executed': False, 'Script_or_sidecar_copied': False, 'sidecar_read': False,
    'new_network_requests': 0, 'real_credentials_read': 0,
    'A19_actual_401_or_expiry_cause': 'UNKNOWN', 'current_platform_authentication': 'NOT_PROVEN'}
with (OUT / 'static-source-verification.json').open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps({'static_facts': len(offsets), 'fixed_session_GETs': len(sessions),
    'redirect_offsets': len(redirects), 'source_sha256': EXPECTED,
    'result': result['result']}))
