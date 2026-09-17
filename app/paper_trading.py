import logging
from typing import Any

from sqlalchemy import select

from app.accounts import Account
from app.config import STARTING_PORTFOLIO_VALUE
from app.db import SessionLocal
from app.db_models import PaperAccounts, PaperPositions, utc_now
from app.markets import MARKETS
from app.positions import get_latest_close_price

logger = logging.getLogger(__name__)


def compute_unrealized_pnl(
    entry_price: float,
    current_price: float,
    side: str,
    quantity: float,
) -> float:
    if quantity < 0:
        raise ValueError("quantity must be non-negative")
    normalized_side = side.upper()
    if normalized_side == "LONG":
        return (current_price - entry_price) * quantity
    if normalized_side == "SHORT":
        return (entry_price - current_price) * quantity
    raise ValueError(f"Unknown side: {side}")


def compute_required_margin(quantity: float, price: float, leverage: float) -> float:
    if leverage <= 0:
        raise ValueError("leverage must be positive")
    if quantity <= 0:
        raise ValueError("quantity must be positive")
    if price <= 0:
        raise ValueError("price must be positive")
    return (quantity * price) / leverage


def assert_sufficient_cash(cash: float, required_margin: float) -> None:
    if cash < required_margin:
        raise ValueError(
            f"Insufficient cash for margin: available={cash} required={required_margin}"
        )


def apply_open_position(cash: float, required_margin: float) -> float:
    assert_sufficient_cash(cash, required_margin)
    return cash - required_margin


def apply_close_position(cash: float, margin_reserved: float, realized_pnl: float) -> float:
    return cash + margin_reserved + realized_pnl


def _get_or_create_paper_account(session, model_id: str) -> PaperAccounts:
    paper_account = session.execute(
        select(PaperAccounts).where(PaperAccounts.modelId == model_id)
    ).scalar_one_or_none()
    if paper_account is None:
        paper_account = PaperAccounts(
            modelId=model_id,
            cashBalance=str(STARTING_PORTFOLIO_VALUE),
        )
        session.add(paper_account)
        session.flush()
        logger.info("Created paper account for model_id=%s starting_cash=%s", model_id, STARTING_PORTFOLIO_VALUE)
    return paper_account


def _open_positions_query(model_id: str):
    return select(PaperPositions).where(
        PaperPositions.modelId == model_id,
        PaperPositions.closedAt.is_(None),
    )


async def _mark_price_for_symbol(symbol: str) -> float:
    if symbol not in MARKETS:
        raise ValueError(f"Unknown market symbol: {symbol}")
    return await get_latest_close_price(MARKETS[symbol]["marketId"])


async def get_portfolio(account: Account) -> dict[str, str]:
    with SessionLocal() as session:
        paper_account = _get_or_create_paper_account(session, account.id)
        open_positions = session.execute(_open_positions_query(account.id)).scalars().all()
        cash = float(paper_account.cashBalance)
        snapshot = [
            {
                "symbol": position.symbol,
                "side": position.side,
                "quantity": float(position.quantity),
                "entryPrice": float(position.entryPrice),
                "marginReserved": float(position.marginReserved),
            }
            for position in open_positions
        ]
        session.commit()

    unrealized_total = 0.0
    reserved_margin = 0.0
    for position in snapshot:
        current_price = await _mark_price_for_symbol(position["symbol"])
        unrealized_total += compute_unrealized_pnl(
            position["entryPrice"],
            current_price,
            position["side"],
            position["quantity"],
        )
        reserved_margin += position["marginReserved"]

    total = cash + reserved_margin + unrealized_total
    logger.info(
        "Paper portfolio model=%s cash=%s reserved=%s unrealized=%s total=%s",
        account.name,
        cash,
        reserved_margin,
        unrealized_total,
        total,
    )
    return {
        "total": str(total),
        "available": str(cash),
    }


async def get_open_positions(account: Account) -> list[dict[str, Any]]:
    with SessionLocal() as session:
        open_positions = session.execute(_open_positions_query(account.id)).scalars().all()
        snapshot = [
            {
                "symbol": position.symbol,
                "side": position.side,
                "quantity": float(position.quantity),
                "entryPrice": float(position.entryPrice),
                "realizedPnl": position.realizedPnl,
            }
            for position in open_positions
        ]

    mapped = []
    for position in snapshot:
        current_price = await _mark_price_for_symbol(position["symbol"])
        unrealized = compute_unrealized_pnl(
            position["entryPrice"],
            current_price,
            position["side"],
            position["quantity"],
        )
        mapped.append(
            {
                "symbol": position["symbol"],
                "position": str(position["quantity"]),
                "sign": position["side"],
                "unrealizedPnl": str(unrealized),
                "realizedPnl": position["realizedPnl"],
                "liquidationPrice": None,
            }
        )
    return mapped


async def create_position(account: Account, symbol: str, side: str, quantity: float) -> None:
    if symbol not in MARKETS:
        raise ValueError(f"Unknown market symbol: {symbol}")
    normalized_side = side.upper()
    if normalized_side not in {"LONG", "SHORT"}:
        raise ValueError(f"Unknown side: {side}")
    if quantity <= 0:
        raise ValueError("quantity must be positive")

    market = MARKETS[symbol]
    latest_price = await get_latest_close_price(market["marketId"])
    required_margin = compute_required_margin(quantity, latest_price, float(market["leverage"]))

    with SessionLocal() as session:
        paper_account = _get_or_create_paper_account(session, account.id)
        cash = float(paper_account.cashBalance)
        new_cash = apply_open_position(cash, required_margin)
        paper_account.cashBalance = str(new_cash)
        session.add(
            PaperPositions(
                modelId=account.id,
                symbol=symbol,
                side=normalized_side,
                quantity=str(quantity),
                entryPrice=str(latest_price),
                marginReserved=str(required_margin),
                realizedPnl="0",
            )
        )
        session.commit()

    logger.info(
        "Opened paper %s position model=%s symbol=%s quantity=%s price=%s margin=%s",
        normalized_side,
        account.name,
        symbol,
        quantity,
        latest_price,
        required_margin,
    )


async def cancel_all_orders(account: Account) -> None:
    with SessionLocal() as session:
        open_positions = session.execute(_open_positions_query(account.id)).scalars().all()
        snapshot = [
            {
                "id": position.id,
                "symbol": position.symbol,
                "side": position.side,
                "quantity": float(position.quantity),
                "entryPrice": float(position.entryPrice),
                "marginReserved": float(position.marginReserved),
            }
            for position in open_positions
        ]

    if not snapshot:
        logger.info("No open paper positions to close for model=%s", account.name)
        return

    realized_by_id: dict[str, float] = {}
    cash_credit = 0.0
    for position in snapshot:
        current_price = await _mark_price_for_symbol(position["symbol"])
        realized = compute_unrealized_pnl(
            position["entryPrice"],
            current_price,
            position["side"],
            position["quantity"],
        )
        realized_by_id[position["id"]] = realized
        cash_credit += apply_close_position(0.0, position["marginReserved"], realized)
        logger.info(
            "Closing paper position model=%s symbol=%s side=%s qty=%s pnl=%s",
            account.name,
            position["symbol"],
            position["side"],
            position["quantity"],
            realized,
        )

    closed_at = utc_now()
    with SessionLocal() as session:
        paper_account = _get_or_create_paper_account(session, account.id)
        paper_account.cashBalance = str(float(paper_account.cashBalance) + cash_credit)
        open_positions = session.execute(_open_positions_query(account.id)).scalars().all()
        for position in open_positions:
            if position.id not in realized_by_id:
                continue
            position.realizedPnl = str(realized_by_id[position.id])
            position.closedAt = closed_at
        session.commit()
