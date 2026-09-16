from app.utils import round_to_3


def _candle_price(candle: object, abbreviated_name: str, full_name: str) -> float:
    if hasattr(candle, abbreviated_name):
        value = getattr(candle, abbreviated_name)
        if value is not None:
            return float(value)
    return float(getattr(candle, full_name))


def get_ema(prices: list[float], period: int) -> list[float]:
    if len(prices) < period:
        raise ValueError("Not enough prices provided")

    multiplier = 2 / (period + 1)
    sma = sum(prices[:period]) / period
    emas = [sma]
    for index in range(period, len(prices)):
        ema = emas[-1] * (1 - multiplier) + prices[index] * multiplier
        emas.append(ema)
    return emas


def get_mid_prices(candlesticks: list[object]) -> list[float]:
    mid_prices: list[float] = []
    for candle in candlesticks:
        open_price = _candle_price(candle, "o", "open")
        close_price = _candle_price(candle, "c", "close")
        mid_prices.append(round_to_3((open_price + close_price) / 2))
    return mid_prices


def get_macd(prices: list[float]) -> list[float]:
    ema26 = get_ema(prices, 26)
    ema12 = get_ema(prices, 12)
    ema12 = ema12[-len(ema26) :]
    return [ema12[index] - ema26[index] for index in range(len(ema26))]
