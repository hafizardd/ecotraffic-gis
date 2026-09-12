from cv.track_emission import FlowCounter, occupancy_counts


def _track(track_id, vehicle_type="car", inside=True):
    return {"id": track_id, "cls": vehicle_type, "inside_roi": inside}


def test_occupancy_counts_unique_ids_and_untracked_boxes():
    assert occupancy_counts([
        _track(1), _track(1), _track(2, "motorcycle"),
        _track(None), _track(3, "truck", False),
    ]) == {"car": 2, "motorcycle": 1, "bus": 0, "truck": 0}


def test_flow_counts_roi_exit_once():
    counter = FlowCounter(min_frames=2, exit_frames=2)

    assert counter.update([_track(1)]) == {"car": 0, "motorcycle": 0, "bus": 0, "truck": 0}
    assert counter.update([_track(1)]) == {"car": 0, "motorcycle": 0, "bus": 0, "truck": 0}
    assert counter.update([_track(1, inside=False)]) == {"car": 1, "motorcycle": 0, "bus": 0, "truck": 0}
    assert counter.update([_track(1, inside=False)]) == {"car": 0, "motorcycle": 0, "bus": 0, "truck": 0}


def test_flow_tolerates_short_missing_tracker_gap():
    counter = FlowCounter(min_frames=1, exit_frames=2)
    counter.update([_track(1)])
    assert counter.update([]) == {"car": 0, "motorcycle": 0, "bus": 0, "truck": 0}
    assert counter.update([]) == {"car": 1, "motorcycle": 0, "bus": 0, "truck": 0}
