import logging
from datetime import datetime, timezone

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.config import SERVER_PORT
from app.db import SessionLocal
from app.db_models import Invocations, PortfolioSize, ToolCallType
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


def _tool_call_type_value(tool_call_type: ToolCallType | str) -> str:
    if isinstance(tool_call_type, ToolCallType):
        return tool_call_type.value
    return str(tool_call_type)


@app.get("/performance")
def get_performance():
    with SessionLocal() as session:
        rows = session.scalars(
            select(PortfolioSize)
            .options(joinedload(PortfolioSize.model))
            .order_by(PortfolioSize.createdAt.asc())
        ).all()
        data = [
            {
                "id": row.id,
                "modelId": row.modelId,
                "netPortfolio": row.netPortfolio,
                "createdAt": serialize_datetime(row.createdAt),
                "updatedAt": serialize_datetime(row.updatedAt),
                "model": {"name": row.model.name if row.model else None},
            }
            for row in rows
        ]
    last_updated = datetime.now(timezone.utc)
    logger.info("Returning %s performance rows", len(data))
    return {"data": data, "lastUpdated": serialize_datetime(last_updated)}


@app.get("/invocations")
def get_invocations(limit: int = Query(default=30)):
    take = limit if isinstance(limit, int) and 1 <= limit <= 200 else 30
    with SessionLocal() as session:
        rows = (
            session.execute(
                select(Invocations)
                .options(
                    joinedload(Invocations.model),
                    joinedload(Invocations.toolCalls),
                )
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
    logger.info("Returning %s invocations", len(data))
    return {"data": data, "lastUpdated": serialize_datetime(last_updated)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host="0.0.0.0", port=SERVER_PORT)
