"""
Server-rendered HTML templates for the dashboard.

Pure Python functions returning HTML strings — no Jinja2, no React, no build step.
"""

import html
import json
from typing import List, Dict, Any, Optional

from ..discovery import DiscoveredAgent


# ---------------------------------------------------------------------------
# Base layout
# ---------------------------------------------------------------------------

def render_base(title: str, content: str) -> str:
    """HTML shell with inline CSS (dark theme)."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
  :root {{
    --bg: #1b1b2f; --surface: #1f2937; --border: #374151;
    --text: #f3f4f6; --muted: #9ca3af; --accent: #3b82f6;
    --accent-hover: #2563eb; --green: #22c55e; --red: #ef4444;
  }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
         background: var(--bg); color: var(--text); line-height: 1.6; }}
  a {{ color: var(--accent); text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  .container {{ max-width: 1100px; margin: 0 auto; padding: 1.5rem; }}

  /* Header */
  header {{ background: var(--surface); border-bottom: 1px solid var(--border); padding: 1rem 0; }}
  header .container {{ display: flex; align-items: center; justify-content: space-between; }}
  header h1 {{ font-size: 1.25rem; font-weight: 600; }}
  header h1 span {{ color: var(--accent); }}
  .nav-links a {{ margin-left: 1.5rem; color: var(--muted); font-size: 0.9rem; }}
  .nav-links a:hover {{ color: var(--text); }}

  /* Cards grid */
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 1rem; margin-top: 1.5rem; }}
  .card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1.25rem; transition: border-color .15s; }}
  .card:hover {{ border-color: var(--accent); }}
  .card h3 {{ font-size: 1rem; margin-bottom: .4rem; }}
  .card p {{ color: var(--muted); font-size: 0.875rem; }}
  .card .meta {{ display: flex; gap: .75rem; margin-top: .75rem; font-size: 0.8rem; color: var(--muted); }}

  /* Badges */
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 9999px; font-size: 0.75rem; font-weight: 500; }}
  .badge-green {{ background: rgba(34,197,94,.15); color: var(--green); }}
  .badge-blue {{ background: rgba(59,130,246,.15); color: var(--accent); }}

  /* Buttons */
  .btn {{ display: inline-block; padding: .5rem 1rem; border-radius: 6px; border: none; cursor: pointer; font-size: .875rem; font-weight: 500; }}
  .btn-primary {{ background: var(--accent); color: #fff; }}
  .btn-primary:hover {{ background: var(--accent-hover); }}
  .btn-outline {{ background: transparent; border: 1px solid var(--border); color: var(--text); }}
  .btn-outline:hover {{ border-color: var(--accent); color: var(--accent); }}

  /* Detail page */
  .detail-header {{ margin-bottom: 1.5rem; }}
  .detail-header h2 {{ font-size: 1.5rem; }}
  .section {{ background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1.25rem; margin-bottom: 1rem; }}
  .section h3 {{ font-size: 1rem; margin-bottom: .75rem; color: var(--accent); }}
  pre {{ background: #111827; border-radius: 6px; padding: 1rem; overflow-x: auto; font-size: 0.8rem; line-height: 1.5; }}
  code {{ font-family: 'SF Mono', 'Fira Code', monospace; }}
  .tool-row {{ padding: .5rem 0; border-bottom: 1px solid var(--border); }}
  .tool-row:last-child {{ border-bottom: none; }}
  .tool-name {{ font-weight: 600; }}
  .tool-desc {{ color: var(--muted); font-size: .85rem; }}

  /* MCP test panel */
  #mcp-panel {{ margin-top: 1rem; }}
  #mcp-result {{ margin-top: .75rem; }}
  textarea {{ width: 100%; background: #111827; color: var(--text); border: 1px solid var(--border);
              border-radius: 6px; padding: .75rem; font-family: monospace; font-size: .8rem; resize: vertical; }}

  /* Toolbar */
  .toolbar {{ display: flex; align-items: center; justify-content: space-between; margin-top: 1.5rem; }}
  .status-text {{ font-size: .85rem; color: var(--muted); }}
  .empty-state {{ text-align: center; padding: 4rem 1rem; color: var(--muted); }}
  .empty-state p {{ margin-top: .5rem; font-size: .9rem; }}
  .spinner {{ display: inline-block; width: 14px; height: 14px; border: 2px solid var(--border);
              border-top-color: var(--accent); border-radius: 50%; animation: spin .6s linear infinite; }}
  @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
</style>
</head>
<body>
<header>
  <div class="container">
    <h1><span>dbx-agent-app</span> dashboard</h1>
    <nav class="nav-links">
      <a href="/">Agents</a>
      <a href="/health">Health</a>
    </nav>
  </div>
</header>
<div class="container">
{content}
</div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Agent list page
# ---------------------------------------------------------------------------

def render_agent_list(agents: List[DiscoveredAgent]) -> str:
    """Main page: grid of agent cards + scan button."""
    if not agents:
        cards_html = """
<div class="empty-state">
  <h2>No agents discovered</h2>
  <p>No agent-enabled Databricks Apps found in your workspace. Click Scan to retry.</p>
</div>"""
    else:
        cards = []
        for a in agents:
            caps = ""
            if a.capabilities:
                badges = "".join(
                    f'<span class="badge badge-blue">{html.escape(c.strip())}</span> '
                    for c in a.capabilities.split(",")
                )
                caps = f'<div class="meta">{badges}</div>'

            desc = html.escape(a.description or "No description")
            cards.append(f"""
<a href="/agent/{html.escape(a.name)}" style="text-decoration:none;color:inherit;">
<div class="card">
  <h3>{html.escape(a.name)}</h3>
  <p>{desc}</p>
  <div class="meta">
    <span>App: {html.escape(a.app_name)}</span>
    {f'<span>Protocol: {html.escape(a.protocol_version)}</span>' if a.protocol_version else ''}
  </div>
  {caps}
</div>
</a>""")
        cards_html = f'<div class="grid">{"".join(cards)}</div>'

    return render_base(
        "Agent Dashboard",
        f"""
<div class="toolbar">
  <span class="status-text" id="status">{len(agents)} agent{"s" if len(agents) != 1 else ""} discovered</span>
  <button class="btn btn-primary" id="scan-btn" onclick="doScan()">Scan workspace</button>
</div>
{cards_html}
<script>
async function doScan() {{
  const btn = document.getElementById('scan-btn');
  const status = document.getElementById('status');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Scanning...';
  try {{
    const resp = await fetch('/api/scan', {{method: 'POST'}});
    if (resp.ok) window.location.reload();
    else status.textContent = 'Scan failed: ' + resp.status;
  }} catch(e) {{
    status.textContent = 'Scan error: ' + e.message;
  }} finally {{
    btn.disabled = false;
    btn.textContent = 'Scan workspace';
  }}
}}
</script>""",
    )


# ---------------------------------------------------------------------------
# Agent detail page
# ---------------------------------------------------------------------------

def render_agent_detail(
    agent: DiscoveredAgent,
    card: Optional[Dict[str, Any]] = None,
) -> str:
    """Detail page: agent card JSON, tools list, MCP test panel."""
    card_json = json.dumps(card, indent=2) if card else "Card not available"

    # Extract tools from card if present
    tools_html = ""
    if card:
        skills = card.get("skills") or card.get("tools") or []
        if skills:
            rows = []
            for t in skills:
                name = html.escape(t.get("name", t.get("id", "unknown")))
                desc = html.escape(t.get("description", ""))
                rows.append(
                    f'<div class="tool-row"><span class="tool-name">{name}</span>'
                    f'<div class="tool-desc">{desc}</div></div>'
                )
            tools_html = f"""
<div class="section">
  <h3>Tools ({len(skills)})</h3>
  {"".join(rows)}
</div>"""

    safe_name = html.escape(agent.name)
    safe_endpoint = html.escape(agent.endpoint_url)

    return render_base(
        f"{safe_name} — Agent Dashboard",
        f"""
<div class="detail-header">
  <a href="/">&larr; All agents</a>
  <h2 style="margin-top:.5rem">{safe_name}</h2>
  <p style="color:var(--muted)">{html.escape(agent.description or 'No description')}</p>
  <div class="meta" style="margin-top:.5rem">
    <span>Endpoint: <code>{safe_endpoint}</code></span>
    <span>App: {html.escape(agent.app_name)}</span>
    {f'<span class="badge badge-green">{html.escape(agent.protocol_version)}</span>' if agent.protocol_version else ''}
  </div>
</div>

<div class="section">
  <h3>Agent Card</h3>
  <pre><code id="card-json">{html.escape(card_json)}</code></pre>
</div>

{tools_html}

<div class="section" id="mcp-panel">
  <h3>MCP Test Panel</h3>
  <p style="font-size:.85rem;color:var(--muted);margin-bottom:.75rem">
    Send a JSON-RPC request to this agent's <code>/api/mcp</code> endpoint.
  </p>
  <div style="display:flex;gap:.5rem;margin-bottom:.5rem">
    <button class="btn btn-outline" onclick="sendMcp('tools/list')">tools/list</button>
    <button class="btn btn-outline" onclick="sendMcp('tools/call')">tools/call</button>
  </div>
  <textarea id="mcp-input" rows="6">{html.escape(json.dumps({"jsonrpc":"2.0","id":"1","method":"tools/list","params":{}}, indent=2))}</textarea>
  <button class="btn btn-primary" style="margin-top:.5rem" onclick="sendMcpRaw()">Send request</button>
  <div id="mcp-result"></div>
</div>

<script>
const agentName = {json.dumps(agent.name)};

function sendMcp(method) {{
  const payload = {{jsonrpc: "2.0", id: "1", method: method, params: {{}}}};
  document.getElementById('mcp-input').value = JSON.stringify(payload, null, 2);
  sendMcpRaw();
}}

async function sendMcpRaw() {{
  const resultEl = document.getElementById('mcp-result');
  resultEl.innerHTML = '<span class="spinner"></span> Sending...';
  try {{
    const body = document.getElementById('mcp-input').value;
    JSON.parse(body); // validate
    const resp = await fetch('/api/agents/' + encodeURIComponent(agentName) + '/mcp', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: body,
    }});
    const data = await resp.json();
    resultEl.innerHTML = '<pre><code>' + escapeHtml(JSON.stringify(data, null, 2)) + '</code></pre>';
  }} catch(e) {{
    resultEl.innerHTML = '<pre style="color:var(--red)">Error: ' + escapeHtml(e.message) + '</pre>';
  }}
}}

function escapeHtml(s) {{
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}}
</script>""",
    )
