"""Regression coverage for the actual MJPEG response generator."""
import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from app.api.routes import cameras


class TrackedStreamTests(unittest.IsolatedAsyncioTestCase):
    async def test_frame_and_metadata_are_read_together(self):
        calls = []
        class Redis:
            def mget(self, keys):
                calls.append(keys)
                return [b'jpeg-content', b'1000.25']
            def close(self): pass
        class DB:
            async def execute(self, *args):
                return SimpleNamespace(scalar_one_or_none=lambda: SimpleNamespace(is_active=True))
        with patch.object(cameras.redis.Redis, 'from_url', return_value=Redis()), patch.object(cameras.time, 'time', return_value=1002.25):
            response = await cameras.get_tracked_stream('test-camera', DB())
            try:
                frame = await asyncio.wait_for(anext(response.body_iterator), 1)
            finally:
                await response.body_iterator.aclose()
        self.assertEqual(calls, [['tracks:snapshot:test-camera', 'tracks:snapshot:test-camera:published_at']])
        header, payload = frame.split(b'\r\n\r\n', 1)
        self.assertIn(b'X-Frame-Id: 1000.25', header)
        self.assertIn(b'X-Frame-Age-Ms: 2000', header)
        self.assertIn(b'Content-Length: 12', header)
        self.assertEqual(payload, b'jpeg-content\r\n')

if __name__ == '__main__': unittest.main()
