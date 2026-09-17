import hmac
import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from app.config import ADMIN_API_TOKEN, SERVER_PORT, STARTING_PORTFOLIO_VALUE
from app.db import SessionLocal
from app.db_models import Invocations, Models, PortfolioSize, ToolCallType, TradingMode
from app.leaderboard import rank_models
from app.settings_repo import get_active_trading_mode, set_active_trading_mode
from app.utils import serialize_datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="ai-trading-bot")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SetModeBody(BaseModel):
    mode: str


class CreateModelBody(BaseModel):
    name: str
    openRoutermodelName: str
    lighterApiKey: str = ""
    accountIndex: str = ""
    testnetLighterApiKey: str | None = None
    testnetAccountIndex: str | None = None


class PatchModelBody(BaseModel):
    name: str | None = None
    openRoutermodelName: str | None = None
    lighterApiKey: str | None = None
    accountIndex: str | None = None
    testnetLighterApiKey: str | None = Field(default=None)
    testnetAccountIndex: str | None = Field(default=None)


def require_admin(x_admin_token: Annotated[str, Header(alias="X-Admin-Token")] = "") -> None:
    expected = ADMIN_API_TOKEN
    if not expected:
        logger.warning("ADMIN_API_TOKEN is not set; rejecting mutating request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin token is not configured",
        )
    if not hmac.compare_digest(x_admin_token, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin token",
        )


def _tool_call_type_value(tool_call_type: ToolCallType | str) -> str:
    if isinstance(tool_call_type, ToolCallType):
        return tool_call_type.value
    return str(tool_call_type)


def _parse_trading_mode(raw_mode: str | None) -> TradingMode:
    if raw_mode is None or raw_mode == "":
        return get_active_trading_mode()
    try:
        return TradingMode(raw_mode)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid mode: {raw_mode}",
        ) from error


def _serialize_model(model: Models) -> dict:
    return {
        "id": model.id,
        "name": model.name,
        "openRoutermodelName": model.openRoutermodelName,
        "accountIndex": model.accountIndex or "",
        "testnetAccountIndex": model.testnetAccountIndex or "",
        "invocationCount": model.invocationCount or 0,
        "hasMainnetCredentials": bool((model.lighterApiKey or "").strip()),
        "hasTestnetCredentials": bool((model.testnetLighterApiKey or "").strip()),
    }


def _non_empty(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None


@app.get("/settings/mode")
def get_mode():
    mode = get_active_trading_mode()
    return {"mode": mode.value}


@app.post("/settings/mode")
def post_mode(body: SetModeBody, _: None = Depends(require_admin)):
    try:
        mode = TradingMode(body.mode)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid mode: {body.mode}",
        ) from error
    set_active_trading_mode(mode)
    logger.info("Trading mode switched to %s", mode.value)
    return {"mode": mode.value}


@app.get("/performance")
def get_performance(mode: str | None = Query(default=None)):
    trading_mode = _parse_trading_mode(mode)
    with SessionLocal() as session:
        rows = session.scalars(
            select(PortfolioSize)
            .options(joinedload(PortfolioSize.model))
            .where(PortfolioSize.tradingMode == trading_mode)
            .order_by(PortfolioSize.createdAt.asc())
        ).all()
        data = [
            {
                "id": row.id,
                "modelId": row.modelId,
                "netPortfolio": row.netPortfolio,
                "tradingMode": row.tradingMode.value if isinstance(row.tradingMode, TradingMode) else str(row.tradingMode),
                "createdAt": serialize_datetime(row.createdAt),
                "updatedAt": serialize_datetime(row.updatedAt),
                "model": {"name": row.model.name if row.model else None},
            }
            for row in rows
        ]
    last_updated = datetime.now(timezone.utc)
    logger.info("Returning %s performance rows mode=%s", len(data), trading_mode.value)
    return {"data": data, "lastUpdated": serialize_datetime(last_updated), "mode": trading_mode.value}


@app.get("/invocations")
def get_invocations(limit: int = Query(default=30), mode: str | None = Query(default=None)):
    take = limit if isinstance(limit, int) and 1 <= limit <= 200 else 30
    trading_mode = _parse_trading_mode(mode)
    with SessionLocal() as session:
        rows = (
            session.execute(
                select(Invocations)
                .options(
                    joinedload(Invocations.model),
                    joinedload(Invocations.toolCalls),
                )
                .where(Invocations.tradingMode == trading_mode)
                .order_by(Invocations.createdAt.desc())
                .limit(take)
            )
            .unique()
            .scalars()
            .all()
        )
        data = []
        for row in rows:
            tool_calls = sorted(row.toolCalls, key=lambda tool_call: tool_call.createdAt)
            data.append(
                {
                    "id": row.id,
                    "modelId": row.modelId,
                    "response": row.response,
                    "tradingMode": row.tradingMode.value if isinstance(row.tradingMode, TradingMode) else str(row.tradingMode),
                    "createdAt": serialize_datetime(row.createdAt),
                    "updatedAt": serialize_datetime(row.updatedAt),
                    "model": {"name": row.model.name if row.model else None},
                    "toolCalls": [
                        {
                            "toolCallType": _tool_call_type_value(tool_call.toolCallType),
                            "metadata": tool_call.metadata_,
                            "createdAt": serialize_datetime(tool_call.createdAt),
                        }
                        for tool_call in tool_calls
                    ],
                }
            )
    last_updated = datetime.now(timezone.utc)
    logger.info("Returning %s invocations mode=%s", len(data), trading_mode.value)
    return {"data": data, "lastUpdated": serialize_datetime(last_updated), "mode": trading_mode.value}


@app.get("/leaderboard")
def get_leaderboard(mode: str | None = Query(default=None)):
    trading_mode = _parse_trading_mode(mode)
    with SessionLocal() as session:
        models = session.scalars(select(Models).order_by(Models.name.asc())).all()
        latest_subquery = (
            select(
                PortfolioSize.modelId.label("modelId"),
                func.max(PortfolioSize.createdAt).label("latestAt"),
            )
            .where(PortfolioSize.tradingMode == trading_mode)
            .group_by(PortfolioSize.modelId)
            .subquery()
        )
        latest_rows = session.execute(
            select(PortfolioSize).join(
                latest_subquery,
                (PortfolioSize.modelId == latest_subquery.c.modelId)
                & (PortfolioSize.createdAt == latest_subquery.c.latestAt)
                & (PortfolioSize.tradingMode == trading_mode),
            )
        ).scalars().all()
        latest_by_model = {row.modelId: row.netPortfolio for row in latest_rows}

        ranked_input: list[tuple[str, str, float | None]] = []
        for model in models:
            raw_value = latest_by_model.get(model.id)
            if raw_value is None:
                ranked_input.append((model.id, model.name, None))
                continue
            try:
                ranked_input.append((model.id, model.name, float(raw_value)))
            except (TypeError, ValueError):
                logger.warning("Skipping non-numeric portfolio value for model=%s value=%s", model.name, raw_value)
                ranked_input.append((model.id, model.name, None))

    entries = rank_models(ranked_input, STARTING_PORTFOLIO_VALUE)
    data = [
        {
            "rank": entry.rank,
            "modelId": entry.model_id,
            "name": entry.name,
            "currentValue": entry.current_value,
            "pnl": entry.pnl,
            "returnPct": entry.return_pct,
        }
        for entry in entries
    ]
    last_updated = datetime.now(timezone.utc)
    logger.info("Returning %s leaderboard rows mode=%s", len(data), trading_mode.value)
    return {"data": data, "lastUpdated": serialize_datetime(last_updated), "mode": trading_mode.value}


@app.get("/models")
def list_models():
    with SessionLocal() as session:
        models = session.scalars(select(Models).order_by(Models.name.asc())).all()
        data = [_serialize_model(model) for model in models]
    logger.info("Returning %s models", len(data))
    return {"data": data}


@app.post("/models")
def create_model(body: CreateModelBody, _: None = Depends(require_admin)):
    name = (body.name or "").strip()
    open_router_model_name = (body.openRoutermodelName or "").strip()
    if not name or not open_router_model_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="name and openRoutermodelName are required",
        )
    model = Models(
        name=name,
        openRoutermodelName=open_router_model_name,
        lighterApiKey=(body.lighterApiKey or "").strip(),
        accountIndex=(body.accountIndex or "").strip(),
        testnetLighterApiKey=_non_empty(body.testnetLighterApiKey),
        testnetAccountIndex=_non_empty(body.testnetAccountIndex),
        invocationCount=0,
    )
    try:
        with SessionLocal() as session:
            session.add(model)
            session.commit()
            session.refresh(model)
            payload = _serialize_model(model)
    except IntegrityError as error:
        logger.warning("Duplicate model name=%s", name)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A model named '{name}' already exists",
        ) from error
    logger.info("Created model id=%s name=%s", payload["id"], payload["name"])
    return payload


@app.patch("/models/{model_id}")
def patch_model(model_id: str, body: PatchModelBody, _: None = Depends(require_admin)):
    with SessionLocal() as session:
        model = session.get(Models, model_id)
        if model is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")
        if body.name is not None:
            name = body.name.strip()
            if not name:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="name cannot be empty")
            model.name = name
        if body.openRoutermodelName is not None:
            open_router_model_name = body.openRoutermodelName.strip()
            if not open_router_model_name:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="openRoutermodelName cannot be empty",
                )
            model.openRoutermodelName = open_router_model_name
        if _non_empty(body.lighterApiKey) is not None:
            model.lighterApiKey = body.lighterApiKey.strip()
        if _non_empty(body.accountIndex) is not None:
            model.accountIndex = body.accountIndex.strip()
        if _non_empty(body.testnetLighterApiKey) is not None:
            model.testnetLighterApiKey = body.testnetLighterApiKey.strip()
        if _non_empty(body.testnetAccountIndex) is not None:
            model.testnetAccountIndex = body.testnetAccountIndex.strip()
        try:
            session.commit()
            session.refresh(model)
            payload = _serialize_model(model)
        except IntegrityError as error:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A model with that name already exists",
            ) from error
    logger.info("Updated model id=%s", model_id)
    return payload


@app.delete("/models/{model_id}")
def delete_model(model_id: str, _: None = Depends(require_admin)):
    with SessionLocal() as session:
        model = session.get(Models, model_id)
        if model is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")
        invocation_count = session.scalar(
            select(func.count()).select_from(Invocations).where(Invocations.modelId == model_id)
        ) or 0
        portfolio_count = session.scalar(
            select(func.count()).select_from(PortfolioSize).where(PortfolioSize.modelId == model_id)
        ) or 0
        if invocation_count or portfolio_count:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot delete a model that still has invocations or portfolio history",
            )
        session.delete(model)
        session.commit()
    logger.info("Deleted model id=%s", model_id)
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host="0.0.0.0", port=SERVER_PORT)
