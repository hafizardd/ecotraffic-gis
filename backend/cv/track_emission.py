"""Small, stateful helpers for emissions derived from tracked boxes."""

from collections import defaultdict


VEHICLE_TYPES = ("car", "motorcycle", "bus", "truck")


def occupancy_counts(tracks: list[dict]) -> dict[str, int]:
    """Count unique tracked vehicles currently inside the configured ROI."""
    ids_by_type: dict[str, set[int]] = defaultdict(set)
    fallback: dict[str, int] = defaultdict(int)
    for track in tracks:
        if not track.get("inside_roi"):
            continue
        vehicle_type = track.get("cls")
        if vehicle_type not in VEHICLE_TYPES:
            continue
        track_id = track.get("id")
        if track_id is None:
            fallback[vehicle_type] += 1
        else:
            ids_by_type[vehicle_type].add(int(track_id))
    return {
        vehicle_type: len(ids_by_type[vehicle_type]) + fallback[vehicle_type]
        for vehicle_type in VEHICLE_TYPES
    }


class FlowCounter:
    """Count vehicles leaving the ROI once, tolerating short tracker gaps."""

    def __init__(self, *, min_frames: int = 3, exit_frames: int = 5) -> None:
        if min_frames <= 0 or exit_frames <= 0:
            raise ValueError("flow frame thresholds must be greater than zero")
        self.min_frames = min_frames
        self.exit_frames = exit_frames
        self._tracks: dict[int, dict[str, int | bool]] = {}

    def update(self, tracks: list[dict]) -> dict[str, int]:
        exits = {vehicle_type: 0 for vehicle_type in VEHICLE_TYPES}
        seen: set[int] = set()
        for track in tracks:
            track_id = track.get("id")
            vehicle_type = track.get("cls")
            if track_id is None or vehicle_type not in VEHICLE_TYPES:
                continue
            track_id = int(track_id)
            seen.add(track_id)
            state = self._tracks.setdefault(
                track_id,
                {"cls": vehicle_type, "frames": 0, "inside": False, "missing": 0},
            )
            state["cls"] = vehicle_type
            state["frames"] = int(state["frames"]) + 1
            state["missing"] = 0
            inside = bool(track.get("inside_roi"))
            if bool(state["inside"]) and not inside and int(state["frames"]) >= self.min_frames:
                exits[vehicle_type] += 1
            state["inside"] = inside

        for track_id, state in list(self._tracks.items()):
            if track_id in seen:
                continue
            state["missing"] = int(state["missing"]) + 1
            if (
                bool(state["inside"])
                and int(state["missing"]) >= self.exit_frames
                and int(state["frames"]) >= self.min_frames
            ):
                exits[str(state["cls"])] += 1
                state["inside"] = False
        return exits
