"""
tracker.py
Tracks all job applications in a local SQLite database.
Also serves a simple Flask dashboard to view application history.
"""

import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "applications.db")


def init_db(db_path: str = DB_PATH) -> None:
    '''
    Creates the applications database and table if it doesn't exist.
    '''
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            location TEXT,
            source TEXT,
            apply_link TEXT,
            match_score INTEGER,
            match_reason TEXT,
            status TEXT DEFAULT 'applied',
            applied_at TEXT,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()


def log_application(job: dict, db_path: str = DB_PATH) -> int:
    '''
    Logs a single job application to the database.
    Returns the inserted row ID.
    '''
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''
        INSERT INTO applications
        (job_id, title, company, location, source, apply_link, match_score,
         match_reason, status, applied_at, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        job.get("job_id", ""),
        job.get("title", ""),
        job.get("company", ""),
        job.get("location", ""),
        job.get("source", ""),
        job.get("apply_link", ""),
        job.get("match_score"),
        job.get("match_reason", ""),
        job.get("status", "applied"),
        job.get("applied_at", datetime.now().isoformat()),
        job.get("notes", "")
    ))
    conn.commit()
    row_id = c.lastrowid
    conn.close()
    return row_id


def log_bulk_applications(jobs: list[dict], db_path: str = DB_PATH) -> int:
    '''
    Logs multiple applications at once. Returns count of logged jobs.
    '''
    count = 0
    for job in jobs:
        if job.get("status") == "applied":
            log_application(job, db_path)
            count += 1
    return count


def get_all_applications(db_path: str = DB_PATH) -> list[dict]:
    '''
    Returns all logged applications as a list of dicts.
    '''
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM applications ORDER BY applied_at DESC")
    rows = [dict(row) for row in c.fetchall()]
    conn.close()
    return rows


def get_stats(db_path: str = DB_PATH) -> dict:
    '''
    Returns application statistics summary.
    '''
    apps = get_all_applications(db_path)
    if not apps:
        return {"total": 0}

    sources = {}
    statuses = {}
    scores = [a["match_score"] for a in apps if a["match_score"]]

    for app in apps:
        src = app.get("source", "Unknown")
        sources[src] = sources.get(src, 0) + 1
        st = app.get("status", "applied")
        statuses[st] = statuses.get(st, 0) + 1

    return {
        "total": len(apps),
        "by_source": sources,
        "by_status": statuses,
        "avg_match_score": round(sum(scores) / len(scores), 1) if scores else 0,
        "max_match_score": max(scores) if scores else 0,
    }


def update_status(app_id: int, new_status: str, notes: str = "",
                  db_path: str = DB_PATH) -> None:
    '''
    Updates the status of an application (e.g. "interview", "rejected", "offer").
    '''
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("UPDATE applications SET status=?, notes=? WHERE id=?",
              (new_status, notes, app_id))
    conn.commit()
    conn.close()


# ─── Flask Dashboard ──────────────────────────────────────────────────────────

def run_dashboard(db_path: str = DB_PATH, port: int = 5000) -> None:
    '''
    Launches a local Flask web dashboard to view application history.
    Visit http://localhost:5000 in your browser.
    '''
    try:
        from flask import Flask, render_template_string, jsonify, request
    except ImportError:
        print("❌ Flask not installed. Run: pip install flask")
        return

    app = Flask(__name__)

    DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>Job Application Tracker</title>
  <meta charset="utf-8">
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
           background: #0f172a; color: #e2e8f0; min-height: 100vh; }
    .header { background: linear-gradient(135deg, #1e40af, #7c3aed);
              padding: 2rem; text-align: center; }
    .header h1 { font-size: 2rem; font-weight: 700; }
    .header p { color: #bfdbfe; margin-top: 0.5rem; }
    .stats { display: flex; gap: 1rem; padding: 1.5rem 2rem; flex-wrap: wrap; }
    .stat-card { background: #1e293b; border-radius: 12px; padding: 1.2rem 1.5rem;
                 flex: 1; min-width: 150px; border: 1px solid #334155; }
    .stat-card .num { font-size: 2rem; font-weight: 700; color: #60a5fa; }
    .stat-card .label { color: #94a3b8; font-size: 0.85rem; margin-top: 0.3rem; }
    .filters { padding: 0 2rem 1rem; display: flex; gap: 1rem; align-items: center; flex-wrap: wrap; }
    .filters input, .filters select {
      background: #1e293b; border: 1px solid #334155; color: #e2e8f0;
      border-radius: 8px; padding: 0.5rem 1rem; font-size: 0.9rem; }
    table { width: 100%; border-collapse: collapse; }
    thead { background: #1e293b; }
    th { padding: 0.9rem 1rem; text-align: left; font-weight: 600;
         color: #94a3b8; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.05em; }
    td { padding: 0.9rem 1rem; border-bottom: 1px solid #1e293b; font-size: 0.9rem; }
    tr:hover td { background: #1e293b; }
    .badge { display: inline-block; padding: 0.2rem 0.7rem; border-radius: 20px;
             font-size: 0.78rem; font-weight: 600; }
    .badge-applied { background: #1e40af22; color: #60a5fa; border: 1px solid #1e40af44; }
    .badge-interview { background: #065f4622; color: #34d399; border: 1px solid #065f4644; }
    .badge-rejected { background: #7f1d1d22; color: #f87171; border: 1px solid #7f1d1d44; }
    .badge-offer { background: #78350f22; color: #fbbf24; border: 1px solid #78350f44; }
    .score { font-weight: 700; }
    .score-high { color: #34d399; }
    .score-mid { color: #fbbf24; }
    .score-low { color: #f87171; }
    .link { color: #60a5fa; text-decoration: none; }
    .link:hover { text-decoration: underline; }
    .table-wrap { padding: 0 2rem 2rem; overflow-x: auto; }
    .empty { text-align: center; padding: 4rem; color: #475569; }
  </style>
</head>
<body>
  <div class="header">
    <h1>🎯 Job Application Tracker</h1>
    <p id="last-updated">Loading...</p>
  </div>

  <div class="stats" id="stats"></div>

  <div class="filters">
    <input type="text" id="search" placeholder="🔍 Search jobs..." oninput="filterTable()">
    <select id="statusFilter" onchange="filterTable()">
      <option value="">All Statuses</option>
      <option value="applied">Applied</option>
      <option value="interview">Interview</option>
      <option value="rejected">Rejected</option>
      <option value="offer">Offer</option>
    </select>
    <select id="sourceFilter" onchange="filterTable()">
      <option value="">All Sources</option>
    </select>
  </div>

  <div class="table-wrap">
    <table id="appTable">
      <thead>
        <tr>
          <th>#</th>
          <th>Job Title</th>
          <th>Company</th>
          <th>Location</th>
          <th>Source</th>
          <th>Match</th>
          <th>Status</th>
          <th>Applied At</th>
          <th>Link</th>
        </tr>
      </thead>
      <tbody id="tableBody"></tbody>
    </table>
    <div class="empty" id="emptyState" style="display:none">No applications found yet. Run the agent to start applying!</div>
  </div>

<script>
let allApps = [];

async function loadData() {
  const res = await fetch('/api/applications');
  const data = await res.json();
  allApps = data.applications;

  const stats = data.stats;
  document.getElementById('stats').innerHTML = `
    <div class="stat-card"><div class="num">${stats.total}</div><div class="label">Total Applied</div></div>
    <div class="stat-card"><div class="num">${stats.avg_match_score || 0}</div><div class="label">Avg Match Score</div></div>
    <div class="stat-card"><div class="num">${(stats.by_status || {}).interview || 0}</div><div class="label">Interviews</div></div>
    <div class="stat-card"><div class="num">${(stats.by_status || {}).offer || 0}</div><div class="label">Offers</div></div>
  `;

  // Populate source filter
  const sources = Object.keys(stats.by_source || {});
  const sf = document.getElementById('sourceFilter');
  sources.forEach(s => { sf.innerHTML += `<option value="${s}">${s}</option>`; });

  document.getElementById('last-updated').textContent =
    `Last updated: ${new Date().toLocaleTimeString()} · ${stats.total} applications tracked`;

  filterTable();
}

function scoreClass(s) {
  if (!s) return '';
  if (s >= 70) return 'score-high';
  if (s >= 50) return 'score-mid';
  return 'score-low';
}

function badgeClass(s) {
  return `badge badge-${s || 'applied'}`;
}

function filterTable() {
  const search = document.getElementById('search').value.toLowerCase();
  const status = document.getElementById('statusFilter').value;
  const source = document.getElementById('sourceFilter').value;

  const filtered = allApps.filter(a => {
    const matchSearch = !search ||
      a.title.toLowerCase().includes(search) ||
      a.company.toLowerCase().includes(search);
    const matchStatus = !status || a.status === status;
    const matchSource = !source || a.source === source;
    return matchSearch && matchStatus && matchSource;
  });

  const tbody = document.getElementById('tableBody');
  if (filtered.length === 0) {
    tbody.innerHTML = '';
    document.getElementById('emptyState').style.display = 'block';
    return;
  }
  document.getElementById('emptyState').style.display = 'none';

  tbody.innerHTML = filtered.map((a, i) => `
    <tr>
      <td style="color:#475569">${i+1}</td>
      <td style="font-weight:600">${a.title}</td>
      <td>${a.company}</td>
      <td style="color:#94a3b8">${a.location || '—'}</td>
      <td><span class="badge badge-applied">${a.source || '—'}</span></td>
      <td><span class="score ${scoreClass(a.match_score)}">${a.match_score || '—'}</span></td>
      <td><span class="${badgeClass(a.status)}">${a.status}</span></td>
      <td style="color:#94a3b8;font-size:0.8rem">${a.applied_at ? a.applied_at.substring(0,16).replace('T',' ') : '—'}</td>
      <td>${a.apply_link ? `<a class="link" href="${a.apply_link}" target="_blank">Open ↗</a>` : '—'}</td>
    </tr>
  `).join('');
}

loadData();
setInterval(loadData, 30000);
</script>
</body>
</html>
"""

    @app.route("/")
    def index():
        return DASHBOARD_HTML

    @app.route("/api/applications")
    def api_applications():
        apps = get_all_applications(db_path)
        stats = get_stats(db_path)
        return jsonify({"applications": apps, "stats": stats})

    @app.route("/api/update_status", methods=["POST"])
    def api_update_status():
        data = request.json
        update_status(data["id"], data["status"], data.get("notes", ""), db_path)
        return jsonify({"success": True})

    print(f"\n🌐 Dashboard running at http://localhost:{port}")
    print("   Press Ctrl+C to stop\n")
    app.run(port=port, debug=False)


if __name__ == "__main__":
    run_dashboard()
