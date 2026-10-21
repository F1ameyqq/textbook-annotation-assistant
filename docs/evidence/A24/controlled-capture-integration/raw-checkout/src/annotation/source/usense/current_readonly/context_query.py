"""Exact captured qze/Axios scalar query; account values are memory-only.

The JS preparation returns only an ephemeral relative URL, never the user/token.
Python validates the exact canonical bytes for native/context registration.
"""
from urllib.parse import parse_qsl, quote, urlsplit
from .gate import BOOK, TARGET, Stop

BOOK_PATH = '/qieti/api/claim_book/books'
BOOK_SLOT = 'A24_CURRENT_CONTEXT_R1_BOOK'
KEYS = ('page', 'pageSize', 'status_list', 'id', 'title', 'team_name', 'username', 'role', 'is_admin')
ADMIN_STATUS = '\u6807\u6ce8\u4e2d,\u8fd4\u4fee,\u5f85\u5ba1\u6838,\u590d\u5ba1,\u5f85\u4ea4\u4ed8,\u95ee\u9898\u4e66\u7c4d,\u65e0\u6cd5\u5165\u5e93,\u91cd\u590d'
OTHER_STATUS = '\u6807\u6ce8\u4e2d,\u8fd4\u4fee,\u5f85\u5ba1\u6838,\u590d\u5ba1'
JS_WHITESPACE = '\u0009\u000a\u000b\u000c\u000d\u0020\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff'
MAX_CONTEXT_UNITS = 512


def usable(value):
    if type(value) is not str or not value.strip(JS_WHITESPACE):
        return False
    try:
        units = len(value.encode('utf-16-le')) // 2
        value.encode('utf-8')
    except UnicodeError:
        return False
    return units <= MAX_CONTEXT_UNITS and not any(ord(c) < 32 or ord(c) == 127 for c in value)


def axios_encode(value):
    return quote(value, safe="-_.!~*'()", encoding='utf-8', errors='strict').replace(
        '%3A', ':').replace('%24', '$').replace('%2C', ',').replace('%20', '+')


def official_endpoint(username, role):
    if not usable(username) or not usable(role):
        raise Stop('BOOK_CONTEXT_UNSUPPORTED')
    status = ADMIN_STATUS if role.strip(JS_WHITESPACE) in ('admin', 'delivery_admin') else OTHER_STATUS
    values = ('1', '10', status, BOOK, '', '', username, role, 'true' if role == 'admin' else 'false')
    return BOOK_PATH + '?' + '&'.join(axios_encode(k) + '=' + axios_encode(v) for k, v in zip(KEYS, values))


def validate_endpoint(endpoint):
    """No caller error/value is interpolated into an exception or diagnostic."""
    try:
        if type(endpoint) is not str or len(endpoint) > 16384 or "'" in endpoint:
            raise ValueError
        parsed = urlsplit(endpoint)
        if (parsed.scheme or parsed.netloc or parsed.fragment or parsed.path != BOOK_PATH or
                '#' in endpoint or any(ord(c) < 32 or ord(c) == 127 for c in endpoint)):
            raise ValueError
        pairs = parse_qsl(parsed.query, keep_blank_values=True, strict_parsing=True,
            encoding='utf-8', errors='strict', max_num_fields=9)
        if tuple(k for k, _ in pairs) != KEYS:
            raise ValueError
        values = dict(pairs)
        if endpoint != official_endpoint(values['username'], values['role']):
            raise ValueError
    except (ValueError, UnicodeError, KeyError, TypeError, Stop):
        raise Stop('BOOK_CONTEXT_QUERY_REJECTED') from None
    return endpoint


# A shared lexical implementation keeps prep and send's derivation identical.
# No fetch/client wrapper/component method is called during preparation.
JS_BUILD = r"""
 const build = consume => {
  if(location.href!==TARGET)return {status:'ORIGINAL_PAGE_CHANGED'};
  let user;
  try{user=JSON.parse(localStorage.getItem('user')||'null');}
  catch(e){return {status:'CONTEXT_MALFORMED'};}
  if(!user||typeof user!=='object'||Array.isArray(user))return {status:'CONTEXT_UNAVAILABLE'};
  const username=user.username,role=user.role;
  const valid=v=>typeof v==='string'&&v.trim().length>0&&v.length<=512&&!/[\x00-\x1f\x7f]/.test(v);
  if(!valid(username)||!valid(role))return {status:'CONTEXT_UNSUPPORTED'};
  const status=['admin','delivery_admin'].includes(role.trim())?ADMIN_STATUS:OTHER_STATUS;
  const enc=v=>encodeURIComponent(v).replace(/%3A/g,':').replace(/%24/g,'$').replace(/%2C/g,',').replace(/%20/g,'+');
  try{
   const fields=[['page','1'],['pageSize','10'],['status_list',status],['id',BOOK],
    ['title',''],['team_name',''],['username',username],['role',role],['is_admin',role==='admin'?'true':'false']];
   const endpoint=BOOK_PATH+'?'+fields.map(([k,v])=>enc(k)+'='+enc(v)).join('&');
   if(new URL(endpoint,location.origin).href!==location.origin+endpoint)return {status:'CONTEXT_UNSUPPORTED'};
   return consume?consume(endpoint,user):{status:'PREPARED',endpoint};
  }catch(e){return {status:'CONTEXT_UNSUPPORTED'};}
 };
"""


def _constants():
    import json
    return '\n'.join(' const ' + name + '=' + json.dumps(value) + ';' for name, value in (
        ('TARGET', TARGET), ('BOOK', BOOK), ('BOOK_PATH', BOOK_PATH),
        ('ADMIN_STATUS', ADMIN_STATUS), ('OTHER_STATUS', OTHER_STATUS)))


PREPARE_JS = '() => {' + _constants() + JS_BUILD + '\n return build();\n}'
SEND_JS = 'async expected => {' + _constants() + JS_BUILD + r"""
 const output=build(async(endpoint,user)=>{
  if(endpoint!==expected)return {context_status:'CONTEXT_CHANGED'};
  if(typeof user.access_token!=='string'||!user.access_token)return {context_status:'SESSION_TOKEN_UNAVAILABLE'};
  const ctl=new AbortController(),timer=setTimeout(()=>ctl.abort(),20000);
  try{
   const r=await fetch(expected,{method:'GET',redirect:'error',signal:ctl.signal,
    headers:{Authorization:'Bearer '+user.access_token}});
   return {context_status:'BOUND_CONTEXT_UNCHANGED',http_status:r.status,body:await r.json()};
  }catch(e){return {context_status:'GET_RESULT_UNKNOWN',http_status:0};}
  finally{clearTimeout(timer);}
 });
 return output&&output.status?{context_status:output.status}:await output;
}"""
