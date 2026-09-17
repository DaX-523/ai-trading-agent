import unittest

from app.paper_trading import (
    apply_close_position,
    apply_open_position,
    assert_sufficient_cash,
    compute_required_margin,
    compute_unrealized_pnl,
)


class PaperTradingMathTests(unittest.TestCase):
    def test_long_profit(self):
        pnl = compute_unrealized_pnl(100.0, 110.0, "LONG", 2.0)
        self.assertEqual(pnl, 20.0)

    def test_long_loss(self):
        pnl = compute_unrealized_pnl(100.0, 90.0, "LONG", 2.0)
        self.assertEqual(pnl, -20.0)

    def test_short_profit(self):
        pnl = compute_unrealized_pnl(100.0, 90.0, "SHORT", 2.0)
        self.assertEqual(pnl, 20.0)

    def test_short_loss(self):
        pnl = compute_unrealized_pnl(100.0, 110.0, "SHORT", 2.0)
        self.assertEqual(pnl, -20.0)

    def test_rejects_unknown_side(self):
        with self.assertRaises(ValueError):
            compute_unrealized_pnl(100.0, 110.0, "FLAT", 1.0)

    def test_rejects_negative_quantity(self):
        with self.assertRaises(ValueError):
            compute_unrealized_pnl(100.0, 110.0, "LONG", -1.0)

    def test_required_margin_uses_leverage(self):
        margin = compute_required_margin(2.0, 100.0, 10.0)
        self.assertEqual(margin, 20.0)

    def test_required_margin_rejects_non_positive_inputs(self):
        with self.assertRaises(ValueError):
            compute_required_margin(1.0, 100.0, 0.0)
        with self.assertRaises(ValueError):
            compute_required_margin(0.0, 100.0, 10.0)

    def test_insufficient_cash_rejected(self):
        with self.assertRaises(ValueError):
            assert_sufficient_cash(10.0, 20.0)
        with self.assertRaises(ValueError):
            apply_open_position(10.0, 20.0)

    def test_open_position_deducts_margin(self):
        self.assertEqual(apply_open_position(1000.0, 200.0), 800.0)

    def test_close_position_returns_margin_plus_pnl(self):
        self.assertEqual(apply_close_position(800.0, 200.0, 50.0), 1050.0)
        self.assertEqual(apply_close_position(800.0, 200.0, -50.0), 950.0)
