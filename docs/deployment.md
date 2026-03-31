# Deployment

## Setup

```bash
cd /home/nayab/embedded-monthly-builds/embedded-monthly-builds/projects/pi-edge-vision-event-detector
cp .env.example .env
./scripts/setup_venv.sh
```

## Run Locally

```bash
./scripts/run_prod.sh
```

The app listens on `http://127.0.0.1:8080/` by default.

## Generate Demo Input Explicitly

```bash
. .venv/bin/activate
python scripts/generate_sample_video.py
```

## Install as a Service

```bash
sudo cp systemd/pi-edge-vision-event-detector.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable pi-edge-vision-event-detector.service
sudo systemctl start pi-edge-vision-event-detector.service
sudo systemctl status pi-edge-vision-event-detector.service --no-pager
```

## Logs

```bash
journalctl -u pi-edge-vision-event-detector.service -f
tail -f data/logs/app.log
```

## Media Layout

- `data/media/live/latest.jpg`
- `data/media/snapshots/YYYY/MM/DD/*.jpg`
- `data/media/clips/YYYY/MM/DD/*.avi`
- `data/vision.db`
