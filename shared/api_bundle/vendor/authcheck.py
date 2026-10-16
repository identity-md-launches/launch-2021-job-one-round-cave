#!/usr/bin/env python3
"""Offline OpenAPI authentication-requirement compatibility. Standard library only."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import sys

PREVIOUS = Path(__file__).with_name('dependcheck.py')
spec = importlib.util.spec_from_file_location('authcheck_depend', PREVIOUS)
depend = importlib.util.module_from_spec(spec)
spec.loader.exec_module(depend)
api = depend.api
MAX_ALTERNATIVES = 64
MAX_SCHEMES = 32
MAX_LABELS = 64
MAX_COMPARISONS = 100000


def policy(document, operation):
    """Effective OR-of-AND policy, using operation override then root default.

    Sets contain symbolic (scheme name, scope/role) obligations; None denotes
    possession of that scheme, distinct from any (even empty) label string.
    No credential is accepted, examined, generated or used.
    """
    raw = operation.get('security', document.obj.get('security', []))
    api.require(isinstance(raw, list), 'security must be an array')
    api.require(len(raw) <= MAX_ALTERNATIVES, 'security exceeds 64 alternatives')
    components = document.obj.get('components', {})
    api.require(isinstance(components, dict), 'components must be an object')
    schemes = components.get('securitySchemes', {})
    api.require(isinstance(schemes, dict), 'securitySchemes must be an object')
    result = []
    for index, option in enumerate(raw or [{}]):
        api.require(isinstance(option, dict), 'security alternative must be an object')
        api.require(len(option) <= MAX_SCHEMES, 'security alternative exceeds 32 schemes')
        obligations = set()
        for name, labels in option.items():
            api.require(name in schemes, 'undeclared security scheme: ' + name)
            scheme = document.resolve(schemes[name])
            api.require(isinstance(scheme, dict), 'security scheme must be an object')
            kind = scheme.get('type')
            allowed = ('apiKey', 'http', 'oauth2', 'openIdConnect')
            if document.obj['openapi'].startswith('3.1.'):
                allowed += ('mutualTLS',)
            api.require(kind in allowed, 'unsupported security scheme type: ' + name)
            api.require(isinstance(labels, list) and all(isinstance(s, str) for s in labels),
                        'security scopes/roles must be arrays of strings')
            api.require(len(labels) <= MAX_LABELS, 'security scheme exceeds 64 scopes/roles')
            if document.obj['openapi'].startswith('3.0.') and kind not in ('oauth2', 'openIdConnect'):
                api.require(not labels, 'OpenAPI 3.0 non-OAuth security arrays must be empty')
            obligations.add((name, None))
            obligations.update((name, label) for label in labels)
        result.append((index, frozenset(obligations), option))
    return result


class Analyzer(depend.Analyzer):
    def __init__(self, old, new):
        super().__init__(old, new)
        self.auth_comparisons = 0

    def operation(self, path, method, old_item, new_item):
        super().operation(path, method, old_item, new_item)
        before = policy(self.old, old_item[method])
        after = policy(self.new, new_item[method])
        loc = api.pointer('/paths', path) + '/' + method + '/security'
        for index, source, described in before:
            covered = False
            for _, target, _ in after:
                self.auth_comparisons += 1
                api.require(self.auth_comparisons <= MAX_COMPARISONS,
                            'security comparison limit exceeded (100000)')
                if target <= source:
                    covered = True
                    break
            if not covered:
                self.emit('breaking', 'security_requirement_incompatible', loc,
                          'Old effective alternative ' + str(index) + ' ' + api.canonical(described) +
                          ' does not meet any new alternative using only its declared schemes and scopes/roles. '
                          'This is a symbolic requirement witness, not a credential or runtime authorization test.')


def compare(old, new):
    analyzer = Analyzer(old, new)
    report = analyzer.run()
    report['extension'] = 'authcheck-v1 (includes dependcheck and all earlier line 4 analyzers)'
    report['security_alternative_comparisons'] = analyzer.auth_comparisons
    return report


def demo():
    capture = Path(__file__).resolve().parents[1] / 'imd-openapi.json'
    old, digest = api.load(capture)
    new = copy.deepcopy(old)
    # This public discovery operation explicitly opts out of root authentication.
    # Removing that override would require one of the REAL declared root schemes.
    del new['paths']['/requests/capabilities']['get']['security']
    report = compare(old, new)
    report.update(capture_sha256=digest, baseline_source='https://api.imd.fun/openapi.json',
                  demo='Hypothetically remove the anonymous override from the captured capabilities operation; no operation called.')
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('demo')
    diff = commands.add_parser('compare')
    diff.add_argument('old')
    diff.add_argument('new')
    args = parser.parse_args(argv)
    try:
        if args.command == 'demo':
            report = demo()
        else:
            old, oh = api.load(args.old)
            new, nh = api.load(args.new)
            report = compare(old, new)
            report.update(old_sha256=oh, new_sha256=nh)
        print(json.dumps(report, indent=2, allow_nan=False))
        return 0 if args.command == 'demo' else {
            'breaking': 1, 'review_required': 3, 'no_detected_breakage': 0}[report['status']]
    except (api.Invalid, OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        print('authcheck: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
