/**
 * FundFlo shared money-flow formulas (browser).
 * Mirrors etl/fundflo_model.py — see docs/FUNDFLO_CONTRACT.md.
 * Modes: foreign | etf | combined | turnover
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.FundFloModel = factory();
  }
})(typeof self !== 'undefined' ? self : this, function () {
  const WINDOW = 5;

  const BLEND_KEYS = [
    'flow', 'momentum', 'rolling', 'rolling_ret', 'rollingRet',
    'daily_flow', 'dailyFlow', 'daily_ret', 'dailyRet',
    'average5', 'market_share', 'marketShare',
    'turnover_change', 'turnoverChange', 'change_pct', 'changePct',
    'foreign_flow_yi', 'etf_flow_yi', 'shares',
  ];

  const finite = (x) => typeof x === 'number' && Number.isFinite(x);

  const asFloat = (x) => {
    const n = typeof x === 'number' ? x : Number(x);
    return Number.isFinite(n) ? n : null;
  };

  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

  /** Smoothstep ease for fractional-frame playback */
  const ease = (t) => {
    const x = clamp(t, 0, 1);
    return x * x * (3 - 2 * x);
  };

  /** normalize(v,s)=clamp(asinh(v/s)/asinh(3),-1,1) */
  const normalize = (value, scale) => {
    const s = finite(scale) && Math.abs(scale) > 0 ? scale : 1;
    return clamp(Math.asinh(value / s) / Math.asinh(3), -1, 1);
  };

  const sharesFromForeignNetQianzhang = (foreignNet) => Number(foreignNet) * 1e6;

  const foreignFlowYiFromShares = (shares, price) => Number(shares) * Number(price) / 1e8;

  /** Honest curated conversion: foreign_net(千張) * price / 100 */
  const foreignFlowYiFromNet = (foreignNetQianzhang, price) =>
    Number(foreignNetQianzhang) * Number(price) / 100;

  const flowOf = (day, mode = 'foreign') => {
    if (!day) return null;
    if (mode === 'etf') return asFloat(day.etf_flow_yi ?? day.etfFlow);
    if (mode === 'combined') {
      const f = asFloat(day.foreign_flow_yi ?? day.flow);
      const e = asFloat(day.etf_flow_yi ?? day.etfFlow);
      if (f == null && e == null) return null;
      return (f || 0) + (e || 0);
    }
    if (mode === 'turnover') return asFloat(day.amount);
    return asFloat(day.foreign_flow_yi ?? day.flow);
  };

  const rollingSum = (days, start, end, mode) => {
    if (start < 0 || end >= days.length || end - start + 1 !== WINDOW) return null;
    let total = 0;
    for (let i = start; i <= end; i++) {
      const d = days[i];
      if (!d) return null;
      const v = flowOf(d, mode);
      if (v == null) return null;
      total += v;
    }
    return total;
  };

  const rollingRet5d = (days, start, end) => {
    if (start < 1 || end >= days.length) return null;
    const close = asFloat(days[end]?.adjustedClose ?? days[end]?.adj_close ?? days[end]?.close);
    const base = asFloat(days[start - 1]?.adjustedClose ?? days[start - 1]?.adj_close ?? days[start - 1]?.close);
    if (close != null && base != null && base !== 0) return (close / base - 1) * 100;
    let prod = 1;
    for (let i = start; i <= end; i++) {
      const ch = asFloat(days[i]?.change ?? days[i]?.daily_ret);
      if (ch == null) return null;
      prod *= 1 + ch / 100;
    }
    return (prod - 1) * 100;
  };

  const turnoverState = (days, frame) => {
    const end = frame + WINDOW;
    const start = end - WINDOW + 1;
    if (!Array.isArray(days) || end >= days.length || end < 0) return null;
    const today = days[end];
    if (!today) return null;
    let amount = asFloat(today.amount);
    let average5 = asFloat(today.average5 ?? today.average_5);
    let changePct = asFloat(
      today.change_pct ?? today.changePct ?? today.turnover_change ?? today.turnoverChange
    );
    const marketShare = asFloat(today.market_share ?? today.marketShare);
    const dailyRet = asFloat(today.daily_ret ?? today.dailyRet ?? today.return ?? today.change);
    let cumRet = asFloat(
      today.cumulative_return ?? today.cumulativeReturn ?? today.rolling_ret_5d ?? today.rollingRet
    );
    if (cumRet == null && start >= 1) cumRet = rollingRet5d(days, start, end);
    if (amount == null) return null;
    if (changePct == null && average5 != null && average5 !== 0) {
      changePct = (amount / average5 - 1) * 100;
    }
    if (average5 == null && end >= WINDOW) {
      const prior = [];
      for (let i = end - WINDOW; i < end; i++) prior.push(asFloat(days[i]?.amount));
      if (prior.every((v) => v != null)) {
        average5 = prior.reduce((s, v) => s + v, 0) / WINDOW;
        if (changePct == null && average5) changePct = (amount / average5 - 1) * 100;
      }
    }
    return {
      flow: changePct,
      rolling: amount,
      momentum: dailyRet,
      prior_rolling: average5,
      rollingRet: cumRet,
      rolling_ret: cumRet,
      dailyFlow: amount,
      daily_flow: amount,
      dailyRet,
      daily_ret: dailyRet,
      average5,
      marketShare,
      market_share: marketShare,
      turnoverChange: changePct,
      turnover_change: changePct,
      changePct,
      change_pct: changePct,
      foreignFlow: asFloat(today.foreign_flow_yi ?? today.flow),
      foreign_flow_yi: asFloat(today.foreign_flow_yi ?? today.flow),
      etfFlow: asFloat(today.etf_flow_yi ?? today.etfFlow) ?? 0,
      etf_flow_yi: asFloat(today.etf_flow_yi ?? today.etfFlow) ?? 0,
      shares: asFloat(today.shares),
      close: asFloat(today.close),
      start,
      end,
    };
  };

  /**
   * @param {object} stock - { days: [...] } or days array
   * @param {number} frame - 0-based playback frame
   * @param {string} mode - foreign | etf | combined | turnover
   */
  const state = (stock, frame, mode = 'foreign') => {
    const days = stock.days || stock;
    if (mode === 'turnover') return turnoverState(days, frame);
    const end = frame + WINDOW;
    const start = end - WINDOW + 1;
    if (!Array.isArray(days) || end >= days.length || start < 0) return null;
    const windowDays = days.slice(start, end + 1);
    if (windowDays.length !== WINDOW || windowDays.some((d) => !d || !finite(flowOf(d, mode)))) {
      return null;
    }
    const rolling = windowDays.reduce((s, d) => s + flowOf(d, mode), 0);
    const priorWindow = days.slice(start - 1, end);
    const hasPrior =
      priorWindow.length === WINDOW &&
      priorWindow.every((d) => d && finite(flowOf(d, mode)));
    const priorRolling = hasPrior
      ? priorWindow.reduce((s, d) => s + flowOf(d, mode), 0)
      : rolling;
    const today = days[end];
    const foreign = asFloat(today.foreign_flow_yi ?? today.flow);
    const etf = asFloat(today.etf_flow_yi ?? today.etfFlow) ?? 0;
    const ret = rollingRet5d(days, start, end);
    return {
      flow: rolling,
      rolling,
      momentum: rolling - priorRolling,
      prior_rolling: priorRolling,
      rollingRet: ret,
      rolling_ret: ret,
      dailyFlow: flowOf(today, mode),
      daily_flow: flowOf(today, mode),
      dailyRet: asFloat(today.change ?? today.daily_ret),
      daily_ret: asFloat(today.change ?? today.daily_ret),
      foreignFlow: foreign,
      foreign_flow_yi: foreign,
      etfFlow: etf,
      etf_flow_yi: etf,
      combined_flow_yi: foreign == null ? null : foreign + etf,
      shares: asFloat(today.shares),
      close: asFloat(today.close),
      start,
      end,
    };
  };

  /** Blend two state dicts for fractional frame (FundFlo interpolated). */
  const interpolateState = (a, b, t, useEase = true) => {
    if (!a && !b) return null;
    if (!a) return { ...b };
    if (!b) return { ...a };
    const tt = useEase ? ease(t) : clamp(t, 0, 1);
    const out = { ...a };
    const keys = new Set([...Object.keys(a), ...Object.keys(b)]);
    for (const key of keys) {
      const va = a[key];
      const vb = b[key];
      if (finite(va) && finite(vb)) out[key] = va + (vb - va) * tt;
      else if (finite(vb)) out[key] = vb;
      else if (finite(va)) out[key] = va;
      else out[key] = vb != null ? vb : va;
    }
    if (out.rolling_ret != null && out.rollingRet == null) out.rollingRet = out.rolling_ret;
    if (out.rollingRet != null && out.rolling_ret == null) out.rolling_ret = out.rollingRet;
    if (out.turnover_change != null) {
      out.turnoverChange = out.turnover_change;
      out.changePct = out.turnover_change;
      out.change_pct = out.turnover_change;
    }
    if (out.market_share != null) out.marketShare = out.market_share;
    return out;
  };

  const robustScale = (values) => {
    const sorted = values.filter(finite).map(Math.abs).sort((a, b) => a - b);
    if (!sorted.length) return 1;
    return Math.max(sorted[Math.floor(sorted.length * 0.85)] || 1, 0.01);
  };

  const scales = (stocks, mode = 'foreign', frames = [0, 1, 2, 3, 4]) => {
    const states = stocks
      .flatMap((stock) => frames.map((frame) => state(stock, frame, mode)))
      .filter(Boolean);
    // x uses flow (changePct in turnover; rolling in flow modes); y = momentum
    return {
      x: robustScale(states.map((s) => s.flow ?? s.rolling)),
      y: robustScale(states.map((s) => s.momentum)),
      size: Math.max(...states.map((s) => Math.abs(s.rolling)), 1),
    };
  };

  const ranked = (stocks, frame, count, direction = 'both', mode = 'foreign') => {
    const scored = stocks
      .map((stock) => ({ stock, value: state(stock, frame, mode) }))
      .filter(({ value }) => {
        if (!value) return false;
        if (mode === 'turnover') {
          const field =
            direction === 'surge' ? 'turnoverChange' : direction === 'share' ? 'marketShare' : 'rolling';
          return finite(value[field]);
        }
        if (direction === 'buy') return value.rolling > 0;
        if (direction === 'sell') return value.rolling < 0;
        return true;
      });
    scored.sort((a, b) => {
      if (mode === 'turnover') {
        const field =
          direction === 'surge' ? 'turnoverChange' : direction === 'share' ? 'marketShare' : 'rolling';
        return b.value[field] - a.value[field];
      }
      if (direction === 'buy') return b.value.rolling - a.value.rolling;
      if (direction === 'sell') return a.value.rolling - b.value.rolling;
      return Math.abs(b.value.rolling) - Math.abs(a.value.rolling);
    });
    return scored.slice(0, count).map(({ stock, value }) => ({ stock, state: value }));
  };

  /** Attach rolling_* fields for a chronological daily series (ETL / consumer). */
  const enrichDayMetrics = (history) => {
    return history.map((day, i) => {
      const row = { ...day };
      const foreign = asFloat(row.foreign_flow_yi);
      const etf = asFloat(row.etf_flow_yi) ?? 0;
      row.etf_flow_yi = etf;
      if (foreign != null) row.combined_flow_yi = foreign + etf;
      const end = i;
      const start = end - WINDOW + 1;
      if (start < 0) return row;
      for (const [mode, rkey, mkey] of [
        ['foreign', 'rolling_foreign_5d_yi', 'momentum_foreign_5d_yi'],
        ['etf', 'rolling_etf_5d_yi', 'momentum_etf_5d_yi'],
        ['combined', 'rolling_combined_5d_yi', 'momentum_combined_5d_yi'],
      ]) {
        const rolling = rollingSum(history, start, end, mode);
        if (rolling == null) continue;
        const prior = rollingSum(history, start - 1, end - 1, mode);
        const priorRolling = prior == null ? rolling : prior;
        row[rkey] = rolling;
        row[mkey] = rolling - priorRolling;
      }
      const ret = rollingRet5d(history, start, end);
      if (ret != null) {
        row.rolling_ret_5d = ret;
        if (row.cumulative_return == null && row.cumulativeReturn == null) {
          row.cumulative_return = ret;
        }
      }
      return row;
    });
  };

  return {
    WINDOW,
    BLEND_KEYS,
    normalize,
    clamp,
    ease,
    flowOf,
    state,
    interpolateState,
    scales,
    ranked,
    rollingSum,
    rollingRet5d,
    enrichDayMetrics,
    robustScale,
    sharesFromForeignNetQianzhang,
    foreignFlowYiFromShares,
    foreignFlowYiFromNet,
  };
});
