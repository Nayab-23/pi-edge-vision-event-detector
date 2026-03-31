# Pi Edge Vision Event Detector

Raspberry Pi edge-vision service that selects the best available local video source, detects motion-driven events, records media, stores metadata, and exposes a local dashboard for review.

## Features

- Video source abstraction with automatic priority:
  - Raspberry Pi camera via `picamera2` when a camera is present
  - USB webcam when a usable `/dev/video*` camera is detected
  - generated sample video for development and demo fallback
- Event detection:
  - motion-detection baseline
  - configurable sensitivity and motion-area threshold
  - cooldown and pre/post event capture windows
  - optional HOG-based person detection behind a config flag
- Capture pipeline:
  - event snapshots
  - short event clips with prebuffered frames
  - persisted metadata in SQLite
- Review surface:
  - local FastAPI REST API
  - dashboard with live preview, event history, and run log
  - config page for detector tuning
- Reliability:
  - startup hardware check
  - rotating file logs
  - storage retention policy for old media and excess event history
  - systemd unit for continuous service mode

## Runtime Modes

The app never depends on optional hardware being present.

1. Prefer Raspberry Pi camera if detected.
2. Otherwise try a USB webcam.
3. Otherwise generate and loop a synthetic sample video at `data/sample/demo_input.avi`.

That fallback path is the expected mode on this Pi today because no official Pi camera or USB webcam was detected.

## API

- `GET /api/summary`
- `GET /api/status`
- `GET /api/events`
- `GET /api/stats`
- `GET /api/config`
- `PUT /api/config`
- `GET /api/logs`

## Local Run

```bash
cd /home/nayab/embedded-monthly-builds/embedded-monthly-builds/projects/pi-edge-vision-event-detector
cp .env.example .env
./scripts/setup_venv.sh
./scripts/run_prod.sh
```

Open:

- Dashboard: `http://127.0.0.1:8080/`
- Config page: `http://127.0.0.1:8080/config`
- API summary: `http://127.0.0.1:8080/api/summary`

## Development

```bash
make install
make test
make run
```

## Repository Layout

- `app/`: FastAPI app, background worker, detector, recorder, store, and source selection
- `templates/`: dashboard and config views
- `static/`: dashboard assets
- `docs/`: architecture, tradeoffs, deployment notes, and screenshots folder
- `systemd/`: service unit
- `tests/`: pytest coverage for non-camera logic
- `scripts/`: setup, run, sample generation, and install helpers

## Deployment

```bash
sudo cp systemd/pi-edge-vision-event-detector.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable pi-edge-vision-event-detector.service
sudo systemctl start pi-edge-vision-event-detector.service
```

See [`docs/deployment.md`](docs/deployment.md) for the full deployment and demo workflow.
