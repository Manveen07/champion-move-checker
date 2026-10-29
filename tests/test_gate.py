"""The gate is only worth something if it fails the matchers it should fail."""

import contextlib
import csv
import io
import json
import tempfile
import unittest
from pathlib import Path

from champion import gate, match, naive
from champion.__main__ import main
from champion.match import HOLD, MATCH, Decision

ROOT = Path(__file__).resolve().parent.parent
CASES = sorted((ROOT / "cases").glob("*.jsonl"))


def always(decision: str, proof: str | None = "x", anchor: str | None = "history"):
    def decide_case(ch, signals, groups):
        m = decision == MATCH
        return [Decision(ch.id, s.id, decision, ["test"], proof if m else None, anchor if m else None) for s in signals]
    return decide_case


class Gate(unittest.TestCase):
    def test_careful_matcher_passes_every_case_file(self):
        self.assertTrue(CASES)
        for path in CASES:
            with self.subTest(path.name):
                self.assertEqual(gate.failures(gate.score(gate.load(path), match.decide_case)), [])

    def test_naive_matcher_is_blocked_on_every_rule_it_breaks(self):
        problems = gate.failures(gate.score(gate.load(ROOT / "cases" / "dev.jsonl"), naive.decide_case))
        self.assertTrue(any("wrong alert" in p for p in problems))
        self.assertTrue(any("lost move" in p for p in problems))
        self.assertTrue(any("name alone" in p for p in problems))

    def test_holding_everything_is_safe_but_blocked(self):
        problems = gate.failures(gate.score(gate.load(ROOT / "cases" / "dev.jsonl"), always(HOLD)))
        self.assertEqual(len(problems), 1)
        self.assertIn("needless holds", problems[0])

    def test_alert_without_proof_or_on_a_name_alone_is_blocked(self):
        dev = gate.load(ROOT / "cases" / "dev.jsonl")
        for kw in ({"proof": None}, {"anchor": "name"}):
            with self.subTest(**kw):
                problems = gate.failures(gate.score(dev, always(MATCH, **kw)))
                self.assertTrue(any("name alone or no proof" in p for p in problems))

    def test_case_missing_a_label_is_refused(self):
        line = json.loads((ROOT / "cases" / "dev.jsonl").read_text(encoding="utf-8").splitlines()[0])
        line["expect"] = {}
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.jsonl"
            bad.write_text(json.dumps(line) + "\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                gate.load(bad)

    def test_case_ids_are_unique_across_files(self):
        ids = [s["id"] for p in CASES for line in p.read_text(encoding="utf-8").splitlines() if line.strip()
               for s in json.loads(line)["signals"]]
        self.assertEqual(len(ids), len(set(ids)))


class Cli(unittest.TestCase):
    def test_gate_exit_codes(self):
        dev = str(ROOT / "cases" / "dev.jsonl")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["gate", dev]), 0)
            self.assertEqual(main(["gate", dev, "--matcher", "naive"]), 1)

    def test_run_writes_alerts_with_proof_and_a_review_queue(self):
        with tempfile.TemporaryDirectory() as tmp:
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["run", str(ROOT / "data"), "--out", tmp]), 0)
            with open(Path(tmp) / "alerts.csv", encoding="utf-8", newline="") as f:
                alerts = list(csv.DictReader(f))
            with open(Path(tmp) / "review.csv", encoding="utf-8", newline="") as f:
                review = list(csv.DictReader(f))
        self.assertEqual((len(alerts), len(review)), (9, 6))
        self.assertTrue(all(a["proof"] for a in alerts))
        self.assertTrue(all(r["reasons"] and not r["proof"] for r in review))


if __name__ == "__main__":
    unittest.main()
