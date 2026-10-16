#!/usr/bin/env python3
"""Gate and extract the bundled real public IMD capture; no network required."""
import hashlib
import json
from pathlib import Path
import tempfile
import zipfile
from zipgate import Rejected, local_path, process


def main():
    source = local_path(Path(__file__).resolve().parents[1] / 'safezip/imd-openapi.json')
    with source.open('rb') as reader:
        payload = reader.read(65537)
    digest = hashlib.sha256(payload).hexdigest()
    if digest != 'be142840c010710cb2a5b9e5c73e71d8e79ec4054c15661699d60bfa627be96a':
        raise ValueError('bundled public capture differs')
    scratch = local_path('test/scratch')
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=scratch, prefix='zipgate-demo-') as temporary:
        root = Path(temporary)
        def pack(name, comment):
            archive_path = root / name
            info = zipfile.ZipInfo('docs/imd/openapi.json')
            info.compress_type = zipfile.ZIP_DEFLATED
            info.comment = comment
            with zipfile.ZipFile(archive_path, 'w') as archive:
                archive.writestr(info, payload)
            return archive_path
        large = pack('large-directory.zip', b'.' * 60000)
        try:
            process(large, root / 'refused', directory_bytes=1024)
        except Rejected as error:
            refusal = str(error)
            assert 'directory byte limit' in refusal
            assert not (root / 'refused').exists()
        else:
            raise AssertionError('large directory accepted')
        ordinary = pack('ordinary.zip', b'')
        approved = hashlib.sha256(ordinary.read_bytes()).hexdigest()
        report = process(ordinary, root / 'unpacked', directory_bytes=1024,
                         entries=1, nodes=3, expected_sha256=approved, seconds=10)
        extracted = (root / 'unpacked/docs/imd/openapi.json').read_bytes()
        assert extracted == payload
        assert report['preflight']['entries'] == 1
        assert not list(root.glob('.safezip-*'))
        print(json.dumps({'ok': True, 'network_used': False,
                          'source': 'https://api.imd.fun/openapi.json',
                          'source_bytes': len(payload), 'source_sha256': digest,
                          'large_directory_refused': refusal,
                          'extracted_bytes_identical': True, 'report': report}, indent=2))


if __name__ == '__main__':
    main()
