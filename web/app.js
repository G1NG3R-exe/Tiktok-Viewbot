/* TikTok Viewbot — frontend logic: form, polling, live log */

const $ = (sel) => document.querySelector(sel);

const form = $("#boost-form");
const urlInput = $("#url");
const viewsInput = $("#views");
const workersInput = $("#workers");
const proxyToggle = $("#use-proxies");
const startBtn = $("#start-btn");
const stopBtn = $("#stop-btn");
const formError = $("#form-error");
const runPanel = $("#run-panel");
const statusPill = $("#status-pill");
const statusText = $("#status-text");
const statBaseline = $("#stat-baseline");
const statSuccesses = $("#stat-successes");
const statAttempts = $("#stat-attempts");
const statElapsed = $("#stat-elapsed");
const bar = $(".bar");
const barFill = $("#bar-fill");
const barCount = $("#bar-count");
const logBox = $("#log");

const TERMINAL = ["idle", "done", "error", "stopped"];
const STATUS_LABELS = {
  idle: "Ready",
  queued: "Queued",
  resolving: "Preparing",
  proxies: "Finding proxies",
  running: "Running",
  done: "Done",
  error: "Error",
  stopped: "Stopped",
};

let renderedLogs = 0;
let lastSnapshot = null;

const isBusy = (s) => s && !TERMINAL.includes(s.status);

function fmt(n) {
  return n === null || n === undefined ? "–" : Number(n).toLocaleString("en-US");
}

function fmtTime(ts) {
  const d = new Date(ts * 1000);
  return d.toLocaleTimeString("en-GB", { hour12: false });
}

function fmtElapsed(snapshot) {
  if (!snapshot.started_at) return "–";
  const end = isBusy(snapshot) ? Date.now() / 1000 : snapshot.finished_at;
  if (!end) return "–";
  const total = Math.max(0, Math.floor(end - snapshot.started_at));
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

function renderLog(log) {
  if (log.length < renderedLogs) {
    logBox.innerHTML = "";
    renderedLogs = 0;
  }
  if (log.length === 0 && renderedLogs === 0) {
    logBox.innerHTML = '<div class="placeholder">Waiting for the bot to start…</div>';
  }
  const nearBottom =
    logBox.scrollHeight - logBox.scrollTop - logBox.clientHeight < 60;

  for (let i = renderedLogs; i < log.length; i++) {
    const entry = log[i];
    if (i === 0) logBox.innerHTML = ""; // replace placeholder
    const line = document.createElement("div");
    line.className = `line ${entry.level}`;
    line.innerHTML =
      `<span class="time">${fmtTime(entry.t)}</span>` +
      `<span class="msg"></span>`;
    line.querySelector(".msg").textContent = entry.text;
    logBox.appendChild(line);
  }
  renderedLogs = log.length;

  if (nearBottom) logBox.scrollTop = logBox.scrollHeight;
}

function render(snapshot) {
  lastSnapshot = snapshot;
  const busy = isBusy(snapshot);
  const started = snapshot.status !== "idle";

  // status pill
  statusText.textContent = STATUS_LABELS[snapshot.status] || snapshot.status;
  statusPill.className = "pill";
  if (["queued", "resolving", "proxies", "running"].includes(snapshot.status)) {
    statusPill.classList.add("running");
  } else if (snapshot.status === "done") {
    statusPill.classList.add("done");
  } else if (snapshot.status === "error" || snapshot.status === "stopped") {
    statusPill.classList.add("error");
  }

  // form lock
  urlInput.disabled = busy;
  viewsInput.disabled = busy;
  workersInput.disabled = busy;
  proxyToggle.disabled = busy;
  startBtn.disabled = busy;

  // run panel
  runPanel.hidden = !started;
  if (!started) return;

  statBaseline.textContent = fmt(snapshot.baseline);
  statSuccesses.textContent = fmt(snapshot.successes);
  statAttempts.textContent = fmt(snapshot.attempts);
  statElapsed.textContent = fmtElapsed(snapshot);

  const pct =
    snapshot.target > 0
      ? Math.min(100, (snapshot.successes / snapshot.target) * 100)
      : 0;
  barFill.style.width = `${pct}%`;
  bar.classList.toggle("filling", busy);
  barCount.textContent = `${snapshot.successes} / ${snapshot.target} views delivered`;

  if (snapshot.status === "done") {
    barCount.textContent = `${snapshot.successes} / ${snapshot.target} — check TikTok in 10–60 min`;
  }
  if (snapshot.error) {
    barCount.textContent = snapshot.error;
  }

  stopBtn.hidden = !busy;
  renderLog(snapshot.log);
}

async function poll() {
  try {
    const res = await fetch("/api/status");
    if (res.ok) render(await res.json());
  } catch {
    /* server briefly unreachable — keep polling */
  }
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  formError.hidden = true;
  const body = {
    url: urlInput.value.trim(),
    views: parseInt(viewsInput.value, 10) || 0,
    workers: parseInt(workersInput.value, 10) || 8,
    use_proxies: proxyToggle.checked,
  };
  if (!body.url) {
    formError.textContent = "Paste a TikTok video URL first.";
    formError.hidden = false;
    return;
  }
  if (body.views < 1) {
    formError.textContent = "Views must be at least 1.";
    formError.hidden = false;
    return;
  }
  startBtn.disabled = true;
  try {
    const res = await fetch("/api/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      formError.textContent = err.detail || "Could not start the job.";
      formError.hidden = false;
      startBtn.disabled = false;
      return;
    }
    renderedLogs = 0;
    logBox.innerHTML = "";
    poll();
  } catch {
    formError.textContent = "Server unreachable — is server.py still running?";
    formError.hidden = false;
    startBtn.disabled = false;
  }
});

stopBtn.addEventListener("click", async () => {
  stopBtn.disabled = true;
  try {
    await fetch("/api/stop", { method: "POST" });
  } finally {
    setTimeout(() => (stopBtn.disabled = false), 1500);
  }
});

poll();
setInterval(poll, 1000);
