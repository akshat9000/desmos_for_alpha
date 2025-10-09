"use strict";

// === Global loading overlay (ref-counted, no flicker) ===
const Loading = (() => {
  let el, styleEl, counter = 0, showTimer = null;

  function ensureDom() {
    if (!styleEl) {
      styleEl = document.createElement("style");
      styleEl.textContent = `
        #loading-overlay{position:fixed;inset:0;display:none;align-items:center;justify-content:center;background:rgba(15,23,42,.35);backdrop-filter:saturate(120%) blur(2px);z-index:9999}
        #loading-overlay .spinner{width:56px;height:56px;border-radius:50%;border:6px solid rgba(255,255,255,.35);border-top-color:#fff;animation:spin 0.9s linear infinite}
        @keyframes spin{to{transform:rotate(360deg)}}
        .is-loading{opacity:.6;pointer-events:none}
      `;
      document.head.appendChild(styleEl);
    }
    if (!el) {
      el = document.createElement("div");
      el.id = "loading-overlay";
      el.innerHTML = `<div class="spinner" aria-label="Loading"></div>`;
      document.body.appendChild(el);
    }
  }

  function reallyShow() {
    ensureDom();
    el.style.display = "flex";
  }

  return {
    show() {
      counter++;
      // small delay to avoid flicker on super fast requests
      if (!showTimer && counter === 1) {
        showTimer = setTimeout(() => { showTimer = null; if (counter > 0) reallyShow(); }, 120);
      }
    },
    hide() {
      counter = Math.max(0, counter - 1);
      if (counter === 0) {
        if (showTimer) { clearTimeout(showTimer); showTimer = null; }
        if (el) el.style.display = "none";
      }
    },
    // helper for per-button visual state
    async wrapButton(btn, fn) {
      if (btn) btn.classList.add("is-loading");
      try { return await fn(); }
      finally { if (btn) btn.classList.remove("is-loading"); }
    }
  };
})();


// --- Optional API base (safe default for relative paths) ---
const API_BASE =
  (typeof window !== "undefined" && window.API_BASE) ||
  "";

// Simple fetch helper
async function api(path, opts = {}) {
  const url = path.startsWith("http") ? path : `${(typeof window !== "undefined" && window.API_BASE) || ""}${path}`;
  Loading.show();
  try {
    const r = await fetch(url, { headers: { "Content-Type": "application/json" }, ...opts });
    if (!r.ok) throw new Error(await r.text());
    return await r.json();
  } finally {
    Loading.hide();
  }
}

// ----- App state (filled in init) -----
let els = {};
let els2 = {};

// ----- Core actions -----
async function runBacktest() {
  const alpha = els.alpha?.value?.trim() || "";
  const payload = {
    alpha,
    top_q: parseFloat(els2.topQ?.value || "0.2"),
    bot_q: parseFloat(els2.botQ?.value || "0.2"),
    cost_bps: parseFloat(els2.costBps?.value || "0"),
    neutralize: true
  };
  const res = await api("/backtest", { method: "POST", body: JSON.stringify(payload) });

  // Equity curve
  Plotly.newPlot(els2.equityChart, [{
    x: res.dates, y: res.equity, mode: "lines", name: "Equity"
  }], { margin: { t: 20, r: 10, b: 40, l: 45 }, xaxis: { type: "date" }, yaxis: { zeroline: false } });

  // Heatmap (signals)
  Plotly.newPlot(els2.heatmap, [{
    z: res.signals,
    x: res.columns,
    y: res.dates,
    type: "heatmap",
    colorscale: "RdBu",
    reversescale: true,
    showscale: true
  }], { margin: { t: 20, r: 10, b: 40, l: 60 }, yaxis: { autorange: "reversed" } });
}

async function showAST() {
  const alpha = els.alpha?.value?.trim() || "";
  const res = await api("/ast", { method: "POST", body: JSON.stringify({ alpha }) });
  if (els.astPretty) els.astPretty.textContent = res.pretty || "";
  if (els.astJson)   els.astJson.textContent   = JSON.stringify(res.tree || {}, null, 2);
}

async function loadFunctions() {
  const data = await api("/functions");
  const list = (data.functions || [])
    .map(fn => {
      const ar = Array.isArray(fn.arity) ? fn.arity.join(",") : String(fn.arity);
      return `<div class="fn"><b>${fn.name}</b> <span style="color:#9fb2d1">[arity ${ar}]</span><br/><span style="color:#8aa">${fn.doc || ""}</span></div>`;
    }).join("");
  if (els.functions) els.functions.innerHTML = list || "No functions registered.";
}

async function parseAlpha() {
  const alpha = els.alpha?.value?.trim() || "";
  const res = await api("/parse", { method: "POST", body: JSON.stringify({ alpha }) });
  if (els.meta) els.meta.textContent = JSON.stringify(res, null, 2);
}

function renderTable(obj) {
  const syms = Object.keys(obj).sort();
  let html = "<thead><tr><th>Symbol</th><th>Value</th></tr></thead><tbody>";
  for (const s of syms) html += `<tr><td>${s}</td><td>${(+obj[s]).toFixed(6)}</td></tr>`;
  html += "</tbody>";
  if (els.evalTable) els.evalTable.innerHTML = html;
}

async function evaluateLatest() {
  const alpha = els.alpha?.value?.trim() || "";
  const res = await api("/evaluate_series_fast", { method: "POST", body: JSON.stringify({ alpha, fields: [] }) });
  const { dates, columns, values } = res || {};
  if (!dates || !dates.length) return;

  const lastIdx = dates.length - 1;
  const lastRow = values[lastIdx];
  const latest = {};
  columns.forEach((c, i) => latest[c] = lastRow[i]);
  if (els.evalDate) els.evalDate.textContent = `Latest date: ${dates[lastIdx]}`;
  renderTable(latest);

  if (els.symbolSelect) {
    els.symbolSelect.innerHTML = columns.map(c => `<option value="${c}">${c}</option>`).join("");
  }
}

async function evaluateSeries() {
  const alpha = els.alpha?.value?.trim() || "";
  const res = await api("/evaluate_series_fast", { method: "POST", body: JSON.stringify({ alpha, fields: [] }) });
  const { dates, columns, values } = res || {};
  if (!dates || !columns) return;

  const selected = els.symbolSelect?.value || columns[0];
  const si = columns.indexOf(selected);

  const y = values.map(row => row[si]);
  const trace = { x: dates, y, mode: "lines", name: selected };
  Plotly.newPlot(els.chart, [trace], {
    margin: { t: 20, r: 10, b: 40, l: 45 },
    xaxis: { type: "date" },
    yaxis: { zeroline: false }
  });
}

// ----- Binding utilities -----
function bindClick(id, handler) {
  const el = document.getElementById(id);
  if (!el) return false;
  el.addEventListener("click", (ev) => {
    ev.preventDefault?.();
    handler().catch(console.error);
  }, { passive: false });
  console.log(`[bind] click -> #${id}`);
  return true;
}

// Wait for elements to exist; handles late/dynamic renders
function waitAndBind() {
  const targets = ["btnFunctions", "btnParse", "btnEvaluate", "btnSeries", "btnBacktest", "btnAST"];
  const found = new Set();

  const tryBindAll = () => {
    let progress = false;
    if (bindClick("btnFunctions", loadFunctions)) { found.add("btnFunctions"); progress = true; }
    if (bindClick("btnParse",     parseAlpha))    { found.add("btnParse");     progress = true; }
    if (bindClick("btnEvaluate",  evaluateLatest)){ found.add("btnEvaluate");  progress = true; }
    if (bindClick("btnSeries",    evaluateSeries)){ found.add("btnSeries");    progress = true; }
    // IMPORTANT: actually call the functions
    if (bindClick("btnBacktest",  runBacktest))   { found.add("btnBacktest");  progress = true; }
    if (bindClick("btnAST",       showAST))       { found.add("btnAST");       progress = true; }
    return progress;
  };

  // First attempt (in case DOM is already ready)
  const initial = tryBindAll();
  if (targets.every(t => found.has(t))) return; // all bound

  // Observe future mutations to catch late-mounted buttons
  const obs = new MutationObserver(() => {
    const did = tryBindAll();
    if (targets.every(t => found.has(t))) {
      console.log("[bind] all listeners attached; disconnecting observer");
      obs.disconnect();
    } else if (did) {
      const missing = targets.filter(t => !found.has(t));
      console.log("[bind] progress; still missing:", missing);
    }
  });

  obs.observe(document.documentElement, { childList: true, subtree: true });
  console.log("[bind] using MutationObserver for late-mounted buttons; currently bound:", Array.from(found));
}

// Delegated fallback (won’t show on the button in Elements, but catches clicks regardless)
function delegatedFallback() {
  document.addEventListener("click", (ev) => {
    const t = ev.target.closest?.("#btnAST, #btnBacktest, #btnFunctions, #btnParse, #btnEvaluate, #btnSeries");
    if (!t) return;
    ev.preventDefault?.();
    if (t.id === "btnAST")       return showAST().catch(console.error);
    if (t.id === "btnBacktest")  return runBacktest().catch(console.error);
    if (t.id === "btnFunctions") return loadFunctions().catch(console.error);
    if (t.id === "btnParse")     return parseAlpha().catch(console.error);
    if (t.id === "btnEvaluate")  return evaluateLatest().catch(console.error);
    if (t.id === "btnSeries")    return evaluateSeries().catch(console.error);
  }, { capture: false });
  console.log("[bind] delegated fallback active");
}

// ----- Init -----
function initApp() {
  els = {
    alpha: document.getElementById("alpha"),
    meta: document.getElementById("meta"),
    functions: document.getElementById("functions"),
    evalTable: document.getElementById("evalTable"),
    evalDate: document.getElementById("evalDate"),
    symbolSelect: document.getElementById("symbolSelect"),
    chart: document.getElementById("chart"),
    astPretty: document.getElementById("astPretty"),
    astJson: document.getElementById("astJson"),
  };
  els2 = {
    topQ: document.getElementById("topQ"),
    botQ: document.getElementById("botQ"),
    costBps: document.getElementById("costBps"),
    equityChart: document.getElementById("equityChart"),
    heatmap: document.getElementById("heatmap"),
  };

  console.log("[boot] API_BASE:", API_BASE || "(empty)");
  delegatedFallback();      // safety net
  waitAndBind();            // direct listeners (will show on the buttons)

  // initial loads (don’t block)
  loadFunctions().catch(console.error);
  parseAlpha().catch(console.error);
  evaluateLatest().catch(console.error);
}

// Start after DOM is ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initApp, { once: true });
} else {
  initApp();
}
