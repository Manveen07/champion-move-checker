"""Decide, for a past champion and a job-change signal: MATCH, HOLD or NO_MATCH, and say why.

MATCH    sure it's the champion and they've moved: the account owner gets an alert.
HOLD     might be the champion, but the record isn't enough or something conflicts: a person checks.
NO_MATCH not the champion, or the champion hasn't moved.

The rule behind every branch: never alert about a stranger, never silently drop a real move.
"""

import re
from dataclasses import dataclass, field
from datetime import date, timedelta

from champion import companies, names

MATCH, HOLD, NO_MATCH = "MATCH", "HOLD", "NO_MATCH"

# Start dates are often only a month, and people still answer old email in their notice period.
DATE_SLACK = timedelta(days=31)


@dataclass(frozen=True)
class Champion:
    id: str
    name: str
    company: str
    title: str = ""
    city: str | None = None
    profile: str | None = None
    last_seen: str | None = None  # last date the CRM saw them active at `company`


@dataclass(frozen=True)
class Signal:
    id: str
    name: str
    company: str  # where they work now
    title: str = ""
    city: str | None = None
    profile: str | None = None
    started: str | None = None  # when they started at `company`
    history: tuple[str, ...] | None = None  # earlier employers, most recent first; None = unknown


@dataclass
class Decision:
    champion_id: str
    signal_id: str
    decision: str
    reasons: list[str] = field(default_factory=list)
    proof: str | None = None  # for a MATCH: the fact that settles identity
    anchor: str | None = None  # what that fact rests on: "profile" or "history" (never the name alone)


def _day(s: str) -> date:
    """'2026-03' or '2026-03-14' -> a date (the 1st when only the month is known)."""
    return date.fromisoformat(s if len(s) > 7 else s + "-01")


# Old and new names for one city, so a renamed city doesn't read as a move.
CITY_NAMES = {
    "bangalore": "bengaluru", "bombay": "mumbai", "madras": "chennai", "calcutta": "kolkata",
    "gurgaon": "gurugram", "kiev": "kyiv", "peking": "beijing", "saigon": "ho chi minh city",
    "nyc": "new york", "new york city": "new york",
}


def _city(c: str | None) -> str | None:
    return CITY_NAMES.get(c.strip().lower(), c.strip().lower()) if c else None


def _profile(url: str) -> str:
    """'http://in.linkedin.example/in/x/?trk=1' and 'https://www.linkedin.example/in/x' -> 'linkedin.example/in/x'"""
    u = url.strip().lower().split("?")[0].split("#")[0].rstrip("/")
    return re.sub(r"^(?:https?://)?(?:www\.|[a-z]{2}\.)?", "", u)


def decide(ch: Champion, sg: Signal, groups: dict[str, str] | None = None) -> Decision:
    """One champion against one signal. Branches run from strongest evidence to weakest."""

    def out(decision: str, *reasons: str, proof: str | None = None, anchor: str | None = None) -> Decision:
        return Decision(ch.id, sg.id, decision, list(reasons), proof, anchor)

    old = ch.company
    if companies.same(sg.company, old, groups):
        return out(NO_MATCH, f"still at {old} (now '{sg.company}'): not a move")

    name = names.compare(ch.name, sg.name)
    name_note = "same name" if name == "exact" else f"'{sg.name}' is '{ch.name}' written another way"
    listed = next((h for h in sg.history or () if companies.same(h, old, groups)), None)
    in_history = listed is not None
    old_seen = f"{old} (listed as '{listed}')" if listed and companies.key(listed) != companies.key(old) else old
    both_profiles = bool(ch.profile and sg.profile)
    same_profile = both_profiles and _profile(ch.profile) == _profile(sg.profile)
    city_a, city_b = _city(ch.city), _city(sg.city)
    clash = ""
    if ch.last_seen and sg.started and _day(ch.last_seen) > _day(sg.started) + DATE_SLACK:
        clash = f"started at {sg.company} in {sg.started}, but the CRM saw them at {old} on {ch.last_seen}"

    if same_profile:
        if clash and name != "different":
            return out(HOLD, f"it's their profile, but they may not have left: {clash}")
        if name != "different":
            return out(MATCH, name_note, proof="same profile URL as the CRM record", anchor="profile")
        if in_history and names.first_names_agree(ch.name, sg.name):
            return out(MATCH, f"new surname: '{sg.name}'",
                       proof=f"same profile URL as the CRM record, and {old_seen} in their history",
                       anchor="profile")
        return out(HOLD, f"same profile URL, but the name is now '{sg.name}': a name change or a wrong URL")

    if name == "different":
        if in_history and names.first_names_agree(ch.name, sg.name):
            return out(HOLD, f"same first name and {old} in their history, new surname: maybe a name change")
        return out(NO_MATCH, f"different name ('{sg.name}')")

    if both_profiles:
        if in_history:
            return out(HOLD, f"name fits and {old} is in their history, but the profile URL differs from the CRM's")
        if not sg.history:
            return out(HOLD, "name fits, but the profile URL differs from the CRM's and there's no work history to check")
        return out(NO_MATCH, f"different profile URL and no {old} in their history")

    if not sg.history:
        if clash:
            return out(NO_MATCH, f"no work history, and {clash}")
        return out(HOLD, f"name fits, but no work history to check {old} against")
    if not in_history:
        if city_a and city_a == city_b:
            return out(HOLD, f"same name and city, but {old} isn't in their listed history: "
                             "an incomplete profile or a namesake")
        return out(NO_MATCH, f"{old} is not in their work history: a namesake")
    if name == "initial":
        return out(HOLD, f"only an initial for the first name ('{sg.name}')")
    if name == "spelling":
        return out(HOLD, f"'{sg.name}' may be another spelling or a short form of '{ch.name}'")

    conflicts = [clash] if clash else []
    if city_a and city_b and city_a != city_b:
        conflicts.append(f"city changed ({ch.city} to {sg.city}) and no profile URL to confirm it's them")
    if conflicts:
        return out(HOLD, *conflicts)

    return out(MATCH, name_note, proof=f"name fits and {old_seen} is in their work history", anchor="history")


def decide_case(ch: Champion, signals: list[Signal], groups: dict[str, str] | None = None) -> list[Decision]:
    """Every signal for one champion. Two sure matches at different companies means neither is sure."""
    decisions = [decide(ch, sg, groups) for sg in signals]
    matches = [(d, sg) for d, sg in zip(decisions, signals) if d.decision == MATCH]
    if len(matches) > 1 and all(companies.same(sg.company, matches[0][1].company, groups) for _, sg in matches):
        for d, _ in matches:
            d.reasons.append(f"the same move, reported {len(matches)} times")
    elif len(matches) > 1:
        for d, _ in matches:
            d.decision, d.proof, d.anchor = HOLD, None, None
            d.reasons.append(f"{len(matches)} signals look like {ch.name}: a person picks")
    return decisions


def run(champions: list[Champion], signals: list[Signal], groups: dict[str, str] | None = None) -> list[Decision]:
    """All champions against all signals; returns only the alerts and holds."""
    kept = [d for ch in champions for d in decide_case(ch, signals, groups) if d.decision != NO_MATCH]
    by_signal: dict[str, list[Decision]] = {}
    for d in kept:
        if d.decision == MATCH:
            by_signal.setdefault(d.signal_id, []).append(d)
    for ds in by_signal.values():
        if len(ds) > 1:  # one person can't be two of our champions
            for d in ds:
                d.decision, d.proof, d.anchor = HOLD, None, None
                d.reasons.append(f"this signal fits {len(ds)} champions: a person picks")
    return kept
