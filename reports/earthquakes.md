# Earthquake monitor

Every earthquake on Earth of magnitude 2.5 or greater in the last 24 hours, straight from the USGS real-time Feed API.

| generated (UTC) | events | busiest hour |
| --- | --- | --- |
| 2026-11-28 06:20 | 39 | 4 quakes |

## By magnitude band

| band | events | strongest |
| --- | --- | --- |
| M 6.0+   (strong) | 0 | - |
| M 5.0-5.9 (moderate) | 2 | M 5.2 — 93 km W of San Antonio de los Cobres, Argentina |
| M 4.0-4.9 (light) | 12 | M 4.8 — 167 km N of Hicks Bay, New Zealand |
| M 2.5-3.9 (minor) | 25 | M 3.6 — 24 km SSW of Boca de Yuma, Dominican Republic |

## Events per UTC hour

| hour (UTC) | events | histogram |
| --- | --- | --- |
| 11-27 07:00 | 1 | █ |
| 11-27 10:00 | 1 | █ |
| 11-27 11:00 | 1 | █ |
| 11-27 12:00 | 3 | ███ |
| 11-27 13:00 | 2 | ██ |
| 11-27 14:00 | 2 | ██ |
| 11-27 16:00 | 2 | ██ |
| 11-27 17:00 | 1 | █ |
| 11-27 18:00 | 1 | █ |
| 11-27 20:00 | 2 | ██ |
| 11-27 21:00 | 2 | ██ |
| 11-27 22:00 | 2 | ██ |
| 11-27 23:00 | 4 | ████ |
| 11-28 00:00 | 3 | ███ |
| 11-28 01:00 | 3 | ███ |
| 11-28 02:00 | 3 | ███ |
| 11-28 03:00 | 3 | ███ |
| 11-28 05:00 | 2 | ██ |
| 11-28 06:00 | 1 | █ |

## Strongest quake in the window

| field | value |
| --- | --- |
| magnitude | M 5.2 |
| where | 93 km W of San Antonio de los Cobres, Argentina |
| when (UTC) | 2026-11-28 02:25:05 |
| depth | 174.6 km |
| coordinates | -24.3, -67.24 |
| tsunami flag | no |

[USGS event page](https://earthquake.usgs.gov/earthquakes/eventpage/us6000ue1h)

## Most reported as felt

| field | value |
| --- | --- |
| magnitude | M 4.0 |
| where | 10 km WSW of Point MacKenzie, Alaska |
| felt by | 445 people |
| when (UTC) | 2026-11-28 06:11:42 |

[USGS event page](https://earthquake.usgs.gov/earthquakes/eventpage/aka2026xnvqjt)

---
Gathered by [PipeDream](https://github.com/frenals/PipeDream) from the [USGS Feed API](https://earthquake.usgs.gov/fdsnws/event/1/). Refreshed every 12 hours by GitHub Actions.
