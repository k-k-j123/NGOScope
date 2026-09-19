"use strict";

const $ = (sel) => document.querySelector(sel);

const VERDICT_CLASS = {
  trustworthy: "trust",
  caution: "caution",
  investigate: "investigate",
};

const els = {
  form: $("#lookup-form"),
  name: $("#ngo-name"),
  state: $("#ngo-state"),
  maxResults: $("#max-results"),
  analyzeBtn: $("#analyze-btn"),
  health: $("#health-badge"),
  status: $("#status"),
  results: $("#results"),
  tabs: document.querySelectorAll(".tab"),
  panes: document.querySelectorAll(".tab-pane"),
  // report pane
  scoreValue: $("#score-value"),
  scoreVerdict: $("#score-verdict"),
  scoreBarFill: $("#score-bar-fill"),
  sentiment: $("#sentiment"),
  reportTitle: $("#report-title"),
  reportError: $("#report-error"),
  explanation: $("#explanation"),
  signals: $("#signals"),
  // web pane
  webResults: $("#web-results"),
  webEmpty: $("#web-empty"),
  // news pane
  newsResults: $("#news-results"),
  newsEmpty: $("#news-empty"),
};

/* ---------------- API ---------------- */

async function api(tool, body) {
  const res = await fetch(`/tools/${tool}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  let data = null;
  try {
    data = await res.json();
  } catch (_) {
    /* non-JSON body */
  }
  if (!res.ok) {
    const msg = data && data.error ? data.error : `Server error (HTTP ${res.status})`;
    throw new Error(msg);
  }
  return data.result;
}

/* ---------------- Form ---------------- */

function collectForm() {
  const ngo_name = els.name.value.trim();
  if (!ngo_name) {
    els.name.focus();
    return null;
  }
  const body = { ngo_name, max_results: parseInt(els.maxResults.value, 10) || 5 };
  const state = els.state.value.trim();
  if (state) body.state = state;
  return body;
}

/* ---------------- Status ---------------- */

function showStatus(msg, kind) {
  els.status.textContent = msg;
  els.status.className = `status status--${kind || "info"}`;
  els.status.hidden = false;
}

function clearStatus() {
  els.status.hidden = true;
}

/* ---------------- Renderers ---------------- */

function renderReport(report) {
  els.reportTitle.textContent = report.ngo_name
    ? `${report.ngo_name}${report.state ? " — " + report.state : ""}`
    : "Report";

  if (report.error) {
    els.reportError.textContent = report.error;
    els.reportError.hidden = false;
    els.scoreValue.textContent = "—";
    els.scoreVerdict.textContent = "Unavailable";
    els.scoreVerdict.className = "verdict-badge";
    els.scoreBarFill.style.width = "0%";
    els.scoreBarFill.className = "score-bar__fill";
    els.sentiment.textContent = "";
    els.explanation.textContent = "";
    els.signals.innerHTML = "";
    return;
  }

  els.reportError.hidden = true;
  const score = Number.isFinite(report.score) ? report.score : 0;
  const verdict = report.verdict || "unknown";
  const className = VERDICT_CLASS[verdict] || "";

  els.scoreValue.textContent = `${score}/100`;
  els.scoreVerdict.textContent = verdict.toUpperCase();
  els.scoreVerdict.className = `verdict-badge${className ? " verdict-badge--" + className : ""}`;
  els.scoreBarFill.style.width = `${score}%`;
  els.scoreBarFill.className = `score-bar__fill${className ? " score-bar__fill--" + className : ""}`;
  els.sentiment.textContent = report.sentiment
    ? `Media sentiment: ${report.sentiment.replace(/_/g, " ")}`
    : "";
  els.explanation.textContent = report.explanation || "";

  els.signals.innerHTML = "";
  const signals = report.signals || [];
  if (signals.length) {
    signals.forEach((s) => {
      const li = document.createElement("li");
      li.textContent = s;
      els.signals.appendChild(li);
    });
  } else {
    const li = document.createElement("li");
    li.className = "muted";
    li.textContent = "No signals recorded.";
    els.signals.appendChild(li);
  }
}

function renderWeb(results) {
  els.webResults.innerHTML = "";
  els.webEmpty.hidden = results.length > 0;
  if (!results.length) {
    els.webEmpty.textContent = "No web results returned.";
    return;
  }
  const frag = document.createDocumentFragment();
  results.forEach((r) => {
    const li = document.createElement("li");
    li.className = "result-item";

    const rank = document.createElement("span");
    rank.className = "result-item__rank";
    rank.textContent = r.position != null ? r.position : "#";

    const body = document.createElement("div");
    body.className = "result-item__body";

    const a = document.createElement("a");
    if (r.link) {
      a.href = r.link;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
    }
    a.textContent = r.title || r.link || "(untitled)";

    const p = document.createElement("p");
    p.textContent = r.snippet || "";

    const url = document.createElement("div");
    url.className = "result-item__url";
    url.textContent = r.link || "";

    body.append(a, p, url);
    li.append(rank, body);
    frag.appendChild(li);
  });
  els.webResults.appendChild(frag);
}

function renderNews(results) {
  els.newsResults.innerHTML = "";
  els.newsEmpty.hidden = results.length > 0;
  if (!results.length) {
    els.newsEmpty.textContent = "No news coverage found.";
    return;
  }
  const frag = document.createDocumentFragment();
  results.forEach((r) => {
    const li = document.createElement("li");
    li.className = "result-item";

    const body = document.createElement("div");
    body.className = "result-item__body";

    const a = document.createElement("a");
    const href = r.url || r.link || "";
    if (href) {
      a.href = href;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
    }
    a.textContent = r.title || "(untitled)";

    const meta = document.createElement("div");
    meta.className = "news-meta";
    meta.textContent = [r.source, r.date].filter(Boolean).join(" · ");

    const p = document.createElement("p");
    p.textContent = r.snippet || "";

    body.append(a, meta, p);
    li.appendChild(body);
    frag.appendChild(li);
  });
  els.newsResults.appendChild(frag);
}

/* ---------------- Actions ---------------- */

async function runAnalyze() {
  const body = collectForm();
  if (!body) return;

  clearStatus();
  els.analyzeBtn.disabled = true;
  els.analyzeBtn.textContent = "Searching…";
  els.results.hidden = true;
  showStatus(`Searching live web + news for "${body.ngo_name}" (≈2 SerpAPI searches)…`);

  try {
    const report = await api("analyze_ngo_credibility", body);
    renderReport(report);
    renderWeb(report.web_results || []);
    renderNews(report.news_results || []);
    els.results.hidden = false;
    switchTab("report");
    clearStatus();
  } catch (err) {
    clearStatus();
    showStatus(err.message, "error");
  } finally {
    els.analyzeBtn.disabled = false;
    els.analyzeBtn.textContent = "Analyze";
  }
}

function switchTab(name) {
  els.tabs.forEach((t) => {
    const active = t.dataset.tab === name;
    t.classList.toggle("is-active", active);
    t.setAttribute("aria-selected", String(active));
  });
  els.panes.forEach((p) => p.classList.toggle("is-active", p.id === `tab-${name}`));
}

async function checkHealth() {
  try {
    const res = await fetch("/health", { cache: "no-store" });
    const ok = res.ok && (await res.json()).status === "ok";
    els.health.textContent = ok ? "server online" : "server error";
    els.health.classList.toggle("is-ok", ok);
  } catch (_) {
    els.health.textContent = "server offline";
    els.health.classList.remove("is-ok");
  }
}

/* ---------------- Wire up ---------------- */

els.form.addEventListener("submit", (e) => {
  e.preventDefault();
  runAnalyze();
});

els.tabs.forEach((t) => t.addEventListener("click", () => switchTab(t.dataset.tab)));

document.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    els.name.value = chip.dataset.example;
    runAnalyze();
  });
});

document.addEventListener("DOMContentLoaded", () => {
  if (!els.name.value) els.name.focus();
  checkHealth();
});