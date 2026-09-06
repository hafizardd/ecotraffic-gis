# EcoTraffic GIS Implementation Source of Truth

This document describes the active implementation, not future product ideas.

## Active Stack

- Frontend: Next.js, React, TypeScript, MapLibre, and CSS modules/global styles.
- Backend: FastAPI, Celery, Redis, PostgreSQL, PostGIS, SQLAlchemy, and Pydantic.
- Computer vision: YOLO vehicle detection through the backend inference worker.

## Camera Inventory

- 56 cameras are seeded in the product inventory.
- 2 cameras are `LIVE` and eligible for online inference.
- 54 cameras are `HISTORICAL`, `REPLAY`, or `SYNTHETIC` and must not enter the live inference queue.

The camera `data_source` and processing state are independent. A camera can remain
visible in the map while being excluded from online inference.

## Freshness Service Levels

- Camera target: approximately 10 seconds between successful live observations.
- Camera status is `fresh` through 30 seconds, `aging` through 90 seconds, and
  `stale` after 90 seconds. Missing timestamps are `unknown`.
- Segment calculations currently target a five-minute analytical cadence. Segment
  freshness is based on the observation and calculation timestamps, not video playback.

The dashboard must expose these states and must not use a static `LIVE` label as a
claim that data is current.

## Data Semantics

Public vehicle categories are `car`, `motorcycle`, `bus`, and `truck`. Internal YOLO
or fuel categories may be retained only as implementation details.

`vehicle_count_semantics: snapshot_occupancy` means vehicles visible in a processed
frame or recent snapshot average. It is not hourly traffic volume. Hourly volume is
available only for valid interval counts or an explicitly labeled model/estimate.

Camera counts are described in the UI as:

> Vehicles visible in the latest processed frame or recent snapshot average. This is not hourly traffic volume.

## Emission Presentation

- Segment line color represents canonical total emission intensity in `g/h`.
- AHP priority and decision score are separate fields and are never encoded as the
  emission color itself.
- Camera markers use canonical total CO2 emission rate when available; CO is shown
  separately in detail views.
- Emission results expose their calculation model, units, factor version, source,
  observation period, calculation timestamp, and freshness state.
- Missing values are rendered as `Data tidak tersedia` or `N/A`, never as zero.

Camera emissions are estimates from visible occupancy using the shared factor model.
The legacy one-kilometre-per-observation-minute assumption is metadata, not an
implicit traffic-flow measurement.

## Historical and Synthetic Data

Historical, replay, and synthetic records remain available for trend and audit views,
but are labeled with their source mode and observation period. They are not presented
as live feeds and do not contribute to current live summaries unless an endpoint
explicitly requests historical data.

## Completed Versus Planned

Completed behavior is documented in this file and the API contracts. Planned work
must remain explicitly labeled in implementation plans. In particular, object
tracking, line-crossing flow estimation, and secondary reporting pages are not
considered live traffic-flow measurements until implemented and verified.
