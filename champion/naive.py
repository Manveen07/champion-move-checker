"""The first version most people build: same name, different company, so they moved.

Kept on purpose. The release gate must block it; if the gate ever passes this, the gate is broken.
"""

from champion.match import MATCH, NO_MATCH, Champion, Decision, Signal


def decide(ch: Champion, sg: Signal, groups: dict[str, str] | None = None) -> Decision:
    if ch.name.lower() == sg.name.lower() and ch.company.lower() != sg.company.lower():
        return Decision(ch.id, sg.id, MATCH, ["same name, different company"], "same name", "name")
    return Decision(ch.id, sg.id, NO_MATCH, ["name differs or same company"])


def decide_case(ch: Champion, signals: list[Signal], groups: dict[str, str] | None = None) -> list[Decision]:
    return [decide(ch, sg, groups) for sg in signals]
