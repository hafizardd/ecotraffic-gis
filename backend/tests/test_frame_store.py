from types import SimpleNamespace

import pytest

from cv.frame_store import FramePayloadTooLarge, RedisFrameStore


class _Redis:
    def __init__(self):
        self.values = {}
        self.setex_calls = []
        self.deleted = []

    def setex(self, key, ttl, value):
        self.values[key] = value
        self.setex_calls.append((key, ttl, value))

    def get(self, key):
        return self.values.get(key)

    def delete(self, key):
        self.deleted.append(key)
        self.values.pop(key, None)


class _Encoded:
    def __init__(self, payload):
        self.payload = payload

    def tobytes(self):
        return self.payload


class _Cv2:
    IMWRITE_JPEG_QUALITY = 1
    IMREAD_COLOR = 2

    def __init__(self, payload=b"jpeg", decoded=None):
        self.payload = payload
        self.decoded = decoded or SimpleNamespace(size=1)
        self.encode_parameters = None

    def imencode(self, _extension, _frame, parameters):
        self.encode_parameters = parameters
        return True, _Encoded(self.payload)

    def imdecode(self, _encoded, _mode):
        return self.decoded


class _Numpy:
    uint8 = "uint8"

    @staticmethod
    def frombuffer(payload, dtype):
        return payload, dtype


def test_frame_is_compressed_stored_with_ttl_and_loaded():
    redis = _Redis()
    cv2 = _Cv2(payload=b"compressed-frame")
    store = RedisFrameStore(
        redis,
        ttl_seconds=180,
        max_bytes=100,
        jpeg_quality=85,
        cv2_module=cv2,
        numpy_module=_Numpy(),
    )

    stored = store.store("job-1", object())
    loaded = store.load(stored.key)
    store.delete(stored.key)

    assert stored.key == "inference:frame:job-1"
    assert stored.size_bytes == len(b"compressed-frame")
    assert redis.setex_calls == [(stored.key, 180, b"compressed-frame")]
    assert cv2.encode_parameters == [1, 85]
    assert loaded.size == 1
    assert redis.deleted == [stored.key]


def test_oversized_frame_is_rejected_before_redis_write():
    redis = _Redis()
    store = RedisFrameStore(
        redis,
        ttl_seconds=180,
        max_bytes=3,
        jpeg_quality=85,
        cv2_module=_Cv2(payload=b"too-large"),
        numpy_module=_Numpy(),
    )

    with pytest.raises(FramePayloadTooLarge):
        store.store("job-1", object())

    assert redis.setex_calls == []
