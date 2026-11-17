# TEST-REPORT.md — gta6-twitch-ccu-forecast-01

Entry: `main.py` (Python 3.13, stdlib only) forecasting GTA VI's launch-day
Twitch viewers, hours 2–24, as five quantiles per hour anchored on the
case's hour-1 print.

## Method

For each comparable launch in the case file, build its release-day log-ratio
curve `r_h = ln(viewers_h / viewers_1)`, h = 2..24, using that launch's own
hour-1 print. Each hour's forecast is the target's hour-1 print times the
weighted 5/25/50/75/95 percentiles of `r_h` across the comparables.

Pool rules (all computed from the case file at runtime; nothing hard-coded
by game name):

- Exclude a launch whose release-day peak exceeds 20x its hour-1 print.
  Its hour 1 fell before its unlock (tiny pre-unlock category), so its
  curve is an unlock artefact — a near-vertical rise — not a viewership
  shape. Observed peak/hour-1 ratios are bimodal (<= 12.1 or >= 92), so
  the 20x cut sits in a wide empty gap.
- Exclude launches flagged `early-access-contaminated` or `Tier: weak` in
  their unlock note, and single-global-unlock launches (their hour 1 is
  again pre-unlock).
- The GTA VI pre-release category history has no release-day hour 1 and
  is skipped by the hour-1 requirement, never treated as a launch curve.
- Missing/sparse hours are skipped, never invented.
- Spread floor: the log q95–q05 span is at least
  `2 * 1.645 * (0.15 + 0.10 * sqrt(h-1))`, centred on the median; it only
  ever widens. An hour with no comparable data falls back to persistence
  with the house baseline's widening spread.

The target's own pre-release history is not used as a level signal (its
level is not launch-day scale); hour 1 is the scale anchor. All parameters
are constants in `main.py`, tuned offline (see below).

## Validation data

Practice answers are not in the kit, so they were fetched once from
SullyGnome with the exact API the kit's `input/NOTICE.txt` documents (one
month-request per game, GameViewers dataset, release month) and saved as
dev-only validation data (never shipped in the entry):

| case | game | hour-1 print | day peak | peak / hour-1 | peak hour |
|------|------|-------------|----------|---------------|-----------|
| p00 | Marvel's Wolverine (2026-09-15) | 23,357 | 212,243 | 9.1x | 21 |
| p01 | Red Dead Redemption 2 (2018-10-26) | 116,550 | 369,358 | 3.2x | 18 |
| p02 | God of War Ragnarök (2022-11-09) | 269,517 | 460,387 | 1.7x | 20 |
| p03 | Marvel's Spider-Man 2 (2023-10-20) | 119,087 | 263,140 | 2.2x | 22 |

Alignment was verified against each case file: the fetched hour-1 value
equals the case's `known` print, and the fetched pre-day tail matches the
case's `history_hourly` exactly.

## Results — practice (4 real cases, SullyGnome answers)

Mean pinball loss on the log scale (lower is better), typical miss, 90%
coverage. House baseline (starter) measured with the same local scorer:
**0.387097 / 82.8% / 0.783** — matching the rules' stated ≈0.387, which
validates the scorer.

| case | this entry | house baseline |
|------|-----------|----------------|
| p00 Wolverine | 0.437405 (miss 111.9%, cov 0.957) | 0.743671 (miss 188.8%, cov 0.522) |
| p01 Red Dead 2 | 0.181611 (miss 24.7%, cov 1.000) | 0.286813 (miss 65.4%, cov 0.913) |
| p02 God of War | 0.189282 (miss 34.5%, cov 1.000) | 0.214579 (miss 42.0%, cov 0.870) |
| p03 Spider-Man 2 | 0.210957 (miss 32.3%, cov 0.913) | 0.303324 (miss 64.4%, cov 0.826) |
| **overall** | **0.254814 (miss 50.8%, cov 0.967)** | **0.387097 (miss 82.8%, cov 0.783)** |

The entry beats the baseline on all four practice cases and by 34%
overall (0.255 vs 0.387).

## Results — leave-one-launch-out cross-validation (38 comparables)

Each of the 37 launch comparables in turn becomes a pseudo-case (hour-1
print = its release-day hour-1, truth = its hours 2..24, pool = the other
comparables). Split by regime, because the two populations behave very
differently:

| regime | n | this entry | house baseline |
|--------|---|-----------|----------------|
| post-unlock hour 1 (peak/hour-1 ≤ 20x) — the final's regime | 29 | 0.322875 (cov 0.883) | 0.359464 |
| pre-unlock hour 1 (peak/hour-1 > 20x) — unlock artefact | 8 | 2.523831 (cov 0.245) | 2.996577 |
| overall | 37 | 0.7987 | 0.9297 |

The pre-unlock regime is essentially unpredictable from an hour-1 print
(the category is ~0 before the unlock hour); no forecaster anchored on
hour 1 can score well there, and the final is not in that regime — GTA VI
unlocks rolling midnight with New Zealand live 13 hours before hour 1,
so hour 1 is already post-unlock with several regions playing.

## Tuning notes (what was tried, what was kept)

- Unweighted pool (all 37): practice 0.335, CV-post-unlock 0.409.
- Excluding early-access/weak/single-unlock: practice 0.319.
- Plus the 20x peak/hour-1 exclusion: practice 0.256, CV-post-unlock
  0.323. Caps 15/20/30/50 are identical (empty gap in the data); a
  soft downweight (0.15x) instead of exclusion was slightly worse on CV.
- Console-only / rolling-midnight upweighting (2–3x): practice improved
  a touch (0.248) but CV-post-unlock worsened (0.34–0.35) — not kept.
- Narrowing the intervals (quantile shrinkage 0.9x): practice 0.247 but
  CV-post-unlock coverage fell 0.883 → 0.790 and loss worsened — not kept.
- Mean-centring instead of median-centring: practice similar, CV worse —
  not kept. Median smoothing across hours: no effect — not kept.
- Spread floor (0.15 + 0.10·√(h−1)): tiny improvement on both metrics and
  cheap insurance against over-narrow bands on the final — kept.

## Determinism and runtime

- Two runs over all four practice cases (`python3 -P -s main.py`, the
  grader's invocation) produce byte-identical `.out` files.
- Single-case runtime ≈ 0.08 s (limit 8 s); all four cases ≈ 0.21 s.
  1 CPU, no network, no wall clock, no randomness.
- Output format verified on all four cases: exactly 23 rows, hours 2–24
  each once, five finite quantiles per row, each > 0 and ≤ 1e9,
  non-decreasing, file sizes 1,450–1,565 bytes (limit 65,536).

## Honest caveats

- p00 (Wolverine) is the weak case (0.437, median miss 111.9%): its curve
  rises 9.1x from a small hour 1, the steepest of the four practice
  targets. If GTA VI's hour 1 turns out small relative to its peak — e.g.
  a surprisingly quiet first hour — the forecast will under-shoot the
  evening peak the same way. The model bets, with the comparables, that a
  rolling-midnight launch's hour 1 already carries real scale.
- The practice is only four launches, and the final is a single launch
  bigger than any comparable (GTA VI's pre-release category alone dwarfs
  most launches). The practice/CV numbers are the best available guide,
  not a guarantee: the final's loss could land anywhere in the range the
  four practice cases span (0.18–0.44) or outside it.
- The 90% coverage on practice (0.967) is above the honest 0.90 — the
  bands are a little wide on big rolling-midnight launches. Narrowing
  them was tested and rejected: it helped practice slightly but hurt the
  broader cross-validation, where the final's uncertainty really lives.
- The final case's pool has 42 comparables (the four practice launches
  included); the numbers above were measured with the 37-comparable
  practice pools.
