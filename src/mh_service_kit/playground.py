PLAYGROUND_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Developer Playground</title>
<style>
  *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
  body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Oxygen,Ubuntu,sans-serif;background:#f5f5f7;color:#1d1d1f;padding:24px;min-height:100vh}
  .container{max-width:960px;margin:0 auto}
  h1{font-size:22px;font-weight:600;margin-bottom:4px}
  .sub{color:#86868b;font-size:13px;margin-bottom:24px}
  .card{background:#fff;border-radius:12px;padding:20px;margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,.08)}
  .card-title{font-size:14px;font-weight:600;margin-bottom:12px;color:#555}
  .row{display:flex;gap:12px;flex-wrap:wrap;align-items:end}
  .col{flex:1;min-width:180px}
  label{display:block;font-size:12px;font-weight:500;color:#555;margin-bottom:4px}
  select,input[type=text],textarea{width:100%;padding:8px 10px;border:1px solid #d2d2d7;border-radius:8px;font-size:13px;background:#fff;outline:none;transition:border-color .15s}
  select:focus,input:focus,textarea:focus{border-color:#0071e3}
  textarea{font-family:ui-monospace,"SF Mono",Menlo,Consolas,monospace;font-size:12px;resize:vertical;min-height:38px}
  .btn{padding:8px 20px;border:none;border-radius:8px;font-size:13px;font-weight:500;cursor:pointer;transition:opacity .15s;display:inline-flex;align-items:center;gap:6px}
  .btn-primary{background:#0071e3;color:#fff}
  .btn-primary:hover{opacity:.85}
  .btn-primary:disabled{opacity:.4;cursor:not-allowed}
  .btn-danger{background:#ff3b30;color:#fff}
  .btn-danger:hover{opacity:.85}
  .params-area{margin-top:12px}
  .param-row{margin-bottom:8px}
  .param-row label{font-size:12px;font-weight:500;color:#555;margin-bottom:2px}
  .param-row .param-type{font-size:11px;color:#86868b;margin-left:6px;font-weight:400}
  .param-row .param-desc{font-size:11px;color:#86868b;margin-top:1px}
  .tabs{display:flex;gap:0;margin-bottom:16px;border-bottom:1px solid #d2d2d7}
  .tab{padding:8px 20px;font-size:13px;cursor:pointer;border:none;background:none;color:#86868b;border-bottom:2px solid transparent;transition:all .15s}
  .tab.active{color:#0071e3;border-bottom-color:#0071e3;font-weight:600}
  .tab:hover{color:#1d1d1f}
  .toolbar{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:12px}
  .toolbar .status-badge{padding:2px 10px;border-radius:12px;font-size:11px;font-weight:500;background:#e8e8ed;color:#555}
  .toolbar .status-badge.running{background:#0071e3;color:#fff}
  .toolbar .status-badge.done{background:#30d158;color:#fff}
  .toolbar .status-badge.error{background:#ff3b30;color:#fff}
  .output-area{background:#1d1d1f;border-radius:10px;padding:16px;font-family:ui-monospace,"SF Mono",Menlo,Consolas,monospace;font-size:12px;line-height:1.6;color:#e8e8ed;max-height:500px;overflow:auto;white-space:pre-wrap;word-break:break-all;position:relative}
  .output-area .line{padding:1px 0;display:flex}
  .output-area .line .tag{flex:0 0 85px;padding:0 6px;border-radius:4px;font-size:11px;font-weight:500;text-align:center;margin-right:8px}
  .tag-start{background:#5e5ce6;color:#fff}
  .tag-progress{background:#0071e3;color:#fff}
  .tag-end{background:#30d158;color:#1d1d1f}
  .tag-error{background:#ff3b30;color:#fff}
  .tag-llm{background:#ff9f0a;color:#1d1d1f}
  .tag-info{background:#48484a;color:#e8e8ed}
  .output-placeholder{color:#48484a;font-style:italic}
  .hidden{display:none !important}
  .clear-btn{position:absolute;top:8px;right:8px;background:#48484a;border:none;color:#e8e8ed;font-size:11px;padding:4px 10px;border-radius:6px;cursor:pointer;opacity:.6;transition:opacity .15s}
  .clear-btn:hover{opacity:1}
</style>
</head>
<body>
<div class="container">
  <h1>🛠️ Developer Playground</h1>
  <p class="sub">Invoke tools and agents, observe SSE events in real-time</p>

  <div class="card">
    <div class="tabs">
      <button class="tab active" data-tab="tool" onclick="switchTab('tool')">Tool</button>
      <button class="tab" data-tab="agent" onclick="switchTab('agent')">Agent</button>
    </div>

    <div id="panel-tool">
      <div class="row">
        <div class="col">
          <label>Tool</label>
          <select id="tool-select" onchange="onToolChange()"><option value="">— select —</option></select>
        </div>
      </div>
      <div class="params-area" id="tool-params"></div>
    </div>

    <div id="panel-agent" class="hidden">
      <div class="row">
        <div class="col">
          <label>Agent</label>
          <select id="agent-select" onchange="onAgentChange()"><option value="">— select —</option></select>
        </div>
      </div>
      <div class="params-area" id="agent-params"></div>
    </div>

    <div class="toolbar" style="margin-top:16px">
      <button class="btn btn-primary" id="invoke-btn" onclick="invoke()">▶ Invoke</button>
      <button class="btn btn-danger hidden" id="cancel-btn" onclick="cancelInvoke()">■ Cancel</button>
      <span class="status-badge hidden" id="status-badge">Idle</span>
    </div>
  </div>

  <div class="card" style="position:relative">
    <div class="card-title">Output (SSE Stream)</div>
    <div class="output-area" id="output"><span class="output-placeholder">Select an endpoint and click Invoke to see results…</span></div>
    <button class="clear-btn" onclick="clearOutput()">✕ Clear</button>
  </div>
</div>

<script>
let currentAbort = null;
let allTools = [];
let allAgents = [];

async function init() {
  try {
    const [tools, agents] = await Promise.all([
      fetch('/tools').then(r => r.json()),
      fetch('/agents').then(r => r.json()),
    ]);
    allTools = tools;
    allAgents = agents;

    const toolSel = document.getElementById('tool-select');
    toolSel.innerHTML = '<option value="">— select —</option>' + tools.map(t =>
      `<option value="${t.name}">${t.display_name}</option>`
    ).join('');

    const agentSel = document.getElementById('agent-select');
    agentSel.innerHTML = '<option value="">— select —</option>' + agents.map(a =>
      `<option value="${a.name}">${a.display_name}</option>`
    ).join('');

    const params = new URLSearchParams(location.search);
    if (params.get('tab') === 'agent') switchTab('agent');
    if (params.get('tool')) { toolSel.value = params.get('tool'); onToolChange(); }
    if (params.get('agent')) { agentSel.value = params.get('agent'); switchTab('agent'); onAgentChange(); }
  } catch(e) {
    appendLine('error', 'Failed to load tools/agents: ' + e.message);
  }
}

function switchTab(tab) {
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tab));
  document.getElementById('panel-tool').classList.toggle('hidden', tab !== 'tool');
  document.getElementById('panel-agent').classList.toggle('hidden', tab !== 'agent');
}

function onToolChange() {
  const sel = document.getElementById('tool-select');
  const tool = allTools.find(t => t.name === sel.value);
  renderParams('tool-params', tool ? tool.parameters : null);
}

function onAgentChange() {
  const sel = document.getElementById('agent-select');
  const agent = allAgents.find(a => a.name === sel.value);
  const area = document.getElementById('agent-params');
  if (!agent) { area.innerHTML = ''; return; }
  area.innerHTML = `
    <div class="param-row">
      <label>User Input <span class="param-type">string</span></label>
      <textarea rows="3" id="agent-text" placeholder="Enter your message for the agent...">${agent.description ? 'Tell me about ' + agent.name : 'Hello'}</textarea>
    </div>
    <div class="param-row">
      <label>System Prompt (optional) <span class="param-type">string</span></label>
      <textarea rows="2" id="agent-system-prompt" placeholder="Leave empty to use default"></textarea>
    </div>
  `;
}

function renderParams(containerId, params) {
  const area = document.getElementById(containerId);
  if (!params || !params.properties) { area.innerHTML = ''; return; }
  const required = new Set(params.required || []);
  area.innerHTML = Object.entries(params.properties).map(([key, prop]) => {
    const isObj = prop.type === 'object' || prop.type === 'array'
      || (prop.anyOf && prop.anyOf.some(s => s.type === 'object' || s.type === 'array'))
      || prop.additionalProperties !== undefined;
    const isEnum = prop.enum && prop.enum.length > 0;
    const req = required.has(key) ? ' *' : '';
    const desc = prop.description ? `<div class="param-desc">${prop.description}</div>` : '';
    const typeInfo = (prop.enum ? prop.enum.join(' | ') : prop.type)
      || (isObj ? 'object' : 'string');

    let input = '';
    if (isObj) {
      const isArray = prop.type === 'array'
        || (prop.anyOf && prop.anyOf.some(s => s.type === 'array'));
      input = `<textarea rows="3" id="param-${key}" placeholder='${isArray ? '["item1","item2"]' : '{"key":"value"}'}'>${prop.default ? JSON.stringify(prop.default, null, 2) : ''}</textarea>`;
    } else if (isEnum) {
      const opts = prop.enum.map(v => `<option value="${v}"${prop.default === v ? ' selected' : ''}>${v}</option>`).join('');
      input = `<select id="param-${key}"><option value="">— select —</option>${opts}</select>`;
    } else {
      input = `<input type="text" id="param-${key}" placeholder="${prop.type || 'value'}" value="${prop.default || ''}">`;
    }

    return `<div class="param-row">
      <label>${key}${req} <span class="param-type">${typeInfo}</span></label>
      ${input}
      ${desc}
    </div>`;
  }).join('');
}

function collectParams(containerId) {
  const area = document.getElementById(containerId);
  const inputs = area.querySelectorAll('[id^="param-"]');
  const args = {};
  inputs.forEach(el => {
    const key = el.id.replace('param-', '');
    let val = el.value;
    if (el.tagName === 'TEXTAREA') {
      try { val = JSON.parse(val); } catch(e) {}
    }
    args[key] = val;
  });
  return args;
}

function isActiveTab(tab) {
  return document.querySelector('.tab.active').dataset.tab === tab;
}

function getActiveEndpoint() {
  if (isActiveTab('tool')) {
    const sel = document.getElementById('tool-select');
    return sel.value ? { type: 'tool', name: sel.value } : null;
  }
  const sel = document.getElementById('agent-select');
  return sel.value ? { type: 'agent', name: sel.value } : null;
}

async function invoke() {
  const ep = getActiveEndpoint();
  if (!ep) { appendLine('error', 'Please select an endpoint first'); return; }

  clearOutput();
  setRunning(true);

  let url, body;
  if (ep.type === 'tool') {
    url = '/tools/' + encodeURIComponent(ep.name) + '/execute';
    body = { args: collectParams('tool-params') };
  } else {
    url = '/agent/' + encodeURIComponent(ep.name) + '/run';
    const text = document.getElementById('agent-text')?.value || '';
    const sysPrompt = document.getElementById('agent-system-prompt')?.value || '';
    body = { user_input: [{ type: 'text', text }] };
    if (sysPrompt) body.system_prompt = sysPrompt;
  }

  currentAbort = new AbortController();
  try {
    const resp = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: currentAbort.signal,
    });

    if (!resp.ok) {
      appendLine('error', `HTTP ${resp.status}: ${resp.statusText}`);
      setRunning(false, 'error');
      return;
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const evt = JSON.parse(line.slice(6));
            appendEvent(evt);
          } catch { /* skip malformed */ }
        }
      }
    }
    setRunning(false, 'done');
  } catch (e) {
    if (e.name === 'AbortError') {
      appendLine('info', '— Cancelled —');
    } else {
      appendLine('error', 'Error: ' + e.message);
    }
    setRunning(false, 'error');
  }
  currentAbort = null;
}

function cancelInvoke() {
  if (currentAbort) {
    currentAbort.abort();
    currentAbort = null;
  }
}

function appendEvent(evt) {
  const t = evt.type || '';
  let tagClass = 'tag-info';
  if (t === 'tool_start' || t === 'agent_start' || t === 'execution_start') tagClass = 'tag-start';
  else if (t === 'tool_progress' || t === 'llm_chunk') tagClass = 'tag-progress';
  else if (t === 'tool_end' || t === 'execution_end' || t === 'agent_end') tagClass = 'tag-end';
  else if (t.includes('error') || t.includes('Error')) tagClass = 'tag-error';
  else if (t.startsWith('llm_')) tagClass = 'tag-llm';

  const content = JSON.stringify(evt, null, 2);
  appendLine(tagClass, `<span class="tag ${tagClass}">${t}</span>${escapeHtml(content)}`);
}

function appendLine(tag, html) {
  const out = document.getElementById('output');
  const placeholder = out.querySelector('.output-placeholder');
  if (placeholder) placeholder.remove();
  const div = document.createElement('div');
  div.className = 'line';
  div.innerHTML = html;
  out.appendChild(div);
  out.scrollTop = out.scrollHeight;
}

function escapeHtml(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

function clearOutput() {
  document.getElementById('output').innerHTML = '<span class="output-placeholder">Select an endpoint and click Invoke to see results…</span>';
}

function setRunning(running, status) {
  const btn = document.getElementById('invoke-btn');
  const cancelBtn = document.getElementById('cancel-btn');
  const badge = document.getElementById('status-badge');
  btn.disabled = running;
  btn.classList.toggle('hidden', running);
  cancelBtn.classList.toggle('hidden', !running);
  badge.classList.toggle('hidden', !running && !status);
  badge.classList.remove('running', 'done', 'error');
  if (running) {
    badge.textContent = 'Running…';
    badge.classList.add('running');
  } else if (status) {
    const labels = { done: 'Done', error: 'Error' };
    badge.textContent = labels[status] || status;
    badge.classList.add(status);
  }
}

document.addEventListener('DOMContentLoaded', init);
</script>
</body>
</html>"""
