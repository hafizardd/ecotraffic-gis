"""Compute and persist per-bus-stop accessibility and intervention class."""

from app.core.database import get_sync_db
from app.services.bus_stop_scoring import score_bus_stops


def main() -> dict:
    with get_sync_db() as db:
        counts = score_bus_stops(db)
    print(f"bus_stop_scoring: {counts}")
    return counts


if __name__ == "__main__":
    main()
