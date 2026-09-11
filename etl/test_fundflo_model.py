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
    normalize,
    rolling_ret_5d,
    rolling_sum,
    shares_from_foreign_net_qianzhang,
    state,
)


def _day(foreign=0.0, etf=0.0, close=100.0, shares=0.0):
    return {
        "foreign_flow_yi": foreign,
        "etf_flow_yi": etf,
        "close": close,
        "adjustedClose": close,
        "shares": shares,
    }


class TestUnits(unittest.TestCase):
    def test_qianzhang_to_shares(self):
        self.assertEqual(shares_from_foreign_net_qianzhang(2.5), 2_500_000.0)

    def test_flow_yi_from_net_honest(self):
        # foreign_net=1 千張, price=100 → 1e6 shares * 100 / 1e8 = 1.0 億
        self.assertAlmostEqual(foreign_flow_yi_from_net(1.0, 100.0), 1.0)
        self.assertAlmostEqual(
            foreign_flow_yi_from_shares(shares_from_foreign_net_qianzhang(1.0), 100.0),
            1.0,
        )
        # NOT /1e5:
        self.assertNotAlmostEqual(foreign_flow_yi_from_net(1.0, 100.0), 1.0 * 100 / 1e5)


class TestFlowOf(unittest.TestCase):
    def test_modes(self):
        d = _day(foreign=3.0, etf=1.5)
        self.assertEqual(flow_of(d, "foreign"), 3.0)
        self.assertEqual(flow_of(d, "etf"), 1.5)
        self.assertEqual(flow_of(d, "combined"), 4.5)


class TestRolling(unittest.TestCase):
    def test_window_and_momentum(self):
        # 11 days so frame 0..5 available; days[0] warmup for frame0 (end=5)
        flows = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
        days = [_day(foreign=float(f), close=100 + i) for i, f in enumerate(flows)]
        self.assertEqual(WINDOW, 5)

        # frame=0 → start=1,end=5 → sum 2+3+4+5+6=20
        st = state(days, 0, "foreign")
        self.assertIsNotNone(st)
        self.assertAlmostEqual(st["rolling"], 20.0)
        # prior start=0,end=4 → 1+2+3+4+5=15; momentum=5
        self.assertAlmostEqual(st["momentum"], 5.0)
        self.assertAlmostEqual(st["daily_flow"], 6.0)

        # ret: close[5]/close[0]-1)*100 = (105/100-1)*100=5
        self.assertAlmostEqual(st["rolling_ret"], 5.0)

    def test_prior_fallback_when_incomplete(self):
        days = [_day(foreign=float(i + 1)) for i in range(5)]
        # enrich path: at end=4, start=0, prior needs -1 → fallback
        r = rolling_sum(days, 0, 4, "foreign")
        self.assertAlmostEqual(r, 15.0)
        prior = rolling_sum(days, -1, 3, "foreign")
        self.assertIsNone(prior)

    def test_combined_rolling(self):
        days = [_day(foreign=1.0, etf=0.5) for _ in range(6)]
        st = state(days, 0, "combined")
        self.assertAlmostEqual(st["rolling"], 7.5)  # 5 days * 1.5


class TestNormalize(unittest.TestCase):
    def test_bounds(self):
        self.assertEqual(normalize(0, 1), 0.0)
        self.assertTrue(-1 <= normalize(1000, 1) <= 1)
        self.assertTrue(-1 <= normalize(-1000, 1) <= 1)
        # asinh(3)/asinh(3)=1
        self.assertAlmostEqual(normalize(3, 1), 1.0)
        self.assertAlmostEqual(normalize(-3, 1), -1.0)


class TestEnrich(unittest.TestCase):
    def test_enrich_fields(self):
        days = [_day(foreign=float(i + 1), etf=0.1, close=100 + i, shares=1000) for i in range(8)]
        enriched = enrich_day_metrics(days)
        # first full rolling at index 4
        self.assertIn("rolling_foreign_5d_yi", enriched[4])
        self.assertAlmostEqual(enriched[4]["rolling_foreign_5d_yi"], 15.0)
        # momentum + ret from index 5
        self.assertIn("momentum_foreign_5d_yi", enriched[5])
        self.assertAlmostEqual(enriched[5]["rolling_foreign_5d_yi"], 20.0)
        self.assertAlmostEqual(enriched[5]["momentum_foreign_5d_yi"], 5.0)
        self.assertAlmostEqual(enriched[5]["combined_flow_yi"], 6.1)
        self.assertAlmostEqual(enriched[5]["rolling_ret_5d"], 5.0)


if __name__ == "__main__":
    unittest.main()
