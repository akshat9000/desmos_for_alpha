async function api(path, opts={}) {
    const r = await fetch(path, { headers: { "Content-Type":"application/json" }, ...opts });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  }
  
  const els = {
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

  const els2 = {
    topQ: document.getElementById("topQ"),
    botQ: document.getElementById("botQ"),
    costBps: document.getElementById("costBps"),
    equityChart: document.getElementById("equityChart"),
    heatmap: document.getElementById("heatmap"),
  };

  async function runBacktest() {
    const alpha = els.alpha.value.trim();
    const payload = {
      alpha,
      top_q: parseFloat(els2.topQ.value || "0.2"),
      bot_q: parseFloat(els2.botQ.value || "0.2"),
      cost_bps: parseFloat(els2.costBps.value || "0"),
      neutralize: true
    };
    const res = await api("/backtest", { method:"POST", body: JSON.stringify(payload) });
  
    // Equity curve
    Plotly.newPlot(els2.equityChart, [{
      x: res.dates, y: res.equity, mode: "lines", name: "Equity"
    }], { margin:{t:20,r:10,b:40,l:45}, xaxis:{type:"date"}, yaxis:{zeroline:false} });
  
    // Heatmap (signals)
    Plotly.newPlot(els2.heatmap, [{
      z: res.signals,
      x: res.columns,
      y: res.dates,
      type: "heatmap",
      colorscale: "RdBu",
      reversescale: true,
      showscale: true
    }], { margin:{t:20,r:10,b:40,l:60}, yaxis:{autorange:"reversed"} });
  }
  
  document.getElementById("btnBacktest").addEventListener("click", runBacktest);

  
  async function showAST() {
    const alpha = els.alpha.value.trim();
    const res = await api("/ast", { method:"POST", body: JSON.stringify({ alpha }) });
    els.astPretty.textContent = res.pretty || "";
    els.astJson.textContent = JSON.stringify(res.tree || {}, null, 2);
  }
  
  document.getElementById("btnAST").addEventListener("click", showAST);  
  
  async function loadFunctions() {
    const data = await api("/functions");
    const list = (data.functions || [])
      .map(fn => {
        const ar = Array.isArray(fn.arity) ? fn.arity.join(",") : String(fn.arity);
        return `<div class="fn"><b>${fn.name}</b> <span style="color:#9fb2d1">[arity ${ar}]</span><br/><span style="color:#8aa">${fn.doc||""}</span></div>`;
      }).join("");
    els.functions.innerHTML = list || "No functions registered.";
  }
  
  async function parseAlpha() {
    const alpha = els.alpha.value.trim();
    const res = await api("/parse", { method:"POST", body: JSON.stringify({ alpha }) });
    els.meta.textContent = JSON.stringify(res, null, 2);
  }
  
  function renderTable(obj) {
    const syms = Object.keys(obj).sort();
    let html = "<thead><tr><th>Symbol</th><th>Value</th></tr></thead><tbody>";
    for (const s of syms) {
      html += `<tr><td>${s}</td><td>${(+obj[s]).toFixed(6)}</td></tr>`;
    }
    html += "</tbody>";
    els.evalTable.innerHTML = html;
  }
  
  async function evaluateLatest() {
    // quick trick: let the server pick latest date from its dataset (your /evaluate uses explicit date;
    // you can adapt it to read last date from CSVs if date omitted, or keep a small helper endpoint).
    // For now, we’ll fetch series and take the last row (works fine).
    const alpha = els.alpha.value.trim();
    const res = await api("/evaluate_series_fast", { method:"POST", body: JSON.stringify({ alpha, fields: [] }) });
    const { dates, columns, values } = res;
  
    if (!dates || dates.length === 0) return;
    const lastIdx = dates.length - 1;
    const lastRow = values[lastIdx];
    const latest = {};
    columns.forEach((c, i) => latest[c] = lastRow[i]);
    els.evalDate.textContent = `Latest date: ${dates[lastIdx]}`;
    renderTable(latest);
  
    // populate symbol selector
    els.symbolSelect.innerHTML = columns.map(c => `<option value="${c}">${c}</option>`).join("");
  }
  
  async function evaluateSeries() {
    const alpha = els.alpha.value.trim();
    const res = await api("/evaluate_series_fast", { method:"POST", body: JSON.stringify({ alpha, fields: [] }) });
    const { dates, columns, values } = res;
    if (!dates || !columns) return;
  
    // plot the first symbol by default or selected one
    const selected = els.symbolSelect.value || columns[0];
    const si = columns.indexOf(selected);
  
    const y = values.map(row => row[si]);
    const trace = { x: dates, y, mode: "lines", name: selected };
    Plotly.newPlot(els.chart, [trace], {
      margin: { t: 20, r: 10, b: 40, l: 45 },
      xaxis: { type: "date" },
      yaxis: { zeroline: false }
    });
  }
  
  document.getElementById("btnFunctions").addEventListener("click", loadFunctions);
  document.getElementById("btnParse").addEventListener("click", parseAlpha);
  document.getElementById("btnEvaluate").addEventListener("click", async () => {
    await evaluateLatest();
  });
  document.getElementById("btnSeries").addEventListener("click", async () => {
    await evaluateSeries();
  });
  
  els.symbolSelect.addEventListener("change", evaluateSeries);
  
  // initial
  loadFunctions();
  parseAlpha();
  evaluateLatest();
  