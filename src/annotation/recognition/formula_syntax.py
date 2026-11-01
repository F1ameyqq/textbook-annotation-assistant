"""Small non-executing LaTeX syntax tree; unsupported syntax stays explicit.

This preserves sequence order and source spans. It is not a CAS, equivalence
checker, or proof that the source image was transcribed correctly.
"""
from __future__ import annotations
import re

_LEX = re.compile(r'\\[A-Za-z]+|\\[,;! ]|[0-9]+(?:\.[0-9]+)?|[A-Za-z]|[{}()\[\]^_+\-=.,|<>]')
PRESENTATION = {'\\left', '\\right', '\\displaystyle', '\\textstyle', '\\scriptstyle', '\\scriptscriptstyle', '\\,', '\\;', '\\!', '\\ '}
FRACTIONS = {'\\frac', '\\dfrac', '\\tfrac'}
OPERATORS = {'+', '-', '=', ',', '.', '<', '>', '|', '\\cdot', '\\times', '\\div', '\\leq', '\\geq'}


class SyntaxFailure(ValueError):
    def __init__(self, position, message):
        self.position = position
        super().__init__(message)


def normalized_ast(value):
    """Discard lexical spans and redundant brace groups, preserving scopes."""
    if isinstance(value, list):
        return [normalized_ast(v) for v in value]
    if not isinstance(value, dict):
        return value
    node = {k: normalized_ast(v) for k, v in value.items() if k != 'raw_source_span'}
    if node.get('type') == 'group' and node.get('delimiters') == '{}':
        return node['body']
    if node.get('type') == 'sequence' and len(node['items']) == 1:
        return node['items'][0]
    return node


def fraction_count(value):
    if isinstance(value, list):
        return sum(fraction_count(v) for v in value)
    if not isinstance(value, dict):
        return 0
    return int(value.get('type') == 'fraction') + sum(fraction_count(v) for v in value.values())


def _parse_formula_latex(raw, *, inline=False):
    tokens = []
    result = {'raw_latex': raw, 'supported': False, 'ast': None, 'normalized_ast': None,
              'tokens': tokens, 'errors': [], 'unparsed_tail': None}
    if not isinstance(raw, str):
        result['errors'] = [{'code': 'FORMULA_NOT_TEXT', 'position': 0}]
        return result
    if len(raw) > 8192:
        result['errors'] = [{'code': 'FORMULA_SYNTAX_LIMIT', 'position': 0}]
        result['unparsed_tail'] = raw
        return result
    operators = OPERATORS | ({'\\because', '\\therefore', '\\approx', '\\neq', ':'} if inline else set())
    styles = {'\\mathrm', '\\mathbf', '\\mathit', '\\text'} if inline else set()
    symbols = {'\\pi', '\\alpha', '\\beta', '\\gamma', '\\theta', '\\ell'} if inline else set()
    supported_commands = FRACTIONS | operators | styles | symbols | ({'\\sqrt'} if inline else set())
    lexer = re.compile(_LEX.pattern + r'|:') if inline else _LEX
    try:
        position = 0
        while position < len(raw):
            if raw[position].isspace():
                position += 1
                continue
            match = lexer.match(raw, position)
            if not match:
                raise SyntaxFailure(position, 'unknown character or command')
            text = match[0]
            kind = ('presentation' if text in PRESENTATION else 'command' if text.startswith('\\')
                    else 'number' if text[0].isdigit() else 'symbol' if text.isalpha() else 'punctuation')
            tokens.append({'kind': kind, 'text': text, 'start': position, 'end': match.end()})
            position = match.end()
            if len(tokens) > 2048:
                raise SyntaxFailure(position, 'too many syntax tokens')
        semantic = [t for t in tokens if t['kind'] != 'presentation']
        cursor = 0

        def current():
            return semantic[cursor] if cursor < len(semantic) else None

        def node(kind, span, **values):
            return {'type': kind, 'raw_source_span': span, **values}

        def group(depth):
            nonlocal cursor
            opening = current()
            closing = {'{': '}', '(': ')', '[': ']'}[opening['text']]
            cursor += 1
            body = sequence(closing, depth+1)
            end = current()
            if end is None or end['text'] != closing:
                raise SyntaxFailure(opening['start'], 'unclosed group')
            cursor += 1
            return node('group', [opening['start'], end['end']], delimiters=opening['text']+closing, body=body)

        def argument(depth, *, braces=False):
            token = current()
            if token is None:
                raise SyntaxFailure(len(raw), 'missing argument')
            if token['text'] == '{':
                return group(depth)
            if braces or token['text'] in {'(', '['} or (token['kind'] == 'number' and len(token['text']) != 1):
                raise SyntaxFailure(token['start'], 'argument needs explicit braces')
            return atom(depth+1)

        def atom(depth):
            nonlocal cursor
            if depth > 32:
                raise SyntaxFailure(current()['start'] if current() else len(raw), 'syntax nesting limit')
            token = current()
            if token is None:
                raise SyntaxFailure(len(raw), 'missing atom')
            text = token['text']
            if text in '{([':
                return group(depth)
            if text in FRACTIONS:
                cursor += 1
                numerator = argument(depth+1, braces=True)
                denominator = argument(depth+1, braces=True)
                return node('fraction', [token['start'], denominator['raw_source_span'][1]],
                            numerator=numerator['body'], denominator=denominator['body'])
            if inline and text == '\\sqrt':
                cursor += 1
                index = None
                if current() is not None and current()['text'] == '[':
                    index = group(depth+1)
                radicand = argument(depth+1)
                return node('radical', [token['start'], radicand['raw_source_span'][1]],
                            index=index, radicand=radicand)
            if text in styles:
                cursor += 1
                body = argument(depth+1, braces=True)
                return node('styled', [token['start'], body['raw_source_span'][1]],
                            style=text, body=body)
            if text in symbols:
                cursor += 1
                return node('symbol', [token['start'], token['end']], value=text)
            if token['kind'] in {'number', 'symbol'}:
                cursor += 1
                return node(token['kind'], [token['start'], token['end']], value=text)
            raise SyntaxFailure(token['start'], 'unsupported atom '+text)

        def sequence(stop, depth):
            nonlocal cursor
            values = []
            while current() is not None and current()['text'] != stop:
                token = current()
                text = token['text']
                if text in operators:
                    cursor += 1
                    values.append(node('operator', [token['start'], token['end']], value=text))
                    continue
                if text in {'}', ')', ']'}:
                    raise SyntaxFailure(token['start'], 'unexpected closing group')
                item = atom(depth+1)
                scripts = set()
                while current() is not None and current()['text'] in {'^', '_'}:
                    operation = current()
                    if operation['text'] in scripts:
                        raise SyntaxFailure(operation['start'], 'double superscript or subscript needs explicit nesting')
                    scripts.add(operation['text'])
                    cursor += 1
                    arg = argument(depth+1)
                    item = node('power' if operation['text'] == '^' else 'subscript',
                                [item['raw_source_span'][0], arg['raw_source_span'][1]],
                                base=item, exponent=arg if operation['text'] == '^' else None,
                                index=arg if operation['text'] == '_' else None)
                values.append(item)
            if not values:
                raise SyntaxFailure(current()['start'] if current() else len(raw), 'empty mathematical sequence')
            return node('sequence', [values[0]['raw_source_span'][0], values[-1]['raw_source_span'][1]], items=values)

        ast = sequence(None, 0)
        if cursor != len(semantic):
            raise SyntaxFailure(current()['start'], 'unconsumed tokens')
        result.update(supported=True, ast=ast, normalized_ast=normalized_ast(ast))
    except SyntaxFailure as exc:
        # A later lexing failure must not move an earlier unknown command out
        # of the unresolved tail. Keep every scanned token and start the tail
        # at the first unsupported source position.
        unknown = [t for t in tokens if t['kind'] == 'command' and t['text'] not in supported_commands]
        position = min([exc.position]+[t['start'] for t in unknown])
        detail = str(exc) if position == exc.position else 'unsupported command before later syntax failure'
        result['errors'].append({'code': 'UNSUPPORTED_FORMULA_SYNTAX', 'position': position, 'detail': detail})
        result['unparsed_tail'] = raw[position:]
    return result


def parse_formula_latex(raw):
    """Historical fraction grammar; new inline constructs remain unsupported."""
    return _parse_formula_latex(raw)


def parse_inline_formula_latex(raw):
    """Explicit inline profile: retain radical/index/style scope without evaluation.

    This adds no transcription certainty and does not simplify or solve math.
    The historical parser's accepted language remains unchanged.
    """
    return {**_parse_formula_latex(raw, inline=True), 'syntax_profile': 'INLINE_ARITHMETIC_RADICAL/0.1'}
