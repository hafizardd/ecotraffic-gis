from app.services.inference_queue import InferenceQueue, ReservationStatus


class _Redis:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def eval(self, *arguments):
        self.calls.append(arguments)
        return next(self.responses)


def test_reservation_statuses_and_depth_are_observable():
    redis = _Redis([1, 2, 3, 7])
    queue = InferenceQueue(
        redis,
        max_pending=64,
        reservation_ttl_seconds=180,
        clock=lambda: 1000,
    )

    assert queue.reserve("camera-1", "job-1") is ReservationStatus.ACCEPTED
    assert queue.reserve("camera-1", "job-2") is ReservationStatus.DUPLICATE
    assert queue.reserve("camera-2", "job-3") is ReservationStatus.FULL
    assert queue.depth() == 7

    reserve_call = redis.calls[0]
    assert reserve_call[1] == 2
    assert reserve_call[2] == "inference:reservations"
    assert reserve_call[3] == "inference:pending:camera-1"
    assert reserve_call[-2:] == ("job-1", 180)


def test_release_is_scoped_to_the_matching_camera_and_job():
    redis = _Redis([1, 0])
    queue = InferenceQueue(
        redis,
        max_pending=10,
        reservation_ttl_seconds=30,
    )

    assert queue.release("camera-1", "job-1") is True
    assert queue.release("camera-1", "stale-job") is False
    assert redis.calls[0][-2:] == ("job-1", "camera-1:job-1")
