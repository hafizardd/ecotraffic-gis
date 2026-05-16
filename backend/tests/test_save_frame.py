import os
from urllib.parse import urlparse

import pytest


STREAM_URL = (
    "https://cctvjss.jogjakota.go.id/atcs/"
    "ATCS_Utara-Timur_Gardena_Jl_Urip%20Sumoharjo_V_Timur.stream/"
    "chunklist_w760075980.m3u8"
)


def camera_name_from_url(url: str) -> str:
    parsed = urlparse(url)
    camera_name = os.path.basename(parsed.path)
    camera_name = camera_name.replace(".stream/playlist.m3u8", "")
    camera_name = camera_name.replace(".stream", "")
    return camera_name or "camera"


def save_frames_from_stream(
    url: str,
    output_dir: str,
    *,
    max_frames: int = 10,
    skip_frames: int = 30,
) -> list[str]:
    """Save up to max_frames from the stream, writing every skip_frames-th frame."""
    import cv2

    os.makedirs(output_dir, exist_ok=True)

    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    if not cap.isOpened():
        raise RuntimeError("Could not open video stream")

    frame_count = 0
    saved_count = 0
    saved_paths: list[str] = []

    try:
        while saved_count < max_frames:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1
            if skip_frames > 1 and (frame_count % skip_frames != 0):
                continue

            output_path = os.path.join(output_dir, f"frame_{saved_count + 1}.jpg")
            if not cv2.imwrite(output_path, frame):
                raise RuntimeError(f"Failed to write frame to {output_path}")

            saved_paths.append(output_path)
            saved_count += 1
    finally:
        cap.release()

    return saved_paths


@pytest.mark.skipif(
    os.getenv("RUN_STREAM_TESTS") != "1",
    reason="Integration test (network/ffmpeg). Set RUN_STREAM_TESTS=1 to enable.",
)
def test_can_save_single_frame(tmp_path):
    out_dir = tmp_path / "frames"
    saved = save_frames_from_stream(
        STREAM_URL,
        str(out_dir),
        max_frames=1,
        skip_frames=1,
    )
    assert len(saved) == 1
    assert os.path.exists(saved[0])


def main() -> None:
    camera = camera_name_from_url(STREAM_URL)
    output_dir = f"frames_{camera}"
    max_frames = int(os.getenv("SAVE_FRAME_MAX_FRAMES", "10"))
    skip_frames = int(os.getenv("SAVE_FRAME_SKIP_FRAMES", "30"))

    saved = save_frames_from_stream(
        STREAM_URL,
        output_dir,
        max_frames=max_frames,
        skip_frames=skip_frames,
    )
    print(f"Saved {len(saved)} frame(s) to {output_dir}")


if __name__ == "__main__":
    main()