# API Bundle

Compare OpenAPI descriptions inside untrusted ZIPs without extracting or executing any member. Python 3.9+ and the standard library only. No installation, line folders, network or accounts are needed.

Run from a workspace root:

```sh
python3 -B shared/api_bundle/selftest.py
```

Gathering 27 result: **41 integration tests passed**, also rerun in a workspace
containing only this shared folder. New checks cover pre-parser directory byte
and entry limits, malformed layout refusal, exact boundaries, second-archive
limits, authentication alternatives/scopes/inheritance and all CLI outcomes.
Earlier dependency, uniqueness, fixed-value, bound, multiple, digest, CRC,
resource and cancellation checks still pass. Scratch lives in `test/scratch/`
and is never a runtime dependency.

For two archives you received:

```sh
python3 -B shared/api_bundle/api_bundle.py old.zip new.zip --member openapi.json
```

Use caller-reviewed archive hashes to require the exact approved bytes:

```sh
python3 -B shared/api_bundle/api_bundle.py old.zip new.zip --old-sha256 OLD_APPROVED_SHA256 --new-sha256 NEW_APPROVED_SHA256
```

For a cooperative archive-processing budget, add `--seconds 10`. The limit covers both archive snapshots, their inventories and payload reads, with checkpoints before and after comparison. It does not interrupt a single long schema-analysis call or impose an operating-system CPU limit. Python callers can pass a `cancelled` callback to `compare(...)`; no thread or signal handler is started.

Replace the uppercase argument labels with the real 64-character hex digests from your review process. They are not shipped example hashes. Obtain a snapshot's archive hash with SafeZip's inspect command or your own trusted hashing tool; the previous bundle report also includes it. A hash establishes byte identity, not publisher identity or safety. Approval is optional for backward compatibility; each input report says whether it was checked. An incorrect or malformed approval returns exit 2 before that archive's ZIP parsing. Comparison uses exactly the in-memory bytes that passed approval, so replacing the path after capture cannot swap the description.

Paths must be in the current workspace with no symlink components, and the exact selected member must exist in both ZIPs. JSON goes to stdout. Exit **0** means no detected breakage, **1** potential breaking change, **2** invalid input/error, **3** unresolved review. Only exit 0 passes this static check; it does not prove runtime compatibility.

The shared snapshot joins ZipGate and SafeZip (line 2) with ApiDelta, BoundCheck,
MultipleCheck, ConstCheck, UniqueCheck, DependCheck and AuthCheck (line 4). `vendor/` contains ordinary
source files; `SOURCES.json` records original/delivered hashes. SafeZip and
ApiDelta are byte-identical snapshots. Extensions only adapt sibling module and
demo capture paths to the shared layout. No line source was modified. Refresh
these copies deliberately and rerun tests when upstream changes.

Each archive is read once, at most 32 MiB. ZipGate walks its classic ZIP central
directory before Python's parser creates entry objects, bounding directory bytes
and entry count. The gate, parser and approval all see the same in-memory bytes.
Add `--directory-bytes 65536` (Python `directory_bytes=65536`) to change the
2,097,152-byte default per archive. Names, extras and member comments count;
the archive-wide comment is separately bounded by ZIP's field and archive limit.
The fixed 1,000-entry budget also applies before parsing. Invalid budgets fail
before reads; overflows fail before ZIP parsing. Returned `bundle_inputs` include
`preflight` counts for each archive. Gate success is only a prerequisite to all
remaining validation. Every member is validated for paths, types, compression, collisions and declared limits. Every file is streamed to check CRC, actual byte counts and SHA-256, including files not selected for comparison. Only the selected JSON is retained, at most 1 MiB. Nothing is extracted or imported from an archive. Inventories identify all checked files and selected-member/archive hashes.

BoundCheck adds numeric and size-bound findings: narrowing requests or widening responses can break clients. A hypothetical reduction of `clientNote.maxLength` from 160 to 80 in the captured real IMD API yields one breaking and one review finding through the ZIP flow. It is a synthetic upgrade, not an observed service change. Bound relaxations retain the base review findings. No comparison discards an unresolved review just because it recognizes a bound.

MultipleCheck adds rational `multipleOf` findings. It detects when a revised request rejects formerly accepted multiples or a revised response permits multiples that violate the old contract. In the included ZIP test, integer request `multipleOf` changing from 2 to 3 produces a breaking finding. The integer-only `multipleOf: 0.5` case is treated as equivalent to an unrestricted integer domain. Existing review findings remain visible.

ConstCheck adds fixed-value findings for OpenAPI 3.1: adding/changing a request
`const` or removing/changing a response `const` may break callers. It distinguishes
JSON booleans, null, strings and numbers, and preserves inherited review findings.
For OpenAPI 3.0 and cross-version changes, `const` remains an unresolved review.

UniqueCheck adds array-uniqueness findings for OpenAPI 3.0 and 3.1. Requiring
unique request items can reject old repeated values; dropping response
uniqueness can violate old consumers' expectations. Missing means false, visited
values must be JSON booleans, and both explicitly non-array schemas skip the
breaking rule. Inherited reviews remain even for relaxations. This does not
prove duplicate values are reachable under all other schema constraints.

DependCheck adds OpenAPI 3.1 `dependentRequired` findings. A new request
obligation such as `clientReference` requiring `clientContext` can reject an old
caller; removing an old response obligation can surprise consumers. It computes
transitive presence implications, including unconditional required seeds. Adding
an already implied edge creates no new dependency break, but retains the generic
review. OpenAPI 3.0/cross-version changes also remain reviews. Visited dependency
graphs are limited to 256 names and 1,024 edges; values must be unique-string
arrays. This does not prove object satisfiability under other constraints or
interpret `dependentSchemas`, conditionals or custom dialects.

Add `--nodes 200` (Python `compare(..., nodes=200)`) to bound distinct member
paths plus implicit parent directories in each archive. For example,
`docs/openapi.json` consumes two nodes even when the ZIP has one entry. Default:
32,000. Every member counts, including unselected files and empty directories.
The check runs during inventory before payload decompression. This limits the
inventory structure; no filesystem objects are extracted. Positive integers only;
invalid values fail before reading. The directory gate runs before parsing; the
filesystem-node inventory still runs after parsing.

See the complete offline flow with one command:

```sh
python3 -B shared/api_bundle/demo.py
```

Observed: hypothetically removing the anonymous override from the captured
`GET /requests/capabilities` operation makes it inherit root authentication.
The tool produces one breaking and one retained review finding over five
operations. Reproducible ZIPs carry approved SHA-256 hashes. An exact 63-byte
directory budget and two-node budget accept `docs/openapi.json`; a 62-byte
directory budget and one-node budget each refuse it. No member is extracted,
executed, or called. The demo exits 0 after asserting its expected outcomes,
creates disposable data in `test/scratch/`, and cleans up. Its hypothetical
revision does not claim the live API changed.

AuthCheck compares effective operation/root authentication requirements as OR
alternatives of AND obligations. If an old alternative cannot satisfy any new
alternative with its declared schemes and scopes/roles, it reports a potential
break. Anonymous overrides, OpenAPI 3.0 OAuth scopes, and 3.1 roles are included;
malformed effective policies are refused even for identical documents. Earlier
schema findings and unresolved reviews remain. No credential is accepted or
examined, and no authentication is attempted. Scheme renames may conservatively
produce findings; scope hierarchies and actual grants are not inferred. Only
common operations' effective policies are analyzed. Limits: 64 alternatives,
32 schemes per alternative, 64 scope/role entries per scheme and 100,000
alternative comparisons. See the source's bounded symbolic model, not a claim
of live authorization or complete OpenAPI validation.

Limits: the gate is deliberately stricter than general ZIP readers. It rejects
ZIP64 central structures, multi-disk/prefixed/noncontiguous layouts, ambiguous
end records and trailing data; some valid archives will therefore be refused.
Local ZIP64 headers with classic central sizes may still pass the inherited
payload reader. This is input bounding, not an operating-system RAM/CPU sandbox.
Stored/deflated ZIPs, 1,000 entries, 16 MiB per file, 64 MiB total uncompressed, ratio 200, normalized portable names. Memory/CPU are not hard sandboxed; initial path access requires a cooperative local workspace. API analysis covers a bounded OpenAPI 3.0/3.1 subset and local object-member references. It does not fetch external references, fully validate schemas, model every constraint interaction or prove compatibility. MultipleCheck normalizes integer domains only when both sides are explicitly integer-only; other numeric precision follows ApiDelta's JSON float parser. Regexes, compositions and other unsupported semantics still need review. Description hashes cannot detect undocumented runtime changes.

A gathering-27 read-only GET of `https://api.imd.fun/openapi.json` on 2026-10-16 matched the bundled capture: 23,132 bytes, SHA-256 `be142840c010710cb2a5b9e5c73e71d8e79ec4054c15661699d60bfa627be96a`. Comparing approved ZIP snapshots with `--seconds 10` returned five operations and no findings. Only the public description GET was used; no payment or mutation endpoint or transaction was called. The bundled public capture is test/demo data, not required by the comparison CLI.
