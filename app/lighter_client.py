import logging
from typing import Any

import lighter
from lighter.nonce_manager import NonceManagerType

from app.accounts import Account
from app.config import API_KEY_INDEX, BASE_URL

logger = logging.getLogger(__name__)


def create_api_client() -> lighter.ApiClient:
    configuration = lighter.Configuration(host=BASE_URL)
    return lighter.ApiClient(configuration)


def create_signer_client(account: Account) -> lighter.SignerClient:
    logger.info(
        "Creating SignerClient for account_index=%s api_key_index=%s",
        account.account_index,
        API_KEY_INDEX,
    )
    return lighter.SignerClient(
        url=BASE_URL,
        account_index=int(account.account_index),
        api_private_keys={API_KEY_INDEX: account.api_key},
        nonce_management_type=NonceManagerType.API,
    )


async def close_client(client: Any) -> None:
    close = getattr(client, "close", None)
    if close is None:
        return
    result = close()
    if hasattr(result, "__await__"):
        await result
