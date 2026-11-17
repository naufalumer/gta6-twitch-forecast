"""Forecast GTA VI's launch-day Twitch viewers hour by hour (make.fun
gta6-twitch-ccu-forecast-01). Python 3.13, standard library only.

Method: comparable-launch log-ratio curves.
-------------------------------------------
For every past big launch shipped in the case file ("comparables"), build
its release-day curve in log space relative to its own hour-1 print:

    r_h = ln(viewers_h / viewers_1),  h = 2..24.

The target's forecast for hour h is its hour-1 print times the weighted
distribution of r_h across the comparables: the five quantiles are the
weighted 5/25/50/75/95 percentiles of that cross-launch distribution.
The target's own history is not used as a level signal (a pre-release
category's level is not launch-day scale); hour 1 is the scale anchor.

Which comparables count, and how much:
  * A launch whose release day peaks more than 20x above its hour-1 print
    is excluded outright. Its hour 1 fell before its unlock (a tiny
    pre-unlock category), so its curve is an unlock artefact -- a near
    vertical rise -- not a viewership shape. A rolling-midnight target
    like GTA VI has hour 1 already post-unlock (New Zealand live 13 h),
    so those shapes would only drag the forecast up. The 20x cut sits in
    a wide empty gap of the data (observed peak/hour-1 ratios are <= 12.1
    or >= 92), so the exact value barely matters.
  * Launches flagged early-access-contaminated or weak in their unlock
    note are excluded, as are single-global-unlock launches (their hour 1
    is again pre-unlock). These are text checks on the unlock note the
    case file itself carries; nothing is hard-coded by game name.
  * The Grand Theft Auto VI pre-release category history that rides along
    as a comparable has no release-day hour 1, so it is skipped by the
    hour-1 requirement, never treated as a launch curve.
  * Missing/sparse hours are skipped, never invented.

Spread: the cross-launch percentile spread already widens over the day.
A floor keeps the 90% band honest when the comparables happen to agree:
the log q95-q05 span is at least 2 * 1.645 * (0.15 + 0.10 * sqrt(h-1)).
The floor is centred on the median log-ratio and only ever widens.

All parameters are constants below, tuned offline on the practice cases
and on leave-one-launch-out cross-validation over the comparables.
Measured with the practice answers fetched from SullyGnome (see
TEST-REPORT.md): practice mean pinball 0.255 (per case 0.437 / 0.182 /
0.189 / 0.211), typical miss 50.8%, 90% coverage 0.967, against the house
baseline's 0.387 / 82.8% / 0.783. Leave-one-launch-out over the 29
post-unlock comparables: 0.323 vs the baseline's 0.359. The program is
deterministic: fixed file order, sorted quantile computation, no
randomness, no wall clock, no network; it reads only the input directory
and writes only the output directory.

Run by the grader as `python3 -P -s /bot/main.py`; -P leaves /bot off
sys.path, so the directory is re-added first (this file is self-contained
and imports nothing beside it, but the line keeps the option open).
"""

import json
import math
import os
import sys
from datetime import datetime
from pathlib import Path

# The grader's -P leaves /bot off sys.path: put it back first.
sys.path.insert(0, str(Path(__file__).resolve().parent))

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

# The quantile levels the contest scores, in the order each row lists them.
LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
# The standard normal's quantile at each level (used by the fallback only).
Z = [-1.645, -0.674, 0.0, 0.674, 1.645]

# --- Tuned constants (see TEST-REPORT.md for how they were chosen) ---
# A comparable whose release-day peak exceeds PEAK_CAP times its hour-1
# print had hour 1 before its unlock: exclude it (see module docstring).
PEAK_CAP = 20.0
# Spread floor: the log q95-q05 span is at least 2 * 1.645 * S(h) with
# S(h) = SPREAD_S0 + SPREAD_S1 * sqrt(h - 1).
SPREAD_S0 = 0.15
SPREAD_S1 = 0.10
# Fallback random-walk spread (house baseline's), used only for an hour
# with no comparable data at all.
FALLBACK_SIGMA = 0.15


def round2(x: float) -> float | int:
    """x rounded to 2 decimals, half up, as JavaScript's Math.round(x * 100) / 100.

    A whole number comes back as an int, so json.dumps writes 1240 where
    JavaScript writes 1240 (not 1240.0).
    """
    scaled = x * 100
    whole = math.floor(scaled)
    if scaled - whole >= 0.5:
        whole += 1
    value = whole / 100
    return int(value) if value.is_integer() else value


def parse_ts(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def release_day_points(comp: dict) -> dict:
    """A comparable's release-day hourly viewers, keyed by UTC hour 1..24.

    Points are taken as given (one per hour, no interpolation); hours the
    source did not sample are simply absent.
    """
    day_start = parse_ts(comp["day_start"])
    points = {}
    for point in comp.get("hourly") or []:
        viewers = point.get("viewers")
        if viewers is None:
            continue
        hour = int((parse_ts(point["from"]) - day_start).total_seconds() // 3600) + 1
        if 1 <= hour <= 24:
            points[hour] = viewers
    return points


def usable(comp: dict) -> bool:
    """Whether a comparable is a usable launch-shape analogue.

    Excludes the early-access-contaminated, weak and single-global-unlock
    launches the case file's own unlock notes flag: their release-day
    curves are shaped by a different unlock (early access already live,
    or one worldwide unlock hour) than a rolling-midnight console launch.
    """
    unlock = (comp.get("unlock") or "").lower()
    if "early-access-contaminated" in unlock:
        return False
    if "tier: weak" in unlock:
        return False
    if "single global" in unlock or "single simultaneous" in unlock:
        return False
    return True


def weighted_quantile(pairs: list, tau: float) -> float:
    """Weighted quantile of [(value, weight)] at level tau."""
    ordered = sorted(pairs)
    total = sum(w for _, w in ordered)
    threshold = tau * total
    acc = 0.0
    for value, weight in ordered:
        acc += weight
        if acc >= threshold:
            return value
    return ordered[-1][0]


def hour_forecast(p1: float, per_hour: dict, hour: int) -> list:
    """The five quantiles (viewers) for one hour from its log-ratio pool."""
    pairs = per_hour.get(hour) or []
    if not pairs:
        # No comparable data for this hour: persistence with a widening
        # spread, the house baseline's shape.
        return [round2(p1 * math.exp(z * FALLBACK_SIGMA * math.sqrt(hour - 1))) for z in Z]
    median = weighted_quantile(pairs, 0.5)
    log_qs = [weighted_quantile(pairs, tau) for tau in LEVELS]
    # Spread floor: widen the log-offsets from the median until the 90%
    # band spans at least 2 * 1.645 * S(hour). Only ever widens.
    span = SPREAD_S0 + SPREAD_S1 * math.sqrt(hour - 1)
    half_span = (log_qs[4] - log_qs[0]) / 2.0
    if half_span < 1.645 * span and half_span > 1e-9:
        scale = (1.645 * span) / half_span
        if scale > 1.0:
            log_qs = [median + (q - median) * scale for q in log_qs]
    quantiles = []
    prev = 0.0
    for log_q in log_qs:
        q = p1 * math.exp(log_q)
        q = max(1.0, min(1e9, q))
        q = max(q, prev)  # keep the row non-decreasing after rounding
        quantiles.append(round2(q))
        prev = quantiles[-1]
    return quantiles


def forecast_case(case: dict, name: str) -> dict:
    if case["levels"] != LEVELS:
        raise ValueError(f"{name} asks for levels {case['levels']}, not {LEVELS}")
    first = next((k for k in case["known"] if k["hour"] == 1), None)
    if first is None:
        raise ValueError(f"{name} has no hour-1 print")
    p1 = max(1.0, float(first["viewers"]))

    # Per-hour pools of (log-ratio to the launch's own hour 1, weight).
    per_hour = {h: [] for h in range(2, 25)}
    for comp in case.get("comparables") or []:
        if not usable(comp):
            continue
        points = release_day_points(comp)
        v1 = points.get(1)
        if not v1 or v1 <= 0:
            # No release-day hour 1 (e.g. the GTA VI pre-release history):
            # not a launch curve, skip it.
            continue
        if max(points.values()) / v1 > PEAK_CAP:
            # Hour 1 fell before this launch's unlock: its curve is an
            # unlock artefact, not a viewership shape.
            continue
        for h in range(2, 25):
            v = points.get(h)
            if v and v > 0:
                per_hour[h].append((math.log(v / v1), 1.0))

    rows = [
        {"hour": row["hour"], "q": hour_forecast(p1, per_hour, row["hour"])}
        for row in case["forecast"]
    ]
    rows.sort(key=lambda r: r["hour"])
    return {"hours": rows}


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # Every case file, in name order, so two runs write the same bytes.
    for path in sorted(INPUT_DIR.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        forecast = forecast_case(case, path.name)
        (OUTPUT_DIR / f"{path.stem}.out").write_text(
            json.dumps(forecast, separators=(",", ":")) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()
