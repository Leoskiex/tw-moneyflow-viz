"""Parse notice / punish / TWT96U / BFI84U + gap4 overlays for money-flow curated build."""
from __future__ import annotations

import re
from typing import Any, Optional


def num(x: Any) -> Optional[float]:
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip().replace(",", "").replace("%", "")
    s = re.sub(r"<[^>]+>", "", s).strip()
    if not s or s in {"-", "--", "---", "+", "N/A"}:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def roc_to_iso(s: str) -> Optional[str]:
    if not s:
        return None
    s = str(s).strip().replace(".", "/")
    m = re.match(r"^(\d{2,3})/(\d{1,2})/(\d{1,2})$", s)
    if not m:
        return None
    y = int(m.group(1)) + 1911
    return f"{y:04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"


def roc_yyyymmdd_to_iso(s: Any) -> Optional[str]:
    """Convert ROC compact date like 1150902 → 2026-09-02. Also accepts ISO / slash forms."""
    if s is None:
        return None
    raw = str(s).strip().replace(".", "").replace("/", "").replace("-", "")
    if not raw:
        return None
    # Already Gregorian YYYYMMDD (8 digits starting with 19/20)
    if re.match(r"^(19|20)\d{6}$", raw):
        return f"{raw[0:4]}-{raw[4:6]}-{raw[6:8]}"
    # ROC YYYMMDD or YYMMDD
    m = re.match(r"^(\d{2,3})(\d{2})(\d{2})$", raw)
    if not m:
        # try slash form via roc_to_iso
        return roc_to_iso(str(s).strip().replace(".", "/"))
    y = int(m.group(1)) + 1911
    return f"{y:04d}-{m.group(2)}-{m.group(3)}"


def _as_list(doc: Any) -> list:
    if doc is None:
        return []
    if isinstance(doc, list):
        return doc
    if isinstance(doc, dict):
        for k in ("data", "tables", "result"):
            v = doc.get(k)
            if isinstance(v, list):
                return v
    return []


def parse_twt96u(doc: Optional[dict]) -> dict:
    out = {}
    if not doc or str(doc.get("stat", "")).upper() != "OK":
        return out

    def clean(x):
        return re.sub(r"<[^>]+>", "", str(x or "")).strip()

    for row in doc.get("data") or []:
        if not row:
            continue
        if len(row) >= 2:
            c1, v1 = clean(row[0]), num(row[1])
            if c1:
                out[c1] = {"sbl_avail_shares": v1 or 0.0}
        if len(row) >= 4:
            c2, v2 = clean(row[2]), num(row[3])
            if c2:
                out[c2] = {"sbl_avail_shares": v2 or 0.0}
    return out


def parse_notice(doc: Optional[dict]) -> dict:
    out = {}
    if not doc or str(doc.get("stat", "")).upper() != "OK":
        return out
    for row in doc.get("data") or []:
        if not row or len(row) < 5:
            continue
        code = str(row[1]).strip()
        out[code] = {
            "notice": True,
            "notice_count": num(row[3]),
            "notice_reason": str(row[4]).strip(),
            "notice_date": roc_to_iso(str(row[5]).replace(".", "/")) if len(row) > 5 else None,
        }
    return out


def parse_punish(doc: Optional[dict]) -> list:
    rows = []
    if not doc or str(doc.get("stat", "")).upper() != "OK":
        return rows
    for row in doc.get("data") or []:
        if not row or len(row) < 8:
            continue
        code = str(row[2]).strip()
        period = str(row[6]).replace("～", "~").replace("〜", "~")
        m = re.search(
            r"(\d{2,3}[/.]\d{1,2}[/.]\d{1,2})\s*[~～\-]\s*(\d{2,3}[/.]\d{1,2}[/.]\d{1,2})",
            period,
        )
        start = end = None
        if m:
            start = roc_to_iso(m.group(1).replace(".", "/"))
            end = roc_to_iso(m.group(2).replace(".", "/"))
        rows.append({
            "code": code,
            "name": str(row[3]).strip(),
            "pub_date": roc_to_iso(str(row[1]).replace(".", "/")),
            "times": num(row[4]),
            "condition": str(row[5]).strip(),
            "period": period,
            "start": start,
            "end": end,
            "measure": str(row[7]).strip(),
        })
    return rows


def active_punish_on(date: str, records: list) -> dict:
    out = {}
    for r in records:
        if not r.get("start") or not r.get("end"):
            continue
        if r["start"] <= date <= r["end"]:
            out[r["code"]] = {
                "disposition": True,
                "disposition_measure": r.get("measure"),
                "disposition_period": r.get("period"),
                "disposition_condition": r.get("condition"),
            }
    return out


def parse_tpex_disposal(doc) -> list:
    """TPEx openapi disposal list → records with code/start/end/reason/measure."""
    rows = []
    for item in _as_list(doc):
        if not isinstance(item, dict):
            continue
        code = str(item.get("SecuritiesCompanyCode") or item.get("Code") or "").strip()
        if not code:
            continue
        period = str(item.get("DispositionPeriod") or "").replace("～", "~").replace("〜", "~")
        start = end = None
        m = re.search(r"(\d{6,7})\s*[~～\-]\s*(\d{6,7})", period)
        if m:
            start = roc_yyyymmdd_to_iso(m.group(1))
            end = roc_yyyymmdd_to_iso(m.group(2))
        reason = str(item.get("DispositionReasons") or "").strip()
        measure = str(item.get("DisposalCondition") or "").strip()
        rows.append({
            "code": code,
            "name": str(item.get("CompanyName") or "").strip(),
            "period": period,
            "start": start,
            "end": end,
            "reason": reason,
            "measure": measure[:120] if measure else reason,
            "condition": reason,
        })
    return rows


def parse_twtbau(doc, date: str) -> dict:
    """TWTBAU1/2 → code → {daytrade_pause, start, end, reason} active on date."""
    out = {}
    for item in _as_list(doc):
        if not isinstance(item, dict):
            continue
        code = str(item.get("Code") or "").strip()
        if not code:
            continue
        start = roc_yyyymmdd_to_iso(item.get("StartDate"))
        end = roc_yyyymmdd_to_iso(item.get("EndDate"))
        if not start or not end:
            continue
        if start <= date <= end:
            out[code] = {
                "daytrade_pause": True,
                "daytrade_pause_start": start,
                "daytrade_pause_end": end,
                "daytrade_pause_reason": str(item.get("Reason") or "").strip(),
            }
    return out


def parse_twtb4u_suspension(doc) -> set:
    """Codes with Suspension == Y (daytrade suspended)."""
    codes = set()
    for item in _as_list(doc):
        if isinstance(item, dict):
            sus = str(item.get("Suspension") or "").strip().upper()
            if sus in ("Y", "Ｙ", "YES"):
                code = str(item.get("Code") or "").strip()
                if code:
                    codes.add(code)
        elif isinstance(item, (list, tuple)) and len(item) >= 4:
            # rwd-style rows sometimes
            sus = str(item[3] if len(item) > 3 else "").strip().upper()
            code = str(item[1] if len(item) > 1 else item[0]).strip()
            if sus in ("Y", "Ｙ") and code:
                codes.add(code)
    return codes


def parse_tpex_warning(doc) -> dict:
    """TPEx trading warning → notice-like map."""
    out = {}
    for item in _as_list(doc):
        if not isinstance(item, dict):
            continue
        code = str(item.get("SecuritiesCompanyCode") or "").strip()
        if not code:
            continue
        info = str(item.get("TradingInformation") or "").strip()
        out[code] = {
            "notice": True,
            "notice_reason": info,
            "tpex_warning": True,
            "trading_information": info,
        }
    return out


def parse_tpex_warning_note(doc) -> dict:
    """TPEx warning note (accumulation) → enrich notice map."""
    out = {}
    for item in _as_list(doc):
        if not isinstance(item, dict):
            continue
        code = str(item.get("SecuritiesCompanyCode") or "").strip()
        if not code:
            continue
        situ = str(item.get("AccumulationSituation") or "").strip()
        out[code] = {
            "notice": True,
            "notice_reason": situ,
            "tpex_warning_note": True,
            "accumulation": situ,
        }
    return out


def parse_tpex_cmode(doc) -> dict:
    """TPEx change-trading mode flags."""
    out = {}

    def yn(v) -> bool:
        s = str(v or "").strip().upper()
        return s in ("Y", "Ｙ", "YES", "1", "TRUE")

    for item in _as_list(doc):
        if not isinstance(item, dict):
            continue
        code = str(item.get("SecuritiesCompanyCode") or "").strip()
        if not code:
            continue
        # key may have leading space in API
        fin_ann = item.get("FinancialAnnouncements")
        if fin_ann is None:
            for k, v in item.items():
                if "Financial" in k:
                    fin_ann = v
                    break
        out[code] = {
            "altered_trading": yn(item.get("AlteredTrading")),
            "periodic_trading": yn(item.get("PeriodicTrading")),
            "managed": yn(item.get("ManagedStock")),
            "halt": yn(item.get("SuspensionOfTrading")),
            "matching_frequency": str(item.get("MatchingFrequency") or "").strip() or None,
        }
    return out


def parse_bfi84u(doc: Optional[dict]) -> dict:
    out = {}
    if not doc or str(doc.get("stat", "")).upper() != "OK":
        return out
    for row in doc.get("data") or []:
        if not row or len(row) < 5:
            continue
        code = str(row[0]).strip()
        out[code] = {
            "stop_sbl": True,
            "stop_sbl_start": roc_to_iso(str(row[2]).replace(".", "/")),
            "stop_sbl_end": roc_to_iso(str(row[3]).replace(".", "/")),
            "stop_sbl_reason": str(row[4]).strip(),
        }
    return out


def _notice_streak(code: str, date: str, notice_by_day: dict, ordered_days: list) -> int:
    """Consecutive trading days ending at `date` where code had notice=True."""
    if date not in notice_by_day and date not in ordered_days:
        # still try from ordered days ending at or before date
        pass
    # find index of date in ordered_days
    try:
        idx = ordered_days.index(date)
    except ValueError:
        # date may be beyond last known; use days <= date
        days = [d for d in ordered_days if d <= date]
        if not days:
            return 1 if (notice_by_day.get(date) or {}).get(code) else 0
        idx = len(days) - 1
        ordered_days = days
    streak = 0
    for i in range(idx, -1, -1):
        d = ordered_days[i]
        day_map = notice_by_day.get(d) or {}
        if day_map.get(code):
            streak += 1
        else:
            break
    return streak


def build_disposition_risk_engine(
    date: str,
    stocks: list,
    notice_by_day: Optional[dict],
) -> None:
    """
    aistockmap-style disposition approaching risk (NOT official publish).
    Mutates stocks in place: disp_risk, disp_risk_reason, notice_streak.
    Core: TWSE 作業要點 第6條 post 2026-08-10 — consecutive notice days approach disposition.
    """
    notice_by_day = notice_by_day or {}
    ordered_days = sorted(notice_by_day.keys())
    today_notice = notice_by_day.get(date) or {}

    for s in stocks:
        code = s["code"]
        reasons = []
        risk = "none"
        streak = _notice_streak(code, date, notice_by_day, ordered_days) if ordered_days else (
            1 if today_notice.get(code) or s.get("notice") else 0
        )
        # if stock is notice today but not in history map, at least streak 1
        if s.get("notice") and streak == 0:
            streak = 1

        if s.get("disposition"):
            risk = "high"
            reasons.append("已列處置")
        else:
            if streak >= 3:
                risk = "high"
                reasons.append("連續注意≥3日（逼近處置門檻）")
            elif streak == 2:
                risk = "med"
                reasons.append("連續注意2日")
            elif streak == 1 or s.get("notice"):
                risk = "low"
                reasons.append("當日注意")

            # notice_count from same-day TWSE notice row
            nc = None
            ninfo = today_notice.get(code)
            if isinstance(ninfo, dict):
                nc = ninfo.get("notice_count")
            if nc is None and s.get("notice_count") is not None:
                nc = s.get("notice_count")
            if nc is not None and nc >= 5:
                if risk in ("none", "low"):
                    risk = "med"
                if risk == "med" and nc >= 8:
                    risk = "high"
                reasons.append("累計注意次數偏高")

            # TPEx warning with 連續 bump
            ti = s.get("trading_information") or s.get("notice_reason") or ""
            if s.get("tpex_warning") and "連續" in str(ti):
                if risk == "none":
                    risk = "low"
                elif risk == "low":
                    risk = "med"
                elif risk == "med":
                    risk = "high"
                reasons.append("櫃買警示含連續")

        s["disp_risk"] = risk
        s["disp_risk_reason"] = "；".join(reasons) if reasons else ""
        s["notice_streak"] = streak


def enrich_stocks_with_rules(
    date: str,
    stocks: list,
    *,
    twt96,
    notice,
    punish_doc,
    bfi84,
    alerts: list,
    tpex_disposal=None,
    twtbau1=None,
    twtbau2=None,
    twtb4u=None,
    tpex_warn=None,
    tpex_warn_note=None,
    tpex_cmode=None,
    notice_history_map=None,
) -> list:
    sbl_map = parse_twt96u(twt96)
    notice_map = parse_notice(notice)
    # merge TPEx warnings as notice-like
    twarn = parse_tpex_warning(tpex_warn)
    tnote = parse_tpex_warning_note(tpex_warn_note)
    for code, info in twarn.items():
        if code not in notice_map:
            notice_map[code] = info
        else:
            notice_map[code] = {**notice_map[code], **{k: v for k, v in info.items() if k != "notice_reason"}}
            if not notice_map[code].get("notice_reason"):
                notice_map[code]["notice_reason"] = info.get("notice_reason")
    for code, info in tnote.items():
        if code not in notice_map:
            notice_map[code] = info
        else:
            notice_map[code]["tpex_warning_note"] = True
            if info.get("accumulation"):
                prev = notice_map[code].get("notice_reason") or ""
                notice_map[code]["notice_reason"] = (prev + "｜" + info["accumulation"]).strip("｜")

    punish_map = active_punish_on(date, parse_punish(punish_doc))
    # Merge TPEx disposal into punish map
    for r in parse_tpex_disposal(tpex_disposal):
        if not r.get("start") or not r.get("end"):
            continue
        if r["start"] <= date <= r["end"]:
            code = r["code"]
            if code not in punish_map:
                punish_map[code] = {
                    "disposition": True,
                    "disposition_measure": r.get("measure"),
                    "disposition_period": r.get("period"),
                    "disposition_condition": r.get("condition") or r.get("reason"),
                    "disposition_source": "tpex",
                }
            else:
                punish_map[code]["disposition_source"] = (
                    punish_map[code].get("disposition_source") or "twse"
                ) + "+tpex"

    stop_map = parse_bfi84u(bfi84)
    bau = parse_twtbau(twtbau1, date)
    # history list can fill gaps
    for code, info in parse_twtbau(twtbau2, date).items():
        bau.setdefault(code, info)
    sus_codes = parse_twtb4u_suspension(twtb4u)
    cmode_map = parse_tpex_cmode(tpex_cmode)

    for s in stocks:
        code = s["code"]
        sb = sbl_map.get(code) or {}
        if sb.get("sbl_avail_shares") is not None:
            s["sbl_avail"] = round((sb["sbl_avail_shares"] or 0.0) / 1000.0, 1)
        else:
            s["sbl_avail"] = None

        ninfo = notice_map.get(code)
        if ninfo:
            s["notice"] = True
            s["notice_reason"] = ninfo.get("notice_reason")
            s["notice_count"] = ninfo.get("notice_count")
            if ninfo.get("tpex_warning"):
                s["tpex_warning"] = True
                s["trading_information"] = ninfo.get("trading_information") or ninfo.get("notice_reason")
            if ninfo.get("tpex_warning_note"):
                s["tpex_warning_note"] = True
        else:
            s["notice"] = False

        pinfo = punish_map.get(code)
        if pinfo:
            s["disposition"] = True
            s["disposition_measure"] = pinfo.get("disposition_measure")
            s["disposition_period"] = pinfo.get("disposition_period")
            s["disposition_source"] = pinfo.get("disposition_source") or "twse"
        else:
            s["disposition"] = False

        st = stop_map.get(code)
        if st and st.get("stop_sbl_start") and st.get("stop_sbl_end") and st["stop_sbl_start"] <= date <= st["stop_sbl_end"]:
            s["stop_sbl"] = True
            s["stop_sbl_reason"] = st.get("stop_sbl_reason")
        else:
            s["stop_sbl"] = False

        binfo = bau.get(code)
        if binfo:
            s["daytrade_pause"] = True
            s["daytrade_pause_reason"] = binfo.get("daytrade_pause_reason")
            s["daytrade_pause_start"] = binfo.get("daytrade_pause_start")
            s["daytrade_pause_end"] = binfo.get("daytrade_pause_end")
        else:
            s["daytrade_pause"] = False

        s["daytrade_suspended"] = code in sus_codes

        cm = cmode_map.get(code) or {}
        s["altered_trading"] = bool(cm.get("altered_trading"))
        s["periodic_trading"] = bool(cm.get("periodic_trading"))
        s["managed"] = bool(cm.get("managed"))
        s["halt"] = bool(cm.get("halt"))

    # Build notice_by_day for risk engine: merge history with today's parsed notice
    notice_by_day = {}
    if notice_history_map:
        for d, m in notice_history_map.items():
            # normalize: allow {code: True} or {code: dict}
            flat = {}
            for c, v in (m or {}).items():
                if v:
                    if isinstance(v, dict):
                        flat[c] = v
                    else:
                        flat[c] = {"notice": True}
            notice_by_day[d] = flat
    # ensure today includes TWSE+TPEx notice
    today_flat = dict(notice_by_day.get(date) or {})
    for c, info in notice_map.items():
        today_flat[c] = info if isinstance(info, dict) else {"notice": True}
    notice_by_day[date] = today_flat

    build_disposition_risk_engine(date, stocks, notice_by_day)

    approaching_n = 0
    for s in stocks:
        if s.get("disposition"):
            alerts.append({
                "level": "高",
                "code": s["code"],
                "name": s["name"],
                "type": "處置股",
                "message": (s.get("disposition_measure") or "處置中")[:80] + "｜" + (s.get("disposition_period") or ""),
                "value": s.get("disposition_period") or "",
            })
        elif s.get("notice"):
            alerts.append({
                "level": "中",
                "code": s["code"],
                "name": s["name"],
                "type": "注意股",
                "message": (s.get("notice_reason") or "注意交易資訊")[:80],
                "value": "注意",
            })
        if s.get("sbl_avail") is not None and s["sbl_avail"] < 50 and abs(s.get("inst_net") or 0) >= 1:
            alerts.append({
                "level": "中",
                "code": s["code"],
                "name": s["name"],
                "type": "借券彈藥低",
                "message": "可借券賣出額度偏低（張）",
                "value": f"{s['sbl_avail']} 張",
            })
        if s.get("daytrade_pause"):
            alerts.append({
                "level": "高",
                "code": s["code"],
                "name": s["name"],
                "type": "暫停先賣後買",
                "message": (s.get("daytrade_pause_reason") or "暫停先賣後買")[:80],
                "value": f"{s.get('daytrade_pause_start') or ''}~{s.get('daytrade_pause_end') or ''}",
            })
        if s.get("daytrade_suspended") and not s.get("daytrade_pause"):
            alerts.append({
                "level": "中",
                "code": s["code"],
                "name": s["name"],
                "type": "當沖暫停",
                "message": "TWTB4U Suspension=Y",
                "value": "Y",
            })
        if s.get("altered_trading") or s.get("periodic_trading") or s.get("halt"):
            bits = []
            if s.get("altered_trading"):
                bits.append("變更交易")
            if s.get("periodic_trading"):
                bits.append("分盤")
            if s.get("halt"):
                bits.append("暫停交易")
            alerts.append({
                "level": "高",
                "code": s["code"],
                "name": s["name"],
                "type": "變更交易",
                "message": "／".join(bits),
                "value": "／".join(bits),
            })
        dr = s.get("disp_risk")
        if dr in ("med", "high") and not s.get("disposition") and approaching_n < 12:
            approaching_n += 1
            alerts.append({
                "level": "高" if dr == "high" else "中",
                "code": s["code"],
                "name": s["name"],
                "type": "逼近處置",
                "message": (s.get("disp_risk_reason") or "")[:80],
                "value": f"streak={s.get('notice_streak')}",
            })

    seen = set()
    uniq = []
    for a in alerts:
        k = (a.get("type"), a.get("code"), str(a.get("message"))[:40])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(a)
    return uniq[:50]


def top_brokers_from_docs(broker1, broker2, n_branches: int = 30, n_firms: int = 20) -> dict:
    """Curate top broker ranking lists for day JSON."""
    branches = []
    for item in _as_list(broker1):
        if not isinstance(item, dict):
            continue
        branches.append({
            "rank": int(num(item.get("Ranking")) or 0),
            "code": str(item.get("Code") or "").strip(),
            "name": str(item.get("Name") or "").strip(),
            "amount": num(item.get("TradingAmount")),
            "ratio": str(item.get("DayClosingRatio") or "").strip(),
        })
    branches.sort(key=lambda x: x["rank"] or 9999)
    firms = []
    for item in _as_list(broker2):
        if not isinstance(item, dict):
            continue
        firms.append({
            "rank": int(num(item.get("Ranking")) or 0),
            "code": str(item.get("FinancialInstitutionsCode") or "").strip(),
            "name": str(item.get("FinancialInstitutionsName") or "").strip(),
            "n_branches": int(num(item.get("NumberOfCompanies")) or 0),
            "amount": num(item.get("TradingAmount")),
            "ratio": str(item.get("DayClosingRatio") or "").strip(),
        })
    firms.sort(key=lambda x: x["rank"] or 9999)
    return {
        "branches": branches[:n_branches],
        "firms": firms[:n_firms],
        "note": "個股分點需官網驗證碼；此處為櫃買券商成交排行＋查詢入口",
        "links": {
            "twse_bsr": "https://bsr.twse.com.tw/bshtm/bsMenu.aspx",
            "tpex_broker": "https://www.tpex.org.tw/www/zh-tw/afterTrading/brokerTrading",
        },
    }
