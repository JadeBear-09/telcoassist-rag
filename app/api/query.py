# ruff: noqa: E501

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["query"])


@router.get("/", response_class=HTMLResponse)
@router.get("/query", response_class=HTMLResponse)
def query_page() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TelcoAssist Query</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f4f6f8;
      --panel: #ffffff;
      --panel-soft: #eef3f7;
      --line: #d7dee8;
      --text: #172033;
      --muted: #5d697a;
      --accent: #087f8c;
      --accent-dark: #05616a;
      --danger: #b42318;
      --warn: #936300;
      --ok: #16703a;
      --shadow: 0 10px 28px rgba(23, 32, 51, 0.08);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 14px 22px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
      position: sticky;
      top: 0;
      z-index: 4;
    }
    h1 {
      margin: 0;
      font-size: 20px;
      line-height: 1.2;
      letter-spacing: 0;
    }
    .headline {
      display: grid;
      gap: 8px;
    }
    .status-row, .nav, .meta-row {
      display: flex;
      gap: 8px;
      align-items: center;
      flex-wrap: wrap;
    }
    .nav a {
      min-height: 34px;
      display: inline-flex;
      align-items: center;
      color: var(--muted);
      text-decoration: none;
      font-size: 14px;
      font-weight: 700;
      padding: 6px 9px;
      border-radius: 6px;
      border: 1px solid transparent;
    }
    .nav a:hover {
      color: var(--accent-dark);
      border-color: var(--line);
      background: var(--panel-soft);
    }
    main {
      width: min(1480px, 100%);
      margin: 0 auto;
      padding: 18px 22px 28px;
      display: grid;
      grid-template-columns: minmax(0, 1.35fr) minmax(360px, 0.8fr);
      gap: 18px;
    }
    section, aside {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
    }
    .query-pane {
      display: grid;
      grid-template-rows: auto auto auto auto minmax(240px, auto);
      min-height: calc(100vh - 118px);
    }
    .pane-head {
      padding: 15px 18px;
      border-bottom: 1px solid var(--line);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
    }
    .pane-title {
      margin: 0;
      font-size: 15px;
      line-height: 1.2;
      letter-spacing: 0;
    }
    .run-setup {
      padding: 14px 18px;
      border-bottom: 1px solid var(--line);
      background: #fbfcfd;
      display: grid;
      gap: 12px;
    }
    .run-grid {
      display: grid;
      grid-template-columns: minmax(170px, 0.7fr) minmax(170px, 0.55fr) minmax(220px, 1fr) minmax(84px, 0.25fr);
      gap: 12px;
      align-items: end;
    }
    .source-note {
      padding: 12px 18px;
      border-bottom: 1px solid var(--line);
      display: grid;
      gap: 8px;
    }
    .source-note p {
      margin: 0;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
    }
    .source-note code {
      color: var(--text);
      background: var(--panel-soft);
      border-radius: 4px;
      padding: 1px 4px;
    }
    .disclaimer {
      color: var(--danger) !important;
    }
    form {
      display: grid;
      gap: 14px;
    }
    .question-form {
      padding: 16px 18px 18px;
      align-content: start;
    }
    label {
      display: grid;
      gap: 6px;
      color: var(--muted);
      font-size: 13px;
      font-weight: 700;
    }
    .key-field {
      display: grid;
      gap: 6px;
    }
    .key-actions {
      display: flex;
      gap: 10px;
      align-items: center;
      flex-wrap: wrap;
      color: var(--muted);
      font-size: 12px;
      font-weight: 800;
    }
    .key-actions label {
      display: inline-flex;
      gap: 6px;
      align-items: center;
      color: var(--muted);
      font-size: 12px;
      font-weight: 800;
    }
    .key-actions input[type="checkbox"] {
      width: auto;
      margin: 0;
    }
    .link-button {
      min-height: auto;
      padding: 0;
      border: 0;
      background: transparent;
      color: var(--accent-dark);
      font-size: 12px;
      font-weight: 900;
    }
    .link-button:hover {
      background: transparent;
      text-decoration: underline;
    }
    input, textarea, select, button {
      font: inherit;
      letter-spacing: 0;
    }
    textarea, input, select {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #ffffff;
      color: var(--text);
      padding: 10px 11px;
      outline: none;
    }
    textarea {
      min-height: 138px;
      resize: vertical;
      line-height: 1.45;
    }
    textarea:focus, input:focus, select:focus {
      border-color: var(--accent);
      box-shadow: 0 0 0 3px rgba(8, 127, 140, 0.14);
    }
    .grid-two {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }
    .examples {
      padding: 13px 18px;
      border-bottom: 1px solid var(--line);
      display: grid;
      gap: 10px;
      background: var(--panel);
    }
    .examples-title {
      color: var(--muted);
      font-size: 13px;
      font-weight: 800;
    }
    .example-list {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }
    .example-button {
      min-height: 36px;
      padding: 8px 10px;
      background: #ffffff;
      color: var(--text);
      border: 1px solid var(--line);
      font-size: 13px;
      font-weight: 800;
    }
    .example-button:hover,
    .example-button.active {
      border-color: var(--accent);
      color: var(--accent-dark);
      background: rgba(8, 127, 140, 0.08);
    }
    .actions {
      display: flex;
      justify-content: flex-end;
      gap: 10px;
      flex-wrap: wrap;
    }
    button {
      border: 1px solid transparent;
      border-radius: 6px;
      padding: 10px 14px;
      cursor: pointer;
      min-height: 42px;
      font-weight: 800;
    }
    button:disabled {
      cursor: not-allowed;
      opacity: 0.6;
    }
    .primary {
      background: var(--accent);
      color: #ffffff;
    }
    .primary:hover { background: var(--accent-dark); }
    .secondary {
      background: var(--panel-soft);
      color: var(--text);
      border-color: var(--line);
    }
    .secondary:hover { border-color: var(--accent); }
    .answer-shell {
      border-top: 1px solid var(--line);
      background: #fbfcfd;
      display: grid;
      align-content: start;
    }
    .answer-meta, .feedback-actions {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      padding: 14px 18px 0;
    }
    .pill {
      display: inline-flex;
      align-items: center;
      min-height: 28px;
      padding: 4px 9px;
      border-radius: 999px;
      background: var(--panel-soft);
      color: var(--muted);
      font-size: 12px;
      font-weight: 800;
      border: 1px solid transparent;
    }
    .pill.ok { color: var(--ok); }
    .pill.bad { color: var(--danger); }
    .pill.warn { color: var(--warn); }
    .pill-button {
      cursor: pointer;
    }
    .pill-button:hover {
      color: var(--accent-dark);
      box-shadow: 0 0 0 2px rgba(8, 127, 140, 0.16);
    }
    .quality-grid {
      padding: 12px 18px 0;
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
    }
    .quality-card {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #ffffff;
      padding: 10px;
      display: grid;
      gap: 4px;
      min-height: 74px;
    }
    .quality-card strong {
      font-size: 12px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0;
    }
    .quality-card span {
      font-size: 13px;
      line-height: 1.35;
      font-weight: 700;
    }
    .answer {
      margin: 0;
      padding: 16px 18px 18px;
      font-family: inherit;
      line-height: 1.55;
      min-height: 170px;
    }
    .answer h3 {
      margin: 14px 0 6px;
      font-size: 15px;
      line-height: 1.3;
      letter-spacing: 0;
    }
    .answer h3:first-child { margin-top: 0; }
    .answer p {
      margin: 0 0 10px;
    }
    .answer ul {
      margin: 0 0 12px 20px;
      padding: 0;
      display: grid;
      gap: 5px;
    }
    .answer hr {
      border: 0;
      border-top: 1px solid var(--line);
      margin: 14px 0;
    }
    .feedback {
      border-top: 1px solid var(--line);
      padding: 0 0 14px;
    }
    .feedback-actions button {
      min-height: 34px;
      padding: 7px 10px;
      font-size: 12px;
    }
    .feedback-status {
      padding: 8px 18px 0;
      color: var(--muted);
      font-size: 12px;
      min-height: 24px;
    }
    aside {
      display: grid;
      grid-template-rows: auto minmax(160px, 230px) minmax(180px, 280px) auto auto minmax(220px, 1fr);
      min-height: calc(100vh - 118px);
      overflow: hidden;
    }
    .settings {
      padding: 14px 16px;
      border-bottom: 1px solid var(--line);
    }
    .helper {
      margin: -6px 0 0;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.4;
    }
    .advanced {
      padding-top: 2px;
    }
    .advanced summary {
      cursor: pointer;
      color: var(--text);
      font-size: 13px;
      font-weight: 800;
      margin-bottom: 12px;
    }
    .advanced-fields {
      display: grid;
      gap: 14px;
    }
    .kb-panel, .preview-panel {
      border-bottom: 1px solid var(--line);
      padding: 12px 16px;
      display: grid;
      gap: 10px;
      overflow: auto;
      background: #fbfcfd;
    }
    .preview-panel {
      align-content: start;
      background: #ffffff;
    }
    .doc-card, .citation {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #ffffff;
      padding: 12px;
      display: grid;
      gap: 7px;
    }
    .doc-card.active {
      border-color: var(--accent);
      box-shadow: 0 0 0 3px rgba(8, 127, 140, 0.14);
    }
    .doc-card-actions {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }
    .mini-button {
      min-height: 30px;
      padding: 6px 9px;
      font-size: 12px;
      width: auto;
    }
    .doc-title, .citation-title {
      font-weight: 900;
      line-height: 1.25;
    }
    .citation-title {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }
    .doc-meta, .citation-meta {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.35;
    }
    .source-path {
      color: var(--muted);
      font-size: 12px;
      overflow-wrap: anywhere;
    }
    .chunk-preview {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px;
      display: grid;
      gap: 8px;
      background: #fbfcfd;
    }
    .chunk-preview-title {
      color: var(--muted);
      font-size: 12px;
      font-weight: 900;
    }
    .chunk-text {
      margin: 0;
      color: var(--text);
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 12px;
      line-height: 1.45;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
    }
    .citations {
      overflow: auto;
      padding: 14px 16px 18px;
      display: grid;
      align-content: start;
      gap: 10px;
      scroll-margin-top: 16px;
    }
    .citation.highlight {
      border-color: #f59e0b;
      box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.2);
    }
    .excerpt {
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
      margin: 0;
    }
    .status {
      min-height: 20px;
      color: var(--muted);
      font-size: 13px;
      font-weight: 700;
    }
    .status.error { color: var(--danger); font-weight: 800; }
    .empty {
      color: var(--muted);
      font-size: 13px;
      padding: 12px;
      border: 1px dashed var(--line);
      border-radius: 8px;
      background: #ffffff;
    }
    @media (max-width: 1060px) {
      main {
        grid-template-columns: 1fr;
        padding: 14px;
      }
      header {
        align-items: flex-start;
        flex-direction: column;
        padding: 14px;
        position: static;
      }
      .query-pane, aside {
        min-height: auto;
      }
      .quality-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }
    }
    @media (max-width: 700px) {
      .run-grid, .grid-two, .quality-grid {
        grid-template-columns: 1fr;
      }
      .pane-head {
        align-items: flex-start;
        flex-direction: column;
      }
      .actions {
        justify-content: stretch;
      }
      button {
        width: 100%;
      }
    }
  </style>
</head>
<body>
  <header>
    <div class="headline">
      <h1>TelcoAssist Query</h1>
      <div class="status-row">
        <span id="kb-status" class="pill">KB loading</span>
        <span id="run-mode" class="pill">Local RAG</span>
        <span id="key-status" class="pill">No key needed</span>
      </div>
    </div>
    <nav class="nav" aria-label="Primary">
      <a href="/upload">Upload ZIP</a>
      <a href="/dashboard/summary">Dashboard JSON</a>
      <a href="/docs">API Docs</a>
    </nav>
  </header>
  <main>
    <section class="query-pane">
      <div class="pane-head">
        <h2 class="pane-title">Ask</h2>
        <div id="status" class="status">Ready</div>
      </div>
      <div class="run-setup">
        <div class="run-grid">
          <label>
            Answer Provider
            <select id="llm-provider">
              <option value="local">Local extractive answer</option>
              <option value="gemini">Gemini API key</option>
              <option value="openai">OpenAI API key</option>
            </select>
          </label>
          <label>
            Answer Style
            <select id="answer-style">
              <option value="standard">Standard support answer</option>
              <option value="brief">Brief triage</option>
              <option value="audit">Audit review</option>
            </select>
          </label>
          <div class="key-field">
            <label>
              Model API Key
              <input id="llm-api-key" type="password" autocomplete="off" placeholder="Optional for Gemini/OpenAI">
            </label>
            <div class="key-actions">
              <label><input id="remember-llm-api-key" type="checkbox"> Remember key</label>
              <button class="link-button" type="button" id="clear-llm-api-key">Forget</button>
            </div>
          </div>
          <label>
            Top K
            <input id="top-k" type="number" min="1" max="12" value="6">
          </label>
        </div>
        <p id="provider-note" class="helper">Local RAG works without an API key. Standard style is best for support users; audit style is for reviewers checking source faithfulness.</p>
      </div>
      <div class="source-note">
        <p>Queries run against five local Deutsche Telekom demo docs from <code>data/raw</code>, indexed into <code>data/processed</code>: 5G Troubleshooting SOP, Billing Dispute Process, eSIM Migration Guide, Network Incident Escalation Runbook, and SIM Activation Policy.</p>
        <p class="disclaimer">Demo answers are grounded in retrieved chunks only. Verify citations before using them for live customer or network operations.</p>
      </div>
      <div class="examples" aria-label="Sample questions">
        <div class="examples-title">Sample questions</div>
        <div class="example-list">
          <button class="example-button" type="button" data-region="" data-product="" data-question="How many docs are in the knowledge base?">KB inventory</button>
          <button class="example-button" type="button" data-region="" data-product="" data-question="What does DT_SIM_POL_048 say about escalation?">Exact lookup</button>
          <button class="example-button" type="button" data-region="" data-product="" data-question="Which document supports the answer about SIM activation escalation?">Source check</button>
          <button class="example-button" type="button" data-region="Germany" data-product="" data-question="Compare SIM activation escalation vs eSIM activation escalation.">Multi-doc compare</button>
          <button class="example-button" type="button" data-region="Germany" data-product="" data-question="For poor 5G after SIM replacement, combine SIM policy and 5G SOP steps.">Cross-doc workflow</button>
          <button class="example-button" type="button" data-region="" data-product="Billing" data-question="What are the latest billing prices with dates?">Missing info</button>
          <button class="example-button" type="button" data-region="Germany" data-product="Billing" data-question="A customer in Berlin has poor 5G signal after SIM replacement. What troubleshooting steps should support follow?">Filter test</button>
          <button class="example-button" type="button" data-region="Germany" data-product="SIM" data-question="Which cited chunk contains the claim that support must verify ICCID status before replacing the SIM again?">Citation test</button>
          <button class="example-button active" type="button" data-region="Germany" data-product="5G" data-question="A customer in Berlin has poor 5G signal after SIM replacement. What troubleshooting steps should support follow?">5G after SIM swap</button>
          <button class="example-button" type="button" data-region="Germany" data-product="SIM" data-question="Customer says mobile data stopped after SIM replacement but voice works. What provisioning checks and escalation path apply?">SIM data inactive</button>
          <button class="example-button" type="button" data-region="Germany" data-product="5G" data-question="What should support collect before escalating degraded 5G service for multiple customers in the same area?">Area degradation</button>
          <button class="example-button" type="button" data-region="Germany" data-product="eSIM" data-question="What steps should support follow when eSIM activation fails during migration?">eSIM activation</button>
          <button class="example-button" type="button" data-region="Germany" data-product="Billing" data-question="A customer disputes roaming charges on the latest invoice. What intake details and escalation criteria apply?">Billing dispute</button>
        </div>
      </div>
      <form id="query-form" class="question-form">
        <label>
          Question
          <textarea id="question" required>A customer in Berlin has poor 5G signal after SIM replacement. What troubleshooting steps should support follow?</textarea>
        </label>
        <div class="grid-two">
          <label>
            Region filter
            <input id="region" value="Germany" autocomplete="off">
          </label>
          <label>
            Product filter
            <input id="product" value="5G" autocomplete="off">
          </label>
        </div>
        <div class="actions">
          <button class="secondary" type="button" id="clear-filters">Clear filters</button>
          <button class="secondary" type="button" id="clear">Clear question</button>
          <button class="primary" type="submit" id="ask">Ask</button>
        </div>
      </form>
      <div class="answer-shell">
        <div id="answer-meta" class="answer-meta"></div>
        <div id="quality-panel" class="quality-grid"></div>
        <div id="answer" class="answer">Answer will appear here.</div>
        <div id="feedback" class="feedback" hidden>
          <div class="feedback-actions">
            <button class="secondary" type="button" data-rating="up" data-reason="other">Mark correct</button>
            <button class="secondary" type="button" data-rating="down" data-reason="wrong_source">Wrong source</button>
            <button class="secondary" type="button" data-rating="down" data-reason="incomplete">Incomplete</button>
            <button class="secondary" type="button" data-rating="down" data-reason="hallucinated">Unsupported</button>
          </div>
          <div id="feedback-status" class="feedback-status"></div>
        </div>
      </div>
    </section>
    <aside>
      <div class="pane-head">
        <h2 class="pane-title">Knowledge Base</h2>
        <a class="pill pill-button" href="/upload">Add docs</a>
      </div>
      <div id="kb-docs" class="kb-panel">
        <div class="empty">Document inventory loading.</div>
      </div>
      <div id="doc-preview" class="preview-panel">
        <div class="empty">Select Preview on a document to see indexed chunks.</div>
      </div>
      <div class="settings" id="settings-form">
        <details class="advanced">
          <summary>Advanced security</summary>
          <div class="advanced-fields">
            <div class="grid-two">
              <label>
                Tenant ID
                <input id="tenant-id" value="demo-tenant" autocomplete="off">
              </label>
              <label>
                User ID
                <input id="user-id" value="support.alice" autocomplete="off">
              </label>
            </div>
            <label>
              Roles
              <input id="roles" value="support_agent,network_admin" autocomplete="off">
            </label>
            <label>
              App Access Key
              <input id="api-key" type="password" autocomplete="off">
            </label>
            <div class="key-actions">
              <label><input id="remember-app-api-key" type="checkbox"> Remember key</label>
              <button class="link-button" type="button" id="clear-app-api-key">Forget</button>
            </div>
            <p class="helper">Tenant/user/roles are ACL demo headers. App access key is only needed when backend API auth is enabled.</p>
          </div>
        </details>
      </div>
      <div class="pane-head">
        <h2 class="pane-title">Evidence</h2>
      </div>
      <div id="citations" class="citations">
        <div class="empty">Sources will appear here.</div>
      </div>
    </aside>
  </main>
  <script>
    const form = document.getElementById("query-form");
    const statusEl = document.getElementById("status");
    const answerEl = document.getElementById("answer");
    const answerMetaEl = document.getElementById("answer-meta");
    const qualityPanelEl = document.getElementById("quality-panel");
    const citationsEl = document.getElementById("citations");
    const docPreviewEl = document.getElementById("doc-preview");
    const askButton = document.getElementById("ask");
    const feedbackEl = document.getElementById("feedback");
    const feedbackStatusEl = document.getElementById("feedback-status");
    const exampleButtons = Array.from(document.querySelectorAll(".example-button"));
    const providerSelect = document.getElementById("llm-provider");
    const providerKeyInput = document.getElementById("llm-api-key");
    const rememberProviderKeyInput = document.getElementById("remember-llm-api-key");
    const appKeyInput = document.getElementById("api-key");
    const rememberAppKeyInput = document.getElementById("remember-app-api-key");
    const answerStyleSelect = document.getElementById("answer-style");
    let lastPayload = null;
    let lastQuestion = "";
    let selectedDocId = "";
    let activeProvider = providerSelect.value;
    const storagePrefix = "telcoassist.query.";

    const value = (id) => document.getElementById(id).value.trim();

    function storageGet(key) {
      try {
        return window.localStorage.getItem(storagePrefix + key) || "";
      } catch (error) {
        return "";
      }
    }

    function storageSet(key, value) {
      try {
        window.localStorage.setItem(storagePrefix + key, value);
      } catch (error) {
        // Browser storage can be blocked; form still works for current request.
      }
    }

    function storageRemove(key) {
      try {
        window.localStorage.removeItem(storagePrefix + key);
      } catch (error) {
        // Browser storage can be blocked; form still works for current request.
      }
    }

    function modelKeyStorageKey(provider) {
      return "llm-api-key." + provider;
    }

    function rememberModelKeyStorageKey(provider) {
      return "remember-llm-api-key." + provider;
    }

    function persistCurrentModelKey(provider = providerSelect.value) {
      if (provider === "local") return;
      const key = providerKeyInput.value.trim();
      if (rememberProviderKeyInput.checked && key) {
        storageSet(modelKeyStorageKey(provider), key);
        storageSet(rememberModelKeyStorageKey(provider), "true");
        return;
      }
      storageRemove(modelKeyStorageKey(provider));
      storageRemove(rememberModelKeyStorageKey(provider));
    }

    function loadModelKeyForProvider() {
      const provider = providerSelect.value;
      if (provider === "local") {
        providerKeyInput.value = "";
        rememberProviderKeyInput.checked = false;
        return;
      }
      const shouldRemember = storageGet(rememberModelKeyStorageKey(provider)) === "true";
      rememberProviderKeyInput.checked = shouldRemember;
      providerKeyInput.value = shouldRemember ? storageGet(modelKeyStorageKey(provider)) : "";
    }

    function persistAppKey() {
      const key = appKeyInput.value.trim();
      if (rememberAppKeyInput.checked && key) {
        storageSet("app-api-key", key);
        storageSet("remember-app-api-key", "true");
        return;
      }
      storageRemove("app-api-key");
      storageRemove("remember-app-api-key");
    }

    function loadAppKey() {
      const shouldRemember = storageGet("remember-app-api-key") === "true";
      rememberAppKeyInput.checked = shouldRemember;
      appKeyInput.value = shouldRemember ? storageGet("app-api-key") : "";
    }

    function restoreSavedFormState() {
      const savedProvider = storageGet("llm-provider");
      if (["local", "gemini", "openai"].includes(savedProvider)) {
        providerSelect.value = savedProvider;
      }
      activeProvider = providerSelect.value;
      const savedAnswerStyle = storageGet("answer-style");
      if (["standard", "brief", "audit"].includes(savedAnswerStyle)) {
        answerStyleSelect.value = savedAnswerStyle;
      }
      const savedTopK = storageGet("top-k");
      if (/^\\d+$/.test(savedTopK)) {
        document.getElementById("top-k").value = savedTopK;
      }
      loadModelKeyForProvider();
      loadAppKey();
    }

    function setStatus(text, error = false) {
      statusEl.textContent = text;
      statusEl.classList.toggle("error", error);
    }

    function setPill(id, text, state = "") {
      const el = document.getElementById(id);
      el.textContent = text;
      el.className = "pill " + state;
    }

    function resetResults(status = "Ready") {
      renderAnswer("Answer will appear here.");
      answerMetaEl.replaceChildren();
      qualityPanelEl.replaceChildren();
      citationsEl.replaceChildren();
      feedbackEl.hidden = true;
      feedbackStatusEl.textContent = "";
      lastPayload = null;
      const empty = document.createElement("div");
      empty.className = "empty";
      empty.textContent = "Sources will appear here.";
      citationsEl.append(empty);
      setStatus(status);
      updateProviderStatus();
    }

    function cleanAnswerMarkdown(text) {
      return (text || "")
        .replaceAll("$\\\\rightarrow$", "->")
        .replaceAll("\\\\rightarrow", "->")
        .replaceAll("\\\\rightarrows", "->")
        .replaceAll("\\\\n", "\\n")
        .replace(/\\s+(#{1,6}\\s+)/g, "\\n$1");
    }

    function appendInlineMarkdown(node, text) {
      const parts = cleanAnswerMarkdown(text).split("**");
      parts.forEach((part, index) => {
        if (!part) return;
        if (index % 2 === 1) {
          const strong = document.createElement("strong");
          strong.textContent = part;
          node.append(strong);
        } else {
          node.append(document.createTextNode(part));
        }
      });
    }

    function renderAnswer(markdown) {
      answerEl.replaceChildren();
      const lines = cleanAnswerMarkdown(markdown).split(/\\r?\\n/);
      let list = null;
      const closeList = () => {
        list = null;
      };
      const addParagraph = (text) => {
        const paragraph = document.createElement("p");
        appendInlineMarkdown(paragraph, text);
        answerEl.append(paragraph);
      };

      lines.forEach((line) => {
        const trimmed = line.trim();
        if (!trimmed) {
          closeList();
          return;
        }
        if (/^-{3,}$/.test(trimmed)) {
          closeList();
          answerEl.append(document.createElement("hr"));
          return;
        }
        const heading = trimmed.match(/^#{1,6}\\s+(.+)$/);
        if (heading) {
          closeList();
          const h3 = document.createElement("h3");
          appendInlineMarkdown(h3, heading[1]);
          answerEl.append(h3);
          return;
        }
        const bullet = trimmed.match(/^[-*]\\s+(.+)$/);
        if (bullet) {
          if (!list) {
            list = document.createElement("ul");
            answerEl.append(list);
          }
          const item = document.createElement("li");
          appendInlineMarkdown(item, bullet[1]);
          list.append(item);
          return;
        }
        closeList();
        addParagraph(trimmed);
      });

      if (!answerEl.childNodes.length) {
        addParagraph("No answer returned.");
      }
    }

    function loadExample(button) {
      document.getElementById("question").value = button.dataset.question || "";
      document.getElementById("region").value = button.dataset.region || "";
      document.getElementById("product").value = button.dataset.product || "";
      exampleButtons.forEach((item) => item.classList.toggle("active", item === button));
      resetResults("Example loaded");
    }

    function formatProvider(provider) {
      const names = {
        index_metadata: "Index metadata",
        local: "Local RAG",
        gemini: "Gemini",
        openai: "OpenAI",
      };
      return names[provider] || provider || "Local RAG";
    }

    function filterSummary() {
      const filters = [];
      if (value("region")) filters.push("region=" + value("region"));
      if (value("product")) filters.push("product=" + value("product"));
      return filters.length ? filters.join(", ") : "none";
    }

    function updateProviderStatus() {
      const provider = providerSelect.value;
      const hasKey = Boolean(providerKeyInput.value.trim());
      if (provider === "local") {
        setPill("run-mode", "Local RAG", "ok");
        setPill("key-status", hasKey ? "Key entered, unused" : "No key needed", hasKey ? "warn" : "");
        document.getElementById("provider-note").textContent = hasKey
          ? "Local provider ignores model API key. Choose Gemini or OpenAI to use it."
          : "Local RAG works without an API key. Standard style is best for support; audit style is for reviewer checks.";
        return;
      }
      setPill("run-mode", provider === "gemini" ? "Gemini mode" : "OpenAI mode", hasKey ? "ok" : "warn");
      setPill("key-status", hasKey ? "Key will be sent" : "Key missing", hasKey ? "ok" : "warn");
      document.getElementById("provider-note").textContent = hasKey
        ? "Key is sent only as a request header. Response provider pill confirms whether it was used."
        : "Enter a model key for this provider. Without one, backend falls back to local RAG unless a server key exists.";
    }

    function renderMeta(payload) {
      const confidence = Math.round((payload.confidence || 0) * 100);
      const sourceCount = (payload.sources || []).length;
      const provider = formatProvider(payload.answer_provider);
      const items = [
        {
          text: "Confidence " + confidence + "%",
          state: payload.insufficient_information ? "bad" : "ok",
        },
        {
          text: "Provider " + provider,
          state: payload.answer_provider === "local" && providerSelect.value !== "local" ? "warn" : "ok",
        },
        { text: "Latency " + payload.latency_ms + " ms", state: "" },
        {
          text: "Sources " + (payload.sources || []).length,
          state: sourceCount ? "" : "warn",
          action: "sources",
        },
        { text: "Filters " + filterSummary(), state: value("region") || value("product") ? "warn" : "" },
      ];
      if (payload.escalation_path) items.push({ text: payload.escalation_path, state: "" });
      answerMetaEl.replaceChildren(
        ...items.map((item) => {
          const node = document.createElement(item.action === "sources" ? "button" : "span");
          node.className = "pill " + item.state + (item.action === "sources" ? " pill-button" : "");
          node.textContent = item.text;
          if (item.action === "sources") {
            node.type = "button";
            node.addEventListener("click", focusSources);
          }
          return node;
        })
      );
      renderQualityPanel(payload);
    }

    function renderQualityPanel(payload) {
      const confidence = Math.round((payload.confidence || 0) * 100);
      const sourceCount = (payload.sources || []).length;
      const cards = [
        ["Provider", (payload.provider_status || formatProvider(payload.answer_provider))],
        ["Grounding", sourceCount ? sourceCount + " cited chunks" : "No citations returned"],
        ["Scope", "Filters: " + filterSummary()],
        ["Decision", payload.insufficient_information ? "Do not rely: insufficient context" : "Review citations before use"],
      ];
      qualityPanelEl.replaceChildren(
        ...cards.map(([label, text]) => {
          const card = document.createElement("div");
          card.className = "quality-card";
          const strong = document.createElement("strong");
          strong.textContent = label;
          const span = document.createElement("span");
          span.textContent = label === "Decision" ? text + " (" + confidence + "%)" : text;
          card.append(strong, span);
          return card;
        })
      );
    }

    function focusSources() {
      const cards = Array.from(citationsEl.querySelectorAll(".citation"));
      if (cards.length === 0) {
        setStatus("No sources returned", true);
        return;
      }
      citationsEl.scrollIntoView({ behavior: "smooth", block: "start" });
      setStatus("Sources shown");
      cards.forEach((card) => card.classList.add("highlight"));
      cards[0].focus({ preventScroll: true });
      window.setTimeout(() => {
        cards.forEach((card) => card.classList.remove("highlight"));
      }, 4000);
    }

    function renderCitations(sources) {
      citationsEl.replaceChildren();
      if (!sources || sources.length === 0) {
        const empty = document.createElement("div");
        empty.className = "empty";
        empty.textContent = "No sources returned.";
        citationsEl.append(empty);
        return;
      }
      sources.forEach((source, index) => {
        const item = document.createElement("article");
        item.className = "citation";
        item.tabIndex = 0;

        const title = document.createElement("div");
        title.className = "citation-title";
        const titleText = document.createElement("span");
        titleText.textContent = source.document_name || source.doc_id;
        const rank = document.createElement("span");
        rank.className = "pill";
        rank.textContent = "#" + (index + 1);
        title.append(titleText, rank);

        const meta = document.createElement("div");
        meta.className = "citation-meta";
        const fields = [
          source.doc_id,
          "chunk " + source.chunk_index,
          "score " + source.score,
          source.metadata?.product,
          source.metadata?.region,
          source.metadata?.doc_type,
        ].filter(Boolean);
        meta.textContent = fields.join(" | ");

        const excerpt = document.createElement("p");
        excerpt.className = "excerpt";
        excerpt.textContent = source.excerpt || "";

        item.append(title, meta, excerpt);
        if (source.metadata?.source_path) {
          const path = document.createElement("div");
          path.className = "source-path";
          path.textContent = "source: " + source.metadata.source_path;
          item.append(path);
        }
        citationsEl.append(item);
      });
    }

    function renderDocuments(payload) {
      const docsEl = document.getElementById("kb-docs");
      docsEl.replaceChildren();
      const docs = payload.documents || [];
      if (docs.length === 0) {
        const empty = document.createElement("div");
        empty.className = "empty";
        empty.textContent = "No indexed documents.";
        docsEl.append(empty);
        return;
      }
      docs.forEach((doc) => {
        const card = document.createElement("article");
        card.className = "doc-card";
        if (doc.doc_id === selectedDocId) card.classList.add("active");
        const title = document.createElement("div");
        title.className = "doc-title";
        title.textContent = doc.title || doc.doc_id;
        const meta = document.createElement("div");
        meta.className = "doc-meta";
        meta.textContent = [doc.doc_id, doc.chunks + " chunks", doc.product, doc.region, doc.doc_type].filter(Boolean).join(" | ");
        card.append(title, meta);
        if (doc.source_path) {
          const path = document.createElement("div");
          path.className = "source-path";
          path.textContent = doc.source_path;
          card.append(path);
        }
        const actions = document.createElement("div");
        actions.className = "doc-card-actions";
        const previewButton = document.createElement("button");
        previewButton.className = "secondary mini-button";
        previewButton.type = "button";
        previewButton.textContent = "Preview";
        previewButton.addEventListener("click", () => loadDocumentPreview(doc.doc_id));
        actions.append(previewButton);
        card.append(actions);
        docsEl.append(card);
      });
    }

    function renderDocumentPreview(payload) {
      docPreviewEl.replaceChildren();
      const title = document.createElement("div");
      title.className = "doc-title";
      title.textContent = payload.title || payload.doc_id;
      const meta = document.createElement("div");
      meta.className = "doc-meta";
      meta.textContent = [
        payload.doc_id,
        payload.chunk_count + " chunks",
        payload.product,
        payload.region,
        payload.doc_type,
      ].filter(Boolean).join(" | ");
      docPreviewEl.append(title, meta);
      if (payload.source_path) {
        const source = document.createElement("div");
        source.className = "source-path";
        source.textContent = "source: " + payload.source_path;
        docPreviewEl.append(source);
      }
      const note = document.createElement("div");
      note.className = "helper";
      note.textContent = payload.preview_note || "Preview shows indexed chunks.";
      docPreviewEl.append(note);
      (payload.chunks || []).forEach((chunk) => {
        const item = document.createElement("div");
        item.className = "chunk-preview";
        const chunkTitle = document.createElement("div");
        chunkTitle.className = "chunk-preview-title";
        chunkTitle.textContent = "chunk " + chunk.chunk_index + " | " + chunk.chunk_id;
        const text = document.createElement("pre");
        text.className = "chunk-text";
        text.textContent = chunk.text || "";
        item.append(chunkTitle, text);
        docPreviewEl.append(item);
      });
      if (payload.truncated) {
        const truncated = document.createElement("div");
        truncated.className = "pill warn";
        truncated.textContent = "Preview truncated";
        docPreviewEl.append(truncated);
      }
    }

    async function loadDocumentPreview(docId) {
      selectedDocId = docId;
      docPreviewEl.replaceChildren();
      const loading = document.createElement("div");
      loading.className = "empty";
      loading.textContent = "Loading preview...";
      docPreviewEl.append(loading);
      try {
        const response = await fetch("/dashboard/documents/" + encodeURIComponent(docId) + "/preview");
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.detail || "Preview failed");
        renderDocumentPreview(payload);
        document.querySelectorAll(".doc-card").forEach((card) => card.classList.remove("active"));
        const matching = Array.from(document.querySelectorAll(".doc-card")).find((card) => card.textContent.includes(docId));
        if (matching) matching.classList.add("active");
      } catch (error) {
        docPreviewEl.replaceChildren();
        const empty = document.createElement("div");
        empty.className = "empty";
        empty.textContent = error.message;
        docPreviewEl.append(empty);
      }
    }

    async function loadKnowledgeState() {
      try {
        const [readyResponse, docsResponse] = await Promise.all([
          fetch("/ready"),
          fetch("/dashboard/documents"),
        ]);
        const ready = await readyResponse.json();
        const docs = await docsResponse.json();
        if (!readyResponse.ok) throw new Error(ready.detail || "Knowledge index not ready");
        setPill("kb-status", "Ready: " + ready.documents + " docs / " + ready.chunks + " chunks", "ok");
        renderDocuments(docs);
        if (!selectedDocId && docs.documents && docs.documents.length > 0) {
          loadDocumentPreview(docs.documents[0].doc_id);
        }
      } catch (error) {
        setPill("kb-status", "KB not ready", "bad");
        const docsEl = document.getElementById("kb-docs");
        docsEl.replaceChildren();
        const empty = document.createElement("div");
        empty.className = "empty";
        empty.textContent = error.message;
        docsEl.append(empty);
      }
    }

    function buildRequest() {
      const filters = {};
      if (value("region")) filters.region = value("region");
      if (value("product")) filters.product = value("product");
      return {
        question: value("question"),
        top_k: Number(value("top-k") || 6),
        answer_style: value("answer-style") || "standard",
        filters,
      };
    }

    function buildHeaders() {
      const headers = { "Content-Type": "application/json" };
      const provider = value("llm-provider");
      const modelKey = value("llm-api-key");
      if (value("api-key")) headers["X-API-Key"] = value("api-key");
      if (modelKey && provider === "gemini") headers["X-Gemini-API-Key"] = modelKey;
      if (modelKey && provider === "openai") headers["X-OpenAI-API-Key"] = modelKey;
      if (value("tenant-id")) headers["X-Tenant-ID"] = value("tenant-id");
      if (value("user-id")) headers["X-User-ID"] = value("user-id");
      if (value("roles")) headers["X-User-Roles"] = value("roles");
      return headers;
    }

    async function submitFeedback(rating, reason) {
      if (!lastPayload) return;
      feedbackStatusEl.textContent = "Saving feedback...";
      const response = await fetch("/feedback", {
        method: "POST",
        headers: buildHeaders(),
        body: JSON.stringify({
          question: lastQuestion,
          answer: lastPayload.answer || "",
          sources: lastPayload.sources || [],
          rating,
          reason,
          comment: "Submitted from query UI",
        }),
      });
      if (!response.ok) {
        const payload = await response.json();
        throw new Error(typeof payload.detail === "string" ? payload.detail : "Feedback failed");
      }
      feedbackStatusEl.textContent = rating === "up" ? "Marked correct." : "Feedback saved for review.";
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      askButton.disabled = true;
      setStatus("Running");
      renderAnswer("Working...");
      answerMetaEl.replaceChildren();
      qualityPanelEl.replaceChildren();
      feedbackEl.hidden = true;
      feedbackStatusEl.textContent = "";

      try {
        const requestBody = buildRequest();
        lastQuestion = requestBody.question;
        const response = await fetch("/ask", {
          method: "POST",
          headers: buildHeaders(),
          body: JSON.stringify(requestBody),
        });
        const payload = await response.json();
        if (!response.ok) {
          const detail = typeof payload.detail === "string"
            ? payload.detail
            : JSON.stringify(payload.detail, null, 2);
          throw new Error(detail || "Request failed");
        }
        lastPayload = payload;
        renderAnswer(payload.answer || "");
        renderMeta(payload);
        renderCitations(payload.sources);
        feedbackEl.hidden = false;
        setStatus("Complete");
      } catch (error) {
        renderAnswer(error.message);
        citationsEl.replaceChildren();
        answerMetaEl.replaceChildren();
        qualityPanelEl.replaceChildren();
        setStatus("Failed", true);
      } finally {
        askButton.disabled = false;
      }
    });

    exampleButtons.forEach((button) => {
      button.addEventListener("click", () => loadExample(button));
    });

    document.getElementById("clear").addEventListener("click", () => {
      document.getElementById("question").value = "";
      exampleButtons.forEach((item) => item.classList.remove("active"));
      resetResults("Ready");
    });

    document.getElementById("clear-filters").addEventListener("click", () => {
      document.getElementById("region").value = "";
      document.getElementById("product").value = "";
      resetResults("Filters cleared");
    });

    document.querySelectorAll("[data-rating]").forEach((button) => {
      button.addEventListener("click", async () => {
        try {
          await submitFeedback(button.dataset.rating, button.dataset.reason);
        } catch (error) {
          feedbackStatusEl.textContent = error.message;
        }
      });
    });

    providerSelect.addEventListener("change", () => {
      persistCurrentModelKey(activeProvider);
      activeProvider = providerSelect.value;
      storageSet("llm-provider", activeProvider);
      loadModelKeyForProvider();
      updateProviderStatus();
    });
    providerKeyInput.addEventListener("input", () => {
      persistCurrentModelKey();
      updateProviderStatus();
    });
    rememberProviderKeyInput.addEventListener("change", () => {
      persistCurrentModelKey();
      updateProviderStatus();
    });
    document.getElementById("clear-llm-api-key").addEventListener("click", () => {
      const provider = providerSelect.value;
      if (provider !== "local") {
        storageRemove(modelKeyStorageKey(provider));
        storageRemove(rememberModelKeyStorageKey(provider));
      }
      providerKeyInput.value = "";
      rememberProviderKeyInput.checked = false;
      updateProviderStatus();
    });
    answerStyleSelect.addEventListener("change", () => storageSet("answer-style", answerStyleSelect.value));
    document.getElementById("top-k").addEventListener("input", () => storageSet("top-k", value("top-k") || "6"));
    appKeyInput.addEventListener("input", persistAppKey);
    rememberAppKeyInput.addEventListener("change", persistAppKey);
    document.getElementById("clear-app-api-key").addEventListener("click", () => {
      storageRemove("app-api-key");
      storageRemove("remember-app-api-key");
      appKeyInput.value = "";
      rememberAppKeyInput.checked = false;
    });
    restoreSavedFormState();
    loadKnowledgeState();
    updateProviderStatus();
  </script>
</body>
</html>"""
