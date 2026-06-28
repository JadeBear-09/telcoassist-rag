# ruff: noqa: E501

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.config import get_settings

router = APIRouter(tags=["upload"])


@router.get("/upload", response_class=HTMLResponse)
def upload_page() -> str:
    if not get_settings().ingest_api_enabled:
        return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TelcoAssist Upload Disabled</title>
  <style>
    body { margin: 0; min-height: 100vh; display: grid; place-items: center; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f4f6f8; color: #172033; }
    main { width: min(560px, calc(100% - 32px)); background: #ffffff; border: 1px solid #d7dee8; border-radius: 8px; padding: 22px; }
    h1 { margin: 0 0 10px; font-size: 22px; letter-spacing: 0; }
    p { margin: 0 0 16px; color: #5d697a; line-height: 1.5; }
    a { color: #05616a; font-weight: 800; text-decoration: none; }
    a:hover { text-decoration: underline; }
  </style>
</head>
<body>
  <main>
    <h1>Upload disabled</h1>
    <p>Document upload is disabled for this public demo. The deployed knowledge base is fixed to the bundled telecom sample docs.</p>
    <a href="/query">Back to query</a>
  </main>
</body>
</html>"""
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TelcoAssist Upload</title>
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
    }
    h1 {
      margin: 0;
      font-size: 22px;
      line-height: 1.2;
      letter-spacing: 0;
    }
    main {
      width: min(940px, 100%);
      margin: 0 auto;
      padding: 20px 22px 28px;
      display: grid;
      gap: 16px;
    }
    a {
      color: var(--accent-dark);
      font-weight: 800;
      text-decoration: none;
    }
    a:hover { text-decoration: underline; }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
    }
    .panel-head {
      padding: 15px 18px;
      border-bottom: 1px solid var(--line);
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      flex-wrap: wrap;
    }
    .panel-body {
      padding: 16px 18px 18px;
      display: grid;
      gap: 14px;
    }
    .status-row {
      display: flex;
      gap: 8px;
      align-items: center;
      flex-wrap: wrap;
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
    }
    .pill.ok { color: var(--ok); }
    .pill.warn { color: var(--warn); }
    .pill.bad { color: var(--danger); }
    form {
      display: grid;
      gap: 14px;
    }
    label {
      display: grid;
      gap: 6px;
      color: var(--muted);
      font-size: 13px;
      font-weight: 800;
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
    input, button {
      font: inherit;
      letter-spacing: 0;
    }
    input[type="password"], input[type="file"] {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #ffffff;
      color: var(--text);
      padding: 10px 11px;
      outline: none;
    }
    input:focus {
      border-color: var(--accent);
      box-shadow: 0 0 0 3px rgba(8, 127, 140, 0.14);
    }
    button {
      border: 1px solid transparent;
      border-radius: 6px;
      padding: 11px 14px;
      min-height: 44px;
      cursor: pointer;
      font-weight: 900;
      background: var(--accent);
      color: #ffffff;
    }
    button:hover { background: var(--accent-dark); }
    .helper {
      margin: 0;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
    }
    .warn-box {
      border: 1px solid rgba(147, 99, 0, 0.3);
      border-radius: 8px;
      background: #fff8e5;
      color: #5f4300;
      padding: 12px;
      font-size: 13px;
      line-height: 1.45;
    }
    details {
      border-top: 1px solid var(--line);
      padding-top: 12px;
    }
    summary {
      cursor: pointer;
      color: var(--text);
      font-size: 13px;
      font-weight: 900;
      margin-bottom: 12px;
    }
    .check-row {
      display: flex;
      gap: 8px;
      align-items: center;
      color: var(--text);
      font-size: 13px;
      font-weight: 800;
    }
    .check-row input {
      width: auto;
    }
    pre {
      margin: 0;
      background: #111827;
      color: #e5e7eb;
      border-radius: 8px;
      padding: 14px;
      min-height: 120px;
      overflow: auto;
      white-space: pre-wrap;
    }
  </style>
</head>
<body>
  <header>
    <h1>TelcoAssist Upload</h1>
    <a href="/query">Back to query</a>
  </header>
  <main>
    <section class="panel">
      <div class="panel-head">
        <strong>Knowledge ingest</strong>
        <div class="status-row">
          <span id="kb-status" class="pill">KB loading</span>
          <span id="auth-note" class="pill ok">No key needed in local demo</span>
        </div>
      </div>
      <div class="panel-body">
        <p class="helper">Upload a ZIP containing supported documents. Supported files: <strong>.md</strong>, <strong>.txt</strong>, <strong>.csv</strong>, <strong>.pdf</strong>.</p>
        <div class="warn-box">Demo upload rebuilds the active local index from this ZIP. For a bigger knowledge base in this prototype, include all docs you want indexed in the ZIP. Enterprise ingestion should use source connectors, versioned append/update jobs, ACL sync, review status, and rollback.</div>
        <form id="upload-form">
          <label>
            Document ZIP
            <input id="zip" name="file" type="file" accept=".zip" required>
          </label>
          <details>
            <summary>Access and vector settings</summary>
            <label>
              App Access Key
              <input id="api-key" type="password" autocomplete="off" placeholder="Optional. Leave blank unless backend API auth is enabled.">
            </label>
            <div class="key-actions">
              <label><input id="remember-app-api-key" type="checkbox"> Remember key</label>
              <button class="link-button" type="button" id="clear-app-api-key">Forget</button>
            </div>
            <p class="helper">This is not a Gemini/OpenAI model key. It only unlocks protected app routes like upload when API auth is enabled.</p>
            <label class="check-row"><input id="use-qdrant" type="checkbox"> Index into Qdrant</label>
          </details>
          <button type="submit">Upload and re-index</button>
        </form>
      </div>
    </section>
    <section class="panel">
      <div class="panel-head">
        <strong>Result</strong>
      </div>
      <div class="panel-body">
        <pre id="result">Waiting for upload.</pre>
      </div>
    </section>
  </main>
  <script>
    const form = document.getElementById("upload-form");
    const result = document.getElementById("result");
    const kbStatus = document.getElementById("kb-status");
    const appKeyInput = document.getElementById("api-key");
    const rememberAppKeyInput = document.getElementById("remember-app-api-key");
    const storagePrefix = "telcoassist.query.";

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
        // Browser storage can be blocked; upload still works for current request.
      }
    }

    function storageRemove(key) {
      try {
        window.localStorage.removeItem(storagePrefix + key);
      } catch (error) {
        // Browser storage can be blocked; upload still works for current request.
      }
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

    async function loadReady() {
      try {
        const response = await fetch("/ready");
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.detail || "Knowledge index not ready");
        kbStatus.textContent = "Ready: " + payload.documents + " docs / " + payload.chunks + " chunks";
        kbStatus.className = "pill ok";
      } catch (error) {
        kbStatus.textContent = "KB not ready";
        kbStatus.className = "pill bad";
      }
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      result.textContent = "Uploading...";
      const body = new FormData();
      body.append("file", document.getElementById("zip").files[0]);
      body.append("use_qdrant", document.getElementById("use-qdrant").checked ? "true" : "false");
      const headers = {};
      const apiKey = appKeyInput.value.trim();
      if (apiKey) headers["X-API-Key"] = apiKey;
      const response = await fetch("/ingest/upload", { method: "POST", headers, body });
      const payload = await response.json();
      if (!response.ok && response.status === 401) {
        result.textContent = "Upload blocked: backend API auth is enabled. Open Access and vector settings, enter App Access Key, then retry.\\n\\n" + JSON.stringify(payload, null, 2);
        return;
      }
      result.textContent = JSON.stringify(payload, null, 2);
      if (response.ok) await loadReady();
    });
    appKeyInput.addEventListener("input", persistAppKey);
    rememberAppKeyInput.addEventListener("change", persistAppKey);
    document.getElementById("clear-app-api-key").addEventListener("click", () => {
      storageRemove("app-api-key");
      storageRemove("remember-app-api-key");
      appKeyInput.value = "";
      rememberAppKeyInput.checked = false;
    });
    loadAppKey();
    loadReady();
  </script>
</body>
</html>"""
