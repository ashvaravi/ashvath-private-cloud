const statusLabel = document.getElementById("statusLabel");
const pidLabel = document.getElementById("pidLabel");
const uptime = document.getElementById("uptime");
const autostart = document.getElementById("autostart");
const exitCode = document.getElementById("exitCode");
const ring = document.getElementById("ring");
const ringText = document.getElementById("ringText");
const logs = document.getElementById("logs");

const startBtn = document.getElementById("startBtn");
const stopBtn = document.getElementById("stopBtn");
const restartBtn = document.getElementById("restartBtn");
const clearBtn = document.getElementById("clearBtn");

let logsHidden = false;

function formatUptime(seconds) {
  seconds = Number(seconds || 0);

  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;

  if (h > 0) return `${h}h ${m}m ${s}s`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

async function api(path, options = {}) {
  const response = await fetch(path, options);
  return response.json();
}

function setBusy(isBusy) {
  startBtn.disabled = isBusy;
  stopBtn.disabled = isBusy;
  restartBtn.disabled = isBusy;
}

function renderStatus(status) {
  const running = Boolean(status.running);

  statusLabel.textContent = running ? "LISTENING" : "STOPPED";
  statusLabel.style.color = running ? "#86efac" : "#ffb4b4";

  pidLabel.textContent = running && status.pid ? `PID: ${status.pid}` : "PID: —";
  uptime.textContent = formatUptime(status.uptime_seconds);
  autostart.textContent = status.autostart_enabled ? "ON" : "OFF";
  exitCode.textContent = status.last_exit_code === null || status.last_exit_code === undefined
    ? "—"
    : String(status.last_exit_code);

  ring.classList.toggle("running", running);
  ring.classList.toggle("idle", !running);
  ringText.textContent = running ? "LIVE" : "OFF";

  startBtn.textContent = running ? "Listening Active" : "Start 24/7 Listening";
}

function renderLogs(items) {
  if (logsHidden) return;

  if (!items || items.length === 0) {
    logs.textContent = "No logs yet.";
    return;
  }

  logs.textContent = items.join("\n");
  logs.scrollTop = logs.scrollHeight;
}

async function refresh() {
  try {
    const statusData = await api("/api/status");
    renderStatus(statusData);

    const logData = await api("/api/logs?limit=220");
    renderLogs(logData.logs);
  } catch (error) {
    statusLabel.textContent = "SERVER ERROR";
    statusLabel.style.color = "#ffb4b4";
    logs.textContent = `Unable to connect to Vetri Voice Station server.\n${error}`;
  }
}

startBtn.addEventListener("click", async () => {
  setBusy(true);
  try {
    const result = await api("/api/start", { method: "POST" });
    renderStatus(result.status);
    await refresh();
  } finally {
    setBusy(false);
  }
});

stopBtn.addEventListener("click", async () => {
  setBusy(true);
  try {
    const result = await api("/api/force-stop", { method: "POST" });
    renderStatus(result.status);
    await refresh();
  } finally {
    setBusy(false);
  }
});

restartBtn.addEventListener("click", async () => {
  setBusy(true);
  try {
    await api("/api/force-stop", { method: "POST" });
    const result = await api("/api/start", { method: "POST" });
    renderStatus(result.status);
    await refresh();
  } finally {
    setBusy(false);
  }
});

clearBtn.addEventListener("click", () => {
  logs.textContent = "View cleared. New logs will appear automatically.";
  logsHidden = true;

  setTimeout(() => {
    logsHidden = false;
    refresh();
  }, 2500);
});

refresh();
setInterval(refresh, 1800);
