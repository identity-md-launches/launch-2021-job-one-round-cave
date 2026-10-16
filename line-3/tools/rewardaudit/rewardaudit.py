#!/usr/bin/env python3
"""Explain and independently check largest-remainder reward rounding, offline."""

import argparse
from fractions import Fraction
import importlib.util
import json
from pathlib import Path
import re
import sys

SPEC = importlib.util.spec_from_file_location(
    "rewardreceipt", Path(__file__).resolve().parents[1] / "rewardreceipt" / "rewardreceipt.py")
rr = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rr)
rs = rr.rs
SCALE = 10 ** 18


def equal(actual, expected, label):
    rs.require(rr.canonical_bytes(actual) == rr.canonical_bytes(expected), label)


def audit(request, report, metadata):
    """Check exact integer quotas and the winner/loser boundary, without allocate()."""
    decimals = rs.validate_metadata(metadata)
    rs.require(isinstance(request, dict) and set(request) == {"budget", "contributors"},
               "request needs exactly budget and contributors")
    budget = rs.token_units(request["budget"], decimals)
    inputs = request["contributors"]
    rs.require(isinstance(inputs, list) and 1 <= len(inputs) <= 1000,
               "contributors must contain 1 to 1000 rows")
    parsed, ids, addresses = [], set(), set()
    for row in inputs:
        rs.require(isinstance(row, dict) and {"id", "weight"} <= set(row)
                   <= {"id", "weight", "address"}, "invalid contributor fields")
        identifier = row["id"]
        rs.require(isinstance(identifier, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", identifier),
                   "invalid contributor id")
        rs.require(identifier not in ids, "duplicate contributor id")
        ids.add(identifier)
        recipient = rs.address(row["address"]) if "address" in row else None
        rs.require(recipient is None or recipient not in addresses, "duplicate recipient address")
        if recipient:
            addresses.add(recipient)
        weight = rs.weight(row["weight"])
        scaled = weight * SCALE
        rs.require(scaled.denominator == 1, "weight exceeds supported precision")
        parsed.append((identifier, scaled.numerator, recipient, weight))
    parsed.sort()
    total = sum(row[1] for row in parsed)
    rs.require(total > 0, "at least one weight must be positive")
    quotas = [divmod(budget * row[1], total) for row in parsed]
    leftover = budget - sum(q[0] for q in quotas)
    rs.require(isinstance(report, dict), "report must be an object")
    header = {
        "schema": "rewardsplit-allocation-v1",
        "purpose": "allocation only; no transaction, balance check, or promise of payment",
        "token": {key: metadata[key] for key in ("chain_id", "address", "symbol", "decimals", "block_number", "block_hash")},
        "budget_units": str(budget),
        "budget_amount": rs.display_units(budget, decimals),
        "method": "largest remainder; equal remainders ordered by ASCII contributor id",
        "rounding_units_distributed": leftover,
        "unallocated_units": "0",
        "all_recipients_supplied": all(row[2] is not None for row in parsed),
    }
    equal({k: v for k, v in report.items() if k != "allocations"}, header,
          "report header differs from request and token capture")
    rows = report.get("allocations")
    rs.require(isinstance(rows, list) and len(rows) == len(parsed), "allocation row count differs")
    winners, losers, explanations = [], [], []
    for row, (identifier, scaled, recipient, weight), (floor, remainder) in zip(rows, parsed, quotas):
        rs.require(isinstance(row, dict) and type(row.get("rounding_unit_awarded")) is bool,
                   "rounding award must be a boolean")
        award = row["rounding_unit_awarded"]
        expected = {"id": identifier, "weight_fraction": str(weight),
                    "units": str(floor + int(award)),
                    "amount": rs.display_units(floor + int(award), decimals),
                    "rounding_unit_awarded": award}
        if recipient is not None:
            expected["address"] = recipient
        equal(row, expected, "allocation row differs from its exact quota floor plus award")
        # A winner must precede every loser by remainder, then ASCII id.
        (winners if award else losers).append((-remainder, identifier))
        explanations.append({"id": identifier,
                             "quota_units_fraction": str(Fraction(budget * scaled, total)),
                             "floor_units": str(floor),
                             "remainder_fraction": str(Fraction(remainder, total)),
                             "rounding_unit_awarded": award, "units": row["units"]})
    rs.require(len(winners) == leftover, "wrong number of rounding units awarded")
    rs.require(not winners or not losers or max(winners) < min(losers),
               "rounding winner loses to an unawarded row by remainder or ASCII id")
    rs.require(sum(int(row["units"]) for row in rows) == budget, "units do not conserve budget")
    cutoff = None
    if winners and losers and max(winners)[0] == min(losers)[0]:
        numerator = -max(winners)[0]
        tied = [row[0] for row, quota in zip(parsed, quotas) if quota[1] == numerator]
        awarded = sorted(key[1] for key in winners if -key[0] == numerator)
        cutoff = {"remainder_fraction": str(Fraction(numerator, total)),
                  "tied_ids": tied, "awarded_ids": awarded,
                  "rule": "ascending ASCII contributor id"}
    result = {
        "schema": "rewardaudit-v1",
        "result": "verified exact quota floors, remainder boundary and conservation",
        "token": header["token"], "budget_units": str(budget),
        "floor_total_units": str(sum(q[0] for q in quotas)),
        "rounding_units": leftover, "cutoff_tie": cutoff,
        "request_sha256": rr.digest(request), "report_sha256": rr.digest(report),
        "metadata_sha256": rr.digest(metadata), "contributors": explanations,
        "scope": "offline arithmetic only; shared input validators, independent integer quota check; no entitlement, identity, balance or payment proof",
    }
    rs.require(len((json.dumps(result, indent=2, ensure_ascii=True) + "\n").encode()) <= rs.MAX_BYTES,
               "audit exceeds 256-KiB output limit")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("demo", help="explain the included real-ZTO three-role rounding tie")
    check = sub.add_parser("check", help="check a saved allocation against the original request")
    check.add_argument("--request", required=True)
    check.add_argument("--report", required=True)
    check.add_argument("--metadata", default=str(rr.ROOT / "zto-mainnet.json"))
    check.add_argument("--output", help="new workspace JSON file; refuses overwrite")
    args = parser.parse_args(argv)
    try:
        if args.command == "demo":
            request = rs.read_json(rr.ROOT / "example.json")
            metadata = rs.read_json(rr.ROOT / "zto-mainnet.json")
            report = rs.allocate(request, metadata)
        else:
            request = rs.read_json(args.request)
            metadata = rs.read_json(args.metadata)
            report = rs.read_json(args.report)
        rs.write_json(audit(request, report, metadata), getattr(args, "output", None))
    except (rs.Invalid, OSError, ValueError, OverflowError, RecursionError) as exc:
        print("rewardaudit: " + (str(exc) if isinstance(exc, rs.Invalid) else type(exc).__name__), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
