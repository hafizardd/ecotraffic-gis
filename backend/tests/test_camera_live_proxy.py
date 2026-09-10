from app.api.routes import cameras


def test_safe_live_filename_accepts_hls_segments():
    assert cameras._safe_live_filename("chunklist.m3u8") == "chunklist.m3u8"
    assert cameras._safe_live_filename("seg-123.ts") == "seg-123.ts"
    assert cameras._safe_live_filename("https://up.example/x/seg.m4s?k=1") == "seg.m4s"


def test_safe_live_filename_rejects_traversal_and_unknown_ext():
    assert cameras._safe_live_filename("../etc/passwd") is None
    assert cameras._safe_live_filename("a/b.ts") == "b.ts"  # basename only
    assert cameras._safe_live_filename("evil.exe") is None
    assert cameras._safe_live_filename("") is None


def test_rewrite_playlist_points_segments_at_proxy():
    upstream = (
        "#EXTM3U\n"
        "#EXT-X-STREAM-INF:BANDWIDTH=800000\n"
        "chunklist.m3u8\n"
        "#EXT-X-KEY:METHOD=AES-128,URI=\"key.key\"\n"
    )
    body = cameras._rewrite_playlist(upstream, "atcs_jlagran")
    assert "/api/cameras/atcs_jlagran/live/chunklist.m3u8" in body
    assert 'URI="/api/cameras/atcs_jlagran/live/key.key"' in body
    assert "chunklist.m3u8\n" not in body.replace("/api/cameras/atcs_jlagran/live/chunklist.m3u8", "")


def test_rewrite_playlist_rewrites_media_segments():
    body = cameras._rewrite_playlist(
        "#EXTM3U\n#EXTINF:10,\nmedia_w1_123.ts\n",
        "atcs_jlagran",
    )
    assert body.endswith("/api/cameras/atcs_jlagran/live/media_w1_123.ts\n")


def test_live_allowlist_matches_track_cams(monkeypatch):
    monkeypatch.setattr(cameras.settings, "TRACK_CAMS", "atcs_jlagran,atcs_balaikota_timur")
    assert cameras._is_live_cam("atcs_jlagran") is True
    assert cameras._is_live_cam("atcs_mirota") is False
