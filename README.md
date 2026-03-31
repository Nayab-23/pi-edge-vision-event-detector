# Pi Edge Vision Event Detector

Raspberry Pi edge-vision service that selects the best available local video source, detects motion-driven events, records media, stores metadata, and exposes a local dashboard for review.

## Planned Scope

- Raspberry Pi camera, USB camera, and sample-video fallback
- Motion detection with configurable sensitivity and cooldown
- Event snapshots and short clips
- SQLite-backed event history and config
- Local FastAPI dashboard and REST API
- systemd service mode

## Development

```bash
make install
make run
```
