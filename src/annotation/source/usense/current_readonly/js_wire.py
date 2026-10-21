"""Restricted static proof for explicit async fetch GET getter modules.

This is not a JS interpreter. Unsupported syntax stays UNKNOWN. Comments and
strings are lexical values, never function/field evidence. No JS is executed.
"""
from dataclasses import dataclass
import re
from .gate import Stop, sha, BOOK

SCHEMA = 'A16-fetch-getter-bindings/v1'
FRAME_BASE = '/qieti/api/annotate_pic/get_manual_annotations_unified_by_order_in_level/'
INFO_BASE = '/qieti/api/annotate_pic/get_question_info/'
CONTENT_BASE = '/qieti/api/verify_annotation/get-ocr-annotation?file_id='
EXPECTED = {
    'sample_frames': [FRAME_BASE, 0, '/', 1],
    'sample_info': [INFO_BASE, 0, '/', 1],
    'content': [CONTENT_BASE, 0, '&question_order=', 1, '&zone=', 2]}


class Unsupported(Exception):
    pass


@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    start: int
    end: int


def lex(text):
    tokens, i = [], 0
    while i < len(text):
        if text[i].isspace():
            i += 1
            continue
        if text.startswith('//', i):
            end = text.find('\n', i + 2)
            i = len(text) if end < 0 else end + 1
            continue
        if text.startswith('/*', i):
            end = text.find('*/', i + 2)
            if end < 0:
                raise Unsupported('UNTERMINATED_COMMENT')
            i = end + 2
            continue
        start, c = i, text[i]
        if c in ('"', "'", '`'):
            i += 1
            value = ''
            while i < len(text) and text[i] != c:
                if text[i] == '\\':
                    i += 1
                    if i >= len(text) or text[i] not in ('\\', '"', "'", '/', 'n', 'r', 't'):
                        raise Unsupported('UNSUPPORTED_STRING_ESCAPE')
                    value += {'n': '\n', 'r': '\r', 't': '\t'}.get(text[i], text[i])
                else:
                    value += text[i]
                i += 1
            if i >= len(text):
                raise Unsupported('UNTERMINATED_STRING')
            i += 1
            tokens.append(Token('template' if c == '`' else 'string', value, start, i))
            continue
        m = re.match(r'[A-Za-z_$][A-Za-z0-9_$]*', text[i:])
        if m:
            i += len(m.group())
            tokens.append(Token('id', m.group(), start, i))
            continue
        # A slash outside comments/strings could begin a regexp. Do not scan
        # executable-looking words out of a regexp literal or guess division.
        if c == '/':
            raise Unsupported('REGEXP_OR_DIVISION_UNSUPPORTED')
        tokens.append(Token('punct', c, i, i + 1))
        i += 1
    return tokens


class Cursor:
    def __init__(self, tokens):
        self.tokens, self.pos = tokens, 0

    def peek(self, value=None):
        t = self.tokens[self.pos] if self.pos < len(self.tokens) else None
        return t if value is None else t is not None and t.value == value

    def take(self, value=None, kind=None):
        if kind is None and value is not None:
            kind = 'id' if re.fullmatch(r'[A-Za-z_$][A-Za-z0-9_$]*', value) else 'punct'
        t = self.peek()
        if t is None or value is not None and t.value != value or kind is not None and t.kind != kind:
            raise Unsupported('UNSUPPORTED_FUNCTION_SHAPE')
        self.pos += 1
        return t

    def done(self):
        return self.pos == len(self.tokens)


def functions(tokens):
    """Only declaration-only top-level modules; no top-level rebinding/eval."""
    c, result = Cursor(tokens), {}
    while not c.done():
        if c.peek(';'):
            c.take(';')
            continue
        if c.peek('export'):
            c.take('export')
        start = c.take('async').start
        c.take('function')
        name = c.take(kind='id').value
        c.take('(')
        params = []
        if not c.peek(')'):
            params.append(c.take(kind='id').value)
            while c.peek(','):
                c.take(',')
                params.append(c.take(kind='id').value)
        c.take(')')
        if len(set(params)) != len(params) or name in result:
            raise Unsupported('AMBIGUOUS_FUNCTION_BINDING')
        c.take('{')
        begin, depth = c.pos, 1
        while depth:
            t = c.take()
            if t.kind == 'punct':
                depth += 1 if t.value == '{' else -1 if t.value == '}' else 0
        result[name] = {'name': name, 'params': params, 'tokens': tokens[begin:c.pos - 1],
            'start': start, 'end': t.end}
    return result


def url_atoms(tokens, params):
    c, atoms = Cursor(tokens), []
    while not c.done():
        t = c.take()
        if t.kind == 'string':
            atoms.append(t.value)
        elif t.kind == 'id' and t.value in params:
            atoms.append(params.index(t.value))
        elif t.kind == 'template':
            pattern = re.compile(r'\$\{([A-Za-z_$][A-Za-z0-9_$]*)\}')
            position = 0
            for m in pattern.finditer(t.value):
                atoms.append(t.value[position:m.start()])
                if m.group(1) not in params:
                    raise Unsupported('UNKNOWN_URL_PARAMETER')
                atoms.append(params.index(m.group(1)))
                position = m.end()
            tail = t.value[position:]
            if '${' in tail or any('${' in a for a in atoms if isinstance(a, str)):
                raise Unsupported('UNSUPPORTED_TEMPLATE_EXPRESSION')
            atoms.append(tail)
        else:
            raise Unsupported('UNSUPPORTED_URL_EXPRESSION')
        if not c.done():
            c.take('+')
    merged = []
    for atom in atoms:
        if atom == '':
            continue
        if isinstance(atom, str) and merged and isinstance(merged[-1], str):
            merged[-1] += atom
        else:
            merged.append(atom)
    return merged


def getter(fn):
    if 'fetch' in fn['params']:
        raise Unsupported('SHADOWED_NATIVE_FETCH')
    c = Cursor(fn['tokens'])
    c.take('const'); response = c.take(kind='id').value; c.take('='); c.take('await'); c.take('fetch'); c.take('(')
    url_start = c.pos
    # The supported URL expression has literals, template literals, identifiers
    # and + only; its comma is therefore unambiguous, including template values.
    while not c.peek(','):
        c.take()
    url_tokens = c.tokens[url_start:c.pos]
    atoms = url_atoms(url_tokens, fn['params'])
    c.take(','); c.take('{'); c.take('method'); c.take(':'); method = c.take(kind='string')
    if method.value != 'GET':
        raise Unsupported('NOT_A_GET_GETTER')
    c.take('}'); c.take(')'); c.take(';')
    c.take('const'); payload = c.take(kind='id').value; c.take('='); c.take('await')
    c.take(response); c.take('.'); c.take('json'); c.take('('); c.take(')'); c.take(';')
    if response == payload or response in fn['params'] or payload in fn['params'] or 'fetch' in (response, payload):
        raise Unsupported('ALIASED_RESPONSE_IDENTITY')
    c.take('return')
    refs = {}
    if c.peek('{'):
        c.take('{')
        while not c.peek('}'):
            field = c.take(kind='id')
            if field.value in refs:
                raise Unsupported('DUPLICATE_RESPONSE_FIELD')
            c.take(':')
            first = c.take(payload)
            c.take('.'); c.take('data'); c.take('.'); last = c.take(field.value)
            refs[field.value] = {'start': first.start, 'end': last.end,
                'response_flow': response + '.json() -> ' + payload + '.data.' + field.value}
            if not c.peek('}'):
                c.take(',')
        c.take('}')
    else:
        first = c.take(payload); c.take('.'); last = c.take('data')
        refs['data'] = {'start': first.start, 'end': last.end,
            'response_flow': response + '.json() -> ' + payload + '.data'}
    c.take(';')
    if not c.done():
        raise Unsupported('UNSUPPORTED_GETTER_STATEMENTS')
    kind = next((name for name, expected in EXPECTED.items() if atoms == expected), None)
    if kind is None or len(fn['params']) != (3 if kind == 'content' else 2):
        raise Unsupported('GETTER_URL_PARAMETER_MAPPING_UNPROVEN')
    wanted = {'success', 'ocr_result', 'rect_ids'} if kind == 'content' else {'data'}
    if set(refs) != wanted:
        raise Unsupported('GETTER_RESPONSE_MAPPING_UNPROVEN')
    return {'kind': kind, 'name': fn['name'], 'url_atoms': atoms,
        'getter_range': {'start': fn['start'], 'end': fn['end']},
        'url_range': {'start': url_tokens[0].start, 'end': url_tokens[-1].end},
        'field_refs': refs}


def call_chain(fn, getters):
    if len(fn['params']) != 2 or any(p in getters for p in fn['params']):
        raise Unsupported('UNSUPPORTED_CALL_CHAIN_PARAMETERS')
    c, found, variables = Cursor(fn['tokens']), {}, set()
    while c.peek('const'):
        start = c.take('const').start
        variable = c.take(kind='id').value
        if variable in variables or variable in fn['params'] or variable in getters:
            raise Unsupported('DUPLICATE_CALL_RESULT')
        variables.add(variable)
        c.take('='); c.take('await'); name = c.take(kind='id').value
        if name not in getters:
            raise Unsupported('UNKNOWN_GETTER_CALL')
        g = getters[name]
        c.take('('); c.take(fn['params'][0]); c.take(','); c.take(fn['params'][1])
        zone = None
        if g['kind'] == 'content':
            c.take(','); zone = c.take(kind='string').value
            if zone not in ('question', 'choice', 'answer'):
                raise Unsupported('UNKNOWN_ZONE_ARGUMENT')
        c.take(')'); end = c.take(';').end
        operation = 'content_' + zone if zone else g['kind']
        if operation in found:
            raise Unsupported('AMBIGUOUS_GETTER_CALL')
        found[operation] = {**g, 'zone': zone, 'call_range': {'start': start, 'end': end},
            'caller': fn['name'], 'caller_params': fn['params'], 'result_variable': variable}
    c.take('return'); c.take('{')
    returned = set()
    while not c.peek('}'):
        variable = c.take(kind='id').value
        if variable not in variables or variable in returned:
            raise Unsupported('UNBOUND_CALL_RESULT')
        returned.add(variable)
        if not c.peek('}'):
            c.take(',')
    c.take('}'); c.take(';')
    if not c.done() or returned != variables or set(found) != {
            'sample_frames', 'sample_info', 'content_question', 'content_choice', 'content_answer'}:
        raise Unsupported('INCOMPLETE_CALL_CHAIN')
    return found


def analyze_asset(raw, ref):
    text = raw.decode('utf-8', errors='strict')
    tokens = lex(text)
    funcs = functions(tokens)
    if 'fetch' in funcs:
        raise Unsupported('SHADOWED_NATIVE_FETCH')
    getters, rejected = {}, []
    for name, fn in funcs.items():
        try:
            getters[name] = getter(fn)
        except Unsupported as e:
            rejected.append({'function': name, 'reason': str(e)})
    for fn in funcs.values():
        try:
            bindings = call_chain(fn, getters)
        except Unsupported:
            continue
        for binding in bindings.values():
            binding['asset_ref'], binding['asset_sha256'] = ref, sha(raw)
            for field_ref in binding['field_refs'].values():
                field_ref['code_sha256'] = sha(text[field_ref['start']:field_ref['end']].encode())
        return {'schema': SCHEMA, 'bindings': bindings, 'complete': True,
            'supported_shape': 'DECLARATION_ONLY_ASYNC_FETCH_JSON_GETTERS_AND_STRAIGHT_CALL_CHAIN',
            'source_position_unit': 'ZERO_BASED_UNICODE_CODEPOINT_HALF_OPEN',
            'asset_sha256': sha(raw), 'rejected_functions': rejected}
    return {'schema': SCHEMA, 'complete': False, 'reason': 'NO_COMPLETE_BOUND_CALL_CHAIN',
        'partial_getters': list(getters.values()), 'rejected_functions': rejected}


def evidenced_paths(wire, order):
    proof = wire.get('binding_proof') or {}
    bindings = proof.get('bindings', {})
    names = {'sample_frames', 'sample_info', 'content_question', 'content_choice', 'content_answer'}
    if (wire.get('status') != 'CURRENT_CODE_CONFIRMED' or proof.get('schema') != SCHEMA or
            proof.get('complete') is not True or set(bindings) != names):
        raise Stop('CURRENT_READ_SCHEMA_REQUIRED')
    result = {}
    for name, binding in bindings.items():
        kind = 'content' if name.startswith('content_') else name
        zone = name[8:] if kind == 'content' else None
        if (binding.get('kind') != kind or binding.get('zone') != zone or
                binding.get('url_atoms') != EXPECTED[kind] or not binding.get('field_refs') or
                not binding.get('getter_range') or not binding.get('call_range') or
                binding.get('asset_sha256') != proof.get('asset_sha256')):
            raise Stop('CURRENT_READ_SCHEMA_REQUIRED')
        values = [BOOK, str(order), zone]
        result[name] = ''.join(values[a] if type(a) is int else a for a in binding['url_atoms'])
    return result
