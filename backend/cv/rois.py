"""Region-of-interest polygons for CCTV tracking verification.

Relative coords (0.0-1.0) so one polygon works across resolutions.
(0,0) = top-left. Keep 4-8 points.
"""

ROIS = {
    "jl_balaikota_timur": [(0.06, 0.65), (0.38, 0.38), (0.64, 0.16), (0.79, 0.18), (0.70, 0.45), (0.50, 0.99)],
    "simpang_jlagran": [(0.00, 0.79), (0.30, 0.42), (0.50, 0.20), (0.66, 0.23), (0.60, 1.00), (0.00, 1.00)],
}
FILL = (0, 255, 0, 80)  # ponytail: fixed green fill; per-camera colors if boxes get confusing.

# DB camera_id slug -> ROIS key (user keys kept verbatim).
ROI_ALIASES = {
    "atcs_jlagran": "simpang_jlagran",
    "atcs_balaikota_timur": "jl_balaikota_timur",
}


def resolve(camera_id: str | None) -> str | None:
    """Map a DB camera slug to a ROIS key, or None if no ROI."""
    if not camera_id:
        return None
    key = ROI_ALIASES.get(camera_id, camera_id)
    return key if key in ROIS else None


def to_normalized(camera_id: str | None) -> list[tuple[float, float]] | None:
    key = resolve(camera_id)
    return list(ROIS[key]) if key else None


def _to_polygon(w: int, h: int, camera: str) -> list[tuple[int, int]]:
    pts = []
    for xr, yr in ROIS[camera]:
        x = min(w, max(0, int(xr * w)))
        y = min(h, max(0, int(yr * h)))
        pts.append((x, y))
    assert len(pts) >= 3, f"ROI needs >=3 points: {camera}"
    return pts


def to_polygon_for_camera(w: int, h: int, camera_id: str | None) -> list[tuple[int, int]] | None:
    key = resolve(camera_id)
    return _to_polygon(w, h, key) if key else None
