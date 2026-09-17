import unittest

from app.leaderboard import rank_models


class LeaderboardRankingTests(unittest.TestCase):
    def test_ranks_by_pnl_descending(self):
        entries = rank_models(
            [
                ("b", "qwen", 900.0),
                ("a", "claude", 1500.0),
                ("c", "deepseek", 1100.0),
            ],
            1000.0,
        )
        self.assertEqual([entry.name for entry in entries], ["claude", "deepseek", "qwen"])
        self.assertEqual([entry.rank for entry in entries], [1, 2, 3])
        self.assertEqual(entries[0].pnl, 500.0)
        self.assertEqual(entries[0].return_pct, 50.0)
        self.assertEqual(entries[2].pnl, -100.0)
        self.assertEqual(entries[2].return_pct, -10.0)

    def test_models_without_data_are_unranked_at_bottom(self):
        entries = rank_models(
            [
                ("a", "claude", None),
                ("b", "qwen", 1200.0),
                ("c", "deepseek", None),
            ],
            1000.0,
        )
        self.assertEqual(entries[0].name, "qwen")
        self.assertEqual(entries[0].rank, 1)
        self.assertEqual([entry.name for entry in entries[1:]], ["claude", "deepseek"])
        self.assertTrue(all(entry.rank is None and entry.current_value is None for entry in entries[1:]))

    def test_rejects_zero_starting_value(self):
        with self.assertRaises(ValueError):
            rank_models([("a", "claude", 1000.0)], 0.0)
