"""Unit tests for etl/fundflo_model.py"""
from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fundflo_model import (
    WINDOW,
    enrich_day_metrics,
    flow_of,
    foreign_flow_yi_from_net,
    foreign_flow_yi_from_shares,
    interpolate_state,
    normalize,
    ranked,
    rolling_ret_5d,
    rolling_sum,
    shares_from_foreign_net_qianzhang,
    state,
)


def _day(foreign=0.0, etf=0.0, close=100.0, shares=0.0, **extra):
    row = {
        "foreign_flow_yi": foreign,
        "etf_flow_yi": etf,
        "close": close,
        "adjustedClose": close,
        "shares": shares,
    }
    row.update(extra)
    return row


class TestUnits(unittest.TestCase):
    def test_qianzhang_to_shares(self):
        self.assertEqual(shares_from_foreign_net_qianzhang(2.5), 2_500_000.0)

    def test_flow_yi_from_net_honest(self):
        self.assertAlmostEqual(foreign_flow_yi_from_net(1.0, 100.0), 1.0)
        self.assertAlmostEqual(
            foreign_flow_yi_from_shares(shares_from_foreign_net_qianzhang(1.0), 100.0),
            1.0,
        )
        self.assertNotAlmostEqual(foreign_flow_yi_from_net(1.0, 100.0), 1.0 * 100 / 1e5)


class TestFlowOf(unittest.TestCase):
    def test_modes(self):
        d = _day(foreign=3.0, etf=1.5)
        self.assertEqual(flow_of(d, "foreign"), 3.0)
        self.assertEqual(flow_of(d, "etf"), 1.5)
        self.assertEqual(flow_of(d, "combined"), 4.5)
        self.assertEqual(flow_of({**d, "amount": 12.5}, "turnover"), 12.5)


class TestRolling(unittest.TestCase):
    def test_window_and_momentum(self):
        flows = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
        days = [_day(foreign=float(f), close=100 + i) for i, f in enumerate(flows)]
        self.assertEqual(WINDOW, 5)

        st = state(days, 0, "foreign")
        self.assertIsNotNone(st)
        self.assertAlmostEqual(st["rolling"], 20.0)
        self.assertAlmostEqual(st["momentum"], 5.0)
        self.assertAlmostEqual(st["daily_flow"], 6.0)
        self.assertAlmostEqual(st["rolling_ret"], 5.0)

    def test_prior_fallback_when_incomplete(self):
        days = [_day(foreign=float(i + 1)) for i in range(5)]
        r = rolling_sum(days, 0, 4, "foreign")
        self.assertAlmostEqual(r, 15.0)
        prior = rolling_sum(days, -1, 3, "foreign")
        self.assertIsNone(prior)

    def test_combined_rolling(self):
        days = [_day(foreign=1.0, etf=0.5) for _ in range(6)]
        st = state(days, 0, "combined")
        self.assertAlmostEqual(st["rolling"], 7.5)

    def test_etf_mode(self):
        days = [_day(foreign=10.0, etf=float(i + 1)) for i in range(6)]
        st = state(days, 0, "etf")
        self.assertAlmostEqual(st["rolling"], 20.0)  # 2+3+4+5+6
        self.assertAlmostEqual(st["momentum"], 5.0)


class TestTurnover(unittest.TestCase):
    def test_turnover_state_mapping(self):
        # 6 days: frame 0 → end=5
        days = []
        for i in range(6):
            days.append(
                _day(
                    foreign=0,
                    close=100 + i,
                    amount=10.0 + i,
                    average5=8.0,
                    change_pct=25.0 + i,
                    market_share=1.5,
                    change=0.5 * i,
                    cumulative_return=2.0,
                )
            )
        st = state(days, 0, "turnover")
        self.assertIsNotNone(st)
        self.assertAlmostEqual(st["rolling"], 15.0)  # amount at end
        self.assertAlmostEqual(st["flow"], 30.0)  # changePct
        self.assertAlmostEqual(st["momentum"], 2.5)  # daily return from change
        self.assertAlmostEqual(st["turnoverChange"], 30.0)
        self.assertAlmostEqual(st["marketShare"], 1.5)
        self.assertAlmostEqual(st["average5"], 8.0)
        self.assertAlmostEqual(st["rolling_ret"], 2.0)

    def test_turnover_ranked_by_amount(self):
        stocks = []
        for code, amt in (("A", 50.0), ("B", 10.0), ("C", 80.0)):
            days = [
                _day(amount=amt, average5=20.0, change_pct=10.0, market_share=1.0, change=1.0, cumulative_return=1.0)
                for _ in range(6)
            ]
            stocks.append({"code": code, "days": days})
        rows = ranked(stocks, 0, 2, "turnover", "turnover")
        self.assertEqual(rows[0]["stock"]["code"], "C")
        self.assertEqual(rows[1]["stock"]["code"], "A")


class TestInterpolate(unittest.TestCase):
    def test_blend_midpoint(self):
        a = {"rolling": 0.0, "momentum": 0.0, "flow": 0.0, "rolling_ret": 0.0}
        b = {"rolling": 10.0, "momentum": 4.0, "flow": 10.0, "rolling_ret": 2.0}
        mid = interpolate_state(a, b, 0.5)
        # ease(0.5)=0.5
        self.assertAlmostEqual(mid["rolling"], 5.0)
        self.assertAlmostEqual(mid["momentum"], 2.0)


class TestNormalize(unittest.TestCase):
    def test_bounds(self):
        self.assertEqual(normalize(0, 1), 0.0)
        self.assertTrue(-1 <= normalize(1000, 1) <= 1)
        self.assertTrue(-1 <= normalize(-1000, 1) <= 1)
        self.assertAlmostEqual(normalize(3, 1), 1.0)
        self.assertAlmostEqual(normalize(-3, 1), -1.0)


class TestEnrich(unittest.TestCase):
    def test_enrich_fields(self):
        days = [_day(foreign=float(i + 1), etf=0.1, close=100 + i, shares=1000) for i in range(8)]
        enriched = enrich_day_metrics(days)
        self.assertIn("rolling_foreign_5d_yi", enriched[4])
        self.assertAlmostEqual(enriched[4]["rolling_foreign_5d_yi"], 15.0)
        self.assertIn("momentum_foreign_5d_yi", enriched[5])
        self.assertAlmostEqual(enriched[5]["rolling_foreign_5d_yi"], 20.0)
        self.assertAlmostEqual(enriched[5]["momentum_foreign_5d_yi"], 5.0)
        self.assertAlmostEqual(enriched[5]["combined_flow_yi"], 6.1)
        self.assertAlmostEqual(enriched[5]["rolling_ret_5d"], 5.0)
        self.assertIn("rolling_etf_5d_yi", enriched[5])


if __name__ == "__main__":
    unittest.main()
