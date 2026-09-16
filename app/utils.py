from datetime import datetime, timezone


def round_to_3(value: float) -> float:
    return float(f"{value:.3f}")


def serialize_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        return value.isoformat(timespec="milliseconds") + "Z"
    return (
        value.astimezone(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )
