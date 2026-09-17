import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy.orm import declarative_base, relationship


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

Base = declarative_base()


class ToolCallType(enum.Enum):
    CREATE_POSITION = "CREATE_POSITION"
    CLOSE_POSITION = "CLOSE_POSITION"


class TradingMode(enum.Enum):
    SANDBOX = "SANDBOX"
    TESTNET = "TESTNET"
    LIVE = "LIVE"


tool_call_type_enum = PgEnum(
    ToolCallType,
    name="ToolCallType",
    create_type=False,
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
)

trading_mode_enum = PgEnum(
    TradingMode,
    name="TradingMode",
    create_type=False,
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
)


class Models(Base):
    __tablename__ = "Models"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, unique=True, nullable=False)
    openRoutermodelName = Column("openRoutermodelName", String, nullable=False)
    lighterApiKey = Column("lighterApiKey", String, nullable=False)
    invocationCount = Column("invocationCount", Integer, nullable=False, default=0)
    accountIndex = Column("accountIndex", String, nullable=False)
    testnetLighterApiKey = Column("testnetLighterApiKey", String, nullable=True)
    testnetAccountIndex = Column("testnetAccountIndex", String, nullable=True)

    invocations = relationship("Invocations", back_populates="model")
    portfolioSizes = relationship("PortfolioSize", back_populates="model")
    paperAccount = relationship("PaperAccounts", back_populates="model", uselist=False)
    paperPositions = relationship("PaperPositions", back_populates="model")


class AppSettings(Base):
    __tablename__ = "AppSettings"

    id = Column(String, primary_key=True)
    activeMode = Column("activeMode", trading_mode_enum, nullable=False, default=TradingMode.SANDBOX)


class Invocations(Base):
    __tablename__ = "Invocations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    modelId = Column("modelId", String, ForeignKey("Models.id"), nullable=False)
    response = Column(String, nullable=False)
    tradingMode = Column("tradingMode", trading_mode_enum, nullable=False, default=TradingMode.SANDBOX)
    createdAt = Column("createdAt", DateTime, nullable=False, default=utc_now)
    updatedAt = Column("updatedAt", DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    model = relationship("Models", back_populates="invocations")
    toolCalls = relationship("ToolCalls", back_populates="invocation")


class ToolCalls(Base):
    __tablename__ = "ToolCalls"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    invocationId = Column("invocationId", String, ForeignKey("Invocations.id"), nullable=False)
    toolCallType = Column("toolCallType", tool_call_type_enum, nullable=False)
    metadata_ = Column("metadata", String, nullable=False)
    createdAt = Column("createdAt", DateTime, nullable=False, default=utc_now)
    updatedAt = Column("updatedAt", DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    invocation = relationship("Invocations", back_populates="toolCalls")


class PortfolioSize(Base):
    __tablename__ = "PortfolioSize"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    modelId = Column("modelId", String, ForeignKey("Models.id"), nullable=False)
    netPortfolio = Column("netPortfolio", String, nullable=False)
    tradingMode = Column("tradingMode", trading_mode_enum, nullable=False, default=TradingMode.SANDBOX)
    createdAt = Column("createdAt", DateTime, nullable=False, default=utc_now)
    updatedAt = Column("updatedAt", DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    model = relationship("Models", back_populates="portfolioSizes")


class PaperAccounts(Base):
    __tablename__ = "PaperAccounts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    modelId = Column("modelId", String, ForeignKey("Models.id"), nullable=False, unique=True)
    cashBalance = Column("cashBalance", String, nullable=False)
    createdAt = Column("createdAt", DateTime, nullable=False, default=utc_now)
    updatedAt = Column("updatedAt", DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    model = relationship("Models", back_populates="paperAccount")


class PaperPositions(Base):
    __tablename__ = "PaperPositions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    modelId = Column("modelId", String, ForeignKey("Models.id"), nullable=False)
    symbol = Column(String, nullable=False)
    side = Column(String, nullable=False)
    quantity = Column(String, nullable=False)
    entryPrice = Column("entryPrice", String, nullable=False)
    marginReserved = Column("marginReserved", String, nullable=False)
    realizedPnl = Column("realizedPnl", String, nullable=False, default="0")
    openedAt = Column("openedAt", DateTime, nullable=False, default=utc_now)
    closedAt = Column("closedAt", DateTime, nullable=True)

    model = relationship("Models", back_populates="paperPositions")
