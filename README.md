# champion-move-checker

When a past champion changes jobs, this finds them at the new company. When it isn't sure it's the same person, it holds the match for a person instead of guessing.

[![test](https://github.com/Manveen07/champion-move-checker/actions/workflows/test.yml/badge.svg)](https://github.com/Manveen07/champion-move-checker/actions/workflows/test.yml)

Python 3.11+, nothing to install · 60 tests · a release gate in CI · made-up data · built in October 2026

```
$ python -m champion gate cases/dev.jsonl --matcher naive      # the naive version
agreement with labels  8/29 = 28%
  wrong alerts          12       must be 0
  lost moves             9       must be 0
BLOCKED

$ python -m champion gate cases/dev.jsonl                      # this one
agreement with labels  29/29 = 100%
PASS
```

Then three blind test sets, each written by a separate agent that never saw the code, and each scored once before any fix:

| Blind set | First run | Wrong alerts | Lost moves | Needless holds | After fixing what it found |
|---|---|---|---|---|---|
| holdout-1 | 23/31 = 74%, BLOCKED | 0 | 2 | 19% | 28/31, PASS |
| holdout-2 | 25/31 = 81%, BLOCKED | 1 | 1 | 13% | 27/31, PASS |
| holdout-3 | 20/31 = 65%, BLOCKED | 0 | 1 | 32% | 25/31, PASS |

No blind set has passed on its first run yet. The raw first-run logs are in [`runs/`](runs/); the code at those moments wasn't committed, so the logs are the only record (more in `runs/README.md`). The after-fix scores are fitted to the sets, not evidence. What each set caught, and what I'd change next, is below.

## Why this exists

A GTM engineer hiring post asked for a champion tracker that holds uncertain matches. At my day job I build outbound pipelines in Clay, n8n and Python, and I can't share that code. So this is a small public version on made-up data, built the way I build the real ones: write labelled cases first, then a release gate that has to block the naive version, then fix until it passes, then test on cases the code has never seen.

## What it decides

| Decision | When | What happens next |
|---|---|---|
| MATCH | it's sure it's them, and they've moved | the account owner gets an alert, with the fact that proves it's them |
| HOLD | it might be them, or something conflicts | a person checks; the reason is written down |
| NO_MATCH | a namesake, or they haven't moved | dropped, with the reason |

From `python -m champion run data` (15 champions, 22 job-change signals: 9 alerts, 6 held, 7 dropped):

| Champion | Signal | Decision | Why |
|---|---|---|---|
| Robert Chen, Northwind Travel | Bob Chen, now CFO at Fabrikam | MATCH | same profile URL as the CRM record |
| Anna Novak, Proseware | Anna Kowalski at Orbitly, same profile URL | MATCH | new surname; same profile URL and Proseware in their history |
| Grace Lin, Trey Research | Grace Lin, now COO at Northwind Travel | MATCH | name fits and Trey Research (listed as 'Treyline') is in their work history |
| James Smith, Woodgrove | two James Smiths, both ex-Woodgrove | HOLD | 2 signals look like James Smith: a person picks |
| Elena Rossi, Contoso | Elena Rossi at Adatum since 2026-01 | HOLD | the CRM saw them at Contoso on 2026-07-20 |
| Amara Nwosu, Kestrel Freight | Amara Nwosu, CFO at Tailspin Toys | HOLD | name and history fit, but the profile URL differs from the CRM's |
| Priya Raman, Contoso | Priya Raman, a designer at Litware, never at Contoso | NO_MATCH | a namesake (the real one, now at Proseware, is an alert) |

## The failure it's built around

The naive version says: same name, different company, so they moved. It's in the repo on purpose (`champion/naive.py`). On 29 labelled signals it agreed with 8. It would have told account owners that 12 people were their champions on the move when they were namesakes or hadn't moved at all (a designer in Chennai who shares a champion's name; "Litware Inc." and "Litware" read as two companies). And it silently dropped 9 real moves (Bob for Robert, José written Jose, a new surname after marriage).

The fix weighs evidence from strongest to weakest:

1. Same company under another name (suffixes, renames): not a move.
2. Same profile URL: it's them, even with a nickname or a short form, or with a new surname when the first name and the old company match. It still holds when the dates say they may not have left, or when the name on the URL is someone else's.
3. Same name (allowing nicknames, accents, middle names, word order) and the old company in their work history: a match, unless the dates contradict, the city changed with no profile to confirm, or two people fit.
4. Held for a person: an initial or another spelling of the first name, no work history, a profile URL that differs from the CRM's, or the same name and city with the old company missing from the history.
5. Two signals that both fit one champion, or one signal that fits two champions: hold all of them.

A name alone is never proof: every alert rests on the same profile URL or the old company in their history. Every rule is one branch of `decide()` in `champion/match.py` and has a test named after the mistake it prevents.

## What the blind tests caught

My own cases pass by construction, so a separate agent wrote 31 more signals from the decision rules alone, without seeing the code (`cases/holdout-1.jsonl`). I ran the code on them once, unchanged:

```
agreement with labels  23/31 = 74%
  wrong alerts           0       must be 0
  lost moves             2       must be 0
  needless holds         6   19%  at most 20%
BLOCKED
```

The two lost moves were real gaps. "Yevgenia" and "Evgeniya" Kharitonova read as two people. And a Benedikt Auer with the same name, title and city was dropped because his profile's history skipped the old company. Six rule changes came out of the run, one per disagreement I agreed with:

- another spelling of a first name is held, not dropped;
- the same name and city with the old company missing from the history is held;
- "Mary-Kate O'Donnell" and "Marykate ODonnell" are the same name;
- a renamed city (Bangalore, Bengaluru) isn't a move;
- the same profile URL, the same first name and the old company in the history is a match despite a new surname (this overturned my own label on dev-07, noted in the case file);
- no work history plus a start date months before we last saw the champion is dropped.

Three disagreements stay by design, all holds where the labeller was sure. In two, the profile URL differs from the CRM's, and a person settles it by opening both profiles. In the third, a first name spelled another way is held rather than matched.

Then a separate code review found two bugs the cases hadn't. A shared middle initial counted as a shared surname ("Robert J. Chen" matched "Robert J. Lee"), and a different profile URL with no work history was dropped instead of held. Both are fixed, with tests.

holdout-1 passes 28 of 31 now, but the code was fixed against it, so it no longer counts as blind.

A fresh agent then wrote holdout-2 (31 signals). First run, unchanged code:

```
agreement with labels  25/31 = 81%
  wrong alerts           1       must be 0
  lost moves             1       must be 0
  needless holds         4   13%  at most 20%
BLOCKED
```

The wrong alert was a profile that matched the CRM's, but the new job started nine months before the champion last replied from the old company. A profile URL proves who it is, not that they left, so that now holds. The lost move was "Becky" for "Rebecca": the nickname table was too small, and now has 138 common nicknames. A short form of a first name ("Seun" for "Oluwaseun") also now counts as weak evidence: a match only with the same profile URL. holdout-2 passes 27 of 31 now, with 4 holds by design.

The third set, holdout-3 (31 signals), was written after every fix, with the situations the first two missed. It was blocked on reviewer time: 10 needless holds, 32%, over my own 20% budget. It also found real gaps: "LLP" and "K.K." company suffixes, MacAllister and McAllister, a surname spelled two ways (Shcherbinina and Scherbinina, which was the lost move), and the same move reported by two sources, which my "two people fit" rule held. Those are fixed. holdout-3 passes 25 of 31 now, with 6 holds by design, at 19% needless holds against a 20% budget, after fixes made against it: fitted, not proof.

I stopped at three blind sets, as I'd decided before the third. More sets from the same kind of AI labeller keep finding the long tail of names; the next real test is labelled real data.

### What the misses say

Across the three first runs, 93 blind signals: 1 wrong alert, 4 lost moves, and the rest of the misses were holds where the labeller was sure. The design leans towards holding on purpose. A wrong alert costs a champion's trust; a hold costs a reviewer a click. holdout-3 shows the price: a third of its signals held for no reason.

The biggest single cause is a profile URL that differs from the CRM's, held 6 times. The labellers called 3 of those the same person (the URL had changed) and 3 a namesake who had passed through the same company. Next I'd split them on title and seniority (a CFO doesn't become a junior analyst), and ship that only after it passes a fresh blind set.

## How it's tested

- **29 dev cases** (`cases/dev.jsonl`), written and labelled while building, each one a way the naive version goes wrong. The careful matcher passes them by construction, so they prove little on their own.
- **Three blind holdouts** (`cases/holdout-*.jsonl`), each written by a separate AI agent from the decision rules only, never the code, and scored once before any fix (the table at the top). The labels come from AI agents, not people, and the agents had similar briefs, so they can share blind spots. Each set was used to fix the code after its first run, so only the first-run numbers count as blind. 1 wrong alert in 93 blind signals means the true rate could still be up to about 5%. Real labelled data would tighten that.
- **A release gate** (`champion/gate.py`). A matcher ships only with 0 wrong alerts, 0 lost moves, needless holds on at most 20% of signals, and no alert on a name alone. The 20% is a budget I chose for reviewer time. Holding everything is safe, and the gate still blocks it: a test checks that.
- **60 unit tests**, one per rule, plus tests that the gate fails the matchers it should fail.
- **CI on every push**: the tests, the gate on every case file, a check that the naive matcher is still blocked, and a run on the sample data.

## Run it

```
python -m unittest                                   # 60 tests
python -m champion gate cases/dev.jsonl              # PASS or BLOCKED, exit 0 or 1
python -m champion gate cases/dev.jsonl --matcher naive
python -m champion compare cases/dev.jsonl           # every decision that changes from naive to careful
python -m champion run data --out out                # out/alerts.csv and out/review.csv
```

## How I'd run it in Clay

1. A table of past champions from the CRM: name, company, profile URL, the last date they replied from their work email.
2. Clay's job-change signal fills in where each one works now and their work history.
3. An HTTP column sends each champion and signal to this check, deployed as a small function, and writes back the decision, proof and reasons.
4. MATCH rows go to the account owner in Slack or the CRM. HOLD rows go to a review view with the reason. NO_MATCH rows stay for the record.

Before switching a live table to a new version of the rules, replay the old and new on the labelled cases (`compare`) and ship only through the gate.

On Salesforce instead of Clay, the same shape: champions are Contacts with a champion flag, each signal and its decision, proof and reasons go into a custom object linked to the Contact, MATCH creates a task for the owner of the new Account, and HOLD rows sit in a list view (or a Slack message) for review.

## Limits

- Made-up data. Real job-change data is messier: missing fields, stale profiles, many more namesakes.
- Latin script only, 138 English nicknames, and a loose spelling check (it also pairs Brian and Bruno, and Dan and Daniela), which is why a spelling match alone only ever holds.
- Each labelled case has one champion, so "one signal fits two champions" is covered by a unit test, not by the gate.
- Rules, not a model. Every decision is explainable and replays for free, but anything the rules don't cover goes to HOLD, which costs reviewer time. An LLM could summarise the evidence on a held match for the reviewer; it shouldn't decide a MATCH on its own.
- No memory between runs: a person held last week is held again, and a reviewer's call isn't kept. The next step I'd build: store each reviewer's call, use it on the next run, and add it as a labelled case, so every correction becomes a test.
- `run()` compares every champion with every signal. Fine for thousands; for more, group by surname first.

## Who built it

Manveen Singh, GTM engineer, built with Claude Code. At my day job the same habits sit behind an outbound pipeline with 870+ automated tests; how I test workflows is written up at [manveen.me/writing](https://manveen.me/writing). MIT licence.
