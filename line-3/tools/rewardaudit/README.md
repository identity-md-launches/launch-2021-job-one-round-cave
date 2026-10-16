# RewardAudit

RewardAudit explains and checks a saved ZTO reward allocation without calling RewardSplit's allocator or RewardReceipt's recomputation verifier. A reviewer sees each contributor's exact fractional quota, integer floor, remainder and final atomic units, plus any equal-remainder tie crossing the rounding cutoff. It checks the entire original report, including token capture, addresses, row order, value types and display amounts.

One command from the repository root demonstrates it:

```sh
python3 -B line-3/tools/rewardaudit/rewardaudit.py demo
```

Tried here: exit **0**. The included address-free three-role example divides exactly **1 ZTO**, using the inherited real Ethereum ZTO metadata capture. Each quota is `1000000000000000000/3` atomic units; each floor is `333333333333333333`. One atomic unit remains. The three equal `1/3` remainders tie, so ASCII ID order awards that unit to `build`. The audit explains this choice and confirms that the shares sum to `1000000000000000000`. Roles are illustrative; no recipient is invented. The demo uses the allocator to create its input report; the audit itself does not call it.

For a real saved allocation, use your original RewardSplit request and the same metadata capture:

```sh
python3 -B line-3/tools/rewardaudit/rewardaudit.py check \
  --request REQUEST.json --report REPORT.json --output AUDIT.json
```

Produce `REPORT.json` with RewardSplit's `allocate` command, rather than its demo (which adds a demo field). `--metadata PATH` overrides the bundled ZTO capture. Output defaults to stdout; `--output` creates a new workspace file and refuses overwrites. Input/output paths must resolve inside the current working directory, so run from your workspace root. Keep the sibling `rewardsplit` and `rewardreceipt` folders: the delivered tool uses Python 3.9+ and only the standard library, with no install or network needed.

The arithmetic check scales decimal weights to exact integers, then applies `divmod(budget * weight, total_weight)` to obtain each floor and remainder numerator. It requires every reported share to equal its floor plus its boolean award; precisely the leftover number of awards must exist. The worst awarded row must outrank the best unawarded row by remainder and then ASCII ID. This boundary check catches incorrect recipients of rounding units even when conservation and all floor/ceiling bounds still hold. It uses a different checking path from the allocator's fractional-quota sorting, while sharing input validators, decimal rendering and canonical hashing. It is not a fully independent implementation of those helpers.

`cutoff_tie` is an object only when equal remainders straddle the award boundary. It lists every tied ID and which were awarded units. It is `null` for no awards, a strict remainder boundary, or ties wholly on one side. Contributor rows are ordered by ASCII ID and retain zero shares. Fractions use reduced `numerator/denominator` strings, or integer strings when the denominator is one. All token amounts and atomic units use exact decimal strings; no floating point is used.

Limits match the existing pipeline: 1–1000 contributors; positive budget fitting uint256; nonnegative decimal weights with at most 18 whole and 18 fractional digits; strict duplicate-key JSON; 256 KiB per input and formatted audit output. Long rosters can exceed the output limit even when the allocation input fits: the audit refuses rather than truncating its explanation. ZTO is the default token; the inherited validator also supports IMD. The metadata is a historical observation, not a fresh chain query.

Exit **0** means the supplied report passed arithmetic and input agreement checks. Exit **2** means invalid input, disagreement, a limit violation or I/O failure. Ties are explained, not treated as errors. Unsigned hashes identify the supplied objects; they do not authenticate a requester. An audit establishes neither work, identity, entitlement, available balance, authorization nor payment. Nothing reads wallet material, signs, sends, pays or posts.

```sh
python3 -B line-3/tools/rewardaudit/selftest.py
```

All **13 tests** passed. They include 250 seeded small cases checked against exhaustive enumeration of possible award subsets; wrong tie and unequal-remainder winners that preserve the budget; report/header/type/address mutations; zero weights; uint256 precision; output bounds; input permutation; duplicate JSON keys; file-based CLI results and overwrite refusal. A test replaces both inherited allocation/verifier functions with exceptions and confirms that the audit still succeeds.
