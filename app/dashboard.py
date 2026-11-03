"""Small same-origin dashboard served by the FastAPI application."""

DASHBOARD_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#f4f7fb">
  <title>Pulsewatch · Uptime Monitor</title>
  <style>
    :root { color-scheme:light; --bg:#f4f7fb; --panel:#fff; --line:#e4eaf2; --muted:#718096; --text:#172b4d; --accent:#126e69; --accent-dark:#0d5652; --red:#b42332; --yellow:#9a6700; }
    * { box-sizing:border-box; }
    body { margin:0; background:linear-gradient(180deg,#eaf4f3 0,#f4f7fb 260px); color:var(--text); font:15px/1.55 Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif; min-height:100vh; }
    main { width:min(1120px,calc(100% - 40px)); margin:0 auto; padding:34px 0 64px; }
    header { display:flex; justify-content:space-between; align-items:center; gap:20px; margin-bottom:28px; }
    header > div:first-child { position:relative; padding-left:48px; }
    header > div:first-child::before { content:"P"; position:absolute; left:0; top:4px; display:grid; place-items:center; width:36px; height:36px; border-radius:12px; background:var(--accent); color:white; font-weight:850; box-shadow:0 5px 12px #126e6933; }
    .eyebrow { color:var(--accent); font-size:11px; font-weight:800; letter-spacing:.13em; text-transform:uppercase; }
    h1 { margin:3px 0 0; font-size:clamp(27px,4vw,36px); line-height:1.15; letter-spacing:-.04em; }
    h2 { margin:0 0 16px; font-size:18px; letter-spacing:-.02em; }
    p { color:var(--muted); }
    a { color:var(--accent); font-weight:650; text-decoration:none; }
    a:hover { color:var(--accent-dark); text-decoration:underline; }
    .panel,.monitor { background:var(--panel); border:1px solid var(--line); border-radius:16px; box-shadow:0 8px 28px #1b36510b; }
    .panel { padding:24px; margin-bottom:18px; }
    #dashboard > .panel:first-child { border-top:3px solid var(--accent); }
    .login { max-width:460px; margin:56px auto; padding:30px; }
    .grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:16px; }
    label { display:block; color:#52647b; font-size:12px; font-weight:700; margin:0 0 6px; }
    input { width:100%; border:1px solid #d8e0ea; background:#fbfcfe; color:var(--text); padding:11px 12px; border-radius:9px; font:inherit; transition:border-color .15s,box-shadow .15s; }
    input:focus { outline:0; border-color:var(--accent); box-shadow:0 0 0 3px #126e691c; }
    button { border:1px solid var(--accent); border-radius:9px; background:var(--accent); color:#fff; padding:10px 15px; font:700 13px system-ui,sans-serif; cursor:pointer; transition:background .15s,transform .15s,box-shadow .15s; }
    button:hover:not(:disabled) { background:var(--accent-dark); box-shadow:0 4px 10px #126e6926; transform:translateY(-1px); }
    button.secondary { background:#fff; color:#30445e; border-color:#d8e0ea; }
    button.secondary:hover:not(:disabled) { background:#f4f7fa; }
    button.danger { background:#fff; color:var(--red); border-color:#f0cbd0; }
    button.danger:hover:not(:disabled) { background:#fff5f5; }
    button:disabled { opacity:.55; cursor:wait; }
    .form-actions { margin-top:17px; display:flex; gap:10px; align-items:center; }
    .toolbar { display:flex; gap:16px; align-items:center; }
    .toolbar button { white-space:nowrap; }
    .section-head { display:flex; justify-content:space-between; align-items:center; gap:16px; margin-bottom:14px; }
    .section-head h2 { margin:0; }
    .monitor-list { display:grid; gap:12px; }
    .monitor { padding:20px; box-shadow:none; transition:border-color .15s,box-shadow .15s; }
    .monitor:hover { border-color:#cbd8e5; box-shadow:0 5px 18px #1b36510c; }
    .monitor-top { display:flex; justify-content:space-between; gap:16px; align-items:flex-start; }
    .monitor-name { font-size:17px; font-weight:750; overflow-wrap:anywhere; }
    .monitor-url { display:block; color:#728198; font-size:13px; font-weight:500; overflow-wrap:anywhere; margin-top:2px; }
    .badge { flex:none; border-radius:999px; padding:5px 11px; font-size:10px; font-weight:850; text-transform:uppercase; letter-spacing:.08em; background:#edf1f5; color:#52647b; }
    .badge.up { color:#13734f; background:#e5f6ed; }
    .badge.down { color:#b42332; background:#fdebed; }
    .badge.degraded { color:#8c5b00; background:#fff4d6; }
    .monitor-meta { display:flex; flex-wrap:wrap; gap:8px 20px; color:#718096; font-size:12px; margin:15px 0; padding-top:13px; border-top:1px solid #edf1f5; }
    .monitor-actions { display:flex; flex-wrap:wrap; gap:8px; }
    .metrics { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px; margin-top:16px; }
    .metric { background:#f7f9fc; border:1px solid #e8edf3; padding:13px; border-radius:11px; min-width:0; }
    .metric-label { color:#718096; font-size:10px; font-weight:750; text-transform:uppercase; letter-spacing:.07em; }
    .metric-value { color:#183b56; font-weight:800; font-size:21px; margin-top:4px; overflow-wrap:anywhere; }
    .message { min-height:22px; color:var(--muted); font-size:13px; margin:12px 0 0; }
    .message.error { color:var(--red); }
    .empty { text-align:center; padding:36px 16px; color:var(--muted); border:1px dashed #cad5e2; border-radius:12px; background:#fbfcfe; }
    .hidden { display:none !important; }
    footer { color:#8492a6; font-size:11px; margin-top:24px; text-align:center; }
    @media(max-width:650px) { main { width:min(100% - 28px,1120px); padding-top:24px; } header { align-items:flex-start; } header > .toolbar { gap:10px; flex-wrap:wrap; justify-content:flex-end; } .grid { grid-template-columns:1fr; } .metrics { grid-template-columns:repeat(2,minmax(0,1fr)); } .panel { padding:18px; } .login { margin:40px auto; } }
  </style>
</head>
<body>
<main>
  <header>
    <div><div class="eyebrow">Distributed uptime monitor</div><h1>Service health</h1></div>
    <div class="toolbar"><a href="/docs" target="_blank" rel="noreferrer">API docs</a><button id="logout" class="secondary hidden" type="button">Log out</button></div>
  </header>

  <section id="login-panel" class="panel login">
    <h2>Sign in to your monitors</h2>
    <p>Use the account you registered with the API.</p>
    <form id="login-form">
      <div style="margin-bottom:13px"><label for="email">Email</label><input id="email" name="email" type="email" autocomplete="username" required></div>
      <div><label for="password">Password</label><input id="password" name="password" type="password" autocomplete="current-password" required></div>
      <div class="form-actions"><button type="submit">Sign in</button></div>
    </form>
    <p id="login-message" class="message" role="status"></p>
  </section>

  <div id="dashboard" class="hidden">
    <section class="panel">
      <h2>Add a monitor</h2>
      <form id="monitor-form">
        <div class="grid">
          <div><label for="monitor-name">Name</label><input id="monitor-name" name="name" maxlength="120" placeholder="Production API" required></div>
          <div><label for="monitor-url">Public URL</label><input id="monitor-url" name="url" type="url" placeholder="https://example.com/health" required></div>
          <div><label for="interval">Check interval (seconds)</label><input id="interval" name="interval_seconds" type="number" min="60" max="86400" value="300" required></div>
          <div><label for="timeout">Timeout (milliseconds)</label><input id="timeout" name="timeout_ms" type="number" min="500" max="15000" value="5000" required></div>
        </div>
        <div class="form-actions"><button type="submit">Add monitor</button></div>
      </form>
      <p id="monitor-message" class="message" role="status"></p>
    </section>

    <section class="panel">
      <div class="section-head"><h2>Your monitors</h2><button id="refresh" class="secondary" type="button">Refresh</button></div>
      <p id="list-message" class="message" role="status"></p>
      <div id="monitor-list" class="monitor-list"></div>
    </section>
  </div>
  <footer>Availability is calculated from recorded checks. Free-tier services may sleep or delay scheduled runs.</footer>
</main>
<script>
  let accessToken = "";
  const byId = (id) => document.getElementById(id);
  const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[char]));

  async function api(path, options = {}) {
    const headers = {"Content-Type":"application/json", ...(options.headers || {})};
    if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
    const response = await fetch(path, {...options, headers});
    const data = response.status === 204 ? null : await response.json().catch(() => null);
    if (!response.ok) {
      if (response.status === 401) logout("Your session expired. Sign in again.");
      throw new Error(data?.detail || `Request failed (${response.status})`);
    }
    return data;
  }

  function setMessage(id, text, isError = false) {
    const element = byId(id);
    element.textContent = text || "";
    element.classList.toggle("error", isError);
  }

  function logout(message = "") {
    accessToken = "";
    byId("dashboard").classList.add("hidden");
    byId("logout").classList.add("hidden");
    byId("login-panel").classList.remove("hidden");
    setMessage("login-message", message, Boolean(message));
  }

  async function loadSummary(monitorId, targetId) {
    const target = byId(targetId);
    target.innerHTML = '<p class="message">Loading 24-hour summary…</p>';
    try {
      const summary = await api(`/monitors/${encodeURIComponent(monitorId)}/summary?hours=24`);
      target.innerHTML = `<div class="metrics">
        <div class="metric"><div class="metric-label">24h success rate</div><div class="metric-value">${summary.uptime_percentage}%</div></div>
        <div class="metric"><div class="metric-label">Successful checks</div><div class="metric-value">${summary.successful_checks}/${summary.total_checks}</div></div>
        <div class="metric"><div class="metric-label">Average latency</div><div class="metric-value">${summary.average_latency_ms == null ? "—" : `${summary.average_latency_ms} ms`}</div></div>
        <div class="metric"><div class="metric-label">P95 latency</div><div class="metric-value">${summary.p95_latency_ms == null ? "—" : `${summary.p95_latency_ms} ms`}</div></div>
      </div>`;
    } catch (error) {
      target.innerHTML = `<p class="message error">${escapeHtml(error.message)}</p>`;
    }
  }

  async function loadMonitors() {
    setMessage("list-message", "Loading monitors…");
    const list = byId("monitor-list");
    try {
      const monitors = await api("/monitors?limit=100");
      setMessage("list-message", "");
      if (!monitors.length) {
        list.innerHTML = '<div class="empty">No monitors yet. Add one above to get started.</div>';
        return;
      }
      list.innerHTML = monitors.map((monitor) => {
        const state = String(monitor.current_state).toLowerCase();
        const summaryId = `summary-${monitor.id}`;
        return `<article class="monitor">
          <div class="monitor-top"><div><div class="monitor-name">${escapeHtml(monitor.name)}</div><a class="monitor-url" href="${escapeHtml(monitor.url)}" target="_blank" rel="noreferrer">${escapeHtml(monitor.url)}</a></div><span class="badge ${escapeHtml(state)}">${escapeHtml(state)}</span></div>
          <div class="monitor-meta"><span>${escapeHtml(monitor.method)} · every ${monitor.interval_seconds}s</span><span>Failures: ${monitor.consecutive_failures}</span><span>Next check: ${new Date(monitor.next_check_at).toLocaleString()}</span></div>
          <div class="monitor-actions"><button class="secondary summary-button" data-id="${escapeHtml(monitor.id)}" data-target="${summaryId}" type="button">Show 24-hour metrics</button><button class="danger delete-button" data-id="${escapeHtml(monitor.id)}" data-name="${escapeHtml(monitor.name)}" type="button">Delete</button></div>
          <div id="${summaryId}"></div>
        </article>`;
      }).join("");
      list.querySelectorAll(".summary-button").forEach((button) => button.addEventListener("click", () => loadSummary(button.dataset.id, button.dataset.target)));
      list.querySelectorAll(".delete-button").forEach((button) => button.addEventListener("click", () => deleteMonitor(button.dataset.id, button.dataset.name)));
    } catch (error) {
      setMessage("list-message", error.message, true);
    }
  }

  async function deleteMonitor(id, name) {
    if (!window.confirm(`Delete monitor “${name}” and its check history?`)) return;
    try {
      await api(`/monitors/${encodeURIComponent(id)}`, {method:"DELETE"});
      await loadMonitors();
    } catch (error) {
      setMessage("list-message", error.message, true);
    }
  }

  byId("login-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = event.currentTarget.querySelector("button[type=submit]");
    button.disabled = true;
    setMessage("login-message", "Signing in…");
    try {
      const form = new FormData(event.currentTarget);
      const result = await api("/auth/login", {method:"POST", body:JSON.stringify({email:form.get("email"), password:form.get("password")})});
      accessToken = result.access_token;
      byId("login-panel").classList.add("hidden");
      byId("dashboard").classList.remove("hidden");
      byId("logout").classList.remove("hidden");
      event.currentTarget.reset();
      await loadMonitors();
    } catch (error) {
      setMessage("login-message", error.message, true);
    } finally {
      button.disabled = false;
    }
  });

  byId("monitor-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = event.currentTarget.querySelector("button[type=submit]");
    button.disabled = true;
    setMessage("monitor-message", "Creating monitor…");
    const form = new FormData(event.currentTarget);
    try {
      await api("/monitors", {method:"POST", body:JSON.stringify({
        name:form.get("name"), url:form.get("url"), method:"GET",
        interval_seconds:Number(form.get("interval_seconds")), timeout_ms:Number(form.get("timeout_ms"))
      })});
      event.currentTarget.reset();
      byId("interval").value = "300";
      byId("timeout").value = "5000";
      setMessage("monitor-message", "Monitor created.");
      await loadMonitors();
    } catch (error) {
      setMessage("monitor-message", error.message, true);
    } finally {
      button.disabled = false;
    }
  });

  byId("refresh").addEventListener("click", loadMonitors);
  byId("logout").addEventListener("click", () => logout());
</script>
</body>
</html>"""
