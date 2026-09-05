from app.services.segment_latest_state import SegmentLatestStateStore


class FakeRedis:
    def __init__(self):
        self.values = {}

    def setex(self, key, ttl, value):
        self.values[key] = value

    def get(self, key):
        return self.values.get(key)

    def scan_iter(self, match):
        return iter(self.values)


def test_segment_latest_state_round_trip_and_listing():
    store = SegmentLatestStateStore(FakeRedis(), ttl_seconds=60)
    stored = store.save("SEG-0001", {"decision_score": 49.05})
    assert stored["segment_id"] == "SEG-0001"
    assert store.load("SEG-0001")["decision_score"] == 49.05
    assert store.load_all() == {"SEG-0001": stored}
