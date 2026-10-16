"""Finite authorization-model oracle and integration/CLI regressions. Offline."""
import copy
import itertools
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import authcheck as a


SCHEMES = {
    'a': {'type': 'apiKey', 'in': 'header', 'name': 'X-A'},
    'b': {'type': 'http', 'scheme': 'bearer'},
    'o': {'type': 'oauth2', 'flows': {'implicit': {
        'authorizationUrl': 'https://example.invalid/authorize',
        'scopes': {'read': 'Read', 'write': 'Write'}}}},
}


def document(security=None, version='3.1.0'):
    op = {'responses': {'200': {'description': 'ok'}}}
    if security is not None:
        op['security'] = security
    return {'openapi': version, 'paths': {'/a~b/c': {'get': op}},
            'components': {'securitySchemes': copy.deepcopy(SCHEMES)}}


def operation(doc):
    return doc['paths']['/a~b/c']['get']


def hits(old, new):
    return [f for f in a.compare(old, new)['findings']
            if f['code'] == 'security_requirement_incompatible']


class Tests(unittest.TestCase):
    def test_exhaustive_finite_oracle(self):
        # Independent evaluator: enumerate all 20 hypothetical holders of a/b
        # and OAuth with absent, empty, read, write or both scopes. No tokens.
        holders = []
        for has_a, has_b, oauth in itertools.product(
                (False, True), (False, True), (None, [], ['read'], ['write'], ['read', 'write'])):
            holder = {}
            if has_a:
                holder['a'] = []
            if has_b:
                holder['b'] = []
            if oauth is not None:
                holder['o'] = oauth
            holders.append(holder)
        options = [{}, {'a': []}, {'b': []}, {'a': [], 'b': []},
                   {'o': []}, {'o': ['read']}, {'o': ['write']}, {'o': ['read', 'write']}]
        def accepts(policy, holder):
            return not policy or any(all(name in holder and
                                        all(label in holder[name] for label in labels)
                                        for name, labels in option.items()) for option in policy)
        policies = [[option for i, option in enumerate(options) if mask & (1 << i)]
                    for mask in range(256)]
        accepted = [{i for i, h in enumerate(holders) if accepts(p, h)} for p in policies]
        docs = [document(p) for p in policies]
        for oi, old in enumerate(docs):
            for ni, new in enumerate(docs):
                self.assertEqual(bool(hits(old, new)), bool(accepted[oi] - accepted[ni]),
                                 (policies[oi], policies[ni]))

    def test_anonymous_defaults_and_optional_alternative(self):
        for before in (None, [], [{}], [{}, {'a': []}]):
            self.assertTrue(hits(document(before), document([{'a': []}])))
            self.assertFalse(hits(document([{'a': []}]), document(before)))
        self.assertFalse(hits(document(), document([{}])))

    def test_and_or_scope_direction(self):
        self.assertTrue(hits(document([{'a': []}, {'b': []}]), document([{'a': [], 'b': []}])))
        self.assertFalse(hits(document([{'a': [], 'b': []}]), document([{'a': []}, {'b': []}])))
        self.assertTrue(hits(document([{'o': ['read']}]), document([{'o': ['read', 'write']}])))
        self.assertFalse(hits(document([{'o': ['read', 'write']}]), document([{'o': ['read']}])))

    def test_root_inheritance_and_override(self):
        old, new = document(), document()
        new['security'] = [{'a': []}]
        self.assertTrue(hits(old, new))
        operation(new)['security'] = []
        self.assertFalse(hits(old, new))
        operation(old)['security'] = [{'b': []}]
        operation(new)['security'] = [{'b': []}]
        self.assertFalse(hits(old, new))
        # A path-level security field is not an OpenAPI inheritance level.
        new['paths']['/a~b/c']['security'] = [{'a': []}]
        del operation(new)['security']
        new['security'] = [{'b': []}]
        self.assertFalse(hits(old, new))

    def test_equivalent_order_duplicate_and_redundancy(self):
        old = document([{'o': ['read', 'write']}, {'a': []}])
        new = document([{'a': []}, {'o': ['write', 'read', 'read']}, {'a': [], 'b': []}])
        self.assertFalse(hits(old, new))
        self.assertFalse(hits(new, old))
        self.assertEqual(a.compare(old, new)['status'], 'review_required')

    def test_version_roles_and_mutual_tls(self):
        old, new = document([{'b': []}]), document([{'b': ['operator']}])
        self.assertTrue(hits(old, new))
        for doc in (old, new):
            doc['openapi'] = '3.0.3'
        with self.assertRaisesRegex(a.api.Invalid, 'non-OAuth'):
            hits(old, new)
        self.assertTrue(hits(document([{'o': []}], '3.0.3'), document([{'o': ['read']}], '3.0.3')))
        old, new = document(), document([{'m': []}])
        new['components']['securitySchemes']['m'] = {'type': 'mutualTLS'}
        self.assertTrue(hits(old, new))
        new['openapi'] = '3.0.3'
        with self.assertRaises(a.api.Invalid):
            hits(old, new)

    def test_references_and_definition_change_review(self):
        old = document([{'alias': []}])
        schemes = old['components']['securitySchemes']
        schemes['a/~'] = schemes.pop('a')
        schemes['alias'] = {'$ref': '#/components/securitySchemes/a~1~0'}
        self.assertFalse(hits(old, copy.deepcopy(old)))
        new = copy.deepcopy(old)
        new['components']['securitySchemes']['a/~']['name'] = 'X-Changed'
        self.assertFalse(hits(old, new))
        self.assertEqual(a.compare(old, new)['status'], 'review_required')
        for ref in ('https://example.invalid/scheme', '#/missing', '#/components/securitySchemes/alias'):
            bad = copy.deepcopy(old)
            bad['components']['securitySchemes']['alias'] = {'$ref': ref}
            with self.assertRaises(a.api.Invalid):
                hits(bad, bad)

    def test_malformed_even_when_identical(self):
        for raw in (None, {}, True, 'a', [False], [{'a': None}], [{'a': 'read'}],
                    [{'a': [1]}], [{'unknown': []}]):
            doc = document()
            operation(doc)['security'] = raw
            with self.subTest(raw=raw), self.assertRaises(a.api.Invalid):
                hits(doc, copy.deepcopy(doc))
        for definition in (None, {}, {'type': 'custom'}):
            doc = document([{'a': []}])
            doc['components']['securitySchemes']['a'] = definition
            with self.assertRaises(a.api.Invalid):
                hits(doc, doc)

    def test_resource_limits(self):
        for policy in ([{}] * 65, [{'o': [str(i) for i in range(65)]}]):
            with self.assertRaises(a.api.Invalid):
                hits(document(), document(policy))
        doc = document([{str(i): [] for i in range(33)}])
        doc['components']['securitySchemes'] = {str(i): SCHEMES['b'] for i in range(33)}
        with self.assertRaisesRegex(a.api.Invalid, '32 schemes'):
            hits(doc, doc)
        old, new = document([{'a': []}] * 64), document([{'b': []}] * 64)
        for doc in (old, new):
            op = operation(doc)
            doc['paths'] = {'/operation' + str(i): {'get': op} for i in range(25)}
        with self.assertRaisesRegex(a.api.Invalid, 'comparison limit'):
            hits(old, new)

    def test_locations_determinism_no_mutation(self):
        old, new = document(), document([{'a': []}])
        saved = copy.deepcopy((old, new))
        report = a.compare(old, new)
        self.assertEqual((old, new), saved)
        self.assertEqual(hits(old, new)[0]['location'], '/paths/~1a~0b~1c/get/security')
        self.assertEqual(report, a.compare(json.loads(json.dumps(old, sort_keys=True)), new))

    def test_inherited_analysis(self):
        old, new = document(), document([{'a': []}])
        for doc, schema in ((old, {'type': 'object'}), (new, {
                'type': 'object', 'dependentRequired': {'a': ['b']}, 'required': ['a']})):
            operation(doc)['requestBody'] = {'content': {'application/json': {'schema': schema}}}
        codes = {f['code'] for f in a.compare(old, new)['findings']}
        self.assertTrue({'dependent_required_incompatible', 'request_property_required',
                         'security_requirement_incompatible', 'security_changed'} <= codes)

    def test_real_capture_and_demo(self):
        report = a.demo()
        self.assertEqual(report['counts'], {'breaking': 1, 'review': 1, 'info': 0})
        self.assertEqual(report['operations_compared'], 5)
        obj, _ = a.api.load(a.depend.unique.const.multiple.bound.BASE.with_name('imd-openapi.json'))
        self.assertEqual(a.compare(obj, obj)['findings'], [])

    def test_cli_and_input_hashes(self):
        scratch = Path('test/scratch')
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as folder:
            old, new = Path(folder) / 'old.json', Path(folder) / 'new.json'
            old.write_text(json.dumps(document([{'a': []}])))
            script = str(Path(__file__).with_name('authcheck.py'))
            for policy, exit_code in (([{'a': []}], 0), ([{'b': []}], 1), ([], 3), ({}, 2)):
                new.write_text(json.dumps(document(policy)))
                run = subprocess.run([sys.executable, '-B', script, 'compare', str(old), str(new)],
                                     capture_output=True, text=True, timeout=10)
                self.assertEqual(run.returncode, exit_code, run.stderr)
                if exit_code != 2:
                    self.assertEqual(len(json.loads(run.stdout)['old_sha256']), 64)
            demo = subprocess.run([sys.executable, '-B', script, 'demo'],
                                  capture_output=True, text=True, timeout=10)
            self.assertEqual(demo.returncode, 0, demo.stderr)


if __name__ == '__main__':
    unittest.main()
