const page = document.body.dataset.page || "dashboard";

const formatTimestamp = (value) => {
  if (!value) return "n/a";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
};

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

function renderRunLog(entries) {
  const root = document.getElementById("run-log");
  if (!root) return;
  if (!entries.length) {
    root.innerHTML = '<div class="list-item muted">No runtime log entries yet.</div>';
    return;
  }
  root.innerHTML = entries.map((entry) => `
    <div class="list-item ${entry.level}">
      <div>
        <strong>${entry.level.toUpperCase()}</strong>
        <span>${entry.message}</span>
      </div>
      <small>${formatTimestamp(entry.created_at)}</small>
    </div>
  `).join("");
}

function renderDashboard(summary) {
  const status = summary.status;
  document.getElementById("status-source").textContent = status.source ? status.source.label : "Unavailable";
  document.getElementById("status-frames").textContent = String(status.frame_count);
  document.getElementById("status-events").textContent = String(summary.stats.total_events);
  document.getElementById("status-last-event").textContent = formatTimestamp(summary.stats.last_event_at);
  document.getElementById("status-message").textContent = status.startup_message;

  const detection = status.last_detection || {};
  document.getElementById("detection-summary").textContent = detection.event_label
    ? `${detection.event_label} · motion ${detection.motion_ratio}`
    : "Awaiting detections";
  document.getElementById("metric-label").textContent = detection.event_label || "idle";
  document.getElementById("metric-motion").textContent = detection.motion_ratio ?? "-";
  document.getElementById("metric-contours").textContent = detection.contour_count ?? "-";
  document.getElementById("metric-advanced").textContent = detection.metadata?.advanced_detection_enabled ? "Enabled" : "Disabled";
  document.getElementById("metric-picam").textContent = status.hardware_check?.pi_camera?.available ? "Yes" : "No";
  document.getElementById("metric-usb").textContent = String(status.hardware_check?.usb_candidates?.length || 0);

  const preview = document.getElementById("live-preview");
  preview.src = status.preview_url ? `${status.preview_url}?ts=${Date.now()}` : "";

  const events = document.getElementById("event-history");
  if (!summary.recent_events.length) {
    events.innerHTML = '<div class="list-item muted">No events recorded yet.</div>';
  } else {
    events.innerHTML = summary.recent_events.map((event) => `
      <article class="event-card">
        ${event.snapshot_url ? `<img src="${event.snapshot_url}" alt="Event snapshot">` : ""}
        <div class="event-card-body">
          <strong>${event.event_label}</strong>
          <span>${formatTimestamp(event.created_at)}</span>
          <span>Motion ratio: ${event.motion_ratio}</span>
          <div class="event-links">
            ${event.clip_url ? `<a href="${event.clip_url}" target="_blank">Clip</a>` : ""}
            ${event.snapshot_url ? `<a href="${event.snapshot_url}" target="_blank">Snapshot</a>` : ""}
          </div>
        </div>
      </article>
    `).join("");
  }

  renderRunLog(summary.run_logs);
}

function populateConfig(config) {
  document.getElementById("cfg-sensitivity").value = config.detection.sensitivity;
  document.getElementById("cfg-motion").value = config.detection.min_motion_area_ratio;
  document.getElementById("cfg-cooldown").value = config.detection.cooldown_seconds;
  document.getElementById("cfg-retention").value = config.storage.retention_days;
  document.getElementById("cfg-advanced").checked = config.detection.advanced_detection_enabled;
  document.getElementById("config-json").textContent = JSON.stringify(config, null, 2);
}

async function refreshDashboard() {
  const summary = await fetchJson("/api/summary");
  renderDashboard(summary);
}

async function refreshConfig() {
  const config = await fetchJson("/api/config");
  populateConfig(config);
}

async function submitConfig(event) {
  event.preventDefault();
  const payload = {
    detection: {
      sensitivity: Number(document.getElementById("cfg-sensitivity").value),
      min_motion_area_ratio: Number(document.getElementById("cfg-motion").value),
      cooldown_seconds: Number(document.getElementById("cfg-cooldown").value),
      advanced_detection_enabled: document.getElementById("cfg-advanced").checked,
    },
    storage: {
      retention_days: Number(document.getElementById("cfg-retention").value),
    },
  };
  const config = await fetchJson("/api/config", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  populateConfig(config);
  document.getElementById("config-status").textContent = `Saved at ${new Date().toLocaleTimeString()}`;
}

if (page === "dashboard") {
  refreshDashboard().catch((error) => console.error(error));
  setInterval(() => refreshDashboard().catch((error) => console.error(error)), 4000);
}

if (page === "config") {
  refreshConfig().catch((error) => console.error(error));
  document.getElementById("config-form").addEventListener("submit", (event) => {
    submitConfig(event).catch((error) => console.error(error));
  });
}
