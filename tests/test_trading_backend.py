import unittest

from app.accounts import Account
from app.config import LIGHTER_MAINNET_BASE_URL, LIGHTER_TESTNET_BASE_URL
from app.db_models import TradingMode
from app.trading_backend import LighterTradingBackend, PaperTradingBackend, get_trading_backend


class TradingBackendFactoryTests(unittest.TestCase):
    def test_sandbox_returns_paper_backend(self):
        backend = get_trading_backend(TradingMode.SANDBOX)
        self.assertIsInstance(backend, PaperTradingBackend)

    def test_testnet_uses_testnet_url_and_credentials(self):
        backend = get_trading_backend(TradingMode.TESTNET)
        self.assertIsInstance(backend, LighterTradingBackend)
        self.assertEqual(backend.base_url, LIGHTER_TESTNET_BASE_URL)
        self.assertTrue(backend.use_testnet_credentials)

    def test_live_uses_mainnet_url_and_credentials(self):
        backend = get_trading_backend(TradingMode.LIVE)
        self.assertIsInstance(backend, LighterTradingBackend)
        self.assertEqual(backend.base_url, LIGHTER_MAINNET_BASE_URL)
        self.assertFalse(backend.use_testnet_credentials)

    def test_testnet_rejects_missing_credentials(self):
        backend = get_trading_backend(TradingMode.TESTNET)
        self.assertIsInstance(backend, LighterTradingBackend)
        account = Account(
            api_key="main-key",
            name="claude",
            model_name="anthropic/claude",
            invocation_count=0,
            id="1",
            account_index="1",
        )
        with self.assertRaises(RuntimeError):
            backend.resolve_credentials(account)

    def test_live_rejects_missing_credentials(self):
        backend = get_trading_backend(TradingMode.LIVE)
        self.assertIsInstance(backend, LighterTradingBackend)
        account = Account(
            api_key="",
            name="claude",
            model_name="anthropic/claude",
            invocation_count=0,
            id="1",
            account_index="",
        )
        with self.assertRaises(RuntimeError):
            backend.resolve_credentials(account)
