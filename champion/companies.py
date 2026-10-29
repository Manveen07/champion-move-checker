"""Decide whether two company names are the same company: suffixes, punctuation, renames."""

import re
import unicodedata
from collections.abc import Iterable

SUFFIXES = {
    "the", "inc", "incorporated", "llc", "ltd", "limited", "corp", "corporation",
    "co", "company", "plc", "gmbh", "ag", "sa", "bv", "pvt", "pte", "group", "holdings",
    "llp", "lp", "kk", "nv", "pty", "srl", "sarl",
}


def key(name: str) -> str:
    """'The Northwind Co., Ltd.' -> 'northwind'"""
    plain = unicodedata.normalize("NFKD", name)
    plain = "".join(c for c in plain if not unicodedata.combining(c)).lower()
    plain = plain.replace("&", " and ").replace(".", "")  # 'K.K.' -> 'kk'
    words = [w for w in re.findall(r"[a-z0-9]+", plain) if w not in SUFFIXES]
    return " ".join(words)


def alias_groups(aliases: Iterable[tuple[str, str]]) -> dict[str, str]:
    """Map each company key to one name for its group, following chains (A=B, B=C)."""
    root: dict[str, str] = {}

    def find(k: str) -> str:
        while root.get(k, k) != k:
            k = root[k]
        return k

    for a, b in aliases:
        ra, rb = find(key(a)), find(key(b))
        if ra != rb:
            root[ra] = rb
    return {k: find(k) for k in root}


def same(a: str, b: str, groups: dict[str, str] | None = None) -> bool:
    """True when a and b name the same company, directly or through a known rename."""
    ka, kb = key(a), key(b)
    if not ka or not kb:
        return False
    if ka == kb:
        return True
    groups = groups or {}
    return groups.get(ka, ka) == groups.get(kb, kb)
