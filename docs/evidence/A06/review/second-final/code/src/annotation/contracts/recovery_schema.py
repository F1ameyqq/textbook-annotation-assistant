"""Fail-closed evaluator for the seven frozen A03 recovery schemas.

This is a deliberately bounded schema dialect, not a general JSON Schema engine.
Unsupported assertions are errors and every schema document is byte pinned.
"""
import hashlib
import math
import re
from datetime import datetime
from pathlib import Path

from .integrity import read_json
from .validation import fail

SCHEMA_HASHES = {
    'action-fact.schema.json': '808f81ea42bcc7fb28cd2d9635dbb869c491bf9cbc4fb3b53a9db7d502eaff96',
    'archive-v1.schema.json': '18c9dac25a44edf48bc3ea9d9c4ee37c405d9b7ce1efddca760f15806dbfadef',
    'case-file.schema.json': 'a615d717deeb8b09ab3e330aa0d6754ee98c5b2edb3ddda91499b4350e079e6b',
    'ledger-export.schema.json': '64ed1f0641943125c81cc3627d5bf82a6dc288595a385dd5ba3a3d7f0c1dc19c',
    'recovery-exchange.schema.json': 'cb0366a1349b04ca1560077747e3862a01af16815404f208ce92429e93cf2a6d',
    'unattempted-basis.schema.json': 'a2faf79099e1c09221ac8e050204994b4d974b6758545b0a760599a75c926fe2',
    'event-prefix.schema.json': '784c94ca63188ccb4a84de3b679128498fe029abf7cff69d5f892e4de3d0e2d7',
}
ANNOTATIONS = {'title', 'description', 'default', '$comment', '$schema', '$id', '$defs', 'discriminator'}
ASSERTIONS = {'$ref', 'type', 'const', 'enum', 'required', 'properties', 'additionalProperties', 'items',
              'minItems', 'maxItems', 'minProperties', 'maxProperties', 'minLength', 'maxLength', 'pattern',
              'minimum', 'maximum', 'exclusiveMinimum', 'exclusiveMaximum', 'anyOf', 'oneOf', 'format',
              'propertyNames', 'uniqueItems'}


def _equal(a, b):
    # JSON booleans are not integers; Python equality alone silently conflates them.
    return type(a) is type(b) and a == b


class FrozenSchemas:
    def __init__(self):
        self.documents = {}
        for name, expected in SCHEMA_HASHES.items():
            path = Path(__file__).parent / 'schemas' / name
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                fail('$', 'RECOVERY_PROFILE_MISMATCH', 'frozen schema bytes differ: ' + name)
            document = read_json(path)
            self.documents[name] = document
            self._dialect(document)

    def _dialect(self, schema):
        if not isinstance(schema, dict):
            fail('$', 'RECOVERY_PROFILE_MISMATCH', 'unsupported boolean schema')
        if set(schema) - ANNOTATIONS - ASSERTIONS:
            fail('$', 'RECOVERY_PROFILE_MISMATCH', 'unsupported schema assertion')
        for field in ('properties', '$defs'):
            for value in schema.get(field, {}).values():
                self._dialect(value)
        for field in ('items', 'additionalProperties', 'propertyNames'):
            if isinstance(schema.get(field), dict):
                self._dialect(schema[field])
        for field in ('anyOf', 'oneOf'):
            for value in schema.get(field, []):
                self._dialect(value)

    def check(self, value, name='recovery-exchange.schema.json', definition=None):
        root = self.documents[name]
        self.validate(value, root['$defs'][definition] if definition else root, root)

    def validate(self, value, schema, root, path='$'):
        def bad(message):
            fail(path, 'SCHEMA', message)
        if '$ref' in schema:
            filename, _, fragment = schema['$ref'].partition('#')
            root = self.documents[filename] if filename else root
            selected = root
            for segment in fragment.strip('/').split('/') if fragment else []:
                selected = selected[segment.replace('~1', '/').replace('~0', '~')]
            self.validate(value, selected, root, path)
            return
        for union in ('anyOf', 'oneOf'):
            if union in schema:
                from .validation import ContractError
                accepted = 0
                variants = schema[union]
                discriminator = schema.get('discriminator')
                if discriminator and isinstance(value, dict):
                    mapping = discriminator['mapping']
                    kind = value.get(discriminator['propertyName'])
                    if kind not in mapping:
                        bad('unknown artifact kind')
                    variants = [{'$ref': mapping[kind]}]
                for variant in variants:
                    try:
                        self.validate(value, variant, root, path)
                        accepted += 1
                    except ContractError:
                        pass
                if accepted == 0 or (union == 'oneOf' and accepted != 1):
                    bad('no unique valid ' + union + ' branch')
        if 'const' in schema and not _equal(value, schema['const']):
            bad('constant differs')
        if 'enum' in schema and not any(_equal(value, member) for member in schema['enum']):
            bad('value outside enum')
        types = {'object': type(value) is dict, 'array': type(value) is list,
                 'string': type(value) is str, 'integer': type(value) is int,
                 'number': type(value) in (int, float), 'boolean': type(value) is bool,
                 'null': value is None}
        if 'type' in schema and not types.get(schema['type'], False):
            bad('expected ' + schema['type'])
        if isinstance(value, dict):
            if not set(schema.get('required', [])) <= set(value):
                bad('missing required fields')
            if not schema.get('minProperties', 0) <= len(value) <= schema.get('maxProperties', math.inf):
                bad('object property count')
            properties = schema.get('properties', {})
            for key, child in value.items():
                if 'propertyNames' in schema:
                    self.validate(key, schema['propertyNames'], root, path)
                child_schema = properties.get(key, schema.get('additionalProperties', {}))
                if child_schema is False:
                    bad('unexpected field ' + key)
                if isinstance(child_schema, dict):
                    self.validate(child, child_schema, root, path + '.' + key)
        if isinstance(value, list):
            if not schema.get('minItems', 0) <= len(value) <= schema.get('maxItems', math.inf):
                bad('array item count')
            if schema.get('uniqueItems') and any(value[i] == value[j] for i in range(len(value)) for j in range(i)):
                bad('duplicate array member')
            for i, child in enumerate(value):
                if 'items' in schema:
                    self.validate(child, schema['items'], root, '{}[{}]'.format(path, i))
        if isinstance(value, str):
            if not schema.get('minLength', 0) <= len(value) <= schema.get('maxLength', math.inf):
                bad('string length')
            if 'pattern' in schema and re.search(schema['pattern'], value) is None:
                bad('string pattern')
            if schema.get('format') == 'date-time':
                try:
                    if datetime.fromisoformat(value.replace('Z', '+00:00')).tzinfo is None:
                        bad('timezone required')
                except ValueError:
                    bad('invalid timestamp')
        if type(value) in (int, float):
            if not math.isfinite(value):
                bad('nonfinite number')
            if not schema.get('minimum', -math.inf) <= value <= schema.get('maximum', math.inf):
                bad('number outside bounds')
            if not schema.get('exclusiveMinimum', -math.inf) < value < schema.get('exclusiveMaximum', math.inf):
                bad('number outside exclusive bounds')
