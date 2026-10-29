# First runs on the blind sets

The raw output of `python -m champion gate` the first time each blind set was scored, saved at the moment it ran
(29 Oct 2026, 08:19, 08:30 and 08:45 UTC), before any fix made against that set. holdout-2 and holdout-3 were scored
straight from a sealed folder outside the repo, which is why their paths differ; holdout-1 had already been copied
into `cases/`.

What these logs can't show: the code as it was at each run. I didn't commit before each first run, so you can't
check those states out, and the repo's history starts after all three. That's the gap in the evidence. From now on,
every blind set gets scored on a tagged commit first, so a checkout reproduces its first run.

(holdout-1's log says "alerts without proof"; the rule was renamed "alerts on name alone" and tightened before
holdout-2.)
