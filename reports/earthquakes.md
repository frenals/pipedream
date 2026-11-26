# Earthquake monitor

Every earthquake on Earth of magnitude 2.5 or greater in the last 24 hours, straight from the USGS real-time Feed API.

| generated (UTC) | events | busiest hour |
| --- | --- | --- |
| 2026-11-26 13:03 | 36 | 4 quakes |

## By magnitude band

| band | events | strongest |
| --- | --- | --- |
| M 6.0+   (strong) | 0 | - |
| M 5.0-5.9 (moderate) | 4 | M 5.5 — 204 km S of Taliwang, Indonesia |
| M 4.0-4.9 (light) | 10 | M 4.8 — 225 km S of Taliwang, Indonesia |
| M 2.5-3.9 (minor) | 22 | M 3.7 — 116 km SSW of Nikolski, Alaska |

## Events per UTC hour

| hour (UTC) | events | histogram |
| --- | --- | --- |
| 11-25 13:00 | 2 | ██ |
| 11-25 15:00 | 1 | █ |
| 11-25 16:00 | 2 | ██ |
| 11-25 17:00 | 1 | █ |
| 11-25 18:00 | 4 | ████ |
| 11-25 21:00 | 2 | ██ |
| 11-25 22:00 | 1 | █ |
| 11-25 23:00 | 1 | █ |
| 11-26 00:00 | 2 | ██ |
| 11-26 01:00 | 4 | ████ |
| 11-26 02:00 | 3 | ███ |
| 11-26 03:00 | 2 | ██ |
| 11-26 05:00 | 1 | █ |
| 11-26 06:00 | 2 | ██ |
| 11-26 07:00 | 2 | ██ |
| 11-26 08:00 | 1 | █ |
| 11-26 09:00 | 4 | ████ |
| 11-26 12:00 | 1 | █ |

## Strongest quake in the window

| field | value |
| --- | --- |
| magnitude | M 5.5 |
| where | 204 km S of Taliwang, Indonesia |
| when (UTC) | 2026-11-26 09:08:40 |
| depth | 15.1 km |
| coordinates | -10.56, 117.2 |
| tsunami flag | no |

[USGS event page](https://earthquake.usgs.gov/earthquakes/eventpage/us6000udm8)

## Most reported as felt

| field | value |
| --- | --- |
| magnitude | M 3.6 |
| where | 27 km NW of Ocotillo, CA |
| felt by | 219 people |
| when (UTC) | 2026-11-26 07:20:41 |

[USGS event page](https://earthquake.usgs.gov/earthquakes/eventpage/ci41580392)

---
Gathered by [PipeDream](https://github.com/frenals/PipeDream) from the [USGS Feed API](https://earthquake.usgs.gov/fdsnws/event/1/). Refreshed every 12 hours by GitHub Actions.
