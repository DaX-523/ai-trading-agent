import logging
import time
from typing import Any

import httpx
import lighter

from app.config import LIGHTER_MAINNET_BASE_URL
from app.lighter_client import close_client, create_api_client, create_signer_client
from app.markets import MARKETS

logger = logging.getLogger(__name__)


async def get_portfolio(*, base_url: str, account_index: str) -> dict[str, str]:
    url = f"{base_url}/api/v1/account"
    params = {"by": "index", "value": account_index}
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
    except Exception:
        logger.exception("Failed to fetch portfolio for account_index=%s", account_index)
        raise

    accounts = payload.get("accounts") or []
    if not accounts:
        raise ValueError(f"No account found for index {account_index}")
    first_account = accounts[0]
    return {
        "total": first_account.get("collateral"),
        "available": first_account.get("available_balance"),
    }


async def get_open_positions(*, base_url: str, account_index: str) -> list[dict[str, Any]]:
    api_client = create_api_client(base_url)
    try:
        account_api = lighter.AccountApi(api_client)
        response = await account_api.account("index", account_index)
        accounts = getattr(response, "accounts", None) or []
        if not accounts:
            return []
        positions = getattr(accounts[0], "positions", None) or []
        mapped = []
        for account_position in positions:
            sign_value = getattr(account_position, "sign")
            mapped.append(
                {
                    "symbol": getattr(account_position, "symbol"),
                    "position": getattr(account_position, "position"),
                    "sign": "LONG" if sign_value == 1 else "SHORT",
                    "unrealizedPnl": getattr(account_position, "unrealized_pnl", getattr(account_position, "unrealizedPnl", None)),
                    "realizedPnl": getattr(account_position, "realized_pnl", getattr(account_position, "realizedPnl", None)),
                    "liquidationPrice": getattr(
                        account_position,
                        "liquidation_price",
                        getattr(account_position, "liquidationPrice", None),
                    ),
                }
            )
        return mapped
    except Exception:
        logger.exception("Failed to fetch open positions for account_index=%s", account_index)
        raise
    finally:
        await close_client(api_client)


async def get_latest_close_price(market_id: int) -> float:
    api_client = create_api_client(LIGHTER_MAINNET_BASE_URL)
    try:
        candlestick_api = lighter.CandlestickApi(api_client)
        end_timestamp = int(time.time() * 1000)
        start_timestamp = end_timestamp - 1000 * 60 * 5
        candles_response = await candlestick_api.candles(
            market_id,
            "1m",
            start_timestamp,
            end_timestamp,
            1,
            set_timestamp_to_end=False,
        )
        raw_candles = getattr(candles_response, "c", None)
        if raw_candles is None:
            raw_candles = getattr(candles_response, "candlesticks", None) or []
        raw_candles = list(raw_candles)
        if not raw_candles:
            raise ValueError("No latest price found")
        latest_candle = raw_candles[-1]
        close_price = getattr(latest_candle, "c", getattr(latest_candle, "close", None))
        if close_price is None:
            raise ValueError("No latest price found")
        return float(close_price)
    finally:
        await close_client(api_client)


async def create_position(
    *,
    base_url: str,
    api_key: str,
    account_index: str,
    symbol: str,
    side: str,
    quantity: float,
) -> None:
    if symbol not in MARKETS:
        raise ValueError(f"Unknown market symbol: {symbol}")

    market = MARKETS[symbol]
    latest_price = await get_latest_close_price(market["marketId"])
    worst_price = latest_price * 1.01 if side == "LONG" else latest_price * 0.99
    base_amount = int(round(quantity * market["qtyDecimals"]))
    price = int(round(worst_price * market["priceDecimals"]))
    is_ask = side != "LONG"

    logger.info(
        "Creating %s position symbol=%s quantity=%s base_amount=%s price=%s account_index=%s base_url=%s",
        side,
        symbol,
        quantity,
        base_amount,
        price,
        account_index,
        base_url,
    )

    client = create_signer_client(base_url=base_url, account_index=account_index, api_key=api_key)
    try:
        _tx, api_response, error = await client.create_order(
            market_index=market["marketId"],
            client_order_index=market["clientOrderIndex"],
            base_amount=base_amount,
            price=price,
            is_ask=is_ask,
            order_type=client.ORDER_TYPE_MARKET,
            time_in_force=client.ORDER_TIME_IN_FORCE_IMMEDIATE_OR_CANCEL,
            reduce_only=False,
            trigger_price=client.NIL_TRIGGER_PRICE,
            order_expiry=client.DEFAULT_IOC_EXPIRY,
        )
        if error is not None:
            raise RuntimeError(f"Failed to create position: {error}")
        logger.info("create_order response=%s", api_response)
    except Exception:
        logger.exception("create_position failed symbol=%s side=%s", symbol, side)
        raise
    finally:
        await close_client(client)


async def cancel_all_orders(*, base_url: str, api_key: str, account_index: str) -> None:
    open_positions = await get_open_positions(base_url=base_url, account_index=account_index)
    client = create_signer_client(base_url=base_url, account_index=account_index, api_key=api_key)
    try:
        for open_position in open_positions:
            position_size = float(open_position["position"])
            if position_size == 0:
                continue
            symbol = open_position["symbol"]
            if symbol not in MARKETS:
                logger.warning("Skipping close for unknown symbol=%s", symbol)
                continue
            market = MARKETS[symbol]
            latest_price = await get_latest_close_price(market["marketId"])
            close_side = "SHORT" if open_position["sign"] == "LONG" else "LONG"
            worst_price = latest_price * 1.01 if close_side == "LONG" else latest_price * 0.99
            base_amount = int(round(abs(position_size) * market["qtyDecimals"]))
            price = int(round(worst_price * market["priceDecimals"]))
            is_ask = close_side != "LONG"
            logger.info(
                "Closing position symbol=%s live_sign=%s close_side=%s base_amount=%s",
                symbol,
                open_position["sign"],
                close_side,
                base_amount,
            )
            _tx, api_response, error = await client.create_order(
                market_index=market["marketId"],
                client_order_index=market["clientOrderIndex"],
                base_amount=base_amount,
                price=price,
                is_ask=is_ask,
                order_type=client.ORDER_TYPE_MARKET,
                time_in_force=client.ORDER_TIME_IN_FORCE_IMMEDIATE_OR_CANCEL,
                reduce_only=False,
                trigger_price=client.NIL_TRIGGER_PRICE,
                order_expiry=client.DEFAULT_IOC_EXPIRY,
            )
            if error is not None:
                raise RuntimeError(f"Failed to close position for {symbol}: {error}")
            logger.info("close order response=%s", api_response)
    except Exception:
        logger.exception("cancel_all_orders failed account_index=%s", account_index)
        raise
    finally:
        await close_client(client)
