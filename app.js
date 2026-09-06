/* Taiwan money-flow viz — loads curated JSON by date (no live TWSE). */
(function () {
  const GREEN = "#22c55e";
  const RED = "#ef4444";
  const TEXT = "#e8eef7";
  const MUTED = "#8b9bb0";
  const GRID = "#243041";

  const fmtSigned = (n, digits = 1) => {
    const v = Number(n);
    if (!isFinite(v)) return "—";
    return (v >= 0 ? "+" : "") + v.toFixed(digits);
  };
  const clsSigned = (n) => (Number(n) >= 0 ? "pos" : "neg");
  const topicLabel = (s) => s.topic || s.topicName || s.topicId || "—";

  let dates = [];
  let dateIdx = 0;
  let slideshowTimer = null;
  let slideshowPlaying = false;
  let D = null;
  let historyKpi = [];
  let regimesDays = [];
  let screensDoc = null;
  let etf981Doc = null;
  let regimeBriefCache = {};
  let digestDoc = null;
  let digestMarkdown = "";
  let regimeByDate = {};
  let regimeViewDate = null;
  const charts = [];
  const layerState = { flow: true, heat: true, short: true, leverage: true };
  const filterState = {
    search: "",
    noEtf: true,
    mappedOnly: false,
    topicId: "",
    topN: 12,
    market: "all",
    rulesOnly: false,
    dispRiskOnly: false,
    daytradePauseOnly: false
  };

  function instNet(s) {
    if (s.inst_net != null) return Number(s.inst_net);
    return Number(s.foreign_net || 0) + Number(s.trust_net || 0) + Number(s.dealer_net || 0);
  }

  function isEtfLike(s) {
    if (s.is_etf != null || s.is_leverage != null) return !!(s.is_etf || s.is_leverage);
    const c = String(s.code || "");
    const n = String(s.name || "");
    return /^00/.test(c) || /[LR]$/.test(c) || n.indexOf("正2") >= 0 || n.indexOf("反1") >= 0 || n.indexOf("ETF") >= 0;
  }

  function isMapped(s) {
    if (s.mapped != null) return !!s.mapped;
    return s.topicId && s.topicId !== "unmapped";
  }

  function filteredStocks() {
    let rows = (D && D.stocks) || [];
    if (filterState.noEtf) rows = rows.filter(function (s) { return !isEtfLike(s); });
    if (filterState.mappedOnly) rows = rows.filter(isMapped);
    if (filterState.market && filterState.market !== "all") {
      rows = rows.filter(function (s) { return (s.market || "twse") === filterState.market; });
    }
    if (filterState.rulesOnly) {
      rows = rows.filter(function (s) {
        return s.notice || s.disposition || s.stop_sbl ||
          s.disp_risk === "med" || s.disp_risk === "high" ||
          s.daytrade_pause || s.daytrade_suspended;
      });
    }
    if (filterState.dispRiskOnly) {
      rows = rows.filter(function (s) { return s.disp_risk === "med" || s.disp_risk === "high"; });
    }
    if (filterState.daytradePauseOnly) {
      rows = rows.filter(function (s) { return s.daytrade_pause || s.daytrade_suspended; });
    }
    if (filterState.topicId) {
      rows = rows.filter(function (s) { return s.topicId === filterState.topicId; });
    }
    const q = (filterState.search || "").trim().toLowerCase();
    if (q) {
      rows = rows.filter(function (s) {
        return String(s.code).toLowerCase().indexOf(q) >= 0 ||
          String(s.name).toLowerCase().indexOf(q) >= 0 ||
          String(topicLabel(s)).toLowerCase().indexOf(q) >= 0;
      });
    }
    return rows;
  }

  function chartStocks() {
    const n = Math.max(5, Math.min(80, Number(filterState.topN) || 12));
    return filteredStocks()
      .slice()
      .sort(function (a, b) { return Math.abs(instNet(b)) - Math.abs(instNet(a)); })
      .slice(0, n);
  }

  function updateFilterStat() {
    const el = document.getElementById("fltStat");
    if (!el || !D) return;
    const all = (D.stocks || []).length;
    const f = filteredStocks().length;
    const n = chartStocks().length;
    el.textContent = "全市場 " + all + " → 篩選 " + f + " → 圖 " + n + " 檔";
  }

  function populateTopicSelect() {
    const sel = document.getElementById("fltTopic");
    if (!sel || !D) return;
    const cur = filterState.topicId;
    const topics = (D.topics || []).slice().sort(function (a, b) {
      return Math.abs(b.inst_net || 0) - Math.abs(a.inst_net || 0);
    });
    sel.innerHTML = "<option value=\"\">全部題材</option>" + topics.map(function (t) {
      return "<option value=\"" + t.id + "\">" + (t.shortname || t.name) + "</option>";
    }).join("");
    sel.value = cur;
  }

  function buildReadingPack() {
    const stocks = filteredStocks().slice().sort(function (a, b) {
      return Math.abs(instNet(b)) - Math.abs(instNet(a));
    });
    const top = stocks.slice(0, 30).map(function (s) {
      return {
        code: s.code, name: s.name, topicId: s.topicId, topic: topicLabel(s),
        change: s.change, inst_net: instNet(s),
        foreign_net: s.foreign_net, trust_net: s.trust_net, dealer_net: s.dealer_net,
        amount: s.amount, margin_util: s.margin_util, market: s.market || "twse", foreign_hold_pct: s.foreign_hold_pct, sbl_avail: s.sbl_avail, notice: !!s.notice, disposition: !!s.disposition, daytrade_pause: !!s.daytrade_pause, disp_risk: s.disp_risk || "none", notice_streak: s.notice_streak || 0, is_etf: isEtfLike(s)
      };
    });
    const topics = (D.topics || []).slice().sort(function (a, b) {
      return Math.abs(b.inst_net || 0) - Math.abs(a.inst_net || 0);
    }).slice(0, 15);
    return {
      meta: D.meta,
      market_kpi: D.market_kpi,
      filters: Object.assign({}, filterState),
      stocks_top: top,
      topics_top: topics,
      groups: (D.groups || []).slice(0, 15),
      alerts: D.alerts || [],
      foreign_cat: D.foreign_cat || [],
      history_kpi_tail: (historyKpi || []).slice(-20),
      regime: getRegimeFor((D.meta && D.meta.date) || null),
      regimes_tail: (regimesDays || []).slice(-20),
      digest: digestDoc ? {
        date: digestDoc.date,
        headline: digestDoc.headline,
        one_liner: digestDoc.one_liner,
        engine: digestDoc.engine,
        llm: digestDoc.llm,
        markdown: digestMarkdown
      } : null
    };
  }


  function disposeCharts() {
    while (charts.length) {
      const c = charts.pop();
      try { c.dispose(); } catch (e) {}
    }
  }

  function applyLayers() {
    document.querySelectorAll("[data-layer-section]").forEach(function (el) {
      const key = el.getAttribute("data-layer-section");
      el.classList.toggle("hidden", !layerState[key]);
    });
  }

  function resizeAll() {
    charts.forEach(function (c) { c.resize(); });
  }

  function themeBase() {
    return {
      backgroundColor: "transparent",
      textStyle: { color: TEXT, fontFamily: "Noto Sans TC, PingFang TC, Microsoft JhengHei, sans-serif" }
    };
  }

  function setError(msg) {
    const el = document.getElementById("errorBanner");
    if (!el) return;
    if (!msg) {
      el.classList.add("hidden");
      el.textContent = "";
    } else {
      el.classList.remove("hidden");
      el.textContent = msg;
    }
  }

  function updateDateControls() {
    const label = document.getElementById("dateLabel");
    const sel = document.getElementById("dateSelect");
    const prev = document.getElementById("btnPrev");
    const next = document.getElementById("btnNext");
    const date = dates[dateIdx] || "—";
    if (label) label.textContent = date;
    if (sel) {
      sel.value = date;
    }
    if (prev) prev.disabled = dateIdx <= 0;
    if (next) next.disabled = dateIdx >= dates.length - 1;
  }

  function renderKpi() {
    const kpi = D.market_kpi || {};
    const kpiItems = [
      { label: "上市外資（億）", value: fmtSigned(kpi.foreign_net), cls: clsSigned(kpi.foreign_net) },
      { label: "上市投信（億）", value: fmtSigned(kpi.trust_net), cls: clsSigned(kpi.trust_net) },
      { label: "上市自營（億）", value: fmtSigned(kpi.dealer_net), cls: clsSigned(kpi.dealer_net) },
      { label: "櫃買外資（億）", value: fmtSigned(kpi.tpex_foreign_net || 0), cls: clsSigned(kpi.tpex_foreign_net || 0) },
      { label: "櫃買投信（億）", value: fmtSigned(kpi.tpex_trust_net || 0), cls: clsSigned(kpi.tpex_trust_net || 0) },
      { label: "全市場外資（億）", value: fmtSigned(kpi.all_foreign_net != null ? kpi.all_foreign_net : kpi.foreign_net), cls: clsSigned(kpi.all_foreign_net != null ? kpi.all_foreign_net : kpi.foreign_net) },
      { label: "成交金額（億）", value: Number(kpi.total_amount || 0).toFixed(1), cls: "neu" },
      { label: "上漲／下跌／平盤", value: (kpi.advance || 0) + " / " + (kpi.decline || 0) + " / " + (kpi.unchanged || 0), cls: "neu" },
      { label: "融資餘額（億）", value: Number(kpi.margin_balance || 0).toFixed(1), cls: "neu" },
      { label: "融券餘額（千張）", value: Number(kpi.short_balance || 0).toFixed(1), cls: "neu" },
      { label: "融資Δ（億）", value: fmtSigned(kpi.margin_delta || 0), cls: clsSigned(kpi.margin_delta || 0) },
      { label: "當沖金額占比%", value: kpi.daytrade_pct != null ? Number(kpi.daytrade_pct).toFixed(2) + "%" : "—", cls: "neu" }
    ];
    document.getElementById("kpiRow").innerHTML = kpiItems.map(function (k) {
      return "<div class=\"kpi\"><div class=\"label\">" + k.label + "</div><div class=\"value " + k.cls + "\">" + k.value + "</div></div>";
    }).join("");
  }

  function renderSankey() {
    const el = document.getElementById("sankeyChart");
    const chart = echarts.init(el);
    charts.push(chart);
    const actors = [
      { key: "foreign_net", name: "外資" },
      { key: "trust_net", name: "投信" },
      { key: "dealer_net", name: "自營" }
    ];
    const ranked = chartStocks().map(function (s) {
        const total = instNet(s);
        return Object.assign({}, s, { total: total, abs: Math.abs(total) });
      });

    const nodeSet = {};
    actors.forEach(function (a) { nodeSet[a.name] = true; });
    ranked.forEach(function (s) {
      nodeSet[s.code + " " + s.name] = true;
      nodeSet[topicLabel(s)] = true;
    });
    const nodes = Object.keys(nodeSet).map(function (n) { return { name: n }; });
    const links = [];
    ranked.forEach(function (s) {
      const stockLabel = s.code + " " + s.name;
      const right = topicLabel(s);
      actors.forEach(function (a) {
        const v = Number(s[a.key]) || 0;
        if (!v) return;
        links.push({
          source: a.name,
          target: stockLabel,
          value: Math.max(Math.abs(v), 0.01),
          raw: v,
          lineStyle: { color: v >= 0 ? GREEN : RED, opacity: 0.45 }
        });
      });
      const stockNet = Number(s.inst_net != null ? s.inst_net : (s.foreign_net + s.trust_net + s.dealer_net));
      links.push({
        source: stockLabel,
        target: right,
        value: Math.max(Math.abs(stockNet), 0.01),
        raw: stockNet,
        lineStyle: { color: stockNet >= 0 ? GREEN : RED, opacity: 0.35 }
      });
    });

    chart.setOption(Object.assign(themeBase(), {
      tooltip: {
        trigger: "item",
        formatter: function (p) {
          if (p.dataType === "edge") {
            return p.data.source + " → " + p.data.target + "<br/>淨額 " + fmtSigned(p.data.raw, 2) + " 千張";
          }
          return p.name;
        }
      },
      series: [{
        type: "sankey",
        emphasis: { focus: "adjacency" },
        nodeAlign: "justify",
        layoutIterations: 32,
        data: nodes,
        links: links,
        lineStyle: { color: "gradient", curveness: 0.5 },
        label: { color: TEXT, fontSize: 11 },
        itemStyle: { borderWidth: 0, color: "#334155" }
      }]
    }));
  }

  function renderSector() {
    const el = document.getElementById("sectorChart");
    const chart = echarts.init(el);
    charts.push(chart);
    const groups = D.groups || D.sectors || [];
    const ranked = groups.slice().sort(function (a, b) {
      const na = Math.abs(a.inst_net != null ? a.inst_net : ((a.foreign_net || 0) + (a.trust_net || 0) + (a.dealer_net || 0)));
      const nb = Math.abs(b.inst_net != null ? b.inst_net : ((b.foreign_net || 0) + (b.trust_net || 0) + (b.dealer_net || 0)));
      return nb - na;
    }).slice(0, 12);

    const names = ranked.map(function (s) { return s.name; });
    const nets = ranked.map(function (s) {
      if (s.inst_net != null) return +Number(s.inst_net).toFixed(2);
      return +((s.foreign_net || 0) + (s.trust_net || 0) + (s.dealer_net || 0)).toFixed(2);
    });
    const vs20 = ranked.map(function (s) { return s.amount_vs_20d != null ? s.amount_vs_20d : (s.vs20 || 1); });

    chart.setOption(Object.assign(themeBase(), {
      tooltip: { trigger: "axis" },
      legend: { data: ["法人合計淨額", "vs20"], textStyle: { color: MUTED }, top: 0 },
      grid: { left: 48, right: 48, top: 36, bottom: 64 },
      xAxis: {
        type: "category",
        data: names,
        axisLabel: { color: MUTED, rotate: 40, fontSize: 10 },
        axisLine: { lineStyle: { color: GRID } }
      },
      yAxis: [
        { type: "value", name: "千張", axisLabel: { color: MUTED }, splitLine: { lineStyle: { color: GRID } } },
        { type: "value", name: "vs20", axisLabel: { color: MUTED }, splitLine: { show: false } }
      ],
      series: [
        {
          name: "法人合計淨額",
          type: "bar",
          data: nets.map(function (v) {
            return { value: v, itemStyle: { color: v >= 0 ? GREEN : RED } };
          })
        },
        {
          name: "vs20",
          type: "line",
          yAxisIndex: 1,
          data: vs20,
          itemStyle: { color: "#38bdf8" },
          lineStyle: { width: 2 }
        }
      ]
    }));
  }

  function renderGroupScatter() {
    const el = document.getElementById("groupScatterChart");
    if (!el) return;
    const chart = echarts.init(el);
    charts.push(chart);
    const groups = D.groups || D.sectors || [];
    const points = groups.map(function (g) {
      const inst = g.inst_net != null ? g.inst_net : ((g.foreign_net || 0) + (g.trust_net || 0) + (g.dealer_net || 0));
      const chg = g.change_pct != null ? g.change_pct : 0;
      const size = g.amount_vs_20d != null ? g.amount_vs_20d : (g.vs20 || 1);
      return {
        name: g.name,
        value: [inst, chg, size, g.margin_delta != null ? g.margin_delta : 0]
      };
    });

    chart.setOption(Object.assign(themeBase(), {
      tooltip: {
        formatter: function (p) {
          return p.name +
            "<br/>資金淨流入 " + fmtSigned(p.value[0], 2) + " 千張" +
            "<br/>漲跌 " + fmtSigned(p.value[1], 2) + "%" +
            "<br/>量能 vs20 " + Number(p.value[2]).toFixed(2) +
            "<br/>融資變動 " + fmtSigned(p.value[3], 0) + " 張";
        }
      },
      grid: { left: 56, right: 28, top: 28, bottom: 48 },
      xAxis: {
        name: "資金淨流入（千張）",
        type: "value",
        axisLabel: { color: MUTED },
        splitLine: { lineStyle: { color: GRID } },
        nameTextStyle: { color: MUTED }
      },
      yAxis: {
        name: "漲跌 %",
        type: "value",
        axisLabel: { color: MUTED },
        splitLine: { lineStyle: { color: GRID } },
        nameTextStyle: { color: MUTED }
      },
      series: [{
        type: "scatter",
        symbolSize: function (val) { return Math.max(14, Math.min(42, val[2] * 22)); },
        data: points,
        itemStyle: {
          color: function (p) { return p.value[1] >= 0 ? GREEN : RED; },
          opacity: 0.82
        },
        label: {
          show: true,
          formatter: function (p) { return p.name; },
          position: "top",
          color: MUTED,
          fontSize: 10
        },
        markLine: {
          silent: true,
          symbol: "none",
          lineStyle: { color: GRID, type: "dashed" },
          data: [{ xAxis: 0 }, { yAxis: 0 }]
        }
      }]
    }));
  }

  function renderTrend() {
    const el = document.getElementById("trendChart");
    const chart = echarts.init(el);
    charts.push(chart);
    const hist = historyKpi.length ? historyKpi : (D.history_kpi || []);
    const datesH = hist.map(function (h) { return h.date.slice(5); });
    const selected = (D.meta && D.meta.date) || dates[dateIdx];
    const markIdx = hist.findIndex(function (h) { return h.date === selected; });

    const foreign = hist.map(function (h) { return h.foreign != null ? h.foreign : h.foreign_net; });
    const trust = hist.map(function (h) { return h.trust != null ? h.trust : h.trust_net; });
    const dealer = hist.map(function (h) { return h.dealer != null ? h.dealer : h.dealer_net; });

    const markLine = markIdx >= 0 ? {
      symbol: "none",
      label: { formatter: selected.slice(5), color: MUTED },
      lineStyle: { color: "#38bdf8", type: "dashed", width: 1.5 },
      data: [{ xAxis: datesH[markIdx] }]
    } : undefined;

    chart.setOption(Object.assign(themeBase(), {
      tooltip: { trigger: "axis" },
      legend: { data: ["外資", "投信", "自營"], textStyle: { color: MUTED }, top: 0 },
      grid: { left: 48, right: 16, top: 36, bottom: 32 },
      xAxis: { type: "category", data: datesH, axisLabel: { color: MUTED, fontSize: 10 }, axisLine: { lineStyle: { color: GRID } } },
      yAxis: { type: "value", name: "億", axisLabel: { color: MUTED }, splitLine: { lineStyle: { color: GRID } } },
      dataZoom: hist.length > 20 ? [{ type: "inside", start: Math.max(0, 100 - 800 / hist.length), end: 100 }] : undefined,
      series: [
        { name: "外資", type: "line", smooth: true, data: foreign, itemStyle: { color: "#38bdf8" }, markLine: markLine },
        { name: "投信", type: "line", smooth: true, data: trust, itemStyle: { color: "#a78bfa" } },
        { name: "自營", type: "line", smooth: true, data: dealer, itemStyle: { color: "#f59e0b" } }
      ]
    }));
  }

  function renderShort() {
    const el = document.getElementById("shortChart");
    const chart = echarts.init(el);
    charts.push(chart);
    const rows = filteredStocks().slice().sort(function (a, b) {
      return ((b.short_sell || 0) + (b.sbl_sell || 0)) - ((a.short_sell || 0) + (a.sbl_sell || 0));
    }).slice(0, Math.max(8, Math.min(20, filterState.topN)));
    chart.setOption(Object.assign(themeBase(), {
      tooltip: { trigger: "axis" },
      legend: { data: ["融券賣出", "借券賣出"], textStyle: { color: MUTED }, top: 0 },
      grid: { left: 88, right: 16, top: 36, bottom: 24 },
      xAxis: { type: "value", axisLabel: { color: MUTED }, splitLine: { lineStyle: { color: GRID } } },
      yAxis: {
        type: "category",
        data: rows.map(function (s) { return s.code + " " + s.name; }),
        axisLabel: { color: MUTED, fontSize: 10 }
      },
      series: [
        { name: "融券賣出", type: "bar", stack: "s", data: rows.map(function (s) { return s.short_sell || 0; }), itemStyle: { color: RED } },
        { name: "借券賣出", type: "bar", stack: "s", data: rows.map(function (s) { return s.sbl_sell || 0; }), itemStyle: { color: "#f97316" } }
      ]
    }));
  }

  function renderLeverage() {
    const el = document.getElementById("leverageChart");
    const chart = echarts.init(el);
    charts.push(chart);
    const levSrc = chartStocks();
    const points = levSrc.map(function (s) {
      return {
        value: [(s.margin_util || 0) * 100, s.change || 0, s.amount || 0],
        name: s.code + " " + s.name
      };
    });
    chart.setOption(Object.assign(themeBase(), {
      tooltip: {
        formatter: function (p) {
          return p.name + "<br/>融資使用率 " + p.value[0].toFixed(1) + "%<br/>漲跌 " + fmtSigned(p.value[1], 2) + "%<br/>成交 " + Number(p.value[2]).toFixed(1) + " 億";
        }
      },
      grid: { left: 48, right: 24, top: 24, bottom: 40 },
      xAxis: { name: "融資使用率 %", type: "value", axisLabel: { color: MUTED }, splitLine: { lineStyle: { color: GRID } }, nameTextStyle: { color: MUTED } },
      yAxis: { name: "漲跌 %", type: "value", axisLabel: { color: MUTED }, splitLine: { lineStyle: { color: GRID } }, nameTextStyle: { color: MUTED } },
      series: [{
        type: "scatter",
        symbolSize: function (val) { return Math.max(12, Math.sqrt(Math.max(val[2], 0.1)) * 1.8); },
        data: points,
        itemStyle: {
          color: function (p) { return p.value[1] >= 0 ? GREEN : RED; },
          opacity: 0.85
        },
        label: {
          show: true,
          formatter: function (p) { return p.name.split(" ")[0]; },
          position: "top",
          color: MUTED,
          fontSize: 10
        }
      }]
    }));
  }

  function renderForeignHold() {
    const el = document.getElementById("foreignHoldChart");
    if (!el) return;
    const chart = echarts.init(el);
    charts.push(chart);
    // Top-N by |inst| often includes OTC/ETF without MI_QFIIS — take QFIIS names from a wider pool
    const n = Math.max(5, Math.min(80, Number(filterState.topN) || 12));
    let rows = chartStocks().filter(function (s) { return s.foreign_hold_pct != null; });
    if (rows.length < Math.min(8, n)) {
      rows = filteredStocks()
        .filter(function (s) { return s.foreign_hold_pct != null; })
        .slice()
        .sort(function (a, b) { return Math.abs(instNet(b)) - Math.abs(instNet(a)); })
        .slice(0, n);
    }
    const points = rows.map(function (s) {
      return {
        name: s.code + " " + s.name,
        value: [Number(s.foreign_hold_pct), instNet(s), s.amount || 0.5, s.change || 0]
      };
    });
    if (!points.length) {
      chart.setOption(Object.assign(themeBase(), {
        title: { text: "無外資持股%可畫（篩選後無 MI_QFIIS）", left: "center", top: "middle", textStyle: { color: MUTED, fontSize: 14 } },
        xAxis: { show: false }, yAxis: { show: false }, series: []
      }));
      return;
    }
    chart.setOption(Object.assign(themeBase(), {
      tooltip: {
        formatter: function (p) {
          return p.name +
            "<br/>外資持股 " + Number(p.value[0]).toFixed(2) + "%" +
            "<br/>法人淨額 " + fmtSigned(p.value[1], 2) + " 千張" +
            "<br/>成交 " + Number(p.value[2]).toFixed(2) + " 億" +
            "<br/>漲跌 " + fmtSigned(p.value[3], 2) + "%";
        }
      },
      grid: { left: 56, right: 28, top: 28, bottom: 48 },
      xAxis: {
        name: "外資持股 %（存量）", type: "value",
        axisLabel: { color: MUTED }, splitLine: { lineStyle: { color: GRID } },
        nameTextStyle: { color: MUTED }
      },
      yAxis: {
        name: "法人淨額（千張）", type: "value",
        axisLabel: { color: MUTED }, splitLine: { lineStyle: { color: GRID } },
        nameTextStyle: { color: MUTED }
      },
      series: [{
        type: "scatter",
        symbolSize: function (val) { return Math.max(10, Math.min(36, Math.sqrt(Math.max(val[2], 0.05)) * 2.2)); },
        data: points,
        itemStyle: {
          color: function (p) { return p.value[1] >= 0 ? GREEN : RED; },
          opacity: 0.8
        },
        label: {
          show: points.length <= 24,
          formatter: function (p) { return p.name.split(" ")[0]; },
          position: "top", color: MUTED, fontSize: 10
        },
        markLine: {
          silent: true, symbol: "none",
          lineStyle: { color: GRID, type: "dashed" },
          data: [{ yAxis: 0 }]
        }
      }]
    }));
  }

  function renderStocksTable() {
    const tbody = document.querySelector("#stocksTable tbody");
    if (!tbody) return;
    const rows = filteredStocks().slice().sort(function (a, b) {
      return Math.abs(instNet(b)) - Math.abs(instNet(a));
    }).slice(0, 200);
    tbody.innerHTML = rows.length ? rows.map(function (s) {
      const net = instNet(s);
      return "<tr>" +
        "<td>" + s.code + "</td>" +
        "<td>" + s.name + (isEtfLike(s) ? " <span style=\"color:#fbbf24\">ETF</span>" : "") + "</td>" +
        "<td>" + topicLabel(s) + "</td>" +
        "<td class=\"" + clsSigned(s.change) + "\">" + fmtSigned(s.change, 2) + "</td>" +
        "<td class=\"" + clsSigned(net) + "\">" + fmtSigned(net, 2) + "</td>" +
        "<td class=\"" + clsSigned(s.foreign_net) + "\">" + fmtSigned(s.foreign_net, 2) + "</td>" +
        "<td class=\"" + clsSigned(s.trust_net) + "\">" + fmtSigned(s.trust_net, 2) + "</td>" +
        "<td class=\"" + clsSigned(s.dealer_net) + "\">" + fmtSigned(s.dealer_net, 2) + "</td>" +
        "<td>" + Number(s.amount || 0).toFixed(2) + "</td>" +
        "<td>" + ((s.margin_util || 0) * 100).toFixed(1) + "%</td>" +
        "<td>" + (s.foreign_hold_pct != null ? Number(s.foreign_hold_pct).toFixed(1) : "—") + "</td>" +
        "<td>" + (s.sbl_avail != null ? Number(s.sbl_avail).toFixed(0) : "—") + "</td>" +
        "<td>" + [
          s.disposition ? "<span style=\"color:#ef4444\">處置</span>" : "",
          s.notice ? "<span style=\"color:#fbbf24\">注意</span>" : "",
          s.stop_sbl ? "<span style=\"color:#a78bfa\">停券</span>" : "",
          s.daytrade_pause ? "<span style=\"color:#f97316\">暫停當沖</span>" : (s.daytrade_suspended ? "<span style=\"color:#fb923c\">當沖停</span>" : ""),
          (s.disp_risk === "high" ? "<span style=\"color:#ef4444\">逼近處置</span>" : (s.disp_risk === "med" ? "<span style=\"color:#f59e0b\">逼近處置·中</span>" : "")),
          s.altered_trading ? "<span style=\"color:#e879f9\">變更交易</span>" : ""
        ].filter(Boolean).join(" ") + "</td>" +
        "<td>" + (s.market === "tpex" ? "上櫃" : "上市") + "</td>" +
        "</tr>";
    }).join("") : "<tr><td colspan=\"14\" style=\"color:#8b9bb0\">無符合篩選的個股</td></tr>";
  }


  function renderBrokers() {
    const tbody = document.querySelector("#brokersTable tbody");
    if (!tbody) return;
    const br = (D && D.brokers) || {};
    const rows = br.branches || [];
    const note = br.note || "個股分點需官網驗證碼；此處為櫃買券商成交排行＋查詢入口";
    const card = document.querySelector("#brokersTable") && document.querySelector("#brokersTable").closest(".card");
    const sub = card && card.querySelector(".sub");
    if (sub) sub.textContent = note;
    const links = br.links || {};
    const a1 = document.getElementById("linkTwseBsr");
    const a2 = document.getElementById("linkTpexBroker");
    if (a1 && links.twse_bsr) a1.href = links.twse_bsr;
    if (a2 && links.tpex_broker) a2.href = links.tpex_broker;
    tbody.innerHTML = rows.length ? rows.map(function (r) {
      return "<tr>" +
        "<td>" + (r.rank || "") + "</td>" +
        "<td>" + (r.code || "") + "</td>" +
        "<td>" + (r.name || "") + "</td>" +
        "<td>" + (r.amount != null ? Number(r.amount).toLocaleString() : "—") + "</td>" +
        "<td>" + (r.ratio || "—") + "</td>" +
        "</tr>";
    }).join("") : "<tr><td colspan=\"5\" style=\"color:#8b9bb0\">本日無券商排行資料</td></tr>";
  }

  function renderAlerts() {
    const tbody = document.querySelector("#alertsTable tbody");
    const alerts = D.alerts || [];
    tbody.innerHTML = alerts.length ? alerts.map(function (a) {
      return "<tr>" +
        "<td><span class=\"lvl lvl-" + a.level + "\">" + a.level + "</span></td>" +
        "<td>" + a.code + "</td>" +
        "<td>" + a.name + "</td>" +
        "<td>" + a.type + "</td>" +
        "<td>" + a.message + "</td>" +
        "<td>" + a.value + "</td>" +
        "</tr>";
    }).join("") : "<tr><td colspan=\"6\" style=\"color:#8b9bb0\">本日無警示</td></tr>";
  }


  const REGIME_LABELS = {
    inst_push: "機構推動",
    leverage_relay: "槓桿接力",
    hot_money: "熱錢噪音",
    risk_off: "風險規避",
    regulatory: "監管摩擦",
    mixed: "法人打架",
    quiet: "平淡"
  };

  function computeRegimeClient(row) {
    // Minimal fallback from history_kpi row when regimes.json missing
    const foreign = Number(row.foreign != null ? row.foreign : row.foreign_net) || 0;
    const trust = Number(row.trust != null ? row.trust : row.trust_net) || 0;
    const dealer = Number(row.dealer != null ? row.dealer : row.dealer_net) || 0;
    const daytrade = Number(row.daytrade != null ? row.daytrade : row.daytrade_pct) || 0;
    const margin = Number(row.margin_delta) || 0;
    let primary = "quiet";
    let evidence = ["（離線推估，缺完整 curated／rules）"];
    if (foreign <= -80) {
      primary = "risk_off";
      evidence = ["外資約 " + fmtSigned(foreign) + " 億（history 推估）"];
    } else if (foreign >= 80 && trust > -50 && dealer > -50) {
      primary = "inst_push";
      evidence = ["外資約 " + fmtSigned(foreign) + " 億（history 推估）"];
    } else if (Math.abs(foreign) >= 40 && ((foreign * trust < 0 && Math.abs(trust) >= 40) || (foreign * dealer < 0 && Math.abs(dealer) >= 40))) {
      primary = "mixed";
      evidence = ["外資／投信／自營異號（history 推估）"];
    } else if (foreign <= 35 && margin > 3) {
      primary = "leverage_relay";
      evidence = ["融資 Δ " + fmtSigned(margin) + " 億（history 推估）"];
    } else if (daytrade >= 40) {
      primary = "hot_money";
      evidence = ["當沖約 " + daytrade.toFixed(1) + "%（history 推估）"];
    }
    return {
      date: row.date,
      primary: primary,
      primary_label: REGIME_LABELS[primary] || primary,
      secondary: null,
      secondary_label: null,
      confidence: 0.35,
      evidence: evidence,
      metrics: {
        foreign: foreign, trust: trust, dealer: dealer,
        daytrade_pct: daytrade, margin_delta: margin
      }
    };
  }

  function ensureRegimesFallback() {
    if (regimesDays.length) return;
    if (!historyKpi || !historyKpi.length) return;
    regimesDays = historyKpi.map(computeRegimeClient);
    regimeByDate = {};
    regimesDays.forEach(function (d) { regimeByDate[d.date] = d; });
  }

  function getRegimeFor(date) {
    ensureRegimesFallback();
    return regimeByDate[date] || null;
  }



  function renderScreens() {
    const meta = document.getElementById("screenMeta");
    const mildBody = document.querySelector("#mildPushTable tbody");
    const exitBody = document.querySelector("#exitWatchTable tbody");
    const heavyBody = document.querySelector("#heavyPushTable tbody");
    if (!mildBody || !exitBody) return;
    const doc = screensDoc;
    function empty(cols) { return "<tr><td colspan=\"" + cols + "\" style=\"color:#8b9bb0\">無</td></tr>"; }
    if (!doc) {
      if (meta) meta.textContent = "尚無 screens 資料（請跑 build_screens.py）";
      mildBody.innerHTML = exitBody.innerHTML = "";
      if (heavyBody) heavyBody.innerHTML = "";
      return;
    }
    const reg = doc.regime || {};
    const c = doc.counts || {};
    if (meta) {
      meta.textContent = (doc.date || "") +
        " · " + (reg.primary_label || "—") +
        " · mild " + (c.mild_push || 0) +
        " · exit " + (c.exit_watch || 0) +
        " · fresh " + (c.fresh_money || 0) +
        " · trap " + (c.leverage_trap || 0) +
        " · " + (doc.disclaimer || "");
    }
    function rows(list, cols) {
      if (!list || !list.length) return empty(cols);
      return list.slice(0, 25).map(function (r) {
        const why = (r.why || []).join("；");
        return "<tr>" +
          "<td>" + (r.score != null ? Number(r.score).toFixed(1) : "—") + "</td>" +
          "<td>" + (r.code || "") + "</td>" +
          "<td>" + (r.name || "") + "</td>" +
          "<td>" + (r.topic || "") + "</td>" +
          "<td class=\"" + clsSigned(r.inst_net) + "\">" + fmtSigned(r.inst_net, 2) + "</td>" +
          (cols >= 9 ? ("<td class=\"" + clsSigned(r.foreign_net) + "\">" + fmtSigned(r.foreign_net, 2) + "</td>") : "") +
          (cols >= 8 ? ("<td class=\"" + clsSigned(r.change) + "\">" + fmtSigned(r.change, 2) + "</td>") : "") +
          (cols >= 9 ? ("<td>" + ((r.margin_util || 0) * 100).toFixed(1) + "%</td>") : "") +
          "<td style=\"max-width:280px;white-space:normal;font-size:0.75rem;color:#94a3b8\">" + why + "</td>" +
          "</tr>";
      }).join("");
    }
    mildBody.innerHTML = rows(doc.mild_push, 9);
    exitBody.innerHTML = rows(doc.exit_watch, 9);
    if (heavyBody) {
      const list = doc.heavy_push_contrast || [];
      heavyBody.innerHTML = list.length ? list.slice(0, 15).map(function (r) {
        return "<tr><td>" + Number(r.score).toFixed(1) + "</td><td>" + r.code + "</td><td>" + r.name + "</td><td>" + r.topic + "</td>" +
          "<td class=\"" + clsSigned(r.inst_net) + "\">" + fmtSigned(r.inst_net, 2) + "</td>" +
          "<td class=\"" + clsSigned(r.change) + "\">" + fmtSigned(r.change, 2) + "</td>" +
          "<td style=\"max-width:280px;white-space:normal;font-size:0.75rem;color:#94a3b8\">" + (r.why || []).join("；") + "</td></tr>";
      }).join("") : empty(7);
    }

    const fsf = doc.foreign_stock_flow || {};
    const accumBody = document.querySelector("#accumTable tbody");
    if (accumBody) {
      const mix = []
        .concat((fsf.fresh_money || []).slice(0, 6).map(function (r) { return Object.assign({bucket: "fresh"}, r); }))
        .concat((fsf.accumulation || []).slice(0, 6).map(function (r) { return Object.assign({bucket: "accum"}, r); }))
        .concat((fsf.distribution || []).slice(0, 6).map(function (r) { return Object.assign({bucket: "dist"}, r); }));
      accumBody.innerHTML = mix.length ? mix.map(function (r) {
        return "<tr><td>" + r.bucket + "</td><td>" + Number(r.score).toFixed(1) + "</td><td>" + r.code + "</td><td>" + r.name + "</td>" +
          "<td class=\"" + clsSigned(r.foreign_net) + "\">" + fmtSigned(r.foreign_net, 2) + "</td>" +
          "<td>" + (r.foreign_hold_pct != null ? Number(r.foreign_hold_pct).toFixed(1) : "—") + "</td></tr>";
      }).join("") : empty(6);
    }
    const lev = doc.leverage_pressure || {};
    const levBody = document.querySelector("#levTable tbody");
    if (levBody) {
      const mix = []
        .concat((lev.leverage_trap || []).slice(0, 8).map(function (r) { return Object.assign({bucket: "trap"}, r); }))
        .concat((lev.delever_with_flow || []).slice(0, 8).map(function (r) { return Object.assign({bucket: "delever"}, r); }));
      levBody.innerHTML = mix.length ? mix.map(function (r) {
        return "<tr><td>" + r.bucket + "</td><td>" + Number(r.score).toFixed(1) + "</td><td>" + r.code + "</td><td>" + r.name + "</td>" +
          "<td class=\"" + clsSigned(r.foreign_net) + "\">" + fmtSigned(r.foreign_net, 2) + "</td>" +
          "<td>" + ((r.margin_util || 0) * 100).toFixed(1) + "%</td></tr>";
      }).join("") : empty(6);
    }
    const sh = doc.short_ammo || {};
    const shortBody = document.querySelector("#shortTable tbody");
    if (shortBody) {
      const mix = []
        .concat((sh.squeeze_risk || []).slice(0, 8).map(function (r) { return Object.assign({bucket: "squeeze"}, r); }))
        .concat((sh.fuel_for_shorts || []).slice(0, 8).map(function (r) { return Object.assign({bucket: "fuel"}, r); }));
      shortBody.innerHTML = mix.length ? mix.map(function (r) {
        return "<tr><td>" + r.bucket + "</td><td>" + Number(r.score).toFixed(1) + "</td><td>" + r.code + "</td><td>" + r.name + "</td>" +
          "<td>" + (r.sbl_avail != null ? Number(r.sbl_avail).toFixed(0) : "—") + "</td></tr>";
      }).join("") : empty(5);
    }
    const dispBody = document.querySelector("#dispCdTable tbody");
    if (dispBody) {
      const list = doc.disposal_countdown || [];
      dispBody.innerHTML = list.length ? list.slice(0, 12).map(function (r) {
        return "<tr><td>" + r.countdown + "</td><td>" + (r.status || "") + "</td><td>" + r.code + "</td><td>" + r.name + "</td>" +
          "<td style=\"max-width:220px;white-space:normal;font-size:0.72rem;color:#94a3b8\">" + (r.path || "") + "</td></tr>";
      }).join("") : empty(5);
    }
    const rot = doc.theme_rotation || {};
    const themeBody = document.querySelector("#themeRotTable tbody");
    if (themeBody) {
      const mix = []
        .concat((rot.theme_acceleration || []).slice(0, 8).map(function (r) { return Object.assign({dir: "加速"}, r); }))
        .concat((rot.theme_fade || []).slice(0, 8).map(function (r) { return Object.assign({dir: "褪色"}, r); }));
      themeBody.innerHTML = mix.length ? mix.map(function (r) {
        return "<tr><td>" + r.dir + "</td><td>" + r.topic + "</td><td>" + Number(r.inst_net).toFixed(1) + "</td>" +
          "<td>" + Number(r.prev_mean).toFixed(1) + "</td><td class=\"" + clsSigned(r.delta) + "\">" + fmtSigned(r.delta, 1) + "</td></tr>";
      }).join("") : empty(5);
    }
    const al = doc.inst_alignment || {};
    const alignBody = document.querySelector("#alignTable tbody");
    if (alignBody) {
      const mix = []
        .concat((al.aligned_bid || []).slice(0, 8).map(function (r) { return Object.assign({bucket: "aligned"}, r); }))
        .concat((al.conflict || []).slice(0, 8).map(function (r) { return Object.assign({bucket: "conflict"}, r); }));
      alignBody.innerHTML = mix.length ? mix.map(function (r) {
        return "<tr><td>" + r.bucket + "</td><td>" + Number(r.score).toFixed(1) + "</td><td>" + r.code + "</td><td>" + r.name + "</td>" +
          "<td style=\"max-width:220px;white-space:normal;font-size:0.72rem;color:#94a3b8\">" + (r.why || []).join("；") + "</td></tr>";
      }).join("") : empty(5);
    }
    const noiseBody = document.querySelector("#noiseTable tbody");
    if (noiseBody) {
      const list = doc.daytrade_noise || [];
      noiseBody.innerHTML = list.length ? list.slice(0, 12).map(function (r) {
        return "<tr><td>" + Number(r.score).toFixed(1) + "</td><td>" + r.code + "</td><td>" + r.name + "</td>" +
          "<td class=\"" + clsSigned(r.change) + "\">" + fmtSigned(r.change, 2) + "</td>" +
          "<td class=\"" + clsSigned(r.inst_net) + "\">" + fmtSigned(r.inst_net, 2) + "</td></tr>";
      }).join("") : empty(5);
    }
    const splitBox = document.getElementById("marketSplitBox");
    const extraMeta = document.getElementById("screenExtraMeta");
    const ms = doc.market_split || {};
    if (splitBox) {
      splitBox.textContent = (ms.label || "—") + " · 上市外资 " + (ms.listed_foreign != null ? ms.listed_foreign : "—") +
        " / 櫃買 " + (ms.tpex_foreign != null ? ms.tpex_foreign : "—") + " · " + (ms.why || "");
    }
    if (extraMeta) {
      extraMeta.textContent = "hot_tape=" + !!(doc.params && doc.params.hot_tape) +
        " · accel " + (c.theme_acceleration || 0) +
        " · fade " + (c.theme_fade || 0) +
        " · squeeze " + (c.squeeze_risk || 0);
    }
  }

  async function loadScreensForDate(date) {
    screensDoc = null;
    if (!date) { renderScreens(); return; }
    try {
      const r = await fetch("data/screens/" + date + ".json", { cache: "no-store" });
      if (r.ok) {
        screensDoc = await r.json();
      } else {
        const r2 = await fetch("data/screens_latest.json", { cache: "no-store" });
        if (r2.ok) {
          const j = await r2.json();
          if (j.date === date) screensDoc = j;
        }
      }
    } catch (e) { screensDoc = null; }
    renderScreens();
    loadEtf981ForDate(date);
  }



  function renderEtf981() {
    const meta = document.getElementById("etf981Meta");
    const flowMeta = document.getElementById("etf981FlowMeta");
    const crossMeta = document.getElementById("etf981CrossMeta");
    const flowBody = document.querySelector("#etf981FlowTable tbody");
    const crossBody = document.querySelector("#etf981CrossTable tbody");
    const holdBody = document.querySelector("#etf981HoldTable tbody");
    if (!flowBody || !crossBody || !holdBody) return;
    function empty(cols) { return "<tr><td colspan=\"" + cols + "\" style=\"color:#8b9bb0\">無</td></tr>"; }
    const doc = etf981Doc;
    if (!doc) {
      if (meta) meta.textContent = "尚無 00981A 資料（請跑 build_00981a.py）";
      flowBody.innerHTML = crossBody.innerHTML = holdBody.innerHTML = empty(6);
      return;
    }
    const reg = doc.regime || {};
    const mf = doc.manager_flow || {};
    const c = mf.counts || {};
    if (meta) {
      meta.textContent = (doc.date || "") +
        " · " + (reg.primary_label || "—") +
        (reg.top_topic ? (" · 體制題材 " + reg.top_topic) : "") +
        " · Δ來源 " + (mf.source || "—") +
        (mf.prev_date ? (" vs " + mf.prev_date) : "") +
        " · " + (doc.disclaimer || "");
    }
    if (flowMeta) {
      flowMeta.textContent = "加碼 " + (c.adds || 0) + " · 減碼 " + (c.cuts || 0) +
        " · 新建倉 " + (c.new || 0) + " · 出清 " + (c.exits || 0) +
        (mf.note ? (" · " + mf.note) : "");
    }
    const flowRows = []
      .concat((mf.adds || []).slice(0, 8).map(function (r) { return Object.assign({dir: "加"}, r); }))
      .concat((mf.cuts || []).slice(0, 8).map(function (r) { return Object.assign({dir: "減"}, r); }))
      .concat((mf.new || []).slice(0, 5).map(function (r) { return Object.assign({dir: "新"}, r); }))
      .concat((mf.exits || []).slice(0, 5).map(function (r) { return Object.assign({dir: "清"}, r); }));
    flowBody.innerHTML = flowRows.length ? flowRows.map(function (r) {
      return "<tr><td>" + r.dir + "</td><td>" + (r.code || "") + "</td><td>" + (r.name || "") + "</td>" +
        "<td>" + (r.weight_pct != null ? Number(r.weight_pct).toFixed(2) : (r.prev_weight_pct != null ? Number(r.prev_weight_pct).toFixed(2) : "—")) + "</td>" +
        "<td class=\"" + clsSigned(r.weight_delta) + "\">" + fmtSigned(r.weight_delta, 2) + "</td>" +
        "<td class=\"" + clsSigned(r.share_delta) + "\">" + (r.share_delta != null ? Number(r.share_delta).toLocaleString() : "—") + "</td></tr>";
    }).join("") : empty(6);

    const cx = doc.cross || {};
    if (crossMeta) {
      crossMeta.textContent = "mild∩ " + ((cx.intersect_mild_push || []).length) +
        " · accel∩ " + ((cx.intersect_theme_accel || []).length) +
        " · exit∩ " + ((cx.flag_exit_watch || []).length) +
        " · regime∩ " + ((cx.aligned_with_regime || []).length);
    }
    const crossRows = []
      .concat((cx.intersect_mild_push || []).slice(0, 8).map(function (r) { return Object.assign({bucket: "mild"}, r); }))
      .concat((cx.intersect_theme_accel || []).slice(0, 8).map(function (r) { return Object.assign({bucket: "accel"}, r); }))
      .concat((cx.flag_exit_watch || []).slice(0, 8).map(function (r) { return Object.assign({bucket: "exit"}, r); }))
      .concat((cx.aligned_with_regime || []).slice(0, 8).map(function (r) { return Object.assign({bucket: "regime"}, r); }));
    crossBody.innerHTML = crossRows.length ? crossRows.map(function (r) {
      return "<tr><td>" + r.bucket + "</td><td>" + (r.code || "") + "</td><td>" + (r.name || "") + "</td>" +
        "<td>" + (r.topic || "—") + "</td>" +
        "<td>" + (r.weight_pct != null ? Number(r.weight_pct).toFixed(2) : "—") + "</td>" +
        "<td class=\"" + clsSigned(r.inst_net) + "\">" + fmtSigned(r.inst_net, 2) + "</td>" +
        "<td class=\"" + clsSigned(r.weight_delta) + "\">" + fmtSigned(r.weight_delta, 2) + "</td></tr>";
    }).join("") : empty(7);

    const holds = (doc.holdings || []).slice(0, 30);
    holdBody.innerHTML = holds.length ? holds.map(function (r) {
      return "<tr><td>" + (r.code || "") + "</td><td>" + (r.name || "") + "</td>" +
        "<td>" + (r.topic || "—") + "</td>" +
        "<td>" + Number(r.weight_pct || 0).toFixed(2) + "</td>" +
        "<td>" + (r.share != null ? Number(r.share).toLocaleString() : "—") + "</td>" +
        "<td class=\"" + clsSigned(r.weight_delta) + "\">" + fmtSigned(r.weight_delta, 2) + "</td>" +
        "<td>" + (r.action || "—") + "</td></tr>";
    }).join("") : empty(7);
  }

  async function loadEtf981ForDate(date) {
    etf981Doc = null;
    try {
      let r = null;
      if (date) r = await fetch("data/etf/00981a/" + date + ".json", { cache: "no-store" });
      if (!r || !r.ok) r = await fetch("data/etf/00981a/latest.json", { cache: "no-store" });
      if (r && r.ok) {
        const j = await r.json();
        if (!date || j.date === date) etf981Doc = j;
        else etf981Doc = j; // still show latest with its own date in meta
      }
    } catch (e) { etf981Doc = null; }
    renderEtf981();
  }




  async function loadDigest() {
    digestDoc = null;
    digestMarkdown = "";
    const meta = document.getElementById("digestMeta");
    const pre = document.getElementById("digestPreview");
    try {
      const [mdRes, jsonRes] = await Promise.all([
        fetch("data/digest_latest.md", { cache: "no-store" }),
        fetch("data/digest_latest.json", { cache: "no-store" })
      ]);
      if (mdRes.ok) digestMarkdown = await mdRes.text();
      if (jsonRes.ok) digestDoc = await jsonRes.json();
      if (pre) pre.textContent = digestMarkdown || "尚無 digest_latest.md（請跑 build_daily_digest.py）";
      if (meta) {
        meta.textContent = digestDoc
          ? ((digestDoc.date || "") + " · " + (digestDoc.headline || "—") +
             " · " + (digestDoc.engine || "") + " · llm=" + String(!!digestDoc.llm))
          : "尚無制式日報";
      }
    } catch (e) {
      if (pre) pre.textContent = "日報載入失敗";
      if (meta) meta.textContent = "載入失敗";
    }
  }

  async function loadRegimeBrief(date) {
    if (!date) return;
    if (regimeBriefCache[date] && regimeBriefCache[date].paragraphs) {
      renderRegime();
      return;
    }
    try {
      let r = await fetch("data/regime_briefs/" + date + ".json", { cache: "no-store" });
      if (!r.ok) {
        r = await fetch("data/regime_brief_latest.json", { cache: "no-store" });
      }
      if (r.ok) {
        const j = await r.json();
        if (j.date) regimeBriefCache[j.date] = j;
        regimeBriefCache[date] = j;
        renderRegime();
      }
    } catch (e) {}
  }

  function renderRegime() {
    const cardDate = regimeViewDate || (D && D.meta && D.meta.date) || (dates[dateIdx] || null);
    const day = cardDate ? getRegimeFor(cardDate) : null;
    const dateHint = document.getElementById("regimeDateHint");
    const primaryEl = document.getElementById("regimePrimary");
    const chipsEl = document.getElementById("regimeChips");
    const evEl = document.getElementById("regimeEvidence");
    const tl = document.getElementById("regimeTimeline");
    const tbody = document.querySelector("#regimeMiniTable tbody");
    if (!primaryEl) return;

    if (!day) {
      if (dateHint) dateHint.textContent = "尚無體制資料";
      primaryEl.textContent = "—";
      if (chipsEl) chipsEl.innerHTML = "";
      if (evEl) evEl.innerHTML = "";
      return;
    }

    if (dateHint) {
      const sync = (D && D.meta && D.meta.date === day.date) ? "（與看板同日）" : "（點選時間軸預覽）";
      dateHint.textContent = "資料日 " + day.date + " " + sync;
    }
    primaryEl.textContent = day.primary_label || REGIME_LABELS[day.primary] || day.primary;
    primaryEl.className = "regime-primary r-" + (day.primary || "quiet");

    const chips = [];
    if (day.secondary) {
      chips.push("<span class=\"regime-chip secondary\">次：" +
        (day.secondary_label || REGIME_LABELS[day.secondary] || day.secondary) + "</span>");
    }
    const confPct = Math.round((Number(day.confidence) || 0) * 100);
    chips.push("<span class=\"regime-chip conf\">信心 " + confPct + "%</span>");
    if (chipsEl) chipsEl.innerHTML = chips.join("");

    const bullets = (day.evidence || []).slice(0, 4);
    if (evEl) {
      evEl.innerHTML = bullets.map(function (b) { return "<li>" + b + "</li>"; }).join("");
    }
    const briefEl = document.getElementById("regimeBriefBox");
    if (briefEl) {
      const br = (day.brief) || regimeBriefCache[day.date];
      if (br && br.paragraphs && br.paragraphs.length) {
        briefEl.innerHTML = "<div style=\"color:var(--muted);font-size:0.72rem;margin-bottom:6px\">制式講解 · 純函數 · 非 LLM" +
          (br.engine ? (" · " + br.engine) : "") + "</div>" +
          br.paragraphs.map(function (para) {
            return "<p style=\"margin:0 0 8px\">" + para.replace(/</g, "&lt;") + "</p>";
          }).join("");
      } else if (br && br.one_liner) {
        briefEl.textContent = br.one_liner;
      } else {
        briefEl.textContent = "制式講解載入中…";
        loadRegimeBrief(day.date);
      }
    }

    // Timeline last ~20
    ensureRegimesFallback();
    const tail = regimesDays.slice(-20);
    if (tl) {
      tl.innerHTML = tail.map(function (r) {
        const active = r.date === day.date ? " active" : "";
        const label = r.primary_label || REGIME_LABELS[r.primary] || r.primary;
        const short = (r.date || "").slice(5);
        return "<button type=\"button\" class=\"regime-pill r-" + r.primary + active +
          "\" data-regime-date=\"" + r.date + "\" title=\"" + r.date + " " + label + "\">" +
          "<span class=\"pdate\">" + short + "</span>" + label + "</button>";
      }).join("");
    }

    // Mini metrics table — prefer regime metrics, else history
    if (tbody) {
      const rows = tail.slice().reverse();
      tbody.innerHTML = rows.map(function (r) {
        const m = r.metrics || {};
        let foreign = m.foreign, trust = m.trust, dealer = m.dealer;
        let daytrade = m.daytrade_pct, margin = m.margin_delta;
        if (foreign == null) {
          const h = (historyKpi || []).find(function (x) { return x.date === r.date; });
          if (h) {
            foreign = h.foreign != null ? h.foreign : h.foreign_net;
            trust = h.trust != null ? h.trust : h.trust_net;
            dealer = h.dealer != null ? h.dealer : h.dealer_net;
            daytrade = h.daytrade != null ? h.daytrade : h.daytrade_pct;
            margin = h.margin_delta;
          }
        }
        const hi = r.date === day.date ? " style=\"background:rgba(56,189,248,0.08)\"" : "";
        return "<tr" + hi + " data-regime-date=\"" + r.date + "\" style=\"cursor:pointer\">" +
          "<td>" + String(r.date).slice(5) + "</td>" +
          "<td class=\"" + clsSigned(foreign) + "\">" + fmtSigned(foreign) + "</td>" +
          "<td class=\"" + clsSigned(trust) + "\">" + fmtSigned(trust) + "</td>" +
          "<td class=\"" + clsSigned(dealer) + "\">" + fmtSigned(dealer) + "</td>" +
          "<td>" + (daytrade != null && isFinite(Number(daytrade)) ? Number(daytrade).toFixed(1) : "—") + "</td>" +
          "<td class=\"" + clsSigned(margin) + "\">" + fmtSigned(margin) + "</td>" +
          "</tr>";
      }).join("");
    }
  }

  function wireRegimeClicks() {
    const section = document.getElementById("regimeSection");
    if (!section || section._regimeWired) return;
    section._regimeWired = true;
    section.addEventListener("click", function (e) {
      const btn = e.target.closest("[data-regime-date]");
      if (!btn) return;
      const d = btn.getAttribute("data-regime-date");
      if (!d) return;
      regimeViewDate = d;
      renderRegime();
    if (typeof D !== "undefined" && D) loadScreensForDate((D.meta && D.meta.date) || "");

    if (typeof loadScreensForDate === "function") loadScreensForDate((D && D.meta && D.meta.date) || "");
    });
  }

  function renderAll() {
    disposeCharts();
    const meta = document.getElementById("metaLine");
    const m = D.meta || {};
    meta.textContent = (m.title || "台股籌碼資金流") + " ｜ 資料日 " + (m.date || "") + " ｜ " + (m.note || "");
    const badge = document.getElementById("dataBadge");
    if (badge) {
      badge.textContent = "CURATED";
      badge.classList.add("live");
    }
    // Sync regime card to loaded day (unless user is mid-preview — reset on date change)
    regimeViewDate = m.date || dates[dateIdx] || null;
    populateTopicSelect();
    renderKpi();
    renderRegime();
    if (typeof D !== "undefined" && D) loadScreensForDate((D.meta && D.meta.date) || "");

    renderSankey();
    renderSector();
    renderGroupScatter();
    renderTrend();
    renderShort();
    renderLeverage();
    renderForeignHold();
    renderStocksTable();
    renderBrokers();
    renderAlerts();
    updateFilterStat();
    applyLayers();
    updateDateControls();
  }


  function stopSlideshow() {
    slideshowPlaying = false;
    if (slideshowTimer) {
      clearTimeout(slideshowTimer);
      slideshowTimer = null;
    }
    const btn = document.getElementById("btnPlay");
    if (btn) {
      btn.classList.remove("on");
      btn.textContent = "▶ 播放";
    }
  }

  function scheduleNextSlide() {
    if (!slideshowPlaying) return;
    const speedEl = document.getElementById("playSpeed");
    const ms = speedEl ? Number(speedEl.value) || 2500 : 2500;
    slideshowTimer = setTimeout(async function () {
      if (!slideshowPlaying) return;
      if (dateIdx >= dates.length - 1) {
        // loop from start
        dateIdx = -1;
      }
      const next = dates[dateIdx + 1];
      await loadDate(next);
      scheduleNextSlide();
    }, ms);
  }

  function startSlideshow() {
    if (!dates.length) return;
    slideshowPlaying = true;
    const btn = document.getElementById("btnPlay");
    if (btn) {
      btn.classList.add("on");
      btn.textContent = "⏸ 暫停";
    }
    // if already at end, restart from beginning
    if (dateIdx >= dates.length - 1) {
      loadDate(dates[0]).then(scheduleNextSlide);
    } else {
      scheduleNextSlide();
    }
  }

  function toggleSlideshow() {
    if (slideshowPlaying) stopSlideshow();
    else startSlideshow();
  }

  async function loadDate(date) {
    setError("");
    try {
      const res = await fetch("data/curated/" + date + ".json", { cache: "no-store" });
      if (!res.ok) throw new Error("HTTP " + res.status + " loading " + date);
      D = await res.json();
        loadScreensForDate((D.meta && D.meta.date) || "");
      const idx = dates.indexOf(date);
      if (idx >= 0) dateIdx = idx;
      renderAll();
    } catch (err) {
      console.error(err);
      setError("載入失敗：" + (err && err.message ? err.message : String(err)) + "（請用 http server 開啟，勿用 file://）");
    }
  }

  async function boot() {
    document.getElementById("layerToggles").addEventListener("click", function (e) {
      const btn = e.target.closest("button[data-layer]");
      if (!btn) return;
      const key = btn.getAttribute("data-layer");
      layerState[key] = !layerState[key];
      btn.classList.toggle("active", layerState[key]);
      applyLayers();
      resizeAll();
    });
    document.getElementById("btnPrev").addEventListener("click", function () {
      stopSlideshow();
      if (dateIdx > 0) loadDate(dates[dateIdx - 1]);
    });
    document.getElementById("btnNext").addEventListener("click", function () {
      stopSlideshow();
      if (dateIdx < dates.length - 1) loadDate(dates[dateIdx + 1]);
    });
    document.getElementById("dateSelect").addEventListener("change", function (e) {
      stopSlideshow();
      if (e.target.value) loadDate(e.target.value);
    });
    const playBtn = document.getElementById("btnPlay");
    if (playBtn) playBtn.addEventListener("click", toggleSlideshow);
    const speedEl = document.getElementById("playSpeed");
    if (speedEl) speedEl.addEventListener("change", function () {
      if (slideshowPlaying) { stopSlideshow(); startSlideshow(); }
    });
    window.addEventListener("resize", resizeAll);
    function wireFilters() {
      const search = document.getElementById("fltSearch");
      const noEtf = document.getElementById("fltNoEtf");
      const mapped = document.getElementById("fltMappedOnly");
      const topic = document.getElementById("fltTopic");
      const topN = document.getElementById("fltTopN");
      const market = document.getElementById("fltMarket");
      const rulesOnly = document.getElementById("fltRulesOnly");
      const dispRisk = document.getElementById("fltDispRisk");
      const daytradePause = document.getElementById("fltDaytradePause");
      const copyBtn = document.getElementById("btnCopyPack");
      function rerender() {
        if (!D) return;
        disposeCharts();
        renderKpi();
        renderSankey();
        renderSector();
        renderGroupScatter();
        renderTrend();
        renderShort();
        renderLeverage();
        renderForeignHold();
        renderStocksTable();
        renderBrokers();
        renderAlerts();
        updateFilterStat();
        applyLayers();
      }
      if (search) search.addEventListener("input", function () {
        filterState.search = search.value || "";
        rerender();
      });
      if (noEtf) noEtf.addEventListener("change", function () {
        filterState.noEtf = !!noEtf.checked;
        rerender();
      });
      if (mapped) mapped.addEventListener("change", function () {
        filterState.mappedOnly = !!mapped.checked;
        rerender();
      });
      if (topic) topic.addEventListener("change", function () {
        filterState.topicId = topic.value || "";
        rerender();
      });
      if (topN) topN.addEventListener("change", function () {
        filterState.topN = Number(topN.value) || 12;
        rerender();
      });
      if (market) market.addEventListener("change", function () {
        filterState.market = market.value || "all";
        rerender();
      });
      if (rulesOnly) rulesOnly.addEventListener("change", function () {
        filterState.rulesOnly = !!rulesOnly.checked;
        rerender();
      });
      if (dispRisk) dispRisk.addEventListener("change", function () {
        filterState.dispRiskOnly = !!dispRisk.checked;
        rerender();
      });
      if (daytradePause) daytradePause.addEventListener("change", function () {
        filterState.daytradePauseOnly = !!daytradePause.checked;
        rerender();
      });
      if (copyBtn) copyBtn.addEventListener("click", async function () {
        if (!D) return;
        const pack = buildReadingPack();
        const text = JSON.stringify(pack, null, 2);
        try {
          await navigator.clipboard.writeText(text);
          copyBtn.textContent = "已複製";
          setTimeout(function () { copyBtn.textContent = "複製解讀包"; }, 1500);
        } catch (e) {
          setError("無法寫入剪貼簿，請手動從 console 複製");
          console.log(pack);
        }
      });
      const digBtn = document.getElementById("btnCopyDigestMd");
      if (digBtn) digBtn.addEventListener("click", async function () {
        const text = digestMarkdown || "";
        if (!text) { digBtn.textContent = "無內容"; return; }
        try {
          await navigator.clipboard.writeText(text);
          digBtn.textContent = "已複製 MD";
          setTimeout(function () { digBtn.textContent = "複製 Markdown"; }, 1500);
        } catch (e) {
          setError("無法寫入剪貼簿");
        }
      });
    }
    wireFilters();

    try {
      const [idxRes, histRes, regRes] = await Promise.all([
        fetch("data/curated/index.json", { cache: "no-store" }),
        fetch("data/history_kpi.json", { cache: "no-store" }),
        fetch("data/regimes.json", { cache: "no-store" })
      ]);
      if (!idxRes.ok) throw new Error("index.json HTTP " + idxRes.status);
      dates = await idxRes.json();
      if (!Array.isArray(dates) || !dates.length) throw new Error("index.json empty");
      if (histRes.ok) {
        historyKpi = await histRes.json();
      }
      if (regRes.ok) {
        const reg = await regRes.json();
        regimesDays = Array.isArray(reg.days) ? reg.days : [];
        regimeByDate = {};
        regimesDays.forEach(function (d) { regimeByDate[d.date] = d; });
      } else {
        regimesDays = [];
        regimeByDate = {};
      }
      const sel = document.getElementById("dateSelect");
      sel.innerHTML = dates.map(function (d) {
        return "<option value=\"" + d + "\">" + d + "</option>";
      }).join("");
      dateIdx = dates.length - 1;
      await loadDate(dates[dateIdx]);
    } catch (err) {
      console.error(err);
      setError("無法載入 curated index：" + (err && err.message ? err.message : String(err)));
      // optional fallback to MF_SAMPLE
      if (window.MF_SAMPLE) {
        D = window.MF_SAMPLE;
        dates = [D.meta.date];
        dateIdx = 0;
        historyKpi = D.history_kpi || [];
        const sel = document.getElementById("dateSelect");
        if (sel) sel.innerHTML = "<option value=\"" + dates[0] + "\">" + dates[0] + "</option>";
        renderAll();
        setError("curated 載入失敗，已退回 MF_SAMPLE 範例資料");
      }
    }
  }

  boot();
})();
