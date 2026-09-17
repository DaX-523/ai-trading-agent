from dataclasses import dataclass


@dataclass
class LeaderboardEntry:
    model_id: str
    name: str
    current_value: float | None
    pnl: float | None
    return_pct: float | None
    rank: int | None


def rank_models(
    models: list[tuple[str, str, float | None]],
    starting_value: float,
) -> list[LeaderboardEntry]:
    if starting_value == 0:
        raise ValueError("starting_value must be non-zero")

    with_data: list[LeaderboardEntry] = []
    without_data: list[LeaderboardEntry] = []
    for model_id, name, current_value in models:
        if current_value is None:
            without_data.append(
                LeaderboardEntry(
                    model_id=model_id,
                    name=name,
                    current_value=None,
                    pnl=None,
                    return_pct=None,
                    rank=None,
                )
            )
            continue
        pnl = current_value - starting_value
        return_pct = (pnl / starting_value) * 100
        with_data.append(
            LeaderboardEntry(
                model_id=model_id,
                name=name,
                current_value=current_value,
                pnl=pnl,
                return_pct=return_pct,
                rank=None,
            )
        )

    with_data.sort(key=lambda entry: (entry.pnl is None, -(entry.pnl or 0), entry.name))
    for index, entry in enumerate(with_data, start=1):
        entry.rank = index
    without_data.sort(key=lambda entry: entry.name)
    return with_data + without_data
