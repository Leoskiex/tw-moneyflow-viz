#!/usr/bin/env python3
"""
Build curated day JSON for tw-moneyflow-viz from TWSE raw + TW topic map.

Units (documented in viz README / DATE_SWITCH.md):
  - market_kpi foreign/trust/dealer: 億元 (BFI82U 元 / 1e8)
  - market_kpi total_amount: 億元 (MI_INDEX / FMTQIK)
  - market_kpi margin_balance / margin_delta: 億元 (MI_MARGN 融資金額 仟元 / 1e5)
  - market_kpi short_balance: 千張 (融券交易單位 / 1000)
  - market_kpi daytrade_pct: % (TWTB4U 金額占市場比重)
  - stock foreign/trust/dealer/inst_net: 千張 (T86 股數 / 1e6)  — share-based
  - stock amount: 億元 (MI_INDEX 成交金額 / 1e8)
  - stock margin_delta: 張; margin_util: 餘額/限額
  - stock short_sell / sbl_sell: 張 (TWTASU 數量); short_util: (融券+借券餘額)/限額
"""
from __future__ import annotations

import json
import math
import os
import re
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional

from overlay_rules import enrich_stocks_with_rules, top_brokers_from_docs, parse_notice

RAW_DIR = Path("/workspace/twse-trading/raw")
TOPIC_PATH = Path("/workspace/aistockmap/topics/TW_TOPIC_MEMBERS.json")
OUT_DIR = Path("/workspace/tw-moneyflow-viz/data/curated")
HISTORY_PATH = Path("/workspace/tw-moneyflow-viz/data/history_kpi.json")
TOP_N = 40  # default Sankey/chart top-N hint only; curated now keeps ALL stocks

def classify_instrument(code: str, name: str) -> dict:
    """Flag ETF / leverage-inverse so the viz can filter them out of theme stories."""
    c = (code or "").strip().upper()
    n = name or ""
    is_lev = bool(
        re.search(r"[LR]$", c)
        or ("正2" in n)
        or ("反1" in n)
        or ("槓桿" in n)
        or ("反向" in n)
    )
    is_etf = bool(
        c.startswith("00")
        or c.startswith("009")
        or ("ETF" in n.upper())
        or ("指數股票型" in n)
        or ("主動" in n and c.startswith("00"))
        or is_lev
    )
    # plain common stock heuristic: 4-digit numeric (or 4-digit + letter A for preferred)
    is_common = bool(re.match(r"^\d{4}[A-Z]?$", c)) and not is_etf
    return {
        "is_etf": is_etf,
        "is_leverage": is_lev,
        "is_common": is_common or (not is_etf and not is_lev),
        "mapped": False,  # filled later
    }

# Preferred primary topic id when a stock sits in multiple topics.
# First match wins; else first membership in map iteration order.
PREFERRED_TOPIC_BY_CODE = {
    "2330": "wafer-foundry",
    "2303": "wafer-foundry",
    "3711": "cowos-advanced-packaging",
    "2454": "hpc-network-ic",
    "2308": "liquid_cooling_advanced",
    "3037": "ic-substrate",
    "2344": "niche-memory",
    "2603": "container-shipping",
}
# ODM / AI-server assemblers — prefer ai-server-odm when present
ODM_CODES = {
    "2317", "2324", "2356", "2382", "3231", "6669", "3017", "2353",
    "2376", "2395", "3706", "4938", "2357",
}
PREFERRED_TOPIC_IDS_ORDER = [
    "wafer-foundry",
    "ai-server-odm",
    "cowos-advanced-packaging",
    "hpc-network-ic",
    "ic-substrate",
    "liquid_cooling_advanced",
    "niche-memory",
    "container-shipping",
    "hbm",
    "silicon-photonics",
]


def num(x: Any) -> Optional[float]:
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip()
    if not s or s in {"-", "--", "---", "N/A", "null"}:
        return None
    s = s.replace(",", "").replace("%", "")
    # strip HTML
    s = re.sub(r"<[^>]+>", "", s)
    s = s.strip()
    if not s or s in {"+", "-"}:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def load_json(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"  warn: fail read {path}: {e}")
        return None


def parse_adv_dec(cell: str) -> int:
    """'762(15)' -> 762"""
    if not cell:
        return 0
    s = str(cell).replace(",", "").strip()
    m = re.match(r"(\d+)", s)
    return int(m.group(1)) if m else 0


def change_sign(html_or_text: str) -> int:
    s = str(html_or_text or "")
    if "green" in s or "－" in s or "−" in s:
        # TWSE uses green for down sometimes; also check for -
        pass
    if re.search(r"color\s*:\s*green", s, re.I) or "color:green" in s.replace(" ", "").lower():
        return -1
    if "－" in s or "−" in s:
        return -1
    # red = up
    if re.search(r"color\s*:\s*red", s, re.I) or "+" in re.sub(r"<[^>]+>", "", s):
        return 1
    plain = re.sub(r"<[^>]+>", "", s).strip()
    if plain.startswith("-") or plain.startswith("－"):
        return -1
    if plain.startswith("+"):
        return 1
    return 0


def build_topic_index(topics: dict) -> dict:
    """code -> list of (topicId, shortname, group, name)"""
    idx = defaultdict(list)
    for tid, info in topics.items():
        short = info.get("shortname") or info.get("name") or tid
        group = info.get("group") or "其他"
        name = info.get("name") or short
        for c in info.get("companies") or []:
            code = str(c.get("code", "")).strip()
            if code:
                idx[code].append((tid, short, group, name))
    return idx


def pick_primary(code: str, memberships: list) -> tuple:
    if not memberships:
        return ("unmapped", "未對應", "其他", "未對應")
    ids = {m[0] for m in memberships}
    if code in PREFERRED_TOPIC_BY_CODE and PREFERRED_TOPIC_BY_CODE[code] in ids:
        want = PREFERRED_TOPIC_BY_CODE[code]
        for m in memberships:
            if m[0] == want:
                return m
    if code in ODM_CODES and "ai-server-odm" in ids:
        for m in memberships:
            if m[0] == "ai-server-odm":
                return m
    for pref in PREFERRED_TOPIC_IDS_ORDER:
        if pref in ids:
            for m in memberships:
                if m[0] == pref:
                    return m
    return memberships[0]


def parse_bfi82u(doc: Optional[dict]) -> dict:
    out = {"foreign_net": 0.0, "trust_net": 0.0, "dealer_net": 0.0}
    if not doc or doc.get("stat") not in ("OK", "ok"):
        return out
    dealer = 0.0
    for row in doc.get("data") or []:
        if len(row) < 4:
            continue
        name = str(row[0]).strip()
        net = num(row[3]) or 0.0
        yi = net / 1e8  # 元 → 億
        if "外資及陸資" in name or (name.startswith("外資") and "自營" not in name):
            out["foreign_net"] += yi
        elif name == "外資自營商":
            out["foreign_net"] += yi
        elif "投信" in name:
            out["trust_net"] = yi
        elif "自營商" in name:
            dealer += yi
        elif name == "合計":
            pass
    out["dealer_net"] = dealer
    # round
    for k in out:
        out[k] = round(out[k], 2)
    return out


def parse_mi_index_kpi(doc: Optional[dict]) -> dict:
    out = {
        "total_amount": None,
        "advance": None,
        "decline": None,
        "unchanged": None,
        "quotes": {},  # code -> {name, change, amount, close}
    }
    if not doc or doc.get("stat") not in ("OK", "ok"):
        return out
    tables = doc.get("tables") or []
    for t in tables:
        title = t.get("title") or ""
        fields = t.get("fields") or []
        data = t.get("data") or []
        if "漲跌證券數" in title or fields[:1] == ["類型"]:
            for row in data:
                if not row:
                    continue
                label = str(row[0])
                # prefer 股票 column if present (index 2), else 整體市場
                col = row[2] if len(row) > 2 else (row[1] if len(row) > 1 else "0")
                if label.startswith("上漲"):
                    out["advance"] = parse_adv_dec(col)
                elif label.startswith("下跌"):
                    out["decline"] = parse_adv_dec(col)
                elif label.startswith("持平"):
                    out["unchanged"] = parse_adv_dec(col)
        if "成交統計" in (fields[0] if fields else "") or "大盤統計" in title:
            for row in data:
                if row and "總計" in str(row[0]):
                    amt = num(row[1])
                    if amt is not None:
                        out["total_amount"] = round(amt / 1e8, 2)
            # fallback: sum 一般股票 + ETF if no 總計
            if out["total_amount"] is None:
                total = 0.0
                found = False
                for row in data:
                    lab = str(row[0])
                    if "一般股票" in lab or lab.strip().startswith("1."):
                        a = num(row[1])
                        if a is not None:
                            total += a
                            found = True
                    if "ETF" in lab:
                        a = num(row[1])
                        if a is not None:
                            total += a
                            found = True
                if found:
                    out["total_amount"] = round(total / 1e8, 2)
        # daily quotes table
        if fields and fields[0] == "證券代號" and "成交金額" in fields:
            # map field names
            fi = {f: i for i, f in enumerate(fields)}
            for row in data:
                code = str(row[0]).strip()
                if not code or not code[0].isdigit():
                    continue
                name = str(row[fi.get("證券名稱", 1)]).strip()
                amount = num(row[fi["成交金額"]]) if "成交金額" in fi else None
                close = num(row[fi["收盤價"]]) if "收盤價" in fi else None
                diff = num(row[fi["漲跌價差"]]) if "漲跌價差" in fi else None
                sign_cell = row[fi["漲跌(+/-)"]] if "漲跌(+/-)" in fi else ""
                chg = None
                if close and close > 0 and diff is not None:
                    sgn = change_sign(sign_cell)
                    # if sign unclear, infer from HTML color already in change_sign
                    signed_diff = abs(diff) * (sgn if sgn != 0 else 1)
                    # If no sign detected but plain negative in diff? diff is abs usually
                    if sgn == 0:
                        # try previous close approx: if red/green missing, leave unsigned as +
                        signed_diff = diff
                    chg = round(signed_diff / (close - signed_diff) * 100, 2) if (close - signed_diff) else 0.0
                    # Better: percent from 漲跌百分比 if available — not in this table.
                    # change % = signed_diff / (close - signed_diff) * 100
                out["quotes"][code] = {
                    "name": name,
                    "amount": round(amount / 1e8, 2) if amount is not None else None,
                    "close": close,
                    "change": chg,
                    "diff": diff,
                    "sign": change_sign(sign_cell),
                }
                # recompute change with sign
                q = out["quotes"][code]
                if q["close"] and q["diff"] is not None:
                    sgn = q["sign"] if q["sign"] != 0 else 1
                    signed = abs(q["diff"]) * sgn
                    prev = q["close"] - signed
                    q["change"] = round(signed / prev * 100, 2) if prev else 0.0
    return out


def parse_fmtqik_amount(doc: Optional[dict], date: str) -> Optional[float]:
    """Fallback total amount from FMTQIK for the day (億)."""
    if not doc or not doc.get("data"):
        return None
    # date is YYYY-MM-DD; FMTQIK uses roc 115/09/04
    y, m, d = date.split("-")
    roc = f"{int(y) - 1911}/{m}/{d}"
    for row in doc["data"]:
        if str(row[0]).strip() == roc:
            amt = num(row[2])
            return round(amt / 1e8, 2) if amt is not None else None
    # last row fallback
    amt = num(doc["data"][-1][2])
    return round(amt / 1e8, 2) if amt is not None else None


def parse_margin_market(doc: Optional[dict]) -> dict:
    out = {"margin_balance": None, "short_balance": None, "margin_delta": None}
    if not doc:
        return out
    tables = doc.get("tables") or []
    if not tables:
        return out
    t0 = tables[0]
    for row in t0.get("data") or []:
        if not row:
            continue
        label = str(row[0])
        # 融資金額(仟元): 前日=row[4], 今日=row[5]
        if "融資金額" in label:
            prev = num(row[4])
            today = num(row[5])
            if today is not None:
                out["margin_balance"] = round(today / 1e5, 2)  # 仟元 → 億
            if today is not None and prev is not None:
                out["margin_delta"] = round((today - prev) / 1e5, 2)
        elif label.startswith("融券") and "交易單位" in label:
            today = num(row[5])
            if today is not None:
                out["short_balance"] = round(today / 1000.0, 2)  # 張 → 千張
    return out


def parse_margin_stocks(doc: Optional[dict]) -> dict:
    """code -> {margin_delta, margin_util, margin_bal, short_bal}"""
    out = {}
    if not doc:
        return out
    tables = doc.get("tables") or []
    if len(tables) < 2:
        return out
    t1 = tables[1]
    for row in t1.get("data") or []:
        if not row or len(row) < 14:
            continue
        code = str(row[0]).strip()
        if not code or not re.match(r"^\d{4}", code):
            continue
        # 融資: 買進2 賣出3 現金4 前日5 今日6 限額7
        # 融券: 買進8 賣出9 現券10 前日11 今日12 限額13
        m_prev, m_today, m_limit = num(row[5]), num(row[6]), num(row[7])
        s_today, s_limit = num(row[12]), num(row[13])
        margin_delta = None
        if m_today is not None and m_prev is not None:
            margin_delta = m_today - m_prev
        margin_util = None
        if m_today is not None and m_limit and m_limit > 0:
            margin_util = round(m_today / m_limit, 4)
        out[code] = {
            "margin_delta": margin_delta,
            "margin_util": margin_util,
            "margin_bal": m_today,
            "short_bal_margin": s_today,
        }
    return out


def parse_twtasu(doc: Optional[dict]) -> dict:
    """code -> {short_sell, sbl_sell} in 張"""
    out = {}
    if not doc or not doc.get("data"):
        return out
    for row in doc["data"]:
        if not row:
            continue
        head = str(row[0]).strip()
        # "2330   台積電"
        m = re.match(r"^(\d{4,6}\w?)\s+", head)
        if not m:
            m = re.match(r"^(\d{4,6}\w?)$", head)
        if not m:
            continue
        code = m.group(1)
        short_sell = num(row[1])  # 融券賣出數量
        sbl_sell = num(row[3]) if len(row) > 3 else None  # 借券賣出數量
        out[code] = {
            "short_sell": short_sell or 0.0,
            "sbl_sell": sbl_sell or 0.0,
        }
    return out


def parse_twt93u(doc: Optional[dict]) -> dict:
    """code -> short_util"""
    out = {}
    if not doc or not doc.get("data"):
        return out
    for row in doc["data"]:
        if not row or len(row) < 14:
            continue
        code = str(row[0]).strip()
        if not re.match(r"^\d{4}", code):
            continue
        # 融券今日餘額 idx6, 融券限額 idx7 (may be huge shares)
        # 借券當日餘額 idx12, 借券限額 idx13
        short_bal = num(row[6]) or 0.0
        short_limit = num(row[7]) or 0.0
        sbl_bal = num(row[12]) or 0.0
        sbl_limit = num(row[13]) or 0.0
        # limits in this API often in shares; balances in shares too for 借券.
        # 融券餘額 appears in shares (26000 for 2330 = 26張*1000?).
        # Use (short_bal + sbl_bal) / max(short_limit, sbl_limit) carefully.
        # For util: 融券餘額/融券限額 if limit looks like 張-scale matching.
        util = None
        if short_limit > 0:
            util = short_bal / short_limit
        if sbl_limit > 0:
            u2 = sbl_bal / sbl_limit
            util = max(util or 0, u2)
        # Also combine if same scale
        if short_limit > 0 and sbl_limit > 0 and abs(short_limit - sbl_limit) / max(short_limit, 1) < 0.01:
            util = (short_bal + sbl_bal) / short_limit
        out[code] = {
            "short_util": round(util, 4) if util is not None else None,
            "short_bal": short_bal,
            "sbl_bal": sbl_bal,
        }
    return out


def parse_twtb4u_pct(doc: Optional[dict]) -> Optional[float]:
    if not doc:
        return None
    tables = doc.get("tables") or []
    if not tables:
        return None
    data = tables[0].get("data") or []
    if not data:
        return None
    # 當日沖銷交易總買進成交金額占市場比重% at index 3
    row = data[0]
    pct = num(row[3]) if len(row) > 3 else None
    return pct


def parse_t86(doc: Optional[dict]) -> list:
    """Return list of stock dicts with nets in 千張."""
    rows = []
    if not doc or not doc.get("data"):
        return rows
    fields = doc.get("fields") or []
    # indices by name when possible
    def idx(name, default):
        try:
            return fields.index(name)
        except ValueError:
            return default

    i_code = 0
    i_name = 1
    i_f = idx("外陸資買賣超股數(不含外資自營商)", 4)
    i_fd = idx("外資自營商買賣超股數", 7)
    i_t = idx("投信買賣超股數", 10)
    i_d = idx("自營商買賣超股數", 11)
    i_all = idx("三大法人買賣超股數", 18)

    for row in doc["data"]:
        if not row:
            continue
        code = str(row[i_code]).strip()
        if not re.match(r"^\d{4}", code):
            continue
        # skip ETFs roughly (00xx often)
        name = str(row[i_name]).strip()
        f = (num(row[i_f]) or 0.0) + (num(row[i_fd]) or 0.0)
        t = num(row[i_t]) or 0.0
        d = num(row[i_d]) or 0.0
        inst = num(row[i_all])
        if inst is None:
            inst = f + t + d
        # 股數 → 千張 (1千張 = 1e6 股)
        rows.append({
            "code": code,
            "name": name,
            "foreign_net": round(f / 1e6, 3),
            "trust_net": round(t / 1e6, 3),
            "dealer_net": round(d / 1e6, 3),
            "inst_net": round(inst / 1e6, 3),
        })
    return rows


def parse_bfiamu(doc: Optional[dict]) -> list:
    sectors = []
    if not doc or not doc.get("data"):
        return sectors
    for row in doc["data"]:
        if not row:
            continue
        name = str(row[0]).strip().replace("類指數", "").strip()
        amount = num(row[2])
        chg = num(row[4]) if len(row) > 4 else None
        sectors.append({
            "name": name,
            "amount": round(amount / 1e8, 2) if amount is not None else None,
            "change_pct": chg,
            "inst_net": None,  # filled later if we map; else leave
            "foreign_net": 0,
            "trust_net": 0,
            "dealer_net": 0,
            "amount_vs_20d": 1.0,
            "vs20": 1.0,
            "margin_delta": 0,
        })
    return sectors


def build_alerts(stocks: list) -> list:
    alerts = []
    for s in stocks:
        mu = s.get("margin_util")
        su = s.get("short_util")
        topic = s.get("topic") or ""
        if mu is not None and mu >= 0.7:
            alerts.append({
                "level": "高" if mu >= 0.8 else "中",
                "code": s["code"],
                "name": s["name"],
                "type": "槓桿偏高",
                "message": f"融資使用率 {mu*100:.0f}%｜題材：{topic}",
                "value": f"融資利用率 {mu*100:.0f}%",
            })
        if su is not None and su >= 0.5:
            alerts.append({
                "level": "高" if su >= 0.6 else "中",
                "code": s["code"],
                "name": s["name"],
                "type": "空單壓力",
                "message": f"空單使用率偏高｜題材：{topic}",
                "value": f"空單利用率 {su*100:.0f}%",
            })
        if (s.get("foreign_net") or 0) <= -5:
            alerts.append({
                "level": "低",
                "code": s["code"],
                "name": s["name"],
                "type": "外資賣超",
                "message": f"外資淨賣超偏大｜題材：{topic}",
                "value": f"{s['foreign_net']:+.2f} 千張",
            })
        if (s.get("margin_delta") or 0) >= 2000 and (s.get("change") or 0) > 2:
            alerts.append({
                "level": "中",
                "code": s["code"],
                "name": s["name"],
                "type": "漲幅＋融資",
                "message": f"漲幅與融資同步上升｜題材：{topic}",
                "value": f"{s.get('change'):+.2f}% / 融資{s['margin_delta']:+.0f}張",
            })
    # dedupe by code+type, keep higher level
    rank = {"高": 0, "中": 1, "低": 2}
    alerts.sort(key=lambda a: (rank.get(a["level"], 9), a["code"]))
    seen = set()
    uniq = []
    for a in alerts:
        k = (a["code"], a["type"])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(a)
    return uniq[:25]



def parse_mi_qfiis(doc: Optional[dict]) -> dict:
    """code -> foreign holdings (pct / shares)."""
    out = {}
    if not doc or str(doc.get("stat", "")).upper() != "OK":
        return out
    for row in doc.get("data") or []:
        if not row or len(row) < 8:
            continue
        code = str(row[0]).strip()
        hold_pct = num(row[7])  # 全體外資及陸資持股比率
        avail_pct = num(row[6])
        limit_pct = num(row[8]) if len(row) > 8 else None
        hold_shares = num(row[5])
        out[code] = {
            "foreign_hold_pct": round(hold_pct, 2) if hold_pct is not None else None,
            "foreign_avail_pct": round(avail_pct, 2) if avail_pct is not None else None,
            "foreign_limit_pct": round(limit_pct, 2) if limit_pct is not None else None,
            "foreign_hold_shares": hold_shares,
        }
    return out


def parse_mi_qfiis_cat(doc) -> list:
    if not isinstance(doc, list):
        return []
    rows = []
    for r in doc:
        rows.append({
            "industry": r.get("IndustryCat"),
            "n": num(r.get("Numbers")) or 0,
            "foreign_hold_pct": num(r.get("Percentage")),
        })
    return rows


def parse_tpex_3i(doc: Optional[dict]) -> list:
    """TPEx institutional nets in 千張. Use aggregate columns to avoid double-count."""
    rows = []
    if not doc or str(doc.get("stat", "")).lower() != "ok":
        return rows
    tables = doc.get("tables") or []
    if not tables:
        return rows
    data = tables[0].get("data") or []
    # cols: 0 code, 1 name,
    # 8-10 外資及陸資合計, 11-13 投信, 20-22 自營商合計, 23 三大法人合計
    for row in data:
        if not row or len(row) < 24:
            continue
        code = str(row[0]).strip()
        name = str(row[1]).strip()
        f = num(row[10]) or 0.0
        tnet = num(row[13]) or 0.0
        d = num(row[22]) or 0.0
        inst = num(row[23])
        if inst is None:
            inst = f + tnet + d
        rows.append({
            "code": code,
            "name": name,
            "foreign_net": round(f / 1e6, 3),
            "trust_net": round(tnet / 1e6, 3),
            "dealer_net": round(d / 1e6, 3),
            "inst_net": round(inst / 1e6, 3),
            "market": "tpex",
        })
    return rows


def parse_tpex_3i_sum(doc: Optional[dict]) -> dict:
    """Market KPI for TPEx in 億元."""
    out = {"foreign_net": 0.0, "trust_net": 0.0, "dealer_net": 0.0, "total_net": 0.0}
    if not doc or str(doc.get("stat", "")).lower() != "ok":
        return out
    tables = doc.get("tables") or []
    if not tables:
        return out
    for row in tables[0].get("data") or []:
        if not row:
            continue
        name = str(row[0]).replace("\u3000", "").replace("　", "").strip()
        net = (num(row[3]) or 0.0) / 1e8
        if name == "外資及陸資合計":
            out["foreign_net"] = round(net, 2)
        elif name == "投信":
            out["trust_net"] = round(net, 2)
        elif name == "自營商合計":
            out["dealer_net"] = round(net, 2)
        elif name.startswith("三大法人合計"):
            out["total_net"] = round(net, 2)
    return out


def parse_tpex_margin(doc: Optional[dict]) -> dict:
    """code -> margin_delta (張) / margin_util."""
    out = {}
    if not doc or str(doc.get("stat", "")).lower() != "ok":
        return out
    tables = doc.get("tables") or []
    if not tables:
        return out
    for row in tables[0].get("data") or []:
        if not row or len(row) < 10:
            continue
        code = str(row[0]).strip()
        prev = num(row[2]) or 0.0
        bal = num(row[6]) or 0.0
        util = num(row[8])
        out[code] = {
            "margin_delta": round(bal - prev, 1),
            "margin_util": round((util or 0.0) / 100.0, 4) if util is not None else 0.0,
            "margin_bal": bal,
        }
    return out



def build_notice_history_map(date: str, all_dates: list, lookback: int = 10) -> dict:
    """Load NOTICE.json for up to `lookback` trading days ending at `date` → {day: {code: dict|True}}."""
    days = [d for d in all_dates if d <= date][-lookback:]
    out = {}
    for d in days:
        doc = load_json(RAW_DIR / d / "NOTICE.json")
        if not doc:
            continue
        m = parse_notice(doc)
        if m:
            out[d] = m
    return out


def build_day(date: str, topic_idx: dict, topics_meta: dict, all_dates: Optional[list] = None) -> Optional[dict]:
    day_dir = RAW_DIR / date
    if not day_dir.is_dir():
        return None

    bfi = load_json(day_dir / "BFI82U.json")
    t86 = load_json(day_dir / "T86.json")
    mi = load_json(day_dir / "MI_INDEX.json")
    margn = load_json(day_dir / "MI_MARGN_ALL.json") or load_json(day_dir / "MI_MARGN_MS.json")
    tasu = load_json(day_dir / "TWTASU.json")
    t93 = load_json(day_dir / "TWT93U.json")
    tb4 = load_json(day_dir / "TWTB4U.json")
    bfi_amu = load_json(day_dir / "BFIAMU.json")
    fmt = load_json(day_dir / "FMTQIK.json")
    qfiis = load_json(day_dir / "MI_QFIIS.json")
    tpex_3i = load_json(day_dir / "TPEX_3I.json")
    tpex_sum = load_json(day_dir / "TPEX_3I_SUM.json")
    tpex_mgn = load_json(day_dir / "TPEX_MARGIN.json")
    qfiis_cat = load_json(RAW_DIR / "shared" / "MI_QFIIS_cat.json")
    twt96 = load_json(RAW_DIR / "shared" / "TWT96U.json")
    bfi84 = load_json(RAW_DIR / "shared" / "BFI84U.json")
    notice = load_json(day_dir / "NOTICE.json")
    punish_doc = None
    shared = RAW_DIR / "shared"
    if shared.is_dir():
        for pp in sorted(shared.glob("PUNISH_*.json")):
            punish_doc = load_json(pp)
            if punish_doc:
                break
    tpex_disposal = load_json(shared / "TPEX_DISPOSAL.json")
    twtbau1 = load_json(shared / "TWTBAU1.json")
    twtbau2 = load_json(shared / "TWTBAU2.json")
    twtb4u_oa = load_json(shared / "TWTB4U.json")
    tpex_warn = load_json(shared / "TPEX_WARNING.json")
    tpex_warn_note = load_json(shared / "TPEX_WARNING_NOTE.json")
    tpex_cmode = load_json(shared / "TPEX_CMODE.json")
    tpex_broker1 = load_json(shared / "TPEX_BROKER1.json")
    tpex_broker2 = load_json(shared / "TPEX_BROKER2.json")
    notice_history_map = build_notice_history_map(date, all_dates or [date], lookback=10)

    # Need at least T86 or BFI82U
    if not t86 and not bfi:
        print(f"  skip {date}: no T86/BFI82U")
        return None

    kpi_inst = parse_bfi82u(bfi)
    mi_kpi = parse_mi_index_kpi(mi)
    marg_mkt = parse_margin_market(margn)
    daytrade = parse_twtb4u_pct(tb4)

    total_amount = mi_kpi["total_amount"]
    if total_amount is None:
        total_amount = parse_fmtqik_amount(fmt, date)

    market_kpi = {
        "foreign_net": kpi_inst["foreign_net"],
        "trust_net": kpi_inst["trust_net"],
        "dealer_net": kpi_inst["dealer_net"],
        "total_amount": total_amount if total_amount is not None else 0.0,
        "advance": mi_kpi["advance"] if mi_kpi["advance"] is not None else 0,
        "decline": mi_kpi["decline"] if mi_kpi["decline"] is not None else 0,
        "unchanged": mi_kpi["unchanged"] if mi_kpi["unchanged"] is not None else 0,
        "margin_balance": marg_mkt["margin_balance"] if marg_mkt["margin_balance"] is not None else 0.0,
        "short_balance": marg_mkt["short_balance"] if marg_mkt["short_balance"] is not None else 0.0,
        "margin_delta": marg_mkt["margin_delta"] if marg_mkt["margin_delta"] is not None else 0.0,
        "daytrade_pct": daytrade,
    }

    marg_stocks = parse_margin_stocks(margn)
    short_day = parse_twtasu(tasu)
    short_util = parse_twt93u(t93)
    quotes = mi_kpi["quotes"]

    t86_rows = parse_t86(t86)
    t86_rows.sort(key=lambda r: abs(r["inst_net"]), reverse=True)
    qfiis_map = parse_mi_qfiis(qfiis)
    tpex_rows = parse_tpex_3i(tpex_3i)
    tpex_rows.sort(key=lambda r: abs(r["inst_net"]), reverse=True)
    tpex_kpi = parse_tpex_3i_sum(tpex_sum)
    tpex_margin_map = parse_tpex_margin(tpex_mgn)
    foreign_cat = parse_mi_qfiis_cat(qfiis_cat)

    market_kpi["tpex_foreign_net"] = tpex_kpi.get("foreign_net", 0.0)
    market_kpi["tpex_trust_net"] = tpex_kpi.get("trust_net", 0.0)
    market_kpi["tpex_dealer_net"] = tpex_kpi.get("dealer_net", 0.0)
    market_kpi["tpex_total_net"] = tpex_kpi.get("total_net", 0.0)
    # combined (上市+上櫃) for quick read — note different venues
    market_kpi["all_foreign_net"] = round(market_kpi["foreign_net"] + market_kpi["tpex_foreign_net"], 2)
    market_kpi["all_trust_net"] = round(market_kpi["trust_net"] + market_kpi["tpex_trust_net"], 2)
    market_kpi["all_dealer_net"] = round(market_kpi["dealer_net"] + market_kpi["tpex_dealer_net"], 2)

    stocks = []
    for r in t86_rows:  # TWSE full market
        code = r["code"]
        tid, short, group, tname = pick_primary(code, topic_idx.get(code, []))
        q = quotes.get(code) or {}
        ms = marg_stocks.get(code) or {}
        sd = short_day.get(code) or {}
        su = short_util.get(code) or {}
        name = q.get("name") or r["name"]
        flags = classify_instrument(code, name)
        flags["mapped"] = tid != "unmapped"
        qf = qfiis_map.get(code) or {}
        stocks.append({
            "code": code,
            "name": name,
            "market": "twse",
            "topic": short,
            "topicId": tid,
            "topicName": tname,
            "group": group,
            "change": q.get("change") if q.get("change") is not None else 0.0,
            "amount": q.get("amount") if q.get("amount") is not None else 0.0,
            "foreign_net": r["foreign_net"],
            "trust_net": r["trust_net"],
            "dealer_net": r["dealer_net"],
            "inst_net": r["inst_net"],
            "margin_delta": ms.get("margin_delta") if ms.get("margin_delta") is not None else 0.0,
            "margin_util": ms.get("margin_util") if ms.get("margin_util") is not None else 0.0,
            "short_sell": sd.get("short_sell") if sd.get("short_sell") is not None else 0.0,
            "sbl_sell": sd.get("sbl_sell") if sd.get("sbl_sell") is not None else 0.0,
            "short_util": su.get("short_util") if su.get("short_util") is not None else 0.0,
            "foreign_hold_pct": qf.get("foreign_hold_pct"),
            "foreign_avail_pct": qf.get("foreign_avail_pct"),
            "foreign_limit_pct": qf.get("foreign_limit_pct"),
            **flags,
        })

    # Append TPEx rows
    for r in tpex_rows:
        code = r["code"]
        tid, short, group, tname = pick_primary(code, topic_idx.get(code, []))
        ms = tpex_margin_map.get(code) or {}
        name = r["name"]
        flags = classify_instrument(code, name)
        flags["mapped"] = tid != "unmapped"
        # QFIIS is TWSE-listed; OTC usually absent — leave null
        qf = qfiis_map.get(code) or {}
        stocks.append({
            "code": code,
            "name": name,
            "market": "tpex",
            "topic": short,
            "topicId": tid,
            "topicName": tname,
            "group": group,
            "change": 0.0,
            "amount": 0.0,
            "foreign_net": r["foreign_net"],
            "trust_net": r["trust_net"],
            "dealer_net": r["dealer_net"],
            "inst_net": r["inst_net"],
            "margin_delta": ms.get("margin_delta") if ms.get("margin_delta") is not None else 0.0,
            "margin_util": ms.get("margin_util") if ms.get("margin_util") is not None else 0.0,
            "short_sell": 0.0,
            "sbl_sell": 0.0,
            "short_util": 0.0,
            "foreign_hold_pct": qf.get("foreign_hold_pct"),
            "foreign_avail_pct": qf.get("foreign_avail_pct"),
            "foreign_limit_pct": qf.get("foreign_limit_pct"),
            **flags,
        })
    # Re-rank combined universe by |inst_net|
    stocks.sort(key=lambda s: abs(s.get("inst_net") or 0), reverse=True)

    # topics aggregate from top stocks (and optionally all T86 for better agg — use all for topics/groups)
    # Re-map ALL t86 for aggregation richness
    all_mapped = []
    for r in t86_rows:
        code = r["code"]
        tid, short, group, tname = pick_primary(code, topic_idx.get(code, []))
        q = quotes.get(code) or {}
        ms = marg_stocks.get(code) or {}
        all_mapped.append({
            **r,
            "topicId": tid,
            "topic": short,
            "topicName": tname,
            "group": group,
            "change": q.get("change"),
            "amount": q.get("amount") or 0.0,
            "margin_delta": ms.get("margin_delta") or 0.0,
        })
    for r in tpex_rows:
        code = r["code"]
        tid, short, group, tname = pick_primary(code, topic_idx.get(code, []))
        ms = tpex_margin_map.get(code) or {}
        all_mapped.append({
            **r,
            "topicId": tid,
            "topic": short,
            "topicName": tname,
            "group": group,
            "change": None,
            "amount": 0.0,
            "margin_delta": ms.get("margin_delta") or 0.0,
        })

    topic_agg = defaultdict(lambda: {
        "foreign_net": 0.0, "trust_net": 0.0, "dealer_net": 0.0,
        "inst_net": 0.0, "amount": 0.0, "margin_delta": 0.0,
        "changes": [], "companyCount": 0,
    })
    for s in all_mapped:
        if s["topicId"] == "unmapped":
            continue
        a = topic_agg[s["topicId"]]
        a["foreign_net"] += s["foreign_net"]
        a["trust_net"] += s["trust_net"]
        a["dealer_net"] += s["dealer_net"]
        a["inst_net"] += s["inst_net"]
        a["amount"] += s["amount"]
        a["margin_delta"] += s["margin_delta"]
        a["companyCount"] += 1
        if s["change"] is not None:
            a["changes"].append(s["change"])
        a["name"] = s["topicName"]
        a["shortname"] = s["topic"]
        a["group"] = s["group"]
        a["id"] = s["topicId"]

    topics = []
    for tid, a in topic_agg.items():
        meta = topics_meta.get(tid) or {}
        topics.append({
            "id": tid,
            "name": a.get("name") or meta.get("name") or tid,
            "shortname": a.get("shortname") or meta.get("shortname") or tid,
            "group": a.get("group") or meta.get("group") or "其他",
            "companyCount": a["companyCount"],
            "foreign_net": round(a["foreign_net"], 3),
            "trust_net": round(a["trust_net"], 3),
            "dealer_net": round(a["dealer_net"], 3),
            "inst_net": round(a["inst_net"], 3),
            "amount": round(a["amount"], 2),
            "vs20": 1.0,
            "change_pct": round(statistics.median(a["changes"]), 2) if a["changes"] else 0.0,
            "margin_delta": round(a["margin_delta"], 1),
        })
    topics.sort(key=lambda t: abs(t["inst_net"]), reverse=True)

    group_agg = defaultdict(lambda: {
        "foreign_net": 0.0, "trust_net": 0.0, "dealer_net": 0.0,
        "inst_net": 0.0, "amount": 0.0, "margin_delta": 0.0,
        "changes": [], "companyCount": 0, "topicIds": set(),
    })
    for s in all_mapped:
        g = s["group"]
        if g == "其他" and s["topicId"] == "unmapped":
            continue
        a = group_agg[g]
        a["foreign_net"] += s["foreign_net"]
        a["trust_net"] += s["trust_net"]
        a["dealer_net"] += s["dealer_net"]
        a["inst_net"] += s["inst_net"]
        a["amount"] += s["amount"]
        a["margin_delta"] += s["margin_delta"]
        a["companyCount"] += 1
        a["topicIds"].add(s["topicId"])
        if s["change"] is not None:
            a["changes"].append(s["change"])

    groups = []
    for gname, a in group_agg.items():
        chg = round(statistics.median(a["changes"]), 2) if a["changes"] else 0.0
        groups.append({
            "name": gname,
            "topicCount": len(a["topicIds"]),
            "companyCount": a["companyCount"],
            "change_pct": chg,
            "inst_net": round(a["inst_net"], 3),
            "amount_vs_20d": 1.0,
            "margin_delta": round(a["margin_delta"], 1),
            "foreign_net": round(a["foreign_net"], 3),
            "trust_net": round(a["trust_net"], 3),
            "dealer_net": round(a["dealer_net"], 3),
            "vs20": 1.0,
            "amount": round(a["amount"], 2),
        })
    groups.sort(key=lambda g: abs(g["inst_net"]), reverse=True)

    sectors = parse_bfiamu(bfi_amu)
    if not sectors:
        sectors = groups  # fallback

    alerts = build_alerts(stocks)
    alerts = enrich_stocks_with_rules(
        date,
        stocks,
        twt96=twt96,
        notice=notice,
        punish_doc=punish_doc,
        bfi84=bfi84,
        alerts=alerts,
        tpex_disposal=tpex_disposal,
        twtbau1=twtbau1,
        twtbau2=twtbau2,
        twtb4u=twtb4u_oa,
        tpex_warn=tpex_warn,
        tpex_warn_note=tpex_warn_note,
        tpex_cmode=tpex_cmode,
        notice_history_map=notice_history_map,
    )

    brokers = top_brokers_from_docs(tpex_broker1, tpex_broker2)
    rules_meta = {
        "tpex_disposal_n": sum(1 for s in stocks if s.get("disposition") and "tpex" in str(s.get("disposition_source") or "")),
        "disposition_n": sum(1 for s in stocks if s.get("disposition")),
        "twtbau_active_n": sum(1 for s in stocks if s.get("daytrade_pause")),
        "daytrade_suspended_n": sum(1 for s in stocks if s.get("daytrade_suspended")),
        "disp_risk_high_n": sum(1 for s in stocks if s.get("disp_risk") == "high"),
        "disp_risk_med_n": sum(1 for s in stocks if s.get("disp_risk") == "med"),
        "notice_n": sum(1 for s in stocks if s.get("notice")),
        "altered_trading_n": sum(1 for s in stocks if s.get("altered_trading")),
        "broker_branches_n": len(brokers.get("branches") or []),
        "broker_firms_n": len(brokers.get("firms") or []),
    }

    return {
        "meta": {
            "date": date,
            "note": "上市+櫃買法人／融資；MI_QFIIS存量；注意/處置/櫃買警示；TWTBAU當沖；券商排行｜圖Top N",
            "source": "TWSE raw+topic map",
            "title": "台股籌碼資金流視覺化",
            "currency": "TWD",
            "unit_inst_stock": "千張",
            "unit_amount": "億元",
            "unit_share": "張",
            "topic_source": "aistockmap/topics/TW_TOPIC_MEMBERS.json",
            "stock_count": len(stocks),
            "sankey_default_top_n": TOP_N,
        },
        "market_kpi": market_kpi,
        "stocks": stocks,
        "topics": topics,  # all mapped topics; UI can rank/filter
        "groups": groups,
        "sectors": sectors,
        "alerts": alerts,
        "foreign_cat": foreign_cat,
        "brokers": brokers,
        "rules_meta": rules_meta,
    }


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    topics_meta = load_json(TOPIC_PATH) or {}
    topic_idx = build_topic_index(topics_meta)

    # Prefer manifest dates with trade_ok; else scan dirs
    dates = []
    man = load_json(RAW_DIR / "manifest.json")
    if man and man.get("days"):
        for d in man["days"]:
            if d.get("status") in ("trade_ok", "ok", "partial") or d.get("ok"):
                dates.append(d["date"])
    if not dates:
        dates = sorted(
            p.name for p in RAW_DIR.iterdir()
            if p.is_dir() and re.match(r"^\d{4}-\d{2}-\d{2}$", p.name)
        )
    # oldest → newest for index; process all
    dates = sorted(set(dates))

    history = []
    ok_dates = []
    for date in dates:
        print(f"build {date}…")
        curated = build_day(date, topic_idx, topics_meta, all_dates=dates)
        if not curated:
            continue
        out_path = OUT_DIR / f"{date}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(curated, f, ensure_ascii=False, separators=(",", ":"))
        ok_dates.append(date)
        k = curated["market_kpi"]
        history.append({
            "date": date,
            "foreign": k["foreign_net"],
            "trust": k["trust_net"],
            "dealer": k["dealer_net"],
            "margin_delta": k.get("margin_delta"),
            "daytrade": k.get("daytrade_pct"),
            # aliases for viz compatibility
            "foreign_net": k["foreign_net"],
            "trust_net": k["trust_net"],
            "dealer_net": k["dealer_net"],
            "amount": k.get("total_amount"),
        })
        print(f"  stocks={len(curated['stocks'])} foreign={k['foreign_net']} trust={k['trust_net']} dealer={k['dealer_net']}")

    with open(OUT_DIR / "index.json", "w", encoding="utf-8") as f:
        json.dump(ok_dates, f, ensure_ascii=False, indent=2)

    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, separators=(",", ":"))

    print(f"\nDone: {len(ok_dates)} curated days → {OUT_DIR}")
    print(f"history_kpi → {HISTORY_PATH} ({len(history)} rows)")
    if "2026-09-04" in ok_dates:
        sample = json.load(open(OUT_DIR / "2026-09-04.json"))
        print("Sample KPI 2026-09-04:", json.dumps(sample["market_kpi"], ensure_ascii=False))
        rm = sample.get("rules_meta") or {}
        print("rules_meta:", json.dumps(rm, ensure_ascii=False))
        br = sample.get("brokers") or {}
        print("brokers branches=", len(br.get("branches") or []), "firms=", len(br.get("firms") or []))

    # Regime labels (heuristic 体制) for viz dashboard
    try:
        from build_regimes import build as build_regimes
        payload = build_regimes()
        n = len(payload.get("days") or [])
        print(f"regimes → /workspace/tw-moneyflow-viz/data/regimes.json ({n} days)")
        for d in (payload.get("days") or [])[-5:]:
            sec = f"+{d.get('secondary')}" if d.get("secondary") else ""
            print(f"  {d['date']}: {d['primary']}{sec} conf={d['confidence']}")
        try:
            from build_regime_brief import build as build_regime_brief
            br = build_regime_brief(all_days=True)
            print(f"regime_brief → latest { (br.get('latest') or {}).get('date') }")
        except Exception as e2:
            print(f"WARNING: build_regime_brief failed: {e2}")
    except Exception as e:
        print(f"WARNING: build_regimes failed: {e}")

    # Deterministic mild_push / exit_watch screens (no LLM)
    try:
        from build_screens import build as build_screens
        scr = build_screens()
        latest = scr.get("latest") or {}
        print(f"screens → /workspace/tw-moneyflow-viz/data/screens ({len(scr.get('dates') or [])} days)")
        print("  counts", latest.get("counts"))
    except Exception as e:
        print(f"WARNING: build_screens failed: {e}")

    # 00981A daily holdings Δ × screens/regime
    try:
        from build_00981a import build as build_00981a
        e981 = build_00981a(use_jojo_if_needed=True)
        mf = (e981.get("manager_flow") or {}).get("counts") or {}
        cx = e981.get("cross") or {}
        print(f"00981A → /workspace/tw-moneyflow-viz/data/etf/00981a/latest.json date={e981.get('date')}")
        print("  flow", mf, "mild∩", len(cx.get("intersect_mild_push") or []),
              "accel∩", len(cx.get("intersect_theme_accel") or []),
              "exit∩", len(cx.get("flag_exit_watch") or []))
    except Exception as e:
        print(f"WARNING: build_00981a failed: {e}")

    # Deterministic daily digest markdown (no LLM)
    try:
        from build_daily_digest import build as build_daily_digest
        dig = build_daily_digest()
        print(f"digest → date={dig.get('date')} chars={len(dig.get('markdown') or '')}")
    except Exception as e:
        print(f"WARNING: build_daily_digest failed: {e}")


if __name__ == "__main__":
    main()
