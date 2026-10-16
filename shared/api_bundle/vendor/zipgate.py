#!/usr/bin/env python3
"""Reject oversized ZIP directories before SafeZip constructs ZipInfo objects."""
import argparse
import hashlib
import hmac
import json
import math
import os
from pathlib import Path
import re
import stat
import struct
import sys
import time
import zipfile
import zlib

from .safezip import Rejected, local_path, process as safe_process


def positive(name, value):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise Rejected(name + ' must be a positive integer')


def directory_gate(data, *, entries=1000, directory_bytes=2097152,
                   checkpoint=lambda: None):
    """Walk a classic, single-disk ZIP central directory without zipfile parsing.

    No per-entry list, name decoding, decompression or output filesystem access.
    Conservative: no ZIP64, SFX prefix, directory signatures or trailing bytes.
    Returns counts only. This is a resource gate, not payload/path validation.
    """
    positive('entries', entries)
    positive('directory_bytes', directory_bytes)
    checkpoint()
    # Last EOCD signature, matching Python's search policy. A signature inside
    # a comment can cause a conservative refusal, never a fallback ambiguity.
    end = data.rfind(b'PK\x05\x06', max(0, len(data) - 65557))
    if end < 0 or end + 22 > len(data):
        raise Rejected('missing or truncated ZIP end record')
    _, disk, cd_disk, disk_count, count, size, offset, comment = struct.unpack_from(
        '<4s4H2IH', data, end)
    if end + 22 + comment != len(data):
        raise Rejected('ZIP end comment length mismatch or trailing bytes')
    if disk or cd_disk or disk_count != count:
        raise Rejected('multi-disk ZIP not supported')
    # Python looks for this locator even without ZIP64 sentinel values. It
    # must also be refused when hidden inside a member comment/extra field.
    if end >= 20 and data[end-20:end-16] == b'PK\x06\x07':
        raise Rejected('ZIP64 locator not supported')
    if count == 65535 or size == 0xffffffff or offset == 0xffffffff:
        raise Rejected('ZIP64 not supported')
    if count > entries:
        raise Rejected('directory entry limit exceeded before ZIP parsing')
    if size > directory_bytes:
        raise Rejected('directory byte limit exceeded before ZIP parsing')
    if offset + size != end:
        raise Rejected('noncontiguous directory, prefix, or ZIP64 end records')
    if count and (offset < 30 or data[:4] != b'PK\x03\x04'):
        raise Rejected('archive must begin with a local file header')
    if not count and offset:
        raise Rejected('empty ZIP must not have a prefix')
    cursor, actual = offset, 0
    while cursor < end:
        checkpoint()
        if actual >= entries:
            raise Rejected('actual directory entry limit exceeded before ZIP parsing')
        if cursor + 46 > end or data[cursor:cursor+4] != b'PK\x01\x02':
            raise Rejected('invalid or truncated central directory record')
        fields = struct.unpack_from('<4s6H3I5H2I', data, cursor)
        compressed, uncompressed = fields[8:10]
        name_len, extra_len, comment_len, member_disk = fields[10:14]
        local_offset = fields[16]
        next_record = cursor + 46 + name_len + extra_len + comment_len
        if next_record > end:
            raise Rejected('central directory variable fields cross its boundary')
        if member_disk:
            raise Rejected('multi-disk member not supported')
        if 0xffffffff in (compressed, uncompressed, local_offset):
            raise Rejected('ZIP64 member not supported')
        if local_offset + 30 > offset:
            raise Rejected('local header lies outside payload area')
        extra = cursor + 46 + name_len
        extra_end = extra + extra_len
        while extra < extra_end:
            checkpoint()
            if extra + 4 > extra_end:
                raise Rejected('truncated extra field')
            tag, length = struct.unpack_from('<HH', data, extra)
            extra += 4
            if tag == 1:
                raise Rejected('ZIP64 extra field not supported')
            if extra + length > extra_end:
                raise Rejected('extra field crosses its boundary')
            extra += length
        actual += 1
        cursor = next_record
    if actual != count:
        raise Rejected('declared and actual directory entry counts differ')
    checkpoint()
    return {'entries': actual, 'directory_bytes': size, 'zip64': False}


def process(archive_path, output=None, *, entries=1000, directory_bytes=2097152,
            archive_bytes=33554432, nodes=32000, file_bytes=16777216,
            total_bytes=67108864, ratio=200, expected_sha256=None,
            seconds=None, cancelled=None):
    """Gate a bounded snapshot, then run SafeZip only on identical archive bytes."""
    for name, value in [('entries', entries), ('directory_bytes', directory_bytes),
                        ('archive_bytes', archive_bytes), ('nodes', nodes),
                        ('file_bytes', file_bytes), ('total_bytes', total_bytes),
                        ('ratio', ratio)]:
        positive(name, value)
    if expected_sha256 is not None and (not isinstance(expected_sha256, str)
            or re.fullmatch(r'[0-9a-fA-F]{64}', expected_sha256) is None):
        raise Rejected('expected SHA-256 must be exactly 64 hexadecimal characters')
    if seconds is not None:
        try:
            valid = (not isinstance(seconds, bool) and isinstance(seconds, (int, float))
                     and math.isfinite(seconds) and seconds > 0)
        except OverflowError:
            valid = False
        if not valid:
            raise Rejected('seconds must be a finite positive number')
    if cancelled is not None and not callable(cancelled):
        raise Rejected('cancelled must be callable')
    started = time.monotonic()

    def checkpoint():
        if cancelled is not None and cancelled():
            raise Rejected('operation cancelled')
        if seconds is not None and time.monotonic() - started >= seconds:
            raise Rejected('operation time budget exceeded')
        return False

    checkpoint()
    source = local_path(archive_path)
    if not source.is_file() or source.stat().st_size > archive_bytes:
        raise Rejected('archive missing, nonregular, or over archive byte limit')
    data = bytearray()
    digest = hashlib.sha256()
    with source.open('rb') as reader:
        if not stat.S_ISREG(os.fstat(reader.fileno()).st_mode):
            raise Rejected('archive must be regular')
        while True:
            checkpoint()
            chunk = reader.read(min(65536, archive_bytes - len(data) + 1))
            if not chunk:
                break
            if len(data) + len(chunk) > archive_bytes:
                raise Rejected('archive byte limit exceeded while reading')
            data.extend(chunk)
            digest.update(chunk)
    approved = digest.hexdigest()
    if expected_sha256 is not None and not hmac.compare_digest(approved, expected_sha256.lower()):
        raise Rejected('archive SHA-256 differs from approved digest')
    gate = directory_gate(data, entries=entries, directory_bytes=directory_bytes,
                          checkpoint=checkpoint)
    # Release this snapshot before SafeZip takes its own. Its digest check runs
    # before zipfile parsing, so pathname replacement cannot bypass the gate.
    del data
    checkpoint()
    result = safe_process(source, output, entries=entries, archive_bytes=archive_bytes,
                          nodes=nodes, file_bytes=file_bytes, total_bytes=total_bytes,
                          ratio=ratio, expected_sha256=approved, cancelled=checkpoint)
    result['preflight'] = gate
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('inspect', 'extract'))
    parser.add_argument('archive_path')
    parser.add_argument('output', nargs='?')
    for name, default in [('entries', 1000), ('directory-bytes', 2097152),
                          ('archive-bytes', 33554432), ('nodes', 32000),
                          ('file-bytes', 16777216), ('total-bytes', 67108864), ('ratio', 200)]:
        parser.add_argument('--' + name, type=int, default=default)
    parser.add_argument('--sha256', dest='expected_sha256')
    parser.add_argument('--seconds', type=float)
    args = vars(parser.parse_args())
    command = args.pop('command')
    if (command == 'extract') != (args['output'] is not None):
        parser.error('extract requires output; inspect takes no output')
    try:
        result = process(**args)
    except (ValueError, OSError, zipfile.BadZipFile, NotImplementedError,
            RuntimeError, EOFError, zlib.error) as error:
        print(json.dumps({'ok': False, 'error': str(error)}, ensure_ascii=True))
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
