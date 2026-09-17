import logging

from app.db import SessionLocal
from app.db_models import AppSettings, TradingMode

logger = logging.getLogger(__name__)

APP_SETTINGS_ID = "default"


def get_active_trading_mode() -> TradingMode:
    with SessionLocal() as session:
        settings = session.get(AppSettings, APP_SETTINGS_ID)
        if settings is None:
            settings = AppSettings(id=APP_SETTINGS_ID, activeMode=TradingMode.SANDBOX)
            session.add(settings)
            session.commit()
            session.refresh(settings)
            logger.info("Created default AppSettings row with mode=SANDBOX")
        return settings.activeMode


def set_active_trading_mode(mode: TradingMode) -> TradingMode:
    with SessionLocal() as session:
        settings = session.get(AppSettings, APP_SETTINGS_ID)
        if settings is None:
            settings = AppSettings(id=APP_SETTINGS_ID, activeMode=mode)
            session.add(settings)
        else:
            settings.activeMode = mode
        session.commit()
        logger.info("Active trading mode set to %s", mode.value)
        return mode
