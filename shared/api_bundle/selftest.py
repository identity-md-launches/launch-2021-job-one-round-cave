"""Offline integration tests; all disposable files live in test/scratch."""
import copy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

import api_bundle as bundle


class BundleTests(unittest.TestCase):
    def auth_doc(self, policy):
        doc = copy.deepcopy(self.doc)
        doc['components'] = {'securitySchemes': {
            'a': {'type': 'http', 'scheme': 'bearer'},
            'b': {'type': 'oauth2', 'flows': {}}}}
        doc['security'] = policy
        return doc

    def test_auth_public_capture_through_approved_bundles(self):
        old = json.loads(Path(__file__).with_name('imd-openapi.json').read_bytes())
        new = copy.deepcopy(old)
        del new['paths']['/requests/capabilities']['get']['security']
        a, b = self.archive('a.zip', old), self.archive('b.zip', new)
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        report = bundle.compare(a, b, old_sha256=hashlib.sha256(a.read_bytes()).hexdigest(),
                                new_sha256=hashlib.sha256(b.read_bytes()).hexdigest())
        self.assertEqual(report['counts'], {'breaking': 1, 'review': 1, 'info': 0})
        self.assertIn('security_requirement_incompatible', [f['code'] for f in report['findings']])
        self.assertEqual(report['operations_compared'], 5)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.iterdir()})

    def test_auth_alternatives_scope_and_direction(self):
        for old, new in [([{'a': []}, {'b': []}], [{'a': [], 'b': []}]),
                         ([{'b': ['read']}], [{'b': ['read', 'write']}]),
                         ([], [{'a': []}])]:
            a, b = self.archive('a.zip', self.auth_doc(old)), self.archive('b.zip', self.auth_doc(new))
            self.assertEqual(bundle.compare(a, b)['status'], 'breaking')
            self.assertEqual(bundle.compare(b, a)['status'], 'review_required')

    def test_auth_override_and_malformed_same_document(self):
        old = self.auth_doc([{'a': []}])
        new = self.auth_doc([{'a': [], 'b': []}])
        for doc in (old, new):
            doc['paths']['/items']['get']['security'] = []
        a, b = self.archive('a.zip', old), self.archive('b.zip', new)
        self.assertEqual(bundle.compare(a, b)['counts']['breaking'], 0)
        bad = self.archive('bad.zip', self.auth_doc([{'unknown': []}]))
        with self.assertRaisesRegex(ValueError, 'undeclared'):
            bundle.compare(bad, bad)

    def test_auth_cli_outcomes_and_limits(self):
        a = self.archive('a.zip', self.auth_doc([]))
        for policy, code in [([], 0), ([{'a': []}], 1), ([{}], 3),
                              ([{'a': 'not-an-array'}], 2), ([{}]*65, 2)]:
            b = self.archive('b.zip', self.auth_doc(policy))
            run = subprocess.run([sys.executable, '-B', bundle.__file__, str(a), str(b)],
                                 capture_output=True, text=True, timeout=10)
            self.assertEqual(run.returncode, code, run.stdout + run.stderr)

    def test_directory_budget_before_parser_and_exact_boundary(self):
        a = self.root / 'comment.zip'
        info = zipfile.ZipInfo('openapi.json')
        info.comment = b'x' * 60000
        with zipfile.ZipFile(a, 'w') as archive:
            archive.writestr(info, json.dumps(self.doc))
        size = 46 + len(info.filename) + len(info.comment)
        with mock.patch.object(bundle.zipfile, 'ZipFile') as parser:
            with self.assertRaisesRegex(ValueError, 'directory byte limit'):
                bundle.read_bundle(a, directory_bytes=size-1)
            parser.assert_not_called()
        _, inventory = bundle.read_bundle(a, directory_bytes=size)
        self.assertEqual(inventory['preflight']['directory_bytes'], size)
        self.assertEqual(inventory['preflight']['entries'], 1)

    def test_directory_count_before_parser(self):
        a = self.root / 'many.zip'
        with zipfile.ZipFile(a, 'w') as archive:
            for n in range(1001):
                archive.writestr(str(n), b'')
        with mock.patch.object(bundle.zipfile, 'ZipFile') as parser:
            with self.assertRaisesRegex(ValueError, 'entry limit'):
                bundle.read_bundle(a)
            parser.assert_not_called()

    def test_directory_refuses_trailing_bytes_and_false_count(self):
        import struct
        a = self.archive('a.zip')
        raw = a.read_bytes()
        for changed in (raw + b'junk', raw[:-14] + struct.pack('<H', 0) + raw[-12:]):
            a.write_bytes(changed)
            with mock.patch.object(bundle.zipfile, 'ZipFile') as parser:
                with self.assertRaises(ValueError):
                    bundle.read_bundle(a)
                parser.assert_not_called()

    def test_invalid_directory_budget_before_io(self):
        for value in (True, False, None, 0, -1, 1.5, '2'):
            with mock.patch.object(Path, 'open') as opened:
                with self.assertRaisesRegex(ValueError, 'positive integer'):
                    bundle.compare('absent.zip', 'absent.zip', directory_bytes=value)
                opened.assert_not_called()

    def test_directory_budget_applies_to_second_archive_cli(self):
        a = self.archive('a.zip')
        b = self.root / 'b.zip'
        info = zipfile.ZipInfo('openapi.json'); info.comment = b'x'*1000
        with zipfile.ZipFile(b, 'w') as archive:
            archive.writestr(info, json.dumps(self.doc))
        run = subprocess.run([sys.executable, '-B', bundle.__file__, str(a), str(b),
                              '--directory-bytes', '100'], capture_output=True, text=True, timeout=10)
        self.assertEqual(run.returncode, 2)
        self.assertIn('directory byte limit', json.loads(run.stdout)['error'])

    def dependency_doc(self, rules=None, response=False, version='3.1.0'):
        doc = copy.deepcopy(self.doc)
        doc['openapi'] = version
        schema = {'type': 'object', 'properties': {name: {'type': 'string'} for name in ('a', 'b', 'c')}}
        if rules is not None:
            schema['dependentRequired'] = rules
        content = {'application/json': {'schema': schema}}
        operation = doc['paths']['/items']['get']
        if response:
            operation['responses']['200']['content'] = content
        else:
            operation['requestBody'] = {'content': content}
        return doc

    def test_dependency_approved_public_api(self):
        old = json.loads(Path(__file__).with_name('imd-openapi.json').read_bytes())
        body = old['paths']['/requests/quote']['post']['requestBody']['content']['application/json']['schema']
        body.setdefault('properties', {}).update({'clientReference': {'type': 'string'}, 'clientContext': {'type': 'string'}})
        new = copy.deepcopy(old)
        new['paths']['/requests/quote']['post']['requestBody']['content']['application/json']['schema']['dependentRequired'] = {'clientReference': ['clientContext']}
        a, b = self.archive('old.zip', old), self.archive('new.zip', new)
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        report = bundle.compare(a, b, old_sha256=hashlib.sha256(a.read_bytes()).hexdigest(), new_sha256=hashlib.sha256(b.read_bytes()).hexdigest())
        self.assertEqual(report['counts'], {'breaking': 1, 'review': 1, 'info': 0})
        self.assertEqual(report['operations_compared'], 5)
        self.assertIn('dependent_required_incompatible', [f['code'] for f in report['findings']])
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.iterdir()})

    def test_dependency_response_and_version_scope(self):
        for version in ('3.1.0', '3.0.3'):
            a = self.archive('a.zip', self.dependency_doc({'a': ['b']}, response=True, version=version))
            b = self.archive('b.zip', self.dependency_doc(response=True, version=version))
            self.assertEqual(bundle.compare(a, b)['status'], 'breaking' if version == '3.1.0' else 'review_required')
            self.assertEqual(bundle.compare(b, a)['status'], 'review_required')

    def test_dependency_transitive_equivalence_retains_review(self):
        a = self.archive('a.zip', self.dependency_doc({'a': ['b'], 'b': ['c']}))
        b = self.archive('b.zip', self.dependency_doc({'a': ['b', 'c'], 'b': ['c']}))
        self.assertEqual(bundle.compare(a, b)['status'], 'review_required')
        self.assertEqual(bundle.compare(b, a)['counts']['breaking'], 0)

    def test_dependency_limits_and_malformed_cli(self):
        a = self.archive('a.zip', self.dependency_doc())
        for rules, expected in ((None, 0), ({'a': ['b']}, 1), ({'a': []}, 3),
                                ({'a': ['b', 'b']}, 2), ({'a': 'b'}, 2),
                                ({'a': [str(n) for n in range(257)]}, 2)):
            b = self.archive('b.zip', self.dependency_doc(rules))
            result = subprocess.run([sys.executable, '-B', str(Path(bundle.__file__)), str(a), str(b)], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, expected, result.stderr)


    def test_uniqueness_on_captured_public_api(self):
        baseline = json.loads(Path(__file__).with_name('imd-openapi.json').read_bytes())
        schema = baseline['paths']['/requests/quote']['post']['requestBody']['content']['application/json']['schema']
        schema.setdefault('properties', {})['tags'] = {'type': 'array', 'items': {'type': 'string'}}
        proposed = copy.deepcopy(baseline)
        proposed['paths']['/requests/quote']['post']['requestBody']['content']['application/json']['schema']['properties']['tags']['uniqueItems'] = True
        a, b = self.archive('old.zip', baseline), self.archive('new.zip', proposed)
        report = bundle.compare(a, b, old_sha256=hashlib.sha256(a.read_bytes()).hexdigest(),
                                new_sha256=hashlib.sha256(b.read_bytes()).hexdigest())
        self.assertEqual(report['counts'], {'breaking': 1, 'review': 1, 'info': 0})
        self.assertIn('unique_items_incompatible', [f['code'] for f in report['findings']])
        self.assertEqual(bundle.compare(b, a)['status'], 'review_required')

    def test_uniqueness_response_and_openapi30(self):
        for version in ('3.0.3', '3.1.0'):
            old = copy.deepcopy(self.doc)
            old['openapi'] = version
            old['paths']['/items']['get']['responses']['200']['content'] = {
                'application/json': {'schema': {'type': 'array', 'uniqueItems': True}}}
            new = copy.deepcopy(old)
            del new['paths']['/items']['get']['responses']['200']['content']['application/json']['schema']['uniqueItems']
            a, b = self.archive('old.zip', old), self.archive('new.zip', new)
            self.assertEqual(bundle.compare(a, b)['counts']['breaking'], 1)
            self.assertEqual(bundle.compare(b, a)['status'], 'review_required')

    def test_uniqueness_invalid_boolean(self):
        old = copy.deepcopy(self.doc)
        old['paths']['/items']['get']['requestBody'] = {'content': {
            'application/json': {'schema': {'type': 'array'}}}}
        new = copy.deepcopy(old)
        new['paths']['/items']['get']['requestBody']['content']['application/json']['schema']['uniqueItems'] = 1
        a, b = self.archive('old.zip', old), self.archive('new.zip', new)
        with self.assertRaises(ValueError):
            bundle.compare(a, b)

    def test_uniqueness_cli_break_review_and_error(self):
        old = copy.deepcopy(self.doc)
        old['paths']['/items']['get']['requestBody'] = {'content': {
            'application/json': {'schema': {'type': 'array'}}}}
        a = self.archive('old.zip', old)
        for value, expected in ((True, 1), (False, 3), ('true', 2)):
            new = copy.deepcopy(old)
            new['paths']['/items']['get']['requestBody']['content']['application/json']['schema']['uniqueItems'] = value
            b = self.archive('new.zip', new)
            result = subprocess.run([sys.executable, '-B', str(Path(bundle.__file__)), str(a), str(b)],
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, expected, result.stderr)

    def setUp(self):
        scratch = Path('test/scratch')
        scratch.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=scratch)
        self.root = Path(self.tmp.name)
        self.doc = {'openapi': '3.1.0', 'paths': {'/items': {'get': {
            'responses': {'200': {'description': 'OK'}}}}}}

    def tearDown(self):
        self.tmp.cleanup()

    def archive(self, name, doc=None, extra=(), compression=zipfile.ZIP_STORED):
        path = self.root / name
        with zipfile.ZipFile(path, 'w', compression=compression) as output:
            output.writestr('openapi.json', json.dumps(self.doc if doc is None else doc))
            for filename, data in extra:
                output.writestr(filename, data)
        return path

    def test_unchanged_with_inert_executable(self):
        a = self.archive('a.zip', extra=[('script.py', 'raise RuntimeError("NEVER EXECUTE")')])
        before = sorted(p.name for p in self.root.iterdir())
        report = bundle.compare(a, a)
        self.assertEqual(report['status'], 'no_detected_breakage')
        self.assertEqual(len(report['bundle_inputs']['old']['checked_files']), 2)
        self.assertEqual(before, sorted(p.name for p in self.root.iterdir()))

    def test_break_and_cli_exit(self):
        a = self.archive('a.zip')
        b = self.archive('b.zip', {'openapi': '3.1.0', 'paths': {}})
        self.assertEqual(bundle.compare(a, b)['counts']['breaking'], 1)
        result = subprocess.run([sys.executable, '-B', str(Path(bundle.__file__)), str(a), str(b)],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'], 'breaking')

    def test_review_exit(self):
        a = self.archive('a.zip')
        changed = copy.deepcopy(self.doc)
        changed['info'] = {'title': 'changed', 'version': '2'}
        b = self.archive('b.zip', changed)
        result = subprocess.run([sys.executable, '-B', str(Path(bundle.__file__)), str(a), str(b)],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 3)

    def test_zip_traversal_refused_even_when_unselected(self):
        a = self.archive('a.zip', extra=[('../escape', b'bad')])
        with self.assertRaises(ValueError):
            bundle.read_bundle(a)

    def test_crc_refused_even_when_unselected(self):
        a = self.archive('a.zip', extra=[('other', b'corrupt-me')])
        raw = a.read_bytes().replace(b'corrupt-me', b'CORRUPT-ME')
        a.write_bytes(raw)
        with self.assertRaises(zipfile.BadZipFile):
            bundle.read_bundle(a)

    def test_duplicate_and_case_collision_refused(self):
        a = self.archive('a.zip', extra=[('OPENAPI.JSON', b'{}')])
        with self.assertRaises(ValueError):
            bundle.read_bundle(a)

    def test_ratio_limit(self):
        a = self.archive('a.zip', extra=[('bomb', b'0'*100000)], compression=zipfile.ZIP_DEFLATED)
        with self.assertRaisesRegex(ValueError, 'ratio'):
            bundle.read_bundle(a)

    def test_json_duplicate_and_size_limits(self):
        for data in [b'{"openapi":"3.1.0","paths":{},"paths":{}}',
                     b' ' * (bundle.apidelta.MAX_BYTES + 1)]:
            a = self.root / 'invalid.zip'
            with zipfile.ZipFile(a, 'w') as output:
                output.writestr('openapi.json', data)
            with self.assertRaises(ValueError):
                bundle.read_bundle(a)

    def test_missing_member_and_symlink(self):
        a = self.archive('a.zip')
        with self.assertRaises(ValueError):
            bundle.read_bundle(a, 'absent.json')
        link = self.root / 'alias.zip'
        link.symlink_to('a.zip')
        with self.assertRaises(ValueError):
            bundle.read_bundle(link)

    def test_real_imd_capture(self):
        # Included public data is copied here, so no line directory is required.
        baseline = json.loads(Path(__file__).with_name('imd-openapi.json').read_bytes())
        a = self.archive('real.zip', baseline)
        report = bundle.compare(a, a)
        self.assertEqual(report['operations_compared'], 5)
        self.assertEqual(report['findings'], [])

    def test_approved_archive_digests(self):
        a = self.archive('approved.zip')
        digest = hashlib.sha256(a.read_bytes()).hexdigest()
        report = bundle.compare(a, a, old_sha256=digest.upper(), new_sha256=digest)
        self.assertTrue(report['bundle_inputs']['old']['approved_sha256_checked'])
        self.assertTrue(report['bundle_inputs']['new']['approved_sha256_checked'])
        self.assertFalse(bundle.compare(a, a)['bundle_inputs']['old']['approved_sha256_checked'])

    def test_wrong_digest_rejected_before_parsing(self):
        a = self.archive('wrong.zip')
        digest = hashlib.sha256(a.read_bytes()).hexdigest()
        # An approved pathname is not enough: a later byte replacement must fail.
        self.archive('wrong.zip', extra=[('extra', b'changed')])
        with mock.patch.object(bundle.zipfile, 'ZipFile') as parser:
            with self.assertRaisesRegex(ValueError, 'differs from approved'):
                bundle.read_bundle(a, expected_sha256=digest)
            parser.assert_not_called()

    def test_malformed_digest(self):
        a = self.archive('malformed.zip')
        for value in ('', 'g'*64, '0'*63, '0'*65, True, 12):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, '64 hexadecimal'):
                bundle.read_bundle(a, expected_sha256=value)

    def test_approval_still_checks_other_member_crc(self):
        a = self.archive('crc.zip', extra=[('unselected', b'corrupt-me')])
        a.write_bytes(a.read_bytes().replace(b'corrupt-me', b'CORRUPT-ME'))
        with self.assertRaises(zipfile.BadZipFile):
            bundle.read_bundle(a, expected_sha256=hashlib.sha256(a.read_bytes()).hexdigest())

    def test_comparison_uses_approved_snapshot_after_replacement(self):
        a = self.archive('replace.zip')
        digest = hashlib.sha256(a.read_bytes()).hexdigest()
        zip_type = zipfile.ZipFile
        replacement = io.BytesIO()
        with zip_type(replacement, 'w') as output:
            output.writestr('openapi.json', '{"openapi":"3.1.0","paths":{}}')

        def replace_then_parse(snapshot):
            a.write_bytes(replacement.getvalue())
            return zip_type(snapshot)

        with mock.patch.object(bundle.zipfile, 'ZipFile', side_effect=replace_then_parse):
            document, inventory = bundle.read_bundle(a, expected_sha256=digest)
        self.assertEqual(document, self.doc)
        self.assertEqual(inventory['archive_sha256'], digest)
        self.assertNotEqual(hashlib.sha256(a.read_bytes()).hexdigest(), digest)

    def test_boundcheck_on_real_api_in_zip(self):
        baseline = json.loads(Path(__file__).with_name('imd-openapi.json').read_bytes())
        schema = baseline['paths']['/requests/quote']['post']['requestBody']['content']['application/json']['schema']
        schema.setdefault('properties', {})['clientNote'] = {'type': 'string', 'maxLength': 160}
        proposed = copy.deepcopy(baseline)
        proposed['paths']['/requests/quote']['post']['requestBody']['content']['application/json']['schema']['properties']['clientNote']['maxLength'] = 80
        old, new = self.archive('old.zip', baseline), self.archive('new.zip', proposed)
        report = bundle.compare(old, new)
        self.assertEqual(report['extension'], 'authcheck-v1 (includes dependcheck and all earlier line 4 analyzers)')
        self.assertEqual(report['counts']['breaking'], 1)
        self.assertEqual(report['counts']['review'], 1)
        self.assertIn('size_bound_incompatible', [f['code'] for f in report['findings']])
        # Relaxation retains the original unresolved review, rather than auto-accepting.
        self.assertEqual(bundle.compare(new, old)['status'], 'review_required')
        self.assertEqual(bundle.compare(old, old)['status'], 'no_detected_breakage')

    def test_cli_approved_bounds_and_wrong_digest(self):
        old_doc = copy.deepcopy(self.doc)
        old_doc['paths']['/items']['get']['responses']['200']['content'] = {
            'application/json': {'schema': {'type': 'number', 'maximum': 10}}}
        new_doc = copy.deepcopy(old_doc)
        new_doc['paths']['/items']['get']['responses']['200']['content']['application/json']['schema']['maximum'] = 20
        a, b = self.archive('a.zip', old_doc), self.archive('b.zip', new_doc)
        argv = [sys.executable, '-B', str(Path(bundle.__file__)), str(a), str(b),
                '--old-sha256', hashlib.sha256(a.read_bytes()).hexdigest(), '--new-sha256']
        result = subprocess.run(argv + [hashlib.sha256(b.read_bytes()).hexdigest()], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(json.loads(result.stdout)['counts']['breaking'], 1)
        result = subprocess.run(argv + ['not-a-digest'], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertFalse(json.loads(result.stdout)['ok'])

    def test_multiple_of_break_and_integer_equivalence_in_zip(self):
        old_doc = copy.deepcopy(self.doc)
        op = old_doc['paths']['/items']['get']
        op['requestBody'] = {'content': {'application/json': {
            'schema': {'type': 'integer', 'multipleOf': 2}}}}
        changed = copy.deepcopy(old_doc)
        changed['paths']['/items']['get']['requestBody']['content']['application/json']['schema']['multipleOf'] = 3
        old, new = self.archive('old.zip', old_doc), self.archive('new.zip', changed)
        report = bundle.compare(old, new)
        self.assertEqual(report['status'], 'breaking')
        self.assertIn('multiple_of_incompatible', [f['code'] for f in report['findings']])
        self.assertEqual(bundle.compare(old, old)['status'], 'no_detected_breakage')
        # On an integer domain, 0.5 and an absent multiple both admit every integer.
        equivalent = copy.deepcopy(old_doc)
        del equivalent['paths']['/items']['get']['requestBody']['content']['application/json']['schema']['multipleOf']
        half = copy.deepcopy(equivalent)
        half['paths']['/items']['get']['requestBody']['content']['application/json']['schema']['multipleOf'] = 0.5
        a, b = self.archive('any.zip', equivalent), self.archive('half.zip', half)
        self.assertFalse(any(f['code'] == 'multiple_of_incompatible'
                             for f in bundle.compare(a, b)['findings']))

    def test_cooperative_cancellation_and_budget(self):
        a = self.archive('a.zip')
        with self.assertRaisesRegex(ValueError, 'cancelled'):
            bundle.compare(a, a, cancelled=lambda: True)
        with self.assertRaisesRegex(ValueError, 'positive'):
            bundle.compare(a, a, seconds=0)
        with self.assertRaisesRegex(ValueError, 'positive'):
            bundle.compare(a, a, seconds=10**1000)
        self.assertEqual(bundle.compare(a, a, seconds=10)['status'], 'no_detected_breakage')
        result = subprocess.run([sys.executable, '-B', str(Path(bundle.__file__)),
                                 str(a), str(a), '--seconds', '0'],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 2)


    def test_const_change_in_approved_public_api_zip(self):
        old = json.loads(Path(__file__).with_name('imd-openapi.json').read_bytes())
        schema = old['paths']['/requests/quote']['post']['requestBody']['content']['application/json']['schema']
        schema.setdefault('properties', {})['clientMode'] = {'type': 'string', 'const': 'standard'}
        new = copy.deepcopy(old)
        new['paths']['/requests/quote']['post']['requestBody']['content']['application/json']['schema']['properties']['clientMode']['const'] = 'express'
        a, b = self.archive('const-old.zip', old), self.archive('const-new.zip', new)
        report = bundle.compare(a, b, old_sha256=hashlib.sha256(a.read_bytes()).hexdigest(),
                                new_sha256=hashlib.sha256(b.read_bytes()).hexdigest())
        self.assertEqual(report['status'], 'breaking')
        self.assertEqual(report['operations_compared'], 5)
        self.assertIn('const_incompatible', [f['code'] for f in report['findings']])
        self.assertEqual(report['counts']['review'], 1)

    def test_response_const_removal_and_openapi30_review(self):
        old = copy.deepcopy(self.doc)
        old['paths']['/items']['get']['responses']['200']['content'] = {
            'application/json': {'schema': {'const': False}}}
        new = copy.deepcopy(old)
        del new['paths']['/items']['get']['responses']['200']['content']['application/json']['schema']['const']
        a, b = self.archive('a.zip', old), self.archive('b.zip', new)
        self.assertIn('const_incompatible', [f['code'] for f in bundle.compare(a, b)['findings']])
        old['openapi'] = new['openapi'] = '3.0.3'
        a, b = self.archive('c.zip', old), self.archive('d.zip', new)
        report = bundle.compare(a, b)
        self.assertEqual(report['status'], 'review_required')
        self.assertNotIn('const_incompatible', [f['code'] for f in report['findings']])

    def test_node_budget_checks_unselected_implicit_parents(self):
        a = self.archive('deep.zip', extra=[('a/b/inert.txt', b'not executed')])
        # openapi.json + a + a/b + a/b/inert.txt = four nodes.
        with mock.patch.object(bundle.zipfile.ZipFile, 'open') as payload:
            with self.assertRaisesRegex(ValueError, 'filesystem node limit'):
                bundle.compare(a, a, nodes=3)
            payload.assert_not_called()
        self.assertEqual(bundle.compare(a, a, nodes=4)['status'], 'no_detected_breakage')

    def test_invalid_node_budget_refused_before_read(self):
        for value in (True, False, 0, -1, 1.0, None, '4'):
            with self.subTest(value=value), mock.patch.object(Path, 'open') as opened:
                with self.assertRaisesRegex(ValueError, 'positive integer'):
                    bundle.compare('nonexistent.zip', 'nonexistent.zip', nodes=value)
                opened.assert_not_called()

    def test_cli_node_budget_and_const_exit(self):
        old = copy.deepcopy(self.doc)
        old['paths']['/items']['get']['requestBody'] = {'content': {
            'application/json': {'schema': {'const': 0}}}}
        new = copy.deepcopy(old)
        new['paths']['/items']['get']['requestBody']['content']['application/json']['schema']['const'] = False
        a, b = self.archive('a.zip', old), self.archive('b.zip', new)
        cmd = [sys.executable, '-B', str(Path(bundle.__file__)), str(a), str(b), '--nodes']
        for value, code in [('0', 2), ('1', 1)]:
            result = subprocess.run(cmd + [value], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, code, result.stderr)
            if code == 1:
                self.assertIn('const_incompatible', [f['code'] for f in json.loads(result.stdout)['findings']])


if __name__ == '__main__':
    unittest.main(verbosity=2)
