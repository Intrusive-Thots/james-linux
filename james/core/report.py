"""
JAMES Report Generator — produces professional HTML pentest reports.
"""

import json
from datetime import datetime
from pathlib import Path


def generate_html_report(
    task_log: list[dict],
    context: dict,
    loot_summary: dict,
    tool_status: dict,
    skills: list[str],
    known_targets: set[str],
    wordlist_inventory: list[dict] | None = None,
) -> str:
    """Generate a self-contained HTML penetration test report."""

    now = datetime.now()
    report_time = now.strftime("%Y-%m-%d %H:%M:%S")
    report_date = now.strftime("%B %d, %Y")

    # Stats
    total_tasks = len(task_log)
    success_count = 0
    error_count = 0
    for e in task_log:
        status = e.get("status")
        if status == "success":
            success_count += 1
        elif status in ("error", "failed"):
            error_count += 1
    tools_installed = sum(1 for v in tool_status.values() if v)
    tools_total = len(tool_status)
    cracked_count = loot_summary.get("cracked_count", 0)

    # Build task rows
    def _status_class(status):
        return {
            "success": "status-success",
            "error": "status-error",
            "failed": "status-error",
            "running": "status-running",
        }.get(status, "status-info")

    task_rows = "".join(f"""
            <tr>
                <td class="mono">{e.get('timestamp', '')[:19]}</td>
                <td>{e.get('action', '')}</td>
                <td><code>{e.get('tool', '')}</code></td>
                <td><span class="{_status_class(e.get('status', ''))}">{e.get('status', '')}</span></td>
                <td class="detail-cell">{json.dumps(e.get("result", {}), default=str)[:200] if e.get("result") else ""}</td>
            </tr>""" for e in task_log)

    # Build loot rows
    loot_rows = "".join(f"""
            <tr>
                <td>{entry.get('essid', '') or entry.get('id', '')}</td>
                <td class="key-value">{entry.get('key', '')}</td>
                <td>{entry.get('method', '')}</td>
                <td class="mono">{entry.get('when', '')[:10]}</td>
            </tr>""" for entry in loot_summary.get("keys", []))

    # Build tool status grid
    tool_grid = "".join(
        f'<span class="tool-badge {"tool-ok" if installed else "tool-missing"}">{"✅" if installed else "❌"} {name}</span>\n'
        for name, installed in sorted(tool_status.items())
    )

    # Build target list
    target_list = "".join(
        f"<li><code>{t}</code></li>\n" for t in sorted(known_targets)
    )

    # Context section
    context_rows = "".join(
        f"<tr><td><strong>{k}</strong></td><td>{v}</td></tr>\n"
        for k, v in context.items()
        if v
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>JAMES Pentest Report — {report_date}</title>
<style>
    :root {{
        --bg: #0a0e17;
        --surface: #0f1521;
        --surface2: #151d2e;
        --border: #1a2540;
        --text: #c0d0e0;
        --text-dim: #4a6080;
        --accent: #00f0ff;
        --accent2: #00ff88;
        --danger: #ff4466;
        --warn: #ffaa00;
        --purple: #aa88ff;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
        background: var(--bg);
        color: var(--text);
        font-family: 'Segoe UI', 'Inter', -apple-system, sans-serif;
        line-height: 1.6;
        padding: 40px 20px;
    }}
    .container {{ max-width: 1100px; margin: 0 auto; }}

    /* Header */
    .report-header {{
        text-align: center;
        padding: 40px 20px;
        border-bottom: 2px solid var(--border);
        margin-bottom: 40px;
        background: linear-gradient(180deg, var(--surface) 0%, var(--bg) 100%);
        border-radius: 12px 12px 0 0;
    }}
    .report-header h1 {{
        font-size: 32px;
        letter-spacing: 6px;
        background: linear-gradient(90deg, var(--accent), var(--accent2));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 8px;
    }}
    .report-header .subtitle {{
        color: var(--text-dim);
        font-size: 14px;
        letter-spacing: 2px;
    }}
    .report-header .date {{
        color: var(--accent);
        font-family: monospace;
        margin-top: 12px;
    }}

    /* Stats cards */
    .stats-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 16px;
        margin-bottom: 32px;
    }}
    .stat-card {{
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 20px;
        text-align: center;
    }}
    .stat-card .stat-value {{
        font-size: 36px;
        font-weight: 700;
        color: var(--accent);
    }}
    .stat-card .stat-label {{
        font-size: 11px;
        color: var(--text-dim);
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 4px;
    }}
    .stat-card.danger .stat-value {{ color: var(--danger); }}
    .stat-card.success .stat-value {{ color: var(--accent2); }}
    .stat-card.warn .stat-value {{ color: var(--warn); }}
    .stat-card.purple .stat-value {{ color: var(--purple); }}

    /* Sections */
    .section {{
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 10px;
        margin-bottom: 24px;
        overflow: hidden;
    }}
    .section-header {{
        background: var(--surface2);
        padding: 14px 20px;
        border-bottom: 1px solid var(--border);
        font-size: 16px;
        font-weight: 600;
        letter-spacing: 1px;
    }}
    .section-body {{ padding: 20px; }}

    /* Tables */
    table {{
        width: 100%;
        border-collapse: collapse;
    }}
    th {{
        text-align: left;
        padding: 10px 12px;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: var(--text-dim);
        border-bottom: 2px solid var(--border);
    }}
    td {{
        padding: 8px 12px;
        border-bottom: 1px solid var(--border);
        font-size: 13px;
    }}
    tr:hover {{ background: var(--surface2); }}

    /* Status badges */
    .status-success {{
        color: var(--accent2);
        background: #00ff8815;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 600;
    }}
    .status-error {{
        color: var(--danger);
        background: #ff446615;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 600;
    }}
    .status-running {{
        color: var(--warn);
        background: #ffaa0015;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 600;
    }}
    .status-info {{
        color: var(--accent);
        background: #00f0ff15;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 600;
    }}

    .mono {{ font-family: 'Fira Code', 'Consolas', monospace; font-size: 12px; }}
    .key-value {{
        color: var(--accent2);
        font-family: 'Fira Code', monospace;
        font-weight: 700;
    }}
    .detail-cell {{
        max-width: 300px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        font-size: 11px;
        color: var(--text-dim);
    }}
    code {{
        background: var(--surface2);
        padding: 1px 6px;
        border-radius: 4px;
        font-size: 12px;
    }}

    /* Tools grid */
    .tools-grid {{
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
    }}
    .tool-badge {{
        padding: 4px 12px;
        border-radius: 6px;
        font-size: 12px;
        border: 1px solid var(--border);
    }}
    .tool-ok {{ background: #00ff8810; color: var(--accent2); }}
    .tool-missing {{ background: #ff446610; color: var(--danger); }}

    /* Targets */
    .target-grid {{
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        list-style: none;
    }}
    .target-grid li {{
        background: var(--surface2);
        padding: 4px 14px;
        border-radius: 8px;
        border: 1px solid var(--border);
    }}

    /* Footer */
    .footer {{
        text-align: center;
        padding: 30px 20px;
        color: var(--text-dim);
        font-size: 11px;
        border-top: 1px solid var(--border);
        margin-top: 40px;
    }}

    @media print {{
        body {{ background: white; color: #333; padding: 20px; }}
        .stat-card {{ border: 1px solid #ddd; }}
        .section {{ border: 1px solid #ddd; }}
        .report-header h1 {{
            background: none;
            -webkit-text-fill-color: #0088aa;
        }}
    }}
</style>
</head>
<body>
<div class="container">
    <div class="report-header">
        <h1>⚡ JAMES</h1>
        <div class="subtitle">PENETRATION TEST REPORT</div>
        <div class="date">{report_time}</div>
    </div>

    <!-- Stats Overview -->
    <div class="stats-grid">
        <div class="stat-card"><div class="stat-value">{total_tasks}</div><div class="stat-label">Tasks Executed</div></div>
        <div class="stat-card success"><div class="stat-value">{success_count}</div><div class="stat-label">Successful</div></div>
        <div class="stat-card danger"><div class="stat-value">{error_count}</div><div class="stat-label">Errors</div></div>
        <div class="stat-card purple"><div class="stat-value">{cracked_count}</div><div class="stat-label">Keys Cracked</div></div>
        <div class="stat-card"><div class="stat-value">{len(known_targets)}</div><div class="stat-label">Targets Found</div></div>
        <div class="stat-card warn"><div class="stat-value">{tools_installed}/{tools_total}</div><div class="stat-label">Tools Installed</div></div>
    </div>

    <!-- Session Context -->
    {"" if not context_rows else f'''
    <div class="section">
        <div class="section-header">🎯 Session Context</div>
        <div class="section-body">
            <table>
                <tr><th>Variable</th><th>Value</th></tr>
                {context_rows}
            </table>
        </div>
    </div>
    '''}

    <!-- Known Targets -->
    {"" if not known_targets else f'''
    <div class="section">
        <div class="section-header">🎯 Discovered Targets ({len(known_targets)})</div>
        <div class="section-body">
            <ul class="target-grid">{target_list}</ul>
        </div>
    </div>
    '''}

    <!-- Cracked Keys -->
    {"" if cracked_count == 0 else f'''
    <div class="section">
        <div class="section-header">🔑 Cracked Credentials ({cracked_count})</div>
        <div class="section-body">
            <table>
                <tr><th>Target/ESSID</th><th>Key</th><th>Method</th><th>Date</th></tr>
                {loot_rows}
            </table>
        </div>
    </div>
    '''}

    <!-- Task Log -->
    <div class="section">
        <div class="section-header">📋 Task Log ({total_tasks} entries)</div>
        <div class="section-body">
            {"<p style='color:var(--text-dim)'>No tasks recorded in this session.</p>" if not task_rows else f'''
            <table>
                <tr><th>Timestamp</th><th>Action</th><th>Tool</th><th>Status</th><th>Details</th></tr>
                {task_rows}
            </table>
            '''}
        </div>
    </div>

    <!-- Tool Status -->
    <div class="section">
        <div class="section-header">⚙️ Tool Status ({tools_installed}/{tools_total} installed)</div>
        <div class="section-body">
            <div class="tools-grid">
                {tool_grid}
            </div>
        </div>
    </div>

    <div class="footer">
        Generated by JAMES Autonomous Pentesting Agent<br>
        {report_time} — {len(skills)} skills available
    </div>
</div>
</body>
</html>"""

    return html


def save_report(html: str, path: str | Path | None = None) -> Path:
    """Save report HTML to disk and return the path."""
    if path is None:
        try:
            loot_dir = Path.home() / ".james" / "loot"
            loot_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = loot_dir / f"report_{timestamp}.html"
        except OSError:
            # Fallback to local workspace loot directory if home is read-only
            loot_dir = Path("./loot")
            loot_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = loot_dir / f"report_{timestamp}.html"
    else:
        path = Path(path)

    try:
        path.write_text(html, encoding="utf-8")
    except OSError:
        # Final fallback to a local file
        fallback_path = Path("james_report_fallback.html")
        fallback_path.write_text(html, encoding="utf-8")
        return fallback_path
    return path
