"""
backend/cv/spot_check.py

One-off visual verification tool.
Grabs a single live frame from the stream, runs detection,
saves the annotated image so you can visually verify classifications.

Usage:
    python -m cv.spot_check
    python -m cv.spot_check --count 5          # grab 5 frames, 5s apart
    python -m cv.spot_check --output-dir checks/
"""

import argparse
import os
import time
from datetime import datetime

import cv2

from cv.detector import VehicleDetector
from cv.emission_factors import calculate_emission

STREAM_URL = os.getenv(
    "STREAM_URL",
    "https://cctvjss.jogjakota.go.id/atcs/ATCS_Utara-Timur_Gardena_Jl_Urip%20Sumoharjo_V_Timur.stream/playlist.m3u8",
)
REFERER = os.getenv("REFERER", "https://cctv.jogjakota.go.id/")

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "logs", "spot_checks")


def run_spot_check(
    detector: VehicleDetector,
    output_dir: str,
    frame_index: int = 1,
):
    print(f"\n--- Frame {frame_index} ---")

    frame = detector.capture_frame(STREAM_URL, REFERER)
    counts, annotated = detector.detect(frame)
    emission = calculate_emission(counts)

    # Print counts + emission to terminal
    print(f"  car={counts['car']}  motorcycle={counts['motorcycle']}  "
          f"bus={counts['bus']}  truck={counts['truck']}")
    print(f"  CO₂: {emission['total_co2_g_per_min']} g/min  "
          f"({emission['total_co2_kg_per_hr']} kg/hr)")

    # Save annotated frame
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    filename = f"frame_{frame_index:02d}_{ts}.jpg"
    path = os.path.join(output_dir, filename)
    cv2.imwrite(path, annotated)
    print(f"  Saved: {path}")

    return path


def main(count: int, interval: int, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)

    print("Loading YOLO model...")
    detector = VehicleDetector()
    print(f"Capturing {count} frame(s), {interval}s apart.")
    print(f"Output dir: {output_dir}\n")

    saved_paths = []

    for i in range(1, count + 1):
        try:
            path = run_spot_check(detector, output_dir, frame_index=i)
            saved_paths.append(path)
        except RuntimeError as e:
            print(f"  [ERROR] Frame {i} capture failed: {e}")

        if i < count:
            print(f"  Waiting {interval}s...")
            time.sleep(interval)

    print(f"\nDone. {len(saved_paths)}/{count} frames saved to: {output_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EcoTraffic — spot check annotated frames")
    parser.add_argument("--count", type=int, default=3, help="Number of frames to grab")
    parser.add_argument("--interval", type=int, default=5, help="Seconds between frames")
    parser.add_argument("--output-dir", type=str, default=OUTPUT_DIR, help="Where to save images")
    args = parser.parse_args()

    main(count=args.count, interval=args.interval, output_dir=args.output_dir)
