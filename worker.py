import asyncio
import logging

from sqlalchemy import select

from app.accounts import Account
from app.agent import invoke_agent
from app.config import AGENT_INTERVAL_SECONDS, PRICE_TRACKER_INTERVAL_SECONDS
from app.db import SessionLocal
from app.db_models import Models, PortfolioSize
from app.settings_repo import get_active_trading_mode
from app.trading_backend import get_trading_backend

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _load_accounts() -> list[Account]:
    with SessionLocal() as session:
        models = session.scalars(select(Models)).all()
        return [
            Account(
                api_key=model.lighterApiKey or "",
                name=model.name,
                model_name=model.openRoutermodelName,
                invocation_count=model.invocationCount,
                id=model.id,
                account_index=model.accountIndex or "",
                testnet_api_key=model.testnetLighterApiKey,
                testnet_account_index=model.testnetAccountIndex,
            )
            for model in models
        ]


async def run_agent_cycle() -> None:
    mode = get_active_trading_mode()
    accounts = _load_accounts()
    logger.info("Agent cycle starting for %s models mode=%s", len(accounts), mode.value)
    for account in accounts:
        try:
            await invoke_agent(account, mode)
        except Exception:
            logger.exception("Agent invocation failed for model=%s mode=%s", account.name, mode.value)


async def run_price_tracker_cycle() -> None:
    mode = get_active_trading_mode()
    backend = get_trading_backend(mode)
    accounts = _load_accounts()
    logger.info("Price tracker cycle starting for %s models mode=%s", len(accounts), mode.value)
    for account in accounts:
        try:
            portfolio = await backend.get_portfolio(account)
            with SessionLocal() as session:
                session.add(
                    PortfolioSize(
                        modelId=account.id,
                        netPortfolio=str(portfolio["total"]),
                        tradingMode=mode,
                    )
                )
                session.commit()
        except Exception:
            logger.exception("Price tracker failed for model=%s mode=%s", account.name, mode.value)


async def agent_loop() -> None:
    await run_agent_cycle()
    while True:
        await asyncio.sleep(AGENT_INTERVAL_SECONDS)
        await run_agent_cycle()


async def price_tracker_loop() -> None:
    while True:
        await asyncio.sleep(PRICE_TRACKER_INTERVAL_SECONDS)
        await run_price_tracker_cycle()


async def main() -> None:
    logger.info(
        "Worker started agent_interval=%ss price_tracker_interval=%ss",
        AGENT_INTERVAL_SECONDS,
        PRICE_TRACKER_INTERVAL_SECONDS,
    )
    await asyncio.gather(agent_loop(), price_tracker_loop())


if __name__ == "__main__":
    asyncio.run(main())
