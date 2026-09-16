import logging
import time
from typing import Literal

import lighter

from app.indicators import get_ema, get_macd, get_mid_prices
from app.lighter_client import close_client, create_api_client
from app.utils import round_to_3

logger = logging.getLogger(__name__)

Duration = Literal["5m", "4h"]


async def get_indicators(duration: Duration, market_id: int) -> dict[str, list[float]]:
    lookback_hours = 2 if duration == "5m" else 96
    end_timestamp = int(time.time() * 1000)
    start_timestamp = end_timestamp - 1000 * 60 * 60 * lookback_hours

    api_client = create_api_client()
    try:
        candlestick_api = lighter.CandlestickApi(api_client)
        # Candlestick timestamps are milliseconds.
        candles_response = await candlestick_api.candles(
            market_id,
            duration,
            start_timestamp,
            end_timestamp,
            50,
            set_timestamp_to_end=False,
        )
        raw_candles = getattr(candles_response, "c", None)
        if raw_candles is None:
            raw_candles = getattr(candles_response, "candlesticks", None) or []
        raw_candles = list(raw_candles)
        logger.info(
            "Fetched %s candles for market_id=%s duration=%s",
            len(raw_candles),
            market_id,
            duration,
        )
        mid_prices = get_mid_prices(raw_candles)
        macd = get_macd(mid_prices)[-10:]
        ema20s = get_ema(mid_prices, 20)
        return {
            "midPrices": [round_to_3(value) for value in mid_prices[-10:]],
            "macd": [round_to_3(value) for value in macd[-10:]],
            "ema20s": [round_to_3(value) for value in ema20s[-10:]],
        }
    finally:
        await close_client(api_client)
