"""python -m champion gate|compare|run  (see README)"""

import argparse
import csv
import json
import sys
from pathlib import Path

from champion import companies, gate, match, naive
from champion.match import HOLD, MATCH, Champion, Signal

MATCHERS = {"careful": match.decide_case, "naive": naive.decide_case}


def cmd_gate(args: argparse.Namespace) -> int:
    cases = gate.load(args.cases)
    rows = gate.score(cases, MATCHERS[args.matcher])
    n = len(rows)
    holds = gate.needless_holds(rows)
    print(f"{args.cases}: {len(cases)} cases, {n} signals, matcher {args.matcher}")
    print(f"agreement with labels  {sum(r.got.decision == r.expected for r in rows)}/{n} = {gate.agreement(rows):.0%}")
    print(f"  wrong alerts         {len(gate.wrong_alerts(rows)):>3}       must be 0")
    print(f"  lost moves           {len(gate.lost_moves(rows)):>3}       must be 0")
    print(f"  needless holds       {len(holds):>3}  {len(holds) / n if n else 0:>4.0%}  at most {gate.MAX_NEEDLESS_HOLD_SHARE:.0%}")
    print(f"  alerts on name alone {len(gate.unproven(rows)):>3}       must be 0")
    misses = [r for r in rows if r.got.decision != r.expected]
    if misses:
        print("disagreements:")
        for r in misses:
            print(f"  {r.signal_id:<10} {r.case.kind:<28} label {r.expected:<8} got {r.got.decision:<8} {'; '.join(r.got.reasons)}")
    problems = gate.failures(rows)
    for p in problems:
        print("BLOCK", p)
    print("BLOCKED" if problems else "PASS")
    return 1 if problems else 0


def cmd_compare(args: argparse.Namespace) -> int:
    """Replay both matchers on the same labelled cases and show every decision that changes."""
    cases = gate.load(args.cases)
    old = {r.signal_id: r for r in gate.score(cases, naive.decide_case)}
    new = gate.score(cases, match.decide_case)
    changed = [r for r in new if r.got.decision != old[r.signal_id].got.decision]
    print(f"naive -> careful on {args.cases}: {len(changed)} of {len(new)} decisions change")
    for r in changed:
        before = old[r.signal_id].got.decision
        mark = "fixed" if r.got.decision == r.expected else "worse" if before == r.expected else "still off"
        print(f"  {r.signal_id:<10} {r.case.kind:<28} label {r.expected:<8} {before:<8} -> {r.got.decision:<8} {mark}")
    worse = sum(old[r.signal_id].got.decision == r.expected for r in changed if r.got.decision != r.expected)
    print(f"{len(changed) - worse} better or still off, {worse} made worse")
    return 0


def _blank_to_none(row: dict[str, str]) -> dict[str, str | None]:
    return {k: (v or None) for k, v in row.items()}


def cmd_run(args: argparse.Namespace) -> int:
    """The workflow itself: every champion against every signal, alerts and a review queue out."""
    data = Path(args.data)
    with open(data / "champions.csv", encoding="utf-8", newline="") as f:
        champions = [Champion(**_blank_to_none(r)) for r in csv.DictReader(f)]
    signals = []
    for line in (data / "signals.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            s = json.loads(line)
            signals.append(Signal(**{**s, "history": tuple(s["history"]) if s.get("history") is not None else None}))
    aliases = []
    if (data / "aliases.csv").exists():
        with open(data / "aliases.csv", encoding="utf-8", newline="") as f:
            aliases = [(r["name"], r["same_as"]) for r in csv.DictReader(f)]
    decisions = match.run(champions, signals, companies.alias_groups(aliases))

    by_ch = {c.id: c for c in champions}
    by_sg = {s.id: s for s in signals}
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, kind in (("alerts.csv", MATCH), ("review.csv", HOLD)):
        with open(out / name, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["champion", "was_at", "signal_name", "now_at", "now_title", "proof", "reasons"])
            for d in decisions:
                if d.decision == kind:
                    ch, sg = by_ch[d.champion_id], by_sg[d.signal_id]
                    w.writerow([ch.name, ch.company, sg.name, sg.company, sg.title, d.proof or "", "; ".join(d.reasons)])
    alerts = sum(d.decision == MATCH for d in decisions)
    review = sum(d.decision == HOLD for d in decisions)
    print(f"{len(champions)} champions, {len(signals)} signals -> {alerts} alerts, {review} held for review, "
          f"{len(signals) - len({d.signal_id for d in decisions})} signals matched nobody")
    print(f"wrote {out / 'alerts.csv'} and {out / 'review.csv'}")
    return 0


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="python -m champion")
    sub = p.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("gate", help="score a matcher on labelled cases; exit 1 if it must not ship")
    g.add_argument("cases")
    g.add_argument("--matcher", choices=sorted(MATCHERS), default="careful")
    c = sub.add_parser("compare", help="replay naive and careful on the same cases, show what changes")
    c.add_argument("cases")
    r = sub.add_parser("run", help="run the checker on data/: alerts.csv and review.csv")
    r.add_argument("data", nargs="?", default="data")
    r.add_argument("--out", default="out")
    args = p.parse_args(argv)
    return {"gate": cmd_gate, "compare": cmd_compare, "run": cmd_run}[args.cmd](args)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main(sys.argv[1:]))
