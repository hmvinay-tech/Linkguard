import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  AlertTriangle,
  Bell,
  CheckCircle2,
  Edit3,
  Gauge,
  Link,
  Loader2,
  LogOut,
  Plus,
  RotateCw,
  ShieldCheck,
  Trash2,
  XCircle,
} from "lucide-react";
import "./styles.css";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api";
const emptyForm = { name: "", url: "", category: "other", description: "" };
const emptyAuth = { email: "", password: "" };

function App() {
  const [token, setToken] = useState(() => localStorage.getItem("linkguard-token") || "");
  const [user, setUser] = useState(null);
  const [authMode, setAuthMode] = useState("login");
  const [authForm, setAuthForm] = useState(emptyAuth);
  const [settingsForm, setSettingsForm] = useState({
    notification_email: "",
    notification_phone: "",
    notifications_enabled: true,
    sms_notifications_enabled: false,
    scan_frequency_minutes: 60,
  });
  const [resources, setResources] = useState([]);
  const [dashboard, setDashboard] = useState(null);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [readmeText, setReadmeText] = useState("");
  const [scanHistory, setScanHistory] = useState([]);
  const notifications = dashboard?.recent_notifications ?? [];
  const unreadCount = notifications.filter((notification) => !notification.read).length;

  useEffect(() => {
    if (token) refreshData();
  }, [token]);

  const latestScans = useMemo(() => {
    const map = new Map();
    for (const scan of dashboard?.latest_scans ?? []) {
      map.set(scan.resource_id, scan);
    }
    return map;
  }, [dashboard]);

  async function request(path, options = {}) {
    const response = await fetch(`${API_BASE}${path}`, {
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...options.headers,
      },
      ...options,
    });
    if (!response.ok) {
      if (response.status === 401) logout();
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail || "Request failed");
    }
    if (response.status === 204) return null;
    return response.json();
  }

  async function submitAuth(event) {
    event.preventDefault();
    setBusy(true);
    try {
      const endpoint = authMode === "signup" ? "/auth/signup" : "/auth/login";
      const response = await fetch(`${API_BASE}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(authForm),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || "Authentication failed");
      }
      const data = await response.json();
      localStorage.setItem("linkguard-token", data.access_token);
      setToken(data.access_token);
      setUser(data.user);
      setSettingsForm({
        notification_email: data.user.notification_email || data.user.email,
        notification_phone: data.user.notification_phone || "",
        notifications_enabled: data.user.notifications_enabled,
        sms_notifications_enabled: data.user.sms_notifications_enabled,
        scan_frequency_minutes: data.user.scan_frequency_minutes,
      });
      setAuthForm(emptyAuth);
      setMessage("");
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  function logout() {
    localStorage.removeItem("linkguard-token");
    setToken("");
    setUser(null);
    setResources([]);
    setDashboard(null);
    setScanHistory([]);
  }

  async function refreshData() {
    setBusy(true);
    try {
      const [me, resourceData, dashboardData, historyData] = await Promise.all([
        request("/auth/me"),
        request("/resources"),
        request("/dashboard"),
        request("/dashboard/history"),
      ]);
      setUser(me);
      setSettingsForm({
        notification_email: me.notification_email || me.email,
        notification_phone: me.notification_phone || "",
        notifications_enabled: me.notifications_enabled,
        sms_notifications_enabled: me.sms_notifications_enabled,
        scan_frequency_minutes: me.scan_frequency_minutes,
      });
      setResources(resourceData);
      setDashboard(dashboardData);
      setScanHistory(historyData);
      setMessage("");
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function saveResource(event) {
    event.preventDefault();
    setBusy(true);
    try {
      const payload = { ...form, description: form.description || null };
      if (editingId) {
        await request(`/resources/${editingId}`, { method: "PUT", body: JSON.stringify(payload) });
        setMessage("Resource updated.");
      } else {
        await request("/resources", { method: "POST", body: JSON.stringify(payload) });
        setMessage("Resource added.");
      }
      setForm(emptyForm);
      setEditingId(null);
      await refreshData();
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function scanResource(id) {
    setBusy(true);
    try {
      await request(`/resources/${id}/scan`, { method: "POST" });
      await refreshData();
      setMessage("Scan complete.");
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function scanAll() {
    setBusy(true);
    try {
      await request("/resources/scan-all", { method: "POST" });
      await refreshData();
      setMessage("All active links scanned.");
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function deleteResource(id) {
    setBusy(true);
    try {
      await request(`/resources/${id}`, { method: "DELETE" });
      await refreshData();
      setMessage("Resource deleted.");
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function seedDemo() {
    setBusy(true);
    try {
      const result = await request("/resources/demo/seed", { method: "POST" });
      await refreshData();
      setMessage(`Demo data ready. Added ${result.created.length}, skipped ${result.skipped_existing.length}.`);
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function importReadme(event) {
    event.preventDefault();
    setBusy(true);
    try {
      const result = await request("/resources/imports/readme", {
        method: "POST",
        body: JSON.stringify({ markdown: readmeText }),
      });
      setReadmeText("");
      await refreshData();
      setMessage(`Imported ${result.imported.length} README links. Skipped ${result.skipped_existing.length}.`);
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function saveSettings(event) {
    event.preventDefault();
    setBusy(true);
    try {
      const updated = await request("/auth/me", {
        method: "PUT",
        body: JSON.stringify({
          notification_email: settingsForm.notification_email || null,
          notification_phone: settingsForm.notification_phone || null,
          notifications_enabled: settingsForm.notifications_enabled,
          sms_notifications_enabled: settingsForm.sms_notifications_enabled,
          scan_frequency_minutes: Number(settingsForm.scan_frequency_minutes),
        }),
      });
      setUser(updated);
      setSettingsForm({
        notification_email: updated.notification_email || updated.email,
        notification_phone: updated.notification_phone || "",
        notifications_enabled: updated.notifications_enabled,
        sms_notifications_enabled: updated.sms_notifications_enabled,
        scan_frequency_minutes: updated.scan_frequency_minutes,
      });
      setMessage("Monitoring settings saved.");
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  async function markNotificationsRead() {
    setBusy(true);
    try {
      await request("/notifications/read", { method: "POST" });
      await refreshData();
      setMessage("Notifications marked as read.");
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  function startEdit(resource) {
    setEditingId(resource.id);
    setForm({
      name: resource.name,
      url: resource.url,
      category: resource.category,
      description: resource.description || "",
    });
  }

  if (!token) {
    return (
      <main className="auth-shell">
        <form className="auth-panel" onSubmit={submitAuth}>
          <div className="brand auth-brand">
            <ShieldCheck size={28} />
            <span>LinkGuard</span>
          </div>
          <h1>{authMode === "signup" ? "Create your monitor" : "Welcome back"}</h1>
          {message && <p className="message">{message}</p>}
          <label>
            Email
            <input
              type="email"
              value={authForm.email}
              onChange={(event) => setAuthForm({ ...authForm, email: event.target.value })}
              required
            />
          </label>
          <label>
            Password
            <input
              type="password"
              value={authForm.password}
              onChange={(event) => setAuthForm({ ...authForm, password: event.target.value })}
              minLength={authMode === "signup" ? 8 : 1}
              required
            />
          </label>
          <button className="primary-button" type="submit" disabled={busy}>
            {busy ? <Loader2 size={18} className="spin" /> : <ShieldCheck size={18} />}
            <span>{authMode === "signup" ? "Sign Up" : "Log In"}</span>
          </button>
          <button
            className="ghost-button"
            type="button"
            onClick={() => {
              setAuthMode(authMode === "signup" ? "login" : "signup");
              setMessage("");
            }}
          >
            <span>{authMode === "signup" ? "Use existing account" : "Create account"}</span>
          </button>
        </form>
      </main>
    );
  }

  const score = dashboard?.health_score ?? 100;
  const issueCount = dashboard?.open_issues?.length ?? 0;

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand">
          <ShieldCheck size={26} />
          <span>LinkGuard</span>
        </div>
        <div className="topbar-actions">
          <span className="account-label">{user?.email}</span>
          <button className="ghost-button" onClick={seedDemo} disabled={busy}>
            <Plus size={18} />
            <span>Demo Data</span>
          </button>
          <button className="primary-button" onClick={scanAll} disabled={busy || resources.length === 0}>
            {busy ? <Loader2 size={18} className="spin" /> : <RotateCw size={18} />}
            <span>Scan All</span>
          </button>
          <button className="icon-button" title="Log out" onClick={logout}>
            <LogOut size={17} />
          </button>
        </div>
      </header>

      <section className="dashboard-grid">
        <div className="score-panel">
          <div className="panel-heading">
            <Gauge size={20} />
            <span>Professional Presence</span>
          </div>
          <strong>{score}</strong>
          <span className="score-label">{score >= 90 ? "Excellent" : score >= 75 ? "Needs attention" : "Critical"}</span>
        </div>

        <Metric icon={<Link size={18} />} label="Total" value={dashboard?.total_resources ?? resources.length} />
        <Metric icon={<CheckCircle2 size={18} />} label="Healthy" value={dashboard?.healthy ?? 0} />
        <Metric icon={<AlertTriangle size={18} />} label="Open Issues" value={issueCount} />
      </section>

      <section className="notifications-band">
        <div className="section-title spread-title">
          <div>
            <Bell size={20} />
            <h1>Notifications</h1>
            {unreadCount > 0 && <span className="unread-badge">{unreadCount} unread</span>}
          </div>
          <button className="ghost-button" onClick={markNotificationsRead} disabled={busy || unreadCount === 0}>
            <CheckCircle2 size={18} />
            <span>Mark Read</span>
          </button>
        </div>
        <div className="notification-list">
          {notifications.length === 0 && <div className="empty-state">Automatic monitoring alerts will appear here.</div>}
          {notifications.map((notification) => (
            <article className={`notification-row ${notification.read ? "" : "unread"}`} key={notification.id}>
              <strong>{notification.title}</strong>
              <span>{notification.message}</span>
              <small>
                {[
                  notification.sms_sent ? "SMS sent" : null,
                  notification.email_sent ? "Email sent" : null,
                  "Saved in app",
                ].filter(Boolean).join(" / ")}
              </small>
            </article>
          ))}
        </div>
      </section>

      <section className="insights-grid">
        <div className="chart-panel">
          <div className="section-title">
            <Gauge size={20} />
            <h1>Scan History</h1>
          </div>
          <HistoryChart scans={scanHistory} />
        </div>

        <form className="readme-import" onSubmit={importReadme}>
          <div className="section-title">
            <Link size={20} />
            <h1>README Import</h1>
          </div>
          <textarea
            value={readmeText}
            onChange={(event) => setReadmeText(event.target.value)}
            placeholder="Paste README markdown with project, demo, certificate, and profile links."
            required
          />
          <button className="primary-button" type="submit" disabled={busy || readmeText.trim().length === 0}>
            <Plus size={18} />
            <span>Import Links</span>
          </button>
        </form>

        <form className="monitoring-panel" onSubmit={saveSettings}>
          <div className="section-title">
            <ShieldCheck size={20} />
            <h1>Monitoring</h1>
          </div>
          <label className="toggle-row">
            <input
              type="checkbox"
              checked={settingsForm.notifications_enabled}
              onChange={(event) => setSettingsForm({ ...settingsForm, notifications_enabled: event.target.checked })}
            />
            Email alerts
          </label>
          <label className="toggle-row">
            <input
              type="checkbox"
              checked={settingsForm.sms_notifications_enabled}
              onChange={(event) => setSettingsForm({ ...settingsForm, sms_notifications_enabled: event.target.checked })}
            />
            SMS alerts
          </label>
          <label>
            Alert Email
            <input
              type="email"
              value={settingsForm.notification_email}
              onChange={(event) => setSettingsForm({ ...settingsForm, notification_email: event.target.value })}
            />
          </label>
          <label>
            Alert Phone
            <input
              type="tel"
              value={settingsForm.notification_phone}
              onChange={(event) => setSettingsForm({ ...settingsForm, notification_phone: event.target.value })}
              placeholder="+15551234567"
            />
          </label>
          <label>
            Scan Every
            <select
              value={settingsForm.scan_frequency_minutes}
              onChange={(event) => setSettingsForm({ ...settingsForm, scan_frequency_minutes: event.target.value })}
            >
              <option value="15">15 minutes</option>
              <option value="60">1 hour</option>
              <option value="360">6 hours</option>
              <option value="1440">1 day</option>
            </select>
          </label>
          <button className="primary-button" type="submit" disabled={busy}>
            <CheckCircle2 size={18} />
            <span>Save Monitoring</span>
          </button>
        </form>
      </section>

      <section className="work-grid">
        <form className="resource-form" onSubmit={saveResource}>
          <div className="section-title">
            <Plus size={20} />
            <h1>{editingId ? "Edit Resource" : "Add Resource"}</h1>
          </div>

          <label>
            Name
            <input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required />
          </label>

          <label>
            URL
            <input
              value={form.url}
              onChange={(event) => setForm({ ...form, url: event.target.value })}
              placeholder="https://example.com"
              required
            />
          </label>

          <label>
            Category
            <select value={form.category} onChange={(event) => setForm({ ...form, category: event.target.value })}>
              <option value="resume">Resume</option>
              <option value="portfolio">Portfolio</option>
              <option value="github">GitHub</option>
              <option value="project">Project</option>
              <option value="certificate">Certificate</option>
              <option value="social">Social</option>
              <option value="other">Other</option>
            </select>
          </label>

          <label>
            Description
            <textarea value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} />
          </label>

          <div className="form-actions">
            <button className="primary-button" type="submit" disabled={busy}>
              {editingId ? <CheckCircle2 size={18} /> : <Plus size={18} />}
              <span>{editingId ? "Save" : "Add"}</span>
            </button>
            {editingId && (
              <button className="ghost-button" type="button" onClick={() => { setEditingId(null); setForm(emptyForm); }}>
                <XCircle size={18} />
                <span>Cancel</span>
              </button>
            )}
          </div>
        </form>

        <section className="content-band">
          <div className="section-title">
            <Activity size={20} />
            <h1>My Links</h1>
          </div>

          {message && <p className="message">{message}</p>}

          <div className="resource-list">
            {resources.length === 0 && <div className="empty-state">Add your first professional link to begin monitoring.</div>}
            {resources.map((resource) => {
              const scan = latestScans.get(resource.id);
              const status = scan?.classification ?? "unscanned";
              return (
                <article className="resource-row" key={resource.id}>
                  <div className={`status-dot ${status}`} />
                  <div className="resource-main">
                    <h2>{resource.name}</h2>
                    <p>{resource.category} - {resource.url}</p>
                    {scan && (
                      <div className="scan-meta">
                        <span>Status {scan.status_code ?? "n/a"}</span>
                        <span>{scan.response_time_ms ?? "-"} ms</span>
                        <span>{scan.redirect_count} redirects</span>
                      </div>
                    )}
                  </div>
                  <span className={`status-pill ${status}`}>{status}</span>
                  <div className="row-actions">
                    <button className="icon-button" title="Scan" onClick={() => scanResource(resource.id)} disabled={busy}>
                      <RotateCw size={16} />
                    </button>
                    <button className="icon-button" title="Edit" onClick={() => startEdit(resource)} disabled={busy}>
                      <Edit3 size={16} />
                    </button>
                    <button className="danger-button" title="Delete" onClick={() => deleteResource(resource.id)} disabled={busy}>
                      <Trash2 size={16} />
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        </section>
      </section>

      {dashboard?.open_issues?.length > 0 && (
        <section className="issues-band">
          <div className="section-title">
            <AlertTriangle size={20} />
            <h1>Open Issues</h1>
          </div>
          <div className="issue-list">
            {dashboard.open_issues.map((issue) => (
              <article className="issue-row" key={issue.id}>
                <strong>{issue.severity}</strong>
                <span>{issue.message}</span>
              </article>
            ))}
          </div>
        </section>
      )}
    </main>
  );
}

function Metric({ icon, label, value }) {
  return (
    <div className="metric">
      <div>{icon}</div>
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

function HistoryChart({ scans }) {
  const points = scans.slice(-20);
  if (points.length === 0) {
    return <div className="empty-state">Run scans to build response-time and health history.</div>;
  }

  const maxTime = Math.max(...points.map((scan) => scan.response_time_ms || 0), 100);
  const width = 640;
  const height = 220;
  const padding = 28;
  const step = points.length > 1 ? (width - padding * 2) / (points.length - 1) : 0;
  const linePoints = points
    .map((scan, index) => {
      const x = padding + index * step;
      const y = height - padding - ((scan.response_time_ms || 0) / maxTime) * (height - padding * 2);
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <div className="chart-wrap">
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Response time history chart">
        <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} className="chart-axis" />
        <line x1={padding} y1={padding} x2={padding} y2={height - padding} className="chart-axis" />
        <polyline points={linePoints} className="chart-line" />
        {points.map((scan, index) => {
          const x = padding + index * step;
          const y = height - padding - ((scan.response_time_ms || 0) / maxTime) * (height - padding * 2);
          return <circle key={scan.id} cx={x} cy={y} r="5" className={`chart-dot ${scan.classification}`} />;
        })}
      </svg>
      <div className="chart-legend">
        <span>{points.length} recent scans</span>
        <span>Peak {maxTime} ms</span>
      </div>
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
