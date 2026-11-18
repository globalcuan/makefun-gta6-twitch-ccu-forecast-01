"""Forecast Twitch launch-day viewers for make.fun contest cases.

Each case file is JSON containing the launch game, known hourly observations,
comparable launches, and requested forecast hours. The program writes one JSON
result per case, with quantiles for each requested hour. It is designed for the
8-second contest runtime, uses only the Python standard library, and produces
deterministic output.

The forecast derives release-day hour-to-hour ratios from comparable curves,
then estimates weighted median log-ratios and robust spreads. Comparable curves
are weighted by scale similarity: launches with hour-1 audiences closer to the
target's hour-1 audience receive more weight. Smoothed lognormal quantiles give
the forecast, with a persistence-based fallback when comparable data is sparse.
"""

import json
import math
import os
import sys
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


ZS = (-1.644854, -0.674490, 0.0, 0.674490, 1.644854)


def parse_time(value):
    """Parse ISO timestamps, including the common UTC Z suffix."""
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def weighted_median(values, weights):
    pairs = sorted(zip(values, weights), key=lambda pair: pair[0])
    if not pairs:
        return None
    halfway = sum(weight for _, weight in pairs) / 2.0
    cumulative = 0.0
    for value, weight in pairs:
        cumulative += weight
        if cumulative >= halfway:
            return value


def finite_positive(value):
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) and number > 0 else None


def release_curve(comparable, start):
    """Aggregate a comparable's points into its 24 release-day hours."""
    end = start + timedelta(hours=24)
    buckets = {}
    for point in comparable.get("hourly", []):
        stamp = parse_time(point.get("from"))
        viewers = finite_positive(point.get("viewers"))
        if stamp is None or viewers is None:
            continue
        try:
            if stamp < start or stamp >= end:
                continue
            hour = 1 + int((stamp - start).total_seconds() // 3600)
        except TypeError:
            continue
        if 1 <= hour <= 24:
            buckets.setdefault(hour, []).append(viewers)
    return {hour: sum(values) / len(values) for hour, values in buckets.items()}


def round2(value):
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def forecast(case):
    first = next((row for row in case.get("known", []) if row.get("hour") == 1), None)
    if first is None:
        raise ValueError("case is missing the known hour-1 row")
    p1 = max(1.0, finite_positive(first.get("viewers")) or 1.0)

    ratios = {hour: [] for hour in range(2, 25)}
    ratio_weights = {hour: [] for hour in ratios}
    target_name = case.get("game", {}).get("name")
    for comparable in case.get("comparables", []):
        if comparable.get("name") == target_name:
            continue
        start = parse_time(comparable.get("day_start"))
        if start is None:
            continue
        curve = release_curve(comparable, start)
        base = curve.get(1)
        if base is None or base <= 0:
            continue
        # Similar-sized launches share a release-day shape, as verified by leave-one-out practice-comparable backtests.
        weight = math.exp(-0.5 * ((math.log10(base) - math.log10(p1)) / 0.6) ** 2)
        for hour in ratios:
            value = curve.get(hour)
            if value is not None and value > 0:
                ratios[hour].append(math.log(value / base))
                ratio_weights[hour].append(weight)

    # Smooth hour-to-hour median and MAD estimates using available neighbors.
    medians = {}
    spreads = {}
    for hour, values in ratios.items():
        if values:
            weights = ratio_weights[hour]
            center = weighted_median(values, weights)
            medians[hour] = center
            spreads[hour] = 1.4826 * weighted_median(
                [abs(value - center) for value in values], weights
            )

    smooth_medians = {}
    smooth_spreads = {}
    for hour in ratios:
        nearby = [neighbor for neighbor in (hour - 1, hour, hour + 1) if neighbor in ratios]
        available_m = [medians[n] for n in nearby if n in medians]
        available_s = [spreads[n] for n in nearby if n in spreads]
        if available_m:
            smooth_medians[hour] = sum(available_m) / len(available_m)
        if available_s:
            smooth_spreads[hour] = sum(available_s) / len(available_s)

    rows = []
    for request in case.get("forecast", []):
        hour = request.get("hour")
        try:
            h = int(hour)
        except (TypeError, ValueError, OverflowError):
            h = 2
        h = min(24, max(2, h))
        if len(ratios[h]) < 5:
            sigma = 0.15 * math.sqrt(h - 1)
            values = [p1 * math.exp(z * sigma) for z in ZS]
        else:
            center = smooth_medians.get(h, weighted_median(ratios[h], ratio_weights[h]))
            spread = max(smooth_spreads.get(h, 0.0), 0.20 + 0.015 * math.sqrt(h - 1))
            spread = min(spread, 1.2)
            values = [p1 * math.exp(center + z * spread) for z in ZS]

        bounded = [min(1e9, max(0.01, value)) for value in values]
        for index in range(1, len(bounded)):
            bounded[index] = max(bounded[index], bounded[index - 1])
        quantiles = [round2(value) for value in bounded]
        rows.append({"hour": hour, "q": quantiles})
    return {"hours": rows}


def main():
    input_dir = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
    output_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    output_dir.mkdir(parents=True, exist_ok=True)
    for input_path in sorted(input_dir.glob("*.in"), key=lambda path: path.name):
        with input_path.open("r", encoding="utf-8") as source:
            case = json.load(source)
        result = forecast(case)
        output_path = output_dir / (str(case["id"]) + ".out")
        with output_path.open("w", encoding="utf-8", newline="\n") as target:
            target.write(json.dumps(result, separators=(",", ":"), allow_nan=False))
            target.write("\n")


if __name__ == "__main__":
    main()
