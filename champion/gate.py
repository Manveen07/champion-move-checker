"""Release gate: run a matcher on labelled cases and block it unless every rule holds.

Rules (a matcher ships only if all four pass):
  1. No wrong alerts:     never MATCH when the label isn't MATCH (an owner would contact a stranger).
  2. No lost moves:       never NO_MATCH when the label is MATCH or HOLD (a real move dropped unseen).
  3. Few needless holds:  HOLD where the label isn't HOLD on at most 20% of signals (reviewer time).
  4. Never on a name alone: each MATCH rests on the same profile URL or the old company in their history.
With 1 and 2 at zero and 3 at most 20%, agreement with the labels is at least 80%. The 20% is a budget I chose
for reviewer time, not a law: tighten it once real traffic shows what a reviewer clears in a day.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from champion import companies
from champion.match import HOLD, MATCH, NO_MATCH, Champion, Decision, Signal

MAX_NEEDLESS_HOLD_SHARE = 0.20
ANCHORS = {"profile", "history"}

Matcher = Callable[[Champion, list[Signal], dict[str, str]], list[Decision]]


@dataclass
class Case:
    id: str
    kind: str
    champion: Champion
    signals: list[Signal]
    aliases: list[tuple[str, str]]
    expect: dict[str, str]
    why: str


@dataclass
class Row:
    case: Case
    signal_id: str
    expected: str
    got: Decision


def load(path: str | Path) -> list[Case]:
    cases = []
    for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        d = json.loads(line)
        signals = [Signal(**{**s, "history": tuple(s["history"]) if s.get("history") is not None else None})
                   for s in d["signals"]]
        case = Case(d["id"], d.get("kind", ""), Champion(**d["champion"]), signals,
                    [tuple(p) for p in d.get("aliases", [])], d["expect"], d.get("why", ""))
        ids = {s.id for s in signals}
        if set(case.expect) != ids or not set(case.expect.values()) <= {MATCH, HOLD, NO_MATCH}:
            raise ValueError(f"{path}:{n}: case {case.id}: expect must give MATCH/HOLD/NO_MATCH for {sorted(ids)}")
        cases.append(case)
    return cases


def score(cases: list[Case], decide_case: Matcher) -> list[Row]:
    rows = []
    for case in cases:
        groups = companies.alias_groups(case.aliases)
        for d in decide_case(case.champion, case.signals, groups):
            rows.append(Row(case, d.signal_id, case.expect[d.signal_id], d))
    return rows


def wrong_alerts(rows: list[Row]) -> list[Row]:
    return [r for r in rows if r.got.decision == MATCH and r.expected != MATCH]


def lost_moves(rows: list[Row]) -> list[Row]:
    return [r for r in rows if r.got.decision == NO_MATCH and r.expected != NO_MATCH]


def needless_holds(rows: list[Row]) -> list[Row]:
    return [r for r in rows if r.got.decision == HOLD and r.expected != HOLD]


def unproven(rows: list[Row]) -> list[Row]:
    return [r for r in rows if r.got.decision == MATCH and not (r.got.proof and r.got.anchor in ANCHORS)]


def failures(rows: list[Row]) -> list[str]:
    """Empty list = ship it. Otherwise one line per broken rule."""
    out = []
    if wrong := wrong_alerts(rows):
        out.append(f"{len(wrong)} wrong alert(s): {', '.join(r.signal_id for r in wrong)}")
    if lost := lost_moves(rows):
        out.append(f"{len(lost)} lost move(s): {', '.join(r.signal_id for r in lost)}")
    holds = needless_holds(rows)
    if rows and len(holds) / len(rows) > MAX_NEEDLESS_HOLD_SHARE:
        out.append(f"needless holds {len(holds)}/{len(rows)} = {len(holds) / len(rows):.0%}, over {MAX_NEEDLESS_HOLD_SHARE:.0%}")
    if bare := unproven(rows):
        out.append(f"{len(bare)} alert(s) on a name alone or no proof: {', '.join(r.signal_id for r in bare)}")
    return out


def agreement(rows: list[Row]) -> float:
    return sum(r.got.decision == r.expected for r in rows) / len(rows) if rows else 0.0
