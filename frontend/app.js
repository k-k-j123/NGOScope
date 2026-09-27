"use strict";

const $ = (sel) => document.querySelector(sel);

/* The form no longer exposes a results-count field, so the lookup uses the
   tool's own default. Keep this as a named constant so it stays discoverable. */
const MAX_RESULTS = 5;

const VERDICT_CLASS = {
  trustworthy: "trust",
  caution: "caution",
  investigate: "investigate",
};

const els = {
  form: $("#lookup-form"),
  name: $("#ngo-name"),
  state: $("#ngo-state"),
  analyzeBtn: $("#analyze-btn"),
  health: $("#health-badge"),
  status: $("#status"),
  results: $("#results"),
  grid: $("#result-grid"),
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
  const body = { ngo_name, max_results: MAX_RESULTS };
  const state = els.state.value.trim();
  if (state) body.state = state;
  return body;
}

/* ---------------- Status ---------------- */

function showStatus(msg, kind) {
  if (!els.status) return;
  els.status.textContent = msg;
  els.status.className = "status status--" + (kind || "info");
  els.status.hidden = false;
}

function clearStatus() {
  if (els.status) els.status.hidden = true;
}

/* ---------------- DOM helpers ----------------
   Search results are untrusted web data, so every snippet, title and URL is
   set with textContent / setAttribute. innerHTML is only ever used on a fresh
   element we just created, never on one holding search output. */

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
}

function bentoCard(label, className) {
  const card = el("div", "cell " + (className || ""));
  card.append(el("div", "cell__label", label));
  return card;
}

/* ---------------- Renderers ---------------- */

function renderReport(report) {
  els.grid.textContent = "";

  const errored = Boolean(report.error);
  const score = !errored && Number.isFinite(report.score) ? report.score : 0;
  const verdict = report.verdict || "unknown";
  const cls = VERDICT_CLASS[verdict] || "";

  /* cell 1 — the score */
  const scoreCard = bentoCard("Credibility score", "cell--score");
  if (errored) {
    scoreCard.append(el("div", "score score--none", "\u2014"));
    scoreCard.append(el("div", "cell__note", "unavailable"));
  } else {
    const figure = el("div", "score");
    figure.append(el("span", "score__num", String(score)));
    figure.append(el("span", "score__den", "/100"));
    scoreCard.append(figure);
  }
  const badge = el(
    "span",
    "verdict" + (cls ? " verdict--" + cls : ""),
    errored ? "Unavailable" : verdict.toUpperCase()
  );
  scoreCard.append(badge);
  els.grid.append(scoreCard);

  /* cell 2 — the verdict and the plain-language read */
  const verdictCard = bentoCard("Verdict", "cell--verdict");
  if (errored) {
    verdictCard.append(el("p", "cell__error", report.error));
  } else {
    verdictCard.append(el("p", "verdict-word", verdict));
    verdictCard.append(
      el(
        "p",
        "cell__note",
        report.sentiment
          ? "Media sentiment: " + report.sentiment.replace(/_/g, " ")
          : "No media sentiment"
      )
    );
    if (report.explanation) {
      verdictCard.append(el("p", "cell__body", report.explanation));
    }
  }
  els.grid.append(verdictCard);

  /* cell 3 — the signals the score was built from */
  const signalCard = bentoCard("Signals", "cell--signals");
  const signals = errored ? [] : report.signals || [];
  if (signals.length) {
    const ul = el("ul", "signals");
    signals.forEach((s) => ul.append(el("li", null, s)));
    signalCard.append(ul);
  } else {
    signalCard.append(
      el("p", "cell__note", errored ? "No signals recorded." : "No signals recorded.")
    );
  }
  els.grid.append(signalCard);

  /* cell 4 — the organic results that were actually read */
  const webCard = bentoCard("Web results", "cell--wide");
  const webResults = report.web_results || [];
  if (webResults.length) {    const ol = el("ol", "sources");
    webResults.forEach((r) => {
      const li = el("li", "source");
      const rank = el("span", "source__rank", r.position != null ? String(r.position) : "#");
      const body = el("div", "source__body");
      const title = el("a", "source__title", r.title || r.link || "(untitled)");
      if (r.link) {
        title.href = r.link;
        title.target = "_blank";
        title.rel = "noopener noreferrer";
      }
      body.append(title);
      if (r.snippet) body.append(el("p", "source__snippet", r.snippet));
      if (r.link) body.append(el("div", "source__url", r.link));
      li.append(rank, body);
      ol.append(li);
    });
    webCard.append(ol);
  } else {
    webCard.append(el("p", "cell__note", errored ? "Not gathered — the lookup did not complete." : "No web results returned."));
  }
  els.grid.append(webCard);

  /* cell 5 — the news coverage, and the sentiment it produced */
  const newsCard = bentoCard("News coverage", "cell--wide");
  const newsResults = report.news_results || [];
  if (newsResults.length) {
    const ul = el("ul", "sources");
    newsResults.forEach((n) => {
      const li = el("li", "source");
      const body = el("div", "source__body");
      const href = n.url || n.link || "";
      const title = el("a", "source__title", n.title || "(untitled)");
      if (href) {
        title.href = href;
        title.target = "_blank";
        title.rel = "noopener noreferrer";
      }
      body.append(title);
      const meta = [n.source, n.date].filter(Boolean).join(" \u00b7 ");
      if (meta) body.append(el("div", "source__meta", meta));
      if (n.snippet) body.append(el("p", "source__snippet", n.snippet));
      li.append(body);
      ul.append(li);
    });
    newsCard.append(ul);
  } else {
    newsCard.append(el("p", "cell__note", errored ? "Not gathered — the lookup did not complete." : "No news coverage found."));
  }
  els.grid.append(newsCard);
}

/* ---------------- Actions ---------------- */

async function runAnalyze() {
  const body = collectForm();
  if (!body) return;

  clearStatus();
  els.analyzeBtn.disabled = true;
  els.analyzeBtn.textContent = "Searching\u2026";
  els.results.hidden = true;
  showStatus(`Searching live web + news for "${body.ngo_name}" (\u22482 SerpAPI searches)\u2026`);

  try {
    const report = await api("analyze_ngo_credibility", body);
    renderReport(report);
    els.results.hidden = false;
    clearStatus();
  } catch (err) {
    clearStatus();
    showStatus(err.message, "error");
  } finally {
    els.analyzeBtn.disabled = false;
    els.analyzeBtn.textContent = "Analyze NGO";
  }
}

async function checkHealth() {
  try {
    const res = await fetch("/health", { cache: "no-store" });
    const ok = res.ok && (await res.json()).status === "ok";
    els.health.textContent = ok ? "System: Online" : "System: Error";
    els.health.classList.toggle("is-off", !ok);
  } catch (_) {
    els.health.textContent = "System: Offline";
    els.health.classList.add("is-off");
  }
}

/* ---------------- Wire up ---------------- */

els.form.addEventListener("submit", (e) => {
  e.preventDefault();
  runAnalyze();
});

document.addEventListener("DOMContentLoaded", () => {
  if (!els.name.value) els.name.focus();
  checkHealth();
});
