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


tool_call_type_enum = PgEnum(
    ToolCallType,
    name="ToolCallType",
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

    invocations = relationship("Invocations", back_populates="model")
    portfolioSizes = relationship("PortfolioSize", back_populates="model")


class Invocations(Base):
    __tablename__ = "Invocations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    modelId = Column("modelId", String, ForeignKey("Models.id"), nullable=False)
    response = Column(String, nullable=False)
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
    createdAt = Column("createdAt", DateTime, nullable=False, default=utc_now)
    updatedAt = Column("updatedAt", DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    model = relationship("Models", back_populates="portfolioSizes")
