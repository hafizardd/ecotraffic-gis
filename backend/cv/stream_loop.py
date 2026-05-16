"""
backend/cv/stream_loop.py

Continuous frame loop — pulls frames from one HLS stream at a fixed interval,
runs YOLOv8 vehicle detection, calculates CO₂ emission, and logs results to
console + CSV.

This is the dry-run pipeline before Celery wraps it.

Usage:
    python -m cv.stream_loop
    python -m cv.stream_loop --interval 10 --output my_log.csv
    python -m cv.stream_loop --camera-id atcs_malioboro --interval 5
"""

import argparse
import csv
import logging
import os
import time
from datetime import datetime
import cv2

from cv.detector import VehicleDetector
from cv.emission_factors import calculate_emission

# ------------------------------------------------------------------
# Logging setup
# ------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Default config (override via CLI args or .env)
# ------------------------------------------------------------------

STREAM_URL = os.getenv(
    "STREAM_URL",
    "https://cctvjss.jogjakota.go.id/atcs/ATCS_Utara-Timur_Gardena_Jl_Urip%20Sumoharjo_V_Timur.stream/playlist.m3u8",
)
REFERER = os.getenv("REFERER", "https://cctv.jogjakota.go.id/")
CAMERA_ID = os.getenv("CAMERA_ID", "atcs_urip_sumoharjo")
INTERVAL_SECONDS = int(os.getenv("INTERVAL_SECONDS", 5))

CSV_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
DEFAULT_CSV_PATH = os.path.join(CSV_DIR, f"{CAMERA_ID}_emissions.csv")

CSV_HEADERS = [
    "timestamp",
    "camera_id",
    "car",
    "motorcycle",
    "bus",
    "truck",
    "total_g_per_min",
    "total_kg_per_hr",
    "cycle_duration_s",
]

# How long to wait before retrying after a stream failure
STREAM_FAILURE_BACKOFF_S = 15

# Max consecutive stream failures before giving up entirely
MAX_CONSECUTIVE_FAILURES = 10


# ------------------------------------------------------------------
# CSV helpers
# ------------------------------------------------------------------

def open_csv(path: str):
    """
    Open CSV file for appending. Write header row if file is new.
    Returns the open file handle and csv.DictWriter.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    is_new = not os.path.exists(path)

    f = open(path, "a", newline="", encoding="utf-8")
    writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)

    if is_new:
        writer.writeheader()
        logger.info(f"Created new CSV log: {path}")
    else:
        logger.info(f"Appending to existing CSV log: {path}")

    return f, writer


def write_row(writer, camera_id: str, counts: dict, emission: dict, duration: float):
    """Write one detection result as a CSV row."""
    writer.writerow({
        "timestamp":       datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "camera_id":       camera_id,
        "car":             counts.get("car", 0),
        "motorcycle":      counts.get("motorcycle", 0),
        "bus":             counts.get("bus", 0),
        "truck":           counts.get("truck", 0),
        "total_g_per_min": emission["total_g_per_min"],
        "total_kg_per_hr": emission["total_kg_per_hr"],
        "cycle_duration_s": round(duration, 2),
    })


# ------------------------------------------------------------------
# Single detection cycle
# ------------------------------------------------------------------

def run_cycle(
    detector: VehicleDetector,
    writer: csv.DictWriter,
    camera_id: str,
    stream_url: str,
    referer: str,
    cycle_number: int = 0,  
    save_every: int = 0,
) -> dict:
    """
    Run one full detection cycle:
        capture → detect → calculate → log → write CSV row.

    Returns the result dict for the caller to use in summary stats.
    Raises RuntimeError if frame capture fails (caller handles retry).
    """
    cycle_start = time.time()

    # 1. Capture frame — raises RuntimeError on failure
    frame = detector.capture_frame(stream_url, referer)

    # 2. Detect vehicles
    counts, annotated = detector.detect(frame)

    # 3. Calculate emissions
    emission = calculate_emission(counts)

    cycle_duration = time.time() - cycle_start

    # 4. Log to console
    logger.info(
        f"[{camera_id}] "
        f"car={counts['car']} moto={counts['motorcycle']} "
        f"bus={counts['bus']} truck={counts['truck']} | "
        f"{emission['total_g_per_min']} g CO₂/min "
        f"({emission['total_kg_per_hr']} kg/hr) | "
        f"cycle={cycle_duration:.1f}s"
    )

    # 5. Write CSV row
    write_row(writer, camera_id, counts, emission, cycle_duration)

    if save_every > 0 and cycle_number % save_every == 0:
        os.makedirs("logs/spot_checks", exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        frame_path = f"logs/spot_checks/cycle_{cycle_number:04d}_{ts}.jpg"
        cv2.imwrite(frame_path, annotated)
        logger.info(f"Saved annotated frame: {frame_path}")

    return {
        "counts": counts,
        "emission": emission,
        "cycle_duration": cycle_duration,
    }


# ------------------------------------------------------------------
# Summary printer
# ------------------------------------------------------------------

def print_summary(stats: dict):
    """Print a readable summary after the loop exits."""
    print("\n" + "=" * 50)
    print("  SESSION SUMMARY")
    print("=" * 50)
    print(f"  Camera        : {stats['camera_id']}")
    print(f"  Total cycles  : {stats['cycles']}")
    print(f"  Failed cycles : {stats['failures']}")
    print(f"  Elapsed time  : {stats['elapsed']:.1f}s")

    if stats["cycles"] > 0:
        avg_g = stats["total_g"] / stats["cycles"]
        print(f"  Avg CO₂/min   : {avg_g:.1f} g")
        print(f"  Peak CO₂/min  : {stats['peak_g']:.1f} g")
        print(f"  Avg cycle time: {stats['total_cycle_time'] / stats['cycles']:.2f}s")

    print(f"  Log saved to  : {stats['csv_path']}")
    print("=" * 50 + "\n")


# ------------------------------------------------------------------
# Main loop
# ------------------------------------------------------------------

def main(
    stream_url: str,
    referer: str,
    camera_id: str,
    interval: int,
    csv_path: str,
    save_every: int,
):
    logger.info("=" * 50)
    logger.info("  EcoTraffic GIS — Stream Loop Starting")
    logger.info("=" * 50)
    logger.info(f"  Camera   : {camera_id}")
    logger.info(f"  Interval : {interval}s")
    logger.info(f"  Stream   : {stream_url}")
    logger.info(f"  CSV      : {csv_path}")
    logger.info("  Press Ctrl+C to stop.\n")

    # Load model once
    detector = VehicleDetector()

    # Open CSV
    csv_file, writer = open_csv(csv_path)

    # Session stats
    stats = {
        "camera_id":       camera_id,
        "cycles":          0,
        "failures":        0,
        "total_g":         0.0,
        "peak_g":          0.0,
        "total_cycle_time": 0.0,
        "elapsed":         0.0,
        "csv_path":        csv_path,
    }

    session_start = time.time()
    consecutive_failures = 0

    try:
        while True:
            loop_start = time.time()

            try:
                result = run_cycle(
                    detector=detector,
                    writer=writer,
                    camera_id=camera_id,
                    stream_url=stream_url,
                    referer=referer,
                    cycle_number=stats["cycles"],
                    save_every=save_every
                )
                csv_file.flush()  # write to disk immediately, don't buffer

                # Update stats
                g = result["emission"]["total_g_per_min"]
                stats["cycles"] += 1
                stats["total_g"] += g
                stats["peak_g"] = max(stats["peak_g"], g)
                stats["total_cycle_time"] += result["cycle_duration"]

                consecutive_failures = 0  # reset on success

            except RuntimeError as e:
                stats["failures"] += 1
                consecutive_failures += 1
                logger.warning(
                    f"Stream capture failed (attempt {consecutive_failures}/"
                    f"{MAX_CONSECUTIVE_FAILURES}): {e}"
                )

                if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                    logger.error(
                        f"Stream failed {MAX_CONSECUTIVE_FAILURES} times in a row. "
                        f"Giving up."
                    )
                    break

                logger.info(f"Retrying in {STREAM_FAILURE_BACKOFF_S}s...")
                time.sleep(STREAM_FAILURE_BACKOFF_S)
                continue

            # Sleep for the remainder of the interval
            elapsed_this_cycle = time.time() - loop_start
            sleep_time = max(0, interval - elapsed_this_cycle)

            if sleep_time > 0:
                logger.debug(f"Sleeping {sleep_time:.1f}s until next cycle.")
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        logger.info("Ctrl+C received — shutting down cleanly.")

    finally:
        stats["elapsed"] = time.time() - session_start
        csv_file.close()
        print_summary(stats)


# ------------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="EcoTraffic GIS — Continuous stream detection loop"
    )
    parser.add_argument(
        "--stream-url",
        type=str,
        default=STREAM_URL,
        help="HLS .m3u8 stream URL",
    )
    parser.add_argument(
        "--referer",
        type=str,
        default=REFERER,
        help="HTTP Referer header for the CCTV portal",
    )
    parser.add_argument(
        "--camera-id",
        type=str,
        default=CAMERA_ID,
        help="Unique label for this camera (used in CSV and logs)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=INTERVAL_SECONDS,
        help="Seconds between detection cycles (default: 5)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=DEFAULT_CSV_PATH,
        help="Path to output CSV log file",
    )

    parser.add_argument(
        "--save-every",
        type=int,
        default=0,
        help="Save annotated frame every N cycles. 0 = disabled.",
    )

    args = parser.parse_args()

    main(
        stream_url=args.stream_url,
        referer=args.referer,
        camera_id=args.camera_id,
        interval=args.interval,
        csv_path=args.output,
        save_every=args.save_every
    )