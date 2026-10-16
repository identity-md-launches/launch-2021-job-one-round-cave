#!/usr/bin/env python3
"""Offline ZIP-to-OpenAPI trial on the included public IMD description."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import zipfile

import api_bundle


def demo():
    baseline_path = Path(__file__).with_name('imd-openapi.json')
    baseline = baseline_path.read_bytes()
    old = json.loads(baseline)
    new = copy.deepcopy(old)
    del new['paths']['/requests/capabilities']['get']['security']
    scratch = Path('test/scratch')
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='api-bundle-demo-', dir=scratch) as directory:
        paths, hashes = [], []
        for name, document in [('old', old), ('new', new)]:
            path = Path(directory) / (name + '.zip')
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr(zipfile.ZipInfo('docs/openapi.json'), json.dumps(document))
            paths.append(path)
            hashes.append(hashlib.sha256(path.read_bytes()).hexdigest())
        report = api_bundle.compare(*paths, member='docs/openapi.json',
                                    old_sha256=hashes[0], new_sha256=hashes[1],
                                    seconds=10, nodes=2, directory_bytes=63)
        rejection = None
        try:
            api_bundle.compare(*paths, member='docs/openapi.json', nodes=1)
        except ValueError as error:
            rejection = str(error)
        directory_rejection = None
        directory_size = report['bundle_inputs']['old']['preflight']['directory_bytes']
        try:
            api_bundle.compare(*paths, member='docs/openapi.json', directory_bytes=directory_size-1)
        except ValueError as error:
            directory_rejection = str(error)
        assert directory_rejection == 'directory byte limit exceeded before ZIP parsing'
        assert rejection == 'filesystem node limit exceeded'
        assert report['counts']['breaking'] == 1
        assert any(f['code'] == 'security_requirement_incompatible' for f in report['findings'])
        return {'demo': 'Hypothetical removal of anonymous access from a captured public API; no service operation called.',
                'baseline_source': 'https://api.imd.fun/openapi.json',
                'baseline_sha256': hashlib.sha256(baseline).hexdigest(),
                'network_used': False, 'files_extracted': 0,
                'directory_bytes_exact': directory_size, 'directory_bytes_too_small': directory_rejection,
                'nodes_1': rejection, 'nodes_2': 'approved archive snapshots compared',
                'comparison': report}


if __name__ == '__main__':
    print(json.dumps(demo(), indent=2))
