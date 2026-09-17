import logging
from typing import Any

import lighter
from lighter.nonce_manager import NonceManagerType

from app.config import API_KEY_INDEX

logger = logging.getLogger(__name__)


def create_api_client(base_url: str) -> lighter.ApiClient:
    configuration = lighter.Configuration(host=base_url)
    return lighter.ApiClient(configuration)


def create_signer_client(*, base_url: str, account_index: str, api_key: str) -> lighter.SignerClient:
    logger.info(
        "Creating SignerClient for account_index=%s api_key_index=%s base_url=%s",
        account_index,
        API_KEY_INDEX,
        base_url,
    )
    return lighter.SignerClient(
        url=base_url,
        account_index=int(account_index),
        api_private_keys={API_KEY_INDEX: api_key},
        nonce_management_type=NonceManagerType.API,
    )


async def close_client(client: Any) -> None:
    close = getattr(client, "close", None)
    if close is None:
        return
    result = close()
    if hasattr(result, "__await__"):
        await result
