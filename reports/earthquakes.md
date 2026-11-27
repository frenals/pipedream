# Earthquake monitor

Every earthquake on Earth of magnitude 2.5 or greater in the last 24 hours, straight from the USGS real-time Feed API.

| generated (UTC) | events | busiest hour |
| --- | --- | --- |
| 2026-11-27 00:58 | 37 | 4 quakes |

## By magnitude band

| band | events | strongest |
| --- | --- | --- |
| M 6.0+   (strong) | 0 | - |
| M 5.0-5.9 (moderate) | 7 | M 5.7 — Revilla Gigedo Islands region |
| M 4.0-4.9 (light) | 9 | M 4.8 — 225 km S of Taliwang, Indonesia |
| M 2.5-3.9 (minor) | 21 | M 3.9 — 72 km N of Charlotte Amalie, U.S. Virgin Islands |

## Events per UTC hour

| hour (UTC) | events | histogram |
| --- | --- | --- |
| 11-26 01:00 | 4 | ████ |
| 11-26 02:00 | 3 | ███ |
| 11-26 03:00 | 2 | ██ |
| 11-26 05:00 | 1 | █ |
| 11-26 06:00 | 2 | ██ |
| 11-26 07:00 | 2 | ██ |
| 11-26 08:00 | 1 | █ |
| 11-26 09:00 | 4 | ████ |
| 11-26 12:00 | 2 | ██ |
| 11-26 14:00 | 2 | ██ |
| 11-26 15:00 | 2 | ██ |
| 11-26 16:00 | 1 | █ |
| 11-26 18:00 | 1 | █ |
| 11-26 19:00 | 1 | █ |
| 11-26 20:00 | 1 | █ |
| 11-26 21:00 | 2 | ██ |
| 11-26 22:00 | 4 | ████ |
| 11-26 23:00 | 1 | █ |
| 11-27 00:00 | 1 | █ |

## Strongest quake in the window

| field | value |
| --- | --- |
| magnitude | M 5.7 |
| where | Revilla Gigedo Islands region |
| when (UTC) | 2026-11-26 15:26:44 |
| depth | 10 km |
| coordinates | 19.81, -109.3 |
| tsunami flag | no |

[USGS event page](https://earthquake.usgs.gov/earthquakes/eventpage/us6000udq5)

## Most reported as felt

| field | value |
| --- | --- |
| magnitude | M 3.6 |
| where | 27 km NW of Ocotillo, CA |
| felt by | 237 people |
| when (UTC) | 2026-11-26 07:20:41 |

[USGS event page](https://earthquake.usgs.gov/earthquakes/eventpage/ci41580392)

---
Gathered by [PipeDream](https://github.com/frenals/PipeDream) from the [USGS Feed API](https://earthquake.usgs.gov/fdsnws/event/1/). Refreshed every 12 hours by GitHub Actions.
