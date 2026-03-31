# Architecture

## Overview

The application is a FastAPI service with a background worker loop. The worker owns video ingestion, detection, recording, retention, and runtime state, while the web layer serves both machine-readable APIs and a browser dashboard.

## Main Modules

### Video Input

- `app/video/probe.py` inspects Raspberry Pi camera availability and `/dev/video*` inventory.
- `app/video/sources.py` chooses one source:
  - `Picamera2Source`
  - `OpenCVCameraSource`
  - `SampleVideoSource`
- `app/video/sample_video.py` generates a deterministic synthetic demo video when no hardware source is available.

### Detection

- `app/services/detector.py` implements the baseline motion detector using a running background model.
- Optional HOG-based person detection is only enabled when configured, because it is significantly heavier than pure motion detection on Raspberry Pi-class hardware.

### Recording and Persistence

- `app/services/recorder.py` keeps a pre-event frame buffer, saves an annotated snapshot, and writes a short AVI clip after the event window closes.
- `app/services/store.py` stores event metadata, runtime config, and run-log entries in SQLite.
- `app/services/retention.py` prunes old events and removes stale media files.

### Runtime

- `app/services/runtime.py` ties everything together:
  - startup hardware check
  - source selection and fallback switching
  - worker loop
  - live preview generation
  - API-facing status and summary state

### Web Layer

- `app/routes/api.py` exposes summary, events, stats, config, and logs.
- `app/routes/pages.py` serves the dashboard and config pages.
- The browser polls the API and reads media from the mounted `/media` path.

## Data Flow

1. App startup initializes logging and SQLite, then selects a source.
2. The worker reads frames at the configured FPS.
3. The detector scores motion and optional person evidence.
4. The recorder saves snapshots and clips for triggered events.
5. The store persists metadata and the dashboard surfaces the results.
6. Retention runs periodically to keep storage bounded.
