#!/usr/bin/env python3
"""Adversarial pre-parser gates and end-to-end extraction checks, offline."""
import hashlib
import io
import json
from pathlib import Path
import random
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import zipgate as gate


def packed(items=(('a', b'hello'),), compression=zipfile.ZIP_STORED, extra=b'', comment=b''):
    data = io.BytesIO()
    with zipfile.ZipFile(data, 'w', compression=compression) as archive:
        for name, payload in items:
            info = zipfile.ZipInfo(name)
            info.compress_type = compression
            info.extra = extra
            archive.writestr(info, payload)
        archive.comment = comment
    return bytearray(data.getvalue())


class GateTests(unittest.TestCase):
    def setUp(self):
        scratch = gate.local_path('test/scratch')
        scratch.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=scratch, prefix='zipgate-tests-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'input.zip'
        self.output = self.root / 'out'

    def save(self, data):
        self.source.write_bytes(data)
        return self.source

    def refuse_before_parser(self, data, **kwargs):
        self.save(data)
        with patch.object(zipfile, 'ZipFile', side_effect=AssertionError('parser reached')):
            with self.assertRaises(gate.Rejected):
                gate.process(self.source, self.output, **kwargs)
        self.assertFalse(self.output.exists())
        self.assertFalse(list(self.root.glob('.safezip-*')))

    def test_stored_and_deflated_extract(self):
        for compression in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
            data = packed((('docs/a', b'hello'), ('empty/', b'')), compression)
            self.save(data)
            result = gate.process(self.source, self.output, entries=2, nodes=3,
                                  expected_sha256=hashlib.sha256(data).hexdigest().upper())
            self.assertEqual((self.output / 'docs/a').read_bytes(), b'hello')
            self.assertTrue((self.output / 'empty').is_dir())
            self.assertEqual(result['preflight']['entries'], 2)
            self.assertTrue(result['content_checked'])
            import shutil
            shutil.rmtree(self.output)

    def test_empty_archive(self):
        result = gate.process(self.save(packed(())), self.output)
        self.assertEqual(result['preflight']['entries'], 0)
        self.assertEqual(list(self.output.iterdir()), [])

    def test_exact_directory_boundary(self):
        data = packed()
        size = gate.directory_gate(data)['directory_bytes']
        self.assertEqual(gate.directory_gate(data, directory_bytes=size)['entries'], 1)
        self.refuse_before_parser(data, directory_bytes=size - 1)

    def test_declared_entry_limit(self):
        self.refuse_before_parser(packed((('a', b''), ('b', b''))), entries=1)

    def test_spoofed_count_low(self):
        data = packed((('a', b''), ('b', b'')))
        end = data.rfind(b'PK\x05\x06')
        struct.pack_into('<HH', data, end + 8, 1, 1)
        self.refuse_before_parser(data, entries=1)
        self.refuse_before_parser(data, entries=10)

    def test_spoofed_count_high(self):
        data = packed()
        end = data.rfind(b'PK\x05\x06')
        struct.pack_into('<HH', data, end + 8, 2, 2)
        self.refuse_before_parser(data)

    def test_trailing_bytes(self):
        self.refuse_before_parser(packed() + b'trailer')

    def test_truncation_every_offset(self):
        data = packed()
        for length in range(len(data)):
            with self.subTest(length=length), self.assertRaises(gate.Rejected):
                gate.directory_gate(data[:length])

    def test_comments_and_unknown_extra(self):
        data = packed(extra=struct.pack('<HH3s', 0xcafe, 3, b'abc'), comment=b'plain comment')
        self.assertTrue(gate.process(self.save(data))['content_checked'])
        self.assertEqual(gate.directory_gate(packed(comment=b'x' * 65535))['entries'], 1)

    def test_ambiguous_comment_refused(self):
        self.refuse_before_parser(packed(comment=b'PK\x05\x06' + b'x' * 22))

    def test_multidisk(self):
        for index in (4, 6, 8):
            data = packed()
            end = data.rfind(b'PK\x05\x06')
            struct.pack_into('<H', data, end + index, 2)
            self.refuse_before_parser(data)
        data = packed()
        struct.pack_into('<H', data, data.find(b'PK\x01\x02') + 34, 1)
        self.refuse_before_parser(data)

    def test_zip64_markers(self):
        for index, fmt, value in ((10, '<H', 65535), (12, '<I', 0xffffffff), (16, '<I', 0xffffffff)):
            data = packed()
            struct.pack_into(fmt, data, data.rfind(b'PK\x05\x06') + index, value)
            self.refuse_before_parser(data)
        for index in (20, 24, 42):
            data = packed()
            struct.pack_into('<I', data, data.find(b'PK\x01\x02') + index, 0xffffffff)
            self.refuse_before_parser(data)
        self.refuse_before_parser(packed(extra=struct.pack('<HH', 1, 0)))

    def test_zip64_locator_hidden_in_member_comment(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            info = zipfile.ZipInfo('a')
            info.comment = struct.pack('<4sIQI', b'PK\x06\x07', 0, 0, 1)
            archive.writestr(info, b'hello')
        self.refuse_before_parser(buffer.getvalue())

    def test_directory_variable_fields(self):
        for index in (28, 30, 32):
            data = packed()
            struct.pack_into('<H', data, data.find(b'PK\x01\x02') + index, 65535)
            self.refuse_before_parser(data)

    def test_directory_signature(self):
        data = packed()
        data[data.find(b'PK\x01\x02')] = 0
        self.refuse_before_parser(data)

    def test_directory_offset_and_size(self):
        for index in (12, 16):
            data = packed()
            end = data.rfind(b'PK\x05\x06')
            value = struct.unpack_from('<I', data, end + index)[0]
            struct.pack_into('<I', data, end + index, value + 1)
            self.refuse_before_parser(data)

    def test_bad_local_offset(self):
        data = packed()
        struct.pack_into('<I', data, data.find(b'PK\x01\x02') + 42, len(data))
        self.refuse_before_parser(data)

    def test_malformed_extra(self):
        for extra in (b'x', struct.pack('<HH', 17, 10)):
            self.refuse_before_parser(packed(extra=extra))

    def test_sfx_prefix(self):
        self.refuse_before_parser(b'executable' + packed())

    def test_invalid_limits(self):
        self.save(packed())
        for name in ('entries', 'directory_bytes', 'archive_bytes', 'nodes', 'file_bytes', 'total_bytes', 'ratio'):
            for value in (0, -1, True, 1.5, '4', float('nan')):
                with self.subTest(name=name, value=value), self.assertRaises(gate.Rejected):
                    gate.process(self.source, **{name: value})
        for value in (0, True, float('inf'), float('nan'), -1, 10**1000):
            with self.assertRaises(gate.Rejected):
                gate.process(self.source, seconds=value)
        with self.assertRaises(gate.Rejected):
            gate.process(self.source, cancelled=False)

    def test_archive_byte_boundary(self):
        data = packed()
        self.assertTrue(gate.process(self.save(data), archive_bytes=len(data))['ok'])
        self.refuse_before_parser(data, archive_bytes=len(data)-1)

    def test_digest_rejected_before_parser(self):
        for digest in ('f' * 64, 'bad', 2):
            self.refuse_before_parser(packed(), expected_sha256=digest)

    def test_replacement_cannot_bypass_gate(self):
        self.save(packed())
        original = gate.safe_process
        replacement = packed((('../escape', b'bad'),))
        def replaced(*args, **kwargs):
            self.source.write_bytes(replacement)
            with patch.object(zipfile, 'ZipFile', side_effect=AssertionError('parser reached')):
                return original(*args, **kwargs)
        with patch.object(gate, 'safe_process', side_effect=replaced):
            with self.assertRaisesRegex(gate.Rejected, 'SHA-256'):
                gate.process(self.source, self.output)
        self.assertFalse(self.output.exists())

    def test_content_corruption_still_checked(self):
        data = packed()
        data[31] ^= 1  # First payload byte in stored entry named 'a'.
        self.save(data)
        with self.assertRaises(zipfile.BadZipFile):
            gate.process(self.source, self.output)
        self.assertFalse(self.output.exists())
        self.assertFalse(list(self.root.glob('.safezip-*')))

    def test_path_rejection_still_checked(self):
        self.save(packed((('../escape', b'bad'),)))
        with self.assertRaises(gate.Rejected):
            gate.process(self.source, self.output)
        self.assertFalse((self.root / 'escape').exists())

    def test_cancellation_and_deadline(self):
        self.save(packed())
        with self.assertRaisesRegex(gate.Rejected, 'cancelled'):
            gate.process(self.source, cancelled=lambda: True)
        with patch.object(gate.time, 'monotonic', side_effect=[0, 2]):
            with self.assertRaisesRegex(gate.Rejected, 'time budget'):
                gate.process(self.source, seconds=1)
        with self.assertRaisesRegex(gate.Rejected, 'cancelled'):
            def stop():
                raise gate.Rejected('cancelled during directory scan')
            gate.directory_gate(packed(), checkpoint=stop)

    def test_seeded_many_valid_layouts(self):
        rng = random.Random(737)
        for _ in range(50):
            count = rng.randrange(12)
            items = [(f'folder/f{i}', rng.randbytes(rng.randrange(60))) for i in range(count)]
            data = packed(items, rng.choice([zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED]))
            self.assertEqual(gate.directory_gate(data, entries=max(1, count))['entries'], count)
            self.assertEqual(len(gate.process(self.save(data))['entries']), count)

    def test_cli(self):
        self.save(packed())
        script = str(Path(gate.__file__))
        for options, code in (([], 0), (['--directory-bytes', '1'], 2)):
            result = subprocess.run([sys.executable, '-B', script, 'inspect', str(self.source), *options],
                                    capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, code, result.stderr)
            self.assertEqual(json.loads(result.stdout)['ok'], code == 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
