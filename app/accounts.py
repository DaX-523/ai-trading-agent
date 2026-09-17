from dataclasses import dataclass


@dataclass
class Account:
    api_key: str
    name: str
    model_name: str
    invocation_count: int
    id: str
    account_index: str
    testnet_api_key: str | None = None
    testnet_account_index: str | None = None
