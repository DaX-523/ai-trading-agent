import logging
from typing import Any, Protocol

from app.accounts import Account
from app.config import LIGHTER_MAINNET_BASE_URL, LIGHTER_TESTNET_BASE_URL
from app.db_models import TradingMode
from app import paper_trading, positions

logger = logging.getLogger(__name__)


class TradingBackend(Protocol):
    async def get_portfolio(self, account: Account) -> dict[str, str]:
        ...

    async def get_open_positions(self, account: Account) -> list[dict[str, Any]]:
        ...

    async def create_position(self, account: Account, symbol: str, side: str, quantity: float) -> None:
        ...

    async def cancel_all_orders(self, account: Account) -> None:
        ...


class PaperTradingBackend:
    async def get_portfolio(self, account: Account) -> dict[str, str]:
        return await paper_trading.get_portfolio(account)

    async def get_open_positions(self, account: Account) -> list[dict[str, Any]]:
        return await paper_trading.get_open_positions(account)

    async def create_position(self, account: Account, symbol: str, side: str, quantity: float) -> None:
        await paper_trading.create_position(account, symbol, side, quantity)

    async def cancel_all_orders(self, account: Account) -> None:
        await paper_trading.cancel_all_orders(account)


class LighterTradingBackend:
    def __init__(self, *, base_url: str, use_testnet_credentials: bool) -> None:
        self.base_url = base_url
        self.use_testnet_credentials = use_testnet_credentials

    def resolve_credentials(self, account: Account) -> tuple[str, str]:
        if self.use_testnet_credentials:
            api_key = (account.testnet_api_key or "").strip()
            account_index = (account.testnet_account_index or "").strip()
            if not api_key or not account_index:
                raise RuntimeError(
                    f"Testnet credentials are not configured for model={account.name}"
                )
            return api_key, account_index

        api_key = (account.api_key or "").strip()
        account_index = (account.account_index or "").strip()
        if not api_key or not account_index:
            raise RuntimeError(
                f"Mainnet credentials are not configured for model={account.name}"
            )
        return api_key, account_index

    async def get_portfolio(self, account: Account) -> dict[str, str]:
        _api_key, account_index = self.resolve_credentials(account)
        return await positions.get_portfolio(base_url=self.base_url, account_index=account_index)

    async def get_open_positions(self, account: Account) -> list[dict[str, Any]]:
        _api_key, account_index = self.resolve_credentials(account)
        return await positions.get_open_positions(base_url=self.base_url, account_index=account_index)

    async def create_position(self, account: Account, symbol: str, side: str, quantity: float) -> None:
        api_key, account_index = self.resolve_credentials(account)
        await positions.create_position(
            base_url=self.base_url,
            api_key=api_key,
            account_index=account_index,
            symbol=symbol,
            side=side,
            quantity=quantity,
        )

    async def cancel_all_orders(self, account: Account) -> None:
        api_key, account_index = self.resolve_credentials(account)
        await positions.cancel_all_orders(
            base_url=self.base_url,
            api_key=api_key,
            account_index=account_index,
        )


def get_trading_backend(mode: TradingMode) -> TradingBackend:
    if mode == TradingMode.SANDBOX:
        logger.info("Using paper trading backend")
        return PaperTradingBackend()
    if mode == TradingMode.TESTNET:
        logger.info("Using Lighter testnet backend url=%s", LIGHTER_TESTNET_BASE_URL)
        return LighterTradingBackend(
            base_url=LIGHTER_TESTNET_BASE_URL,
            use_testnet_credentials=True,
        )
    if mode == TradingMode.LIVE:
        logger.info("Using Lighter mainnet backend url=%s", LIGHTER_MAINNET_BASE_URL)
        return LighterTradingBackend(
            base_url=LIGHTER_MAINNET_BASE_URL,
            use_testnet_credentials=False,
        )
    raise ValueError(f"Unknown trading mode: {mode}")
