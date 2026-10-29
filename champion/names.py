"""Compare two people's names: accents, nicknames, initials, middle names, word order."""

import re
import unicodedata

# nickname -> the formal first names it can stand for (common English ones; not exhaustive)
_PAIRS = """
abby:abigail abe:abraham al:albert,alan,alfred alex:alexander,alexandra,alexis andy:andrew annie:ann,anne,anna
art:arthur barb:barbara becca:rebecca becky:rebecca ben:benjamin benny:benjamin bert:albert,robert,herbert
beth:elizabeth,bethany betsy:elizabeth betty:elizabeth bill:william billy:william bob:robert bobby:robert
brad:bradley cam:cameron cassie:cassandra cathy:catherine,cathryn charlie:charles chuck:charles
chris:christopher,christine,christina cindy:cynthia cliff:clifford dan:daniel danny:daniel dave:david davy:david
deb:deborah debbie:deborah dick:richard don:donald donny:donald doug:douglas drew:andrew ed:edward eddie:edward
eliza:elizabeth ellie:eleanor,ellen,elizabeth fred:frederick,alfred freddie:frederick,alfred gabe:gabriel
greg:gregory hank:henry harry:henry,harold jack:john,jackson jake:jacob jamie:james jan:janet,janice
jeff:jeffrey jen:jennifer jenny:jennifer jerry:gerald,jerome jess:jessica jessie:jessica jim:james jimmy:james
joe:joseph joey:joseph johnny:john jon:john,jonathan josh:joshua judy:judith kat:katherine,catherine
kate:katherine,catherine,kathryn kathy:katherine,kathryn katie:katherine,catherine,kathryn ken:kenneth
kenny:kenneth kim:kimberly larry:lawrence len:leonard lenny:leonard libby:elizabeth liz:elizabeth
lizzie:elizabeth lou:louis,louise maggie:margaret mandy:amanda marge:margaret matt:matthew max:maximilian,maxwell
meg:margaret,megan mel:melissa,melanie,melvin mick:michael mike:michael mikey:michael nat:nathan,nathaniel,natalie
nate:nathan,nathaniel ned:edward nick:nicholas nicky:nicholas nikki:nicole pam:pamela pat:patricia,patrick
patty:patricia peggy:margaret pete:peter phil:philip,phillip ray:raymond rich:richard richie:richard
rick:richard ricky:richard rob:robert robbie:robert ron:ronald ronnie:ronald sam:samuel,samantha
sammy:samuel,samantha sandy:sandra sasha:alexander,alexandra steve:steven,stephen stevie:steven,stephen
sue:susan,suzanne susie:susan,suzanne ted:edward,theodore teddy:theodore theo:theodore tim:timothy
timmy:timothy tom:thomas tommy:thomas tony:anthony,antonio trish:patricia val:valerie vicky:victoria
vicki:victoria vince:vincent walt:walter will:william zach:zachary zack:zachary
"""
NICKNAMES: dict[str, set[str]] = {
    nick: set(formal.split(",")) for nick, formal in (pair.split(":") for pair in _PAIRS.split())
}


def tokens(name: str) -> list[str]:
    """'José  Pérez-Ruiz' -> ['jose', 'perez', 'ruiz']; 'MacAllister' and 'McAllister' -> 'mcallister'"""
    plain = unicodedata.normalize("NFKD", name)
    plain = "".join(c for c in plain if not unicodedata.combining(c)).lower()
    return [re.sub(r"^mac(?=[a-z]{3})", "mc", t) for t in re.findall(r"[a-z]+", plain)]


def same_first(a: str, b: str) -> bool:
    """Same first name, allowing a nickname on either side ('bob' and 'robert')."""
    if a == b:
        return True
    formal_a = NICKNAMES.get(a, {a})
    formal_b = NICKNAMES.get(b, {b})
    return bool(formal_a & formal_b)


def _skeleton(word: str) -> str:
    """Consonants only, doubles collapsed: 'yevgenia' and 'evgeniya' both give 'vgn'."""
    w = word.replace("x", "ks").replace("ph", "f").replace("c", "k").replace("h", "")
    w = re.sub(r"[aeiouy]", "", w)
    return re.sub(r"(.)\1+", r"\1", w)


def spellings(a: str, b: str) -> bool:
    """Maybe one first name: two spellings ('yevgenia', 'evgeniya') or a short form ('seun', 'oluwaseun').

    Loose on purpose ('brian' and 'bruno' pass, so do 'dan' and 'daniela'), so it only ever counts as weak evidence.
    """
    short, long_ = sorted((a, b), key=len)
    if len(short) >= 3 and short != long_ and (long_.startswith(short) or long_.endswith(short)):
        return True
    sa = _skeleton(a)
    return len(sa) >= 3 and sa == _skeleton(b)


def compare(a: str, b: str) -> str:
    """How two names relate: 'exact', 'variant', 'initial', 'spelling' or 'different'.

    variant: same person written differently (nickname, accent, middle name, hyphenated
    surname, punctuation, word order). initial: one side has only an initial for the first
    name. spelling: first names that may be one name spelled another way or shortened (Yevgenia and
    Evgeniya, Seun and Oluwaseun): weak evidence.
    different: no surname in common, or first names that can't be the same.
    """
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return "different"
    if ta == tb:
        return "exact"
    if sorted(ta) == sorted(tb) or "".join(ta) == "".join(tb):
        return "variant"
    # Surnames: the words after the first, minus initials and prefixes like the O in O'Brien. Two names share
    # one when either side's last surname word appears on the other side ('Fernandez-Ortiz' and 'Fernandez').
    sur_a = [t for t in ta[1:] if len(t) > 1]
    sur_b = [t for t in tb[1:] if len(t) > 1]
    if not sur_a or not sur_b:
        return "different"
    shared = sur_a[-1] in sur_b or sur_b[-1] in sur_a
    # A surname spelled another way ('Shcherbinina', 'Scherbinina') is only weak evidence, like a first name's.
    sounds_alike = len(_skeleton(sur_a[-1])) >= 3 and _skeleton(sur_a[-1]) == _skeleton(sur_b[-1])
    if not shared and not sounds_alike:
        return "different"
    first_a, first_b = ta[0], tb[0]
    if same_first(first_a, first_b):
        first = "variant"
    elif (len(first_a) == 1 and first_b.startswith(first_a)) or (len(first_b) == 1 and first_a.startswith(first_b)):
        first = "initial"
    elif spellings(first_a, first_b):
        first = "spelling"
    else:
        return "different"
    return first if shared else "spelling"


def first_names_agree(a: str, b: str) -> bool:
    """True when the first names could be the same person's, whatever the surname says."""
    ta, tb = tokens(a), tokens(b)
    return bool(ta and tb and same_first(ta[0], tb[0]))
