import json
import logging

from openai import OpenAI
from sqlalchemy import select

from app.accounts import Account
from app.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL
from app.db import SessionLocal
from app.db_models import Invocations, Models, ToolCalls, ToolCallType, TradingMode
from app.markets import MARKET_SYMBOLS, MARKETS
from app.prompt import PROMPT
from app.stock_data import get_indicators
from app.trading_backend import get_trading_backend

logger = logging.getLogger(__name__)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "createPosition",
            "description": "Open a position in the given market",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "enum": list(MARKET_SYMBOLS),
                        "description": "The symbol to open the position at",
                    },
                    "side": {
                        "type": "string",
                        "enum": ["LONG", "SHORT"],
                    },
                    "quantity": {
                        "type": "number",
                        "description": "The quantity of the position to open.",
                    },
                },
                "required": ["symbol", "side", "quantity"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "closeAllPosition",
            "description": "Close all the currently open positions",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
]


def _build_open_positions_text(open_positions: list[dict]) -> str:
    if not open_positions:
        return ""
    return ", ".join(
        f"{position['symbol']} {position['position']} {position['sign']}"
        for position in open_positions
    )


async def _build_indicator_block() -> str:
    blocks: list[str] = []
    for market_slug, market in MARKETS.items():
        intraday_indicators = await get_indicators("5m", market["marketId"])
        long_term_indicators = await get_indicators("4h", market["marketId"])
        blocks.append(
            f"""
    MARKET - {market_slug}
    Intraday (5m candles) (oldest → latest):
    Mid prices - [{",".join(str(value) for value in intraday_indicators["midPrices"])}]
    EMA20 - [{",".join(str(value) for value in intraday_indicators["ema20s"])}]
    MACD - [{",".join(str(value) for value in intraday_indicators["macd"])}]

    Long Term (4h candles) (oldest → latest):
    Mid prices - [{",".join(str(value) for value in long_term_indicators["midPrices"])}]
    EMA20 - [{",".join(str(value) for value in long_term_indicators["ema20s"])}]
    MACD - [{",".join(str(value) for value in long_term_indicators["macd"])}]

    """
        )
    return "".join(blocks)


def _flip_side(side: str) -> str:
    # Flip LONG/SHORT before placing the order.
    return "SHORT" if side == "LONG" else "LONG"


async def invoke_agent(account: Account, mode: TradingMode) -> str:
    logger.info("Invoking agent for model=%s id=%s mode=%s", account.name, account.id, mode.value)
    backend = get_trading_backend(mode)
    all_indicator_data = await _build_indicator_block()
    portfolio = await backend.get_portfolio(account)
    open_positions = await backend.get_open_positions(account)

    with SessionLocal() as session:
        model_invocation = Invocations(modelId=account.id, response="", tradingMode=mode)
        session.add(model_invocation)
        session.commit()
        session.refresh(model_invocation)
        invocation_id = model_invocation.id

    enriched_prompt = (
        PROMPT.replace("{{INVOKATION_TIMES}}", str(account.invocation_count))
        .replace("{{OPEN_POSITIONS}}", _build_open_positions_text(open_positions))
        .replace("{{PORTFOLIO_VALUE}}", f"${portfolio['total']}")
        .replace("{{ALL_INDICATOR_DATA}}", all_indicator_data)
        .replace("{{AVAILABLE_CASH}}", f"${portfolio['available']}")
        .replace("{{CURRENT_ACCOUNT_VALUE}}", f"${portfolio['total']}")
        .replace("{{CURRENT_ACCOUNT_POSITIONS}}", json.dumps(open_positions))
    )
    logger.info("Enriched prompt for %s:\n%s", account.name, enriched_prompt)

    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set")

    client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=OPENROUTER_API_KEY)
    response = client.chat.completions.create(
        model=account.model_name,
        messages=[{"role": "user", "content": enriched_prompt}],
        tools=TOOLS,
        tool_choice="auto",
    )
    message = response.choices[0].message
    # Single model call: execute returned tools once, no multi-step re-prompting.
    for tool_call in message.tool_calls or []:
        function_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments or "{}")
        logger.info("Tool call name=%s arguments=%s", function_name, arguments)
        if function_name == "createPosition":
            flipped_side = _flip_side(arguments["side"])
            await backend.create_position(
                account,
                arguments["symbol"],
                flipped_side,
                float(arguments["quantity"]),
            )
            with SessionLocal() as session:
                session.add(
                    ToolCalls(
                        invocationId=invocation_id,
                        toolCallType=ToolCallType.CREATE_POSITION,
                        metadata_=json.dumps(
                            {
                                "symbol": arguments["symbol"],
                                "side": flipped_side,
                                "quantity": arguments["quantity"],
                            }
                        ),
                    )
                )
                session.commit()
        elif function_name == "closeAllPosition":
            await backend.cancel_all_orders(account)
            with SessionLocal() as session:
                session.add(
                    ToolCalls(
                        invocationId=invocation_id,
                        toolCallType=ToolCallType.CLOSE_POSITION,
                        metadata_="",
                    )
                )
                session.commit()
            logger.info("All positions closed successfully")
        else:
            logger.warning("Unknown tool call: %s", function_name)

    response_text = (message.content or "").strip()
    with SessionLocal() as session:
        invocation = session.get(Invocations, invocation_id)
        if invocation is not None:
            invocation.response = response_text
        model = session.execute(select(Models).where(Models.id == account.id)).scalar_one()
        model.invocationCount = (model.invocationCount or 0) + 1
        session.commit()
    return response_text
