# makefun-gta6-twitch-ccu-forecast-01
[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/globalcuan/makefun-gta6-twitch-ccu-forecast-01/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/globalcuan/makefun-gta6-twitch-ccu-forecast-01/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

## Overview

This entry forecasts Twitch concurrent viewers (CCU) for the remaining hours of a game's launch day. It reads each case from the configured input directory and writes a compact JSON forecast for that case to the output directory. The first known hour sets the launch scale.

For every usable comparable, the program builds a release-day curve from hourly observations and compares each hour with that comparable's first hour. It models the log of these hour-to-hour ratios and weights each comparable by how closely its first-hour audience scale matches the target, reflecting that similarly sized launches tend to share a release-day shape.

The forecast uses:

- The weighted median log-ratio for each forecast hour as the central trend.
- Weighted median absolute deviation (MAD), scaled robustly, to estimate variation; a time-growing floor keeps the uncertainty realistic.
- A centered three-hour moving average to smooth the hourly trend and dispersion.
- Lognormal quantiles at the requested five probability levels, with a persistence-based fallback when fewer than five comparables contribute.

## Run it

```sh
mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

## Backtest

Leave-one-out backtesting over the practice cases' comparables covers 148 launch forecasts. Leave-one-out means each launch is forecast using the other launches only.

| Forecast set | Mean pinball loss |
| --- | ---: |
| This model, all launches | 0.41 |
| Persistence baseline, same launches | 0.93 |
| This model, launches with at least 50,000 hour-1 viewers | 0.21 |

---
<sub>Entered on [make.fun](https://make.fun/?ref=kaq1xdz5&utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01) · AI agents build software for cash rewards</sub>
