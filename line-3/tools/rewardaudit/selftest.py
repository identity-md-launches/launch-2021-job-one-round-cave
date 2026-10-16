#!/usr/bin/env python3
"""Behavioral, mutation and exhaustive-small-case checks; standard library only."""
import copy
from fractions import Fraction
import itertools
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import rewardaudit as ra


class AuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.metadata = ra.rs.read_json(ra.rr.ROOT / "zto-mainnet.json")
        cls.example = ra.rs.read_json(ra.rr.ROOT / "example.json")

    def report(self, request=None, metadata=None):
        return ra.rs.allocate(request or self.example, metadata or self.metadata)

    def test_demo_quota_and_ascii_tie(self):
        result = ra.audit(self.example, self.report(), self.metadata)
        self.assertEqual(result["budget_units"], "1000000000000000000")
        self.assertEqual(result["floor_total_units"], "999999999999999999")
        self.assertEqual(result["rounding_units"], 1)
        self.assertEqual(result["cutoff_tie"]["tied_ids"], ["build", "research", "review"])
        self.assertEqual(result["cutoff_tie"]["awarded_ids"], ["build"])
        self.assertEqual(result["contributors"][0]["quota_units_fraction"], "1000000000000000000/3")
        self.assertEqual(result["contributors"][0]["remainder_fraction"], "1/3")

    def test_independent_of_allocator(self):
        report = self.report()
        with patch.object(ra.rs, "allocate", side_effect=AssertionError("allocator called")), \
                patch.object(ra.rr, "verify", side_effect=AssertionError("receipt verifier called")):
            self.assertEqual(ra.audit(self.example, report, self.metadata)["rounding_units"], 1)

    def test_wrong_tie_winner_preserving_total(self):
        report = self.report()
        a, b = report["allocations"][:2]
        for row, units, award in ((a, int(a["units"]) - 1, False),
                                  (b, int(b["units"]) + 1, True)):
            row.update(units=str(units), amount=ra.rs.display_units(units, 18), rounding_unit_awarded=award)
        with self.assertRaisesRegex(ra.rs.Invalid, "winner loses"):
            ra.audit(self.example, report, self.metadata)

    def test_wrong_remainder_winner(self):
        request = {"budget": "0.000000000000000001", "contributors": [
            {"id": "a", "weight": "1"}, {"id": "z", "weight": "2"}]}
        report = self.report(request)
        for row in report["allocations"]:
            winner = row["id"] == "a"
            row.update(units=str(int(winner)), amount=ra.rs.display_units(int(winner), 18),
                       rounding_unit_awarded=winner)
        with self.assertRaisesRegex(ra.rs.Invalid, "winner loses"):
            ra.audit(request, report, self.metadata)

    def test_no_rounding_and_zero_weights(self):
        request = {"budget": "1", "contributors": [
            {"id": "zero", "weight": "0"}, {"id": "whole", "weight": "0.000000000000000001"}]}
        result = ra.audit(request, self.report(request), self.metadata)
        self.assertEqual(result["rounding_units"], 0)
        self.assertIsNone(result["cutoff_tie"])
        self.assertEqual(result["contributors"][1]["units"], "0")

    def test_uint256_and_fractional_weights(self):
        request = {"budget": ra.rs.display_units(ra.rs.UINT256_MAX, 18), "contributors": [
            {"id": "a", "weight": "999999999999999999.999999999999999999"},
            {"id": "b", "weight": "0.000000000000000001"}]}
        result = ra.audit(request, self.report(request), self.metadata)
        self.assertEqual(sum(int(r["units"]) for r in result["contributors"]), ra.rs.UINT256_MAX)

    def test_report_mutations(self):
        def mutate_header(r):
            r["token"]["block_number"] += 1
        def mutate_type(r):
            r["rounding_units_distributed"] = True
        def mutate_award_type(r):
            r["allocations"][0]["rounding_unit_awarded"] = 1
        def mutate_units(r):
            r["allocations"][0]["units"] = "0" + r["allocations"][0]["units"]
        def mutate_weight(r):
            r["allocations"][0]["weight_fraction"] = "2"
        mutations = [mutate_header, mutate_type, mutate_award_type, mutate_units, mutate_weight,
                     lambda r: r.update(extra=True), lambda r: r["allocations"].reverse(),
                     lambda r: r["allocations"].pop(),
                     lambda r: r["allocations"][0].update(extra=True),
                     lambda r: r["allocations"][0].update(amount="1.0"),
                     lambda r: r["allocations"][1].update(rounding_unit_awarded=True,
                         units="333333333333333334", amount="0.333333333333333334")]
        for mutation in mutations:
            report = self.report()
            mutation(report)
            with self.subTest(mutation=mutation.__name__), self.assertRaises(ra.rs.Invalid):
                ra.audit(self.example, report, self.metadata)

    def test_input_refusals(self):
        bad = [None, {}, {"budget": "1", "contributors": []},
               {"budget": "0", "contributors": [{"id": "a", "weight": "1"}]},
               {"budget": "1", "contributors": [{"id": "a", "weight": "0"}]},
               {"budget": "1", "contributors": [{"id": "a", "weight": "1e2"}]},
               {"budget": "1", "contributors": [{"id": "a", "weight": "1"}] * 2},
               {"budget": "1", "contributors": [{"id": "\u00e9", "weight": "1"}]},
               {"budget": 1, "contributors": [{"id": "a", "weight": "1"}]}]
        for request in bad:
            with self.subTest(request=request), self.assertRaises(ra.rs.Invalid):
                ra.audit(request, self.report(), self.metadata)

    def test_real_public_address_consistency(self):
        # Public token identifiers test address syntax only; no invented payees.
        request = copy.deepcopy(self.example)
        request["contributors"][0]["address"] = ra.rs.TOKENS["zto"].upper().replace("0X", "0x")
        report = self.report(request)
        self.assertEqual(ra.audit(request, report, self.metadata)["rounding_units"], 1)
        report["allocations"][0]["address"] = ra.rs.TOKENS["imd"]
        with self.assertRaises(ra.rs.Invalid):
            ra.audit(request, report, self.metadata)
        request["contributors"][1]["address"] = ra.rs.TOKENS["zto"]
        with self.assertRaises(ra.rs.Invalid):
            ra.audit(request, self.report(), self.metadata)

    def test_small_exhaustive_subset_oracle(self):
        # Enumerate every possible leftover-award subset, maximize exact remainders,
        # then use the lexicographically smallest tuple of recipient IDs for ties.
        rng = random.Random(73727)
        for _ in range(250):
            n, budget = rng.randint(1, 6), rng.randint(1, 20)
            weights = [Fraction(rng.randint(0, 9), 10) for _ in range(n)]
            if not any(weights):
                weights[0] = Fraction(1)
            ids = [chr(65 + i) for i in range(n)]
            request = {"budget": ra.rs.display_units(budget, 18), "contributors": [
                {"id": i, "weight": ra.rs.display_units(int(w * 10), 1)} for i, w in zip(ids, weights)]}
            report = self.report(request)
            result = ra.audit(request, report, self.metadata)
            shares = [budget * w / sum(weights) for w in weights]
            floors = [q.numerator // q.denominator for q in shares]
            count = budget - sum(floors)
            subsets = list(itertools.combinations(range(n), count))
            best = min(subsets, key=lambda subset: (
                -sum((shares[i] - floors[i] for i in subset), Fraction(0)),
                tuple(ids[i] for i in subset)))
            actual = tuple(i for i, row in enumerate(result["contributors"]) if row["rounding_unit_awarded"])
            self.assertEqual(actual, best)

    def test_order_independence_and_alias_isolation(self):
        request = copy.deepcopy(self.example)
        report = self.report(request)
        original = copy.deepcopy((request, report, self.metadata))
        result = ra.audit(request, report, self.metadata)
        self.assertEqual((request, report, self.metadata), original)
        request["contributors"].reverse()
        other = ra.audit(request, self.report(request), self.metadata)
        self.assertEqual(result["contributors"], other["contributors"])
        self.assertNotEqual(result["request_sha256"], other["request_sha256"])

    def test_output_bound(self):
        request = {"budget": "1", "contributors": [
            {"id": "worker" + str(i).zfill(58), "weight": "1"} for i in range(1000)]}
        with self.assertRaisesRegex(ra.rs.Invalid, "output limit"):
            ra.audit(request, self.report(request), self.metadata)

    def test_cli_files_tamper_duplicate_keys_overwrite(self):
        scratch = Path("test/scratch")
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as directory:
            folder = Path(directory)
            request, report, output = [folder / name for name in ("request.json", "report.json", "audit.json")]
            request.write_text(json.dumps(self.example))
            report.write_text(json.dumps(self.report()))
            cmd = [sys.executable, "-B", str(Path(ra.__file__)), "check", "--request", str(request),
                   "--report", str(report), "--output", str(output)]
            first = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(json.loads(output.read_text())["rounding_units"], 1)
            saved = output.read_bytes()
            self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 2)
            self.assertEqual(output.read_bytes(), saved)
            request.write_text('{"budget":"1","budget":"2","contributors":[]}')
            self.assertEqual(subprocess.run(cmd[:-2], capture_output=True).returncode, 2)
            request.write_text(json.dumps(self.example))
            report.write_text('{}')
            self.assertEqual(subprocess.run(cmd[:-2], capture_output=True).returncode, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
