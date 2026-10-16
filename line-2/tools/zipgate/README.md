# ZipGate

Check central-directory resource limits **before** Python's ZIP parser creates
its list of entries, then use the existing SafeZip to inspect every payload or
publish a bounded extraction. Python 3.9+ standard library only, plus the shipped
sibling `../safezip/safezip.py`. Keep both folders together. No installation,
network, wallet, environment access or transaction is involved.

From the workspace root, run this offline demonstration:

```sh
python3 -B line-2/tools/zipgate/demo.py
```

Tried here: the real bundled IMD public API description (23,132 bytes; provenance
in `../safezip/sample-source.json`) was wrapped in two ZIPs. One with a 60,000-byte
member comment was rejected against a 1,024-byte directory budget, before ZIP
parsing or staging. The ordinary one passed with one entry, 67 directory bytes
and three filesystem nodes, extracted with an approved SHA-256 and matched the
capture byte-for-byte. No API endpoint was called. These are historical public
bytes, not a fresh observation of the service.

Run the adversarial checks:

```sh
python3 -B line-2/tools/zipgate/selftest.py
```

Tried here: **28 tests passed**, including 50 seeded valid layouts and every
truncation of a simple archive. Refusal tests replace `ZipFile` with a failing
sentinel to verify the parser is never reached for excessive or false entry
counts, directory byte overflows, malformed records/extra fields, ZIP64,
multi-disk layouts, prefixes, ambiguous comments and trailing bytes. Integration
checks cover stored/deflated extraction, empty ZIPs, exact budget boundaries,
replacement between gate and parser, CRC corruption, traversal, cancellation,
invalid options and CLI exits. The 76 inherited SafeZip/ZipAudit/ZipDiff tests
also passed unchanged.

## Use

For your own archive in the current workspace:

```sh
python3 -B line-2/tools/zipgate/zipgate.py inspect incoming.zip --entries 100 --directory-bytes 65536
python3 -B line-2/tools/zipgate/zipgate.py extract incoming.zip unpacked --sha256 APPROVED_SHA256 --directory-bytes 65536
```

Replace `APPROVED_SHA256` with the exact 64-hex digest from an inventory you have
reviewed; it is not a shipped value. Inspect writes nothing. Extract requires a
new destination whose parent already exists. Success prints JSON and exits 0;
refusal, damage or I/O failure prints `ok: false` and exits 2. Output includes the
ordinary SafeZip inventory and `preflight` counts. Merely passing the preflight
is **not** success: SafeZip still checks names, types, collisions, decompression,
CRC, hashes and extraction limits. Empty ZIPs are allowed.

The API is `zipgate.process(path, output=None, **limits)`. Defaults:

| Option / API name | Default |
| --- | ---: |
| `--directory-bytes` / `directory_bytes` | 2,097,152 |
| `--entries` / `entries` | 1,000 |
| `--archive-bytes` / `archive_bytes` | 33,554,432 |
| `--nodes` / `nodes` | 32,000 |
| `--file-bytes` / `file_bytes` | 16,777,216 |
| `--total-bytes` / `total_bytes` | 67,108,864 |
| `--ratio` / `ratio` | 200 |

`--sha256` maps to `expected_sha256`; it is optional. `--seconds` / `seconds`
covers both the gate and SafeZip with one cooperative monotonic budget. The API
also accepts a fast, nonmutating `cancelled` callback. All count/byte/ratio limits
are strictly positive integers; booleans are refused. Paths must remain inside
the current workspace, without symlinks. Nothing in an archive is executed.

## How it bounds parsing

The gate captures at most `archive_bytes` bytes, searches the bounded ZIP end
record region and checks the declared directory byte/count budgets. It then
walks fixed headers and length-delimited fields without retaining names or
per-entry objects. Actual entry count must match the declaration and stay within
the entry budget. Directory bytes include headers, names, extras and member
comments; the archive-wide comment is separately bounded by ZIP's 65,535-byte
field and the archive byte budget.

Only classic, single-disk ZIPs with a contiguous directory/end record and no
executable prefix are supported; ZIP64 locators (even hidden in comments), sentinel values and ZIP64 central extra
fields are rejected. Archives using ZIP64 local headers alone may still be
accepted if their central directory uses classic sizes and offsets: local headers
are handled by SafeZip/Python. Digital signatures, trailing bytes and embedded
end-record signatures in comments may be conservatively rejected. The classic
end-record sentinel reserves 65,535, so at most 65,534 entries are supported.
Stored and deflated payloads remain SafeZip's supported formats.

The first snapshot is released, then SafeZip captures the source again and
requires the gate's exact digest **before parsing**. Replacing the source cannot
substitute an ungated archive. A caller's optional approved digest binds both
phases to their reviewed bytes. Digests do not authenticate a publisher.

This limits the inputs to Python's directory parser, not exact RAM or elapsed
time. Snapshot buffers, interpreter objects and the parser still have overhead;
this is not an operating-system sandbox. A single I/O/parser/decompression call
can overrun a cooperative deadline. Use a cooperative workspace with no hostile
concurrent path mutation; SafeZip's staging, atomic publication and race
limitations still apply. The gate makes deliberately stricter format choices;
useful valid archives may be refused. It does not inspect nested archives or
establish that extracted content is safe to execute. No coin is needed.
