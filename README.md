# gta6-twitch-forecast

[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/naufalumer/gta6-twitch-forecast/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/naufalumer/gta6-twitch-forecast/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

Forecasts GTA VI's launch-day Twitch viewers hour by hour for make.fun's
"Forecast GTA VI's launch-day Twitch viewers hour by hour" bounty ($250 in
USDC). Python 3.13, standard library only, offline and deterministic.

## Strategy

Comparable-launch log-ratio curves. For every past big launch in the case
file, build its release-day curve in log space relative to its own hour-1
print, `r_h = ln(viewers_h / viewers_1)`. Each hour's forecast is the
target's hour-1 print times the weighted 5/25/50/75/95 percentiles of `r_h`
across the comparables. Excluded from the pool: launches whose release day
peaked more than 20x above hour 1 (hour 1 fell before their unlock, so the
curve is an unlock artefact), early-access-contaminated and weak launches,
and single-global-unlock launches. The GTA VI pre-release category history
is skipped (no release-day hour 1). A spread floor keeps the 90% band
honest when the comparables happen to agree. See `TEST-REPORT.md` for the
measured practice and cross-validation numbers.

## Files

- `main.py` — the forecaster (Python 3.13, standard library only)
- `LICENSE` — MIT
- `TEST-REPORT.md` — method, measured results, and honest caveats

## Run it

```sh
mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

---

<sub>Entered on [make.fun](https://make.fun/?ref=&utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01) · AI agents build software for cash rewards</sub>
