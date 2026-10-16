# AuthCheck

Detect potential breaking changes to OpenAPI authentication requirements before
updating an integration. Python 3.9+, standard library only, offline by default.
Keep the six sibling tool folders alongside this one; no installation is needed.

From the repository root, one command shows it working:

```sh
python3 -B line-4/tools/authcheck/authcheck.py demo
```

The demonstration uses the bundled **real public IMD OpenAPI description**. Its
`GET /requests/capabilities` operation explicitly permits anonymous requests.
The demo removes that override in memory, making the operation inherit the
description's real root security requirements. It reports **one potential break
and one retained review**, across five operations, and exits 0. This proposed
change is hypothetical; no API operation or authentication attempt is performed.

Compare your saved descriptions:

```sh
python3 -B line-4/tools/authcheck/authcheck.py compare line-4/tools/apidelta/imd-openapi.json line-4/live-openapi-27.json
```

Replace the two filenames with old and proposed JSON descriptions. Paths must
resolve inside the current working directory. The deterministic report includes
both exact input-byte SHA-256 hashes, findings and escaped operation locations.

| Exit | Meaning |
| --- | --- |
| 0 | No detected breakage, or successful demonstration |
| 1 | Potential breaking change |
| 2 | Invalid/unsupported input, file error or resource limit |
| 3 | Unresolved review findings without a detected break |

Only exit 0 is an automated pass within the supported subset; it does not prove
runtime compatibility. A successful demo deliberately exits 0 despite its
illustrative breaking finding.

## What it checks

A security array is a list of alternatives. Each alternative requires every
named scheme and all its listed scopes or roles. The operation's `security`
overrides the root declaration; `[]` removes authentication requirements, and
`{}` inside the array permits anonymous access. An absent declaration defaults
to no declared requirement. Path-item security is not an inheritance level.
These rules follow the official
[OpenAPI 3.1 Security Requirement Object](https://spec.openapis.org/oas/v3.1.0.html#security-requirement-object)
and [Operation Object](https://spec.openapis.org/oas/v3.1.0.html#operation-object).

For every old alternative, AuthCheck asks whether some new alternative requires
only a subset of its obligations. If none does, clients satisfying just that
old alternative may be rejected. For example, changing `[{"a":[]},{"b":[]}]`
to `[{"a":[],"b":[]}]` removes the ability to use either scheme alone.
Adding an OAuth scope can also exclude previously sufficient authorization.
Reordering, duplicate labels, and adding redundant alternatives do not produce
new authentication-breaking findings. The earlier generic review remains.

OAuth2 and OpenID Connect scopes are supported in OpenAPI 3.0.x and 3.1.x.
For other scheme types, 3.0 requires empty arrays; 3.1 permits role names.
Mutual TLS is accepted only in 3.1. Local scheme references are resolved for
type checks, including escaped names; remote references are never fetched.
All earlier DependCheck, UniqueCheck, ConstCheck, MultipleCheck, BoundCheck
and ApiDelta analyses remain active.

## Limits and interpretation

This is symbolic static comparison, not an authentication client, security audit,
full OpenAPI validator, or authorization test. It never accepts actual credentials.
Scheme names are distinct identifiers: renamed schemes or different names that
alias the same definition can conservatively produce potential breaks. It does
not infer equivalence from similar scheme descriptions, scope/role hierarchies,
token issuers, flows, endpoints, header names, or runtime grants. Changes to scheme
definitions still receive inherited document reviews, even when requirements
retain the same names. Missing declarations do not prove a live endpoint is public.

Only effective policies of operations present in both descriptions are analyzed.
Unused/overridden policies and newly added operations are not fully validated.
The older tools still handle added/removed operations and metadata. Declared
scheme type and security-array shapes are checked, but complete scheme-specific
required fields and OAuth flow validity are outside this tool's scope. Changed
or unvisited schemas retain the earlier tools' limitations.

Effective policies are limited to 64 alternatives, 32 schemes per alternative,
64 scope/role entries per scheme, and 100,000 alternative comparisons per run.
Malformed effective policies fail even if old and new documents are identical.
Inherited limits also apply: 1 MiB files, 50,000 nodes, depth 80, 20,000 schema
visits and 2,000 findings. Limit failures return 2, never a partial pass.

## What happened when tried

On 2026-10-16:

- All **13 new tests passed**, including an independent finite authorization
  oracle comparing **65,536 pairs of policies** against 20 possible holders of
  symbolic scheme/scope obligations. No actual credentials were involved.
- All **103 inherited tests passed** unchanged. Integration cases cover global
  inheritance, operation overrides, AND/OR direction, OAuth scopes, 3.1 roles,
  malformed inputs, local references, limits, all CLI exits, exact hashes, and
  preservation of inherited findings.
- The demo returned one breaking finding and one review over five operations.
- A read-only GET of `https://api.imd.fun/openapi.json` with User-Agent
  `Pepeolithic-AuthCheck/27.0` returned HTTP 200 and 23,132 bytes. Its SHA-256
  matched the bundled capture; comparison found five operations and zero findings.
  [The capture](../../live-openapi-27.json) and
  [dated observation](../../live-check-27.json) are included for offline use.

Run the regressions with:

```sh
python3 -B line-4/tools/authcheck/selftest.py
```

The runtime reads only supplied workspace descriptions and sibling Python source.
It has no network, environment, wallet, signature, transaction or payment code.
No coin or price is needed for static API-description analysis.
