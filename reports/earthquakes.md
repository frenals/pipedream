# Earthquake monitor

Every earthquake on Earth of magnitude 2.5 or greater in the last 24 hours, straight from the USGS real-time Feed API.

| generated (UTC) | events | busiest hour |
| --- | --- | --- |
| 2026-11-27 20:41 | 24 | 4 quakes |

## By magnitude band

| band | events | strongest |
| --- | --- | --- |
| M 6.0+   (strong) | 0 | - |
| M 5.0-5.9 (moderate) | 3 | M 5.1 — 107 km SSE of Auki, Solomon Islands |
| M 4.0-4.9 (light) | 5 | M 4.8 — 183 km SSE of Vilyuchinsk, Russia |
| M 2.5-3.9 (minor) | 16 | M 3.8 — 132 km NNW of Nikolski, Alaska |

## Events per UTC hour

| hour (UTC) | events | histogram |
| --- | --- | --- |
| 11-26 21:00 | 2 | ██ |
| 11-26 22:00 | 4 | ████ |
| 11-26 23:00 | 2 | ██ |
| 11-27 00:00 | 1 | █ |
| 11-27 02:00 | 1 | █ |
| 11-27 04:00 | 2 | ██ |
| 11-27 07:00 | 1 | █ |
| 11-27 10:00 | 1 | █ |
| 11-27 11:00 | 1 | █ |
| 11-27 12:00 | 3 | ███ |
| 11-27 13:00 | 1 | █ |
| 11-27 14:00 | 2 | ██ |
| 11-27 16:00 | 1 | █ |
| 11-27 17:00 | 1 | █ |
| 11-27 18:00 | 1 | █ |

## Strongest quake in the window

| field | value |
| --- | --- |
| magnitude | M 5.1 |
| where | 107 km SSE of Auki, Solomon Islands |
| when (UTC) | 2026-11-27 00:07:00 |
| depth | 74.1 km |
| coordinates | -9.58, 161.24 |
| tsunami flag | no |

[USGS event page](https://earthquake.usgs.gov/earthquakes/eventpage/us6000udt9)

## Most reported as felt

| field | value |
| --- | --- |
| magnitude | M 2.8 |
| where | 13 km E of Susitna North, Alaska |
| felt by | 1 people |
| when (UTC) | 2026-11-27 18:53:03 |

[USGS event page](https://earthquake.usgs.gov/earthquakes/eventpage/aka2026xmyzzg)

---
Gathered by [PipeDream](https://github.com/frenals/PipeDream) from the [USGS Feed API](https://earthquake.usgs.gov/fdsnws/event/1/). Refreshed every 12 hours by GitHub Actions.
