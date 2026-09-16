import unittest
from types import SimpleNamespace

from app.indicators import get_ema, get_macd, get_mid_prices


class IndicatorTests(unittest.TestCase):
    def test_get_ema_matches_seed_sma(self):
        prices = [1.0, 2.0, 3.0, 4.0, 5.0]
        emas = get_ema(prices, 3)
        self.assertEqual(emas[0], 2.0)
        self.assertEqual(len(emas), 3)

    def test_get_ema_requires_enough_prices(self):
        with self.assertRaises(ValueError):
            get_ema([1.0, 2.0], 3)

    def test_get_mid_prices_from_abbreviated_candles(self):
        candles = [
            SimpleNamespace(o=10.0, c=12.0),
            SimpleNamespace(o=1.111, c=1.111),
        ]
        self.assertEqual(get_mid_prices(candles), [11.0, 1.111])

    def test_get_macd_aligns_ema_lengths(self):
        prices = [float(index) for index in range(1, 40)]
        macd = get_macd(prices)
        self.assertEqual(len(macd), len(get_ema(prices, 26)))


if __name__ == "__main__":
    unittest.main()
