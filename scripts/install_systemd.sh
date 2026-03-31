#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
service_name="pi-edge-vision-event-detector.service"

sudo cp "${project_dir}/systemd/${service_name}" "/etc/systemd/system/${service_name}"
sudo systemctl daemon-reload
sudo systemctl enable "${service_name}"
sudo systemctl restart "${service_name}"
sudo systemctl status "${service_name}" --no-pager
