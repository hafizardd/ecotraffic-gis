from ultralytics import YOLO
import cv2
import os
import subprocess
import time
import argparse
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

STREAM_URL = "https://cctvjss.jogjakota.go.id/atcs/ATCS_Utara-Timur_Gardena_Jl_Urip%20Sumoharjo_V_Timur.stream/playlist.m3u8"
REFERER = "https://cctv.jogjakota.go.id/"

VEHICLE_CLASSES = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck"
}

MODEL_PATH = os.path.join(BASE_DIR, "yolo", "yolov8l.pt")


def get_frame_from_stream_opencv(url, timeout=10):
    """Try to capture frame using OpenCV VideoCapture."""
    cap = cv2.VideoCapture(url)
    
    start_time = time.time()
    while not cap.isOpened():
        if time.time() - start_time > timeout:
            cap.release()
            return None
        time.sleep(0.5)
    
    ret, frame = cap.read()
    cap.release()
    
    if ret and frame is not None:
        return frame
    return None


def get_frame_from_stream_ffmpeg(url, referer):
    """Fallback: capture frame using ffmpeg subprocess."""
    cmd = [
        "ffmpeg",
        "-y",
        "-headers", f"Referer: {referer}",
        "-i", url,
        "-frames:v", "1",
        "-f", "image2pipe",
        "-vcodec", "png",
        "-"
    ]
    
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            timeout=30
        )
        
        if proc.returncode == 0 and proc.stdout:
            nparr = np.frombuffer(proc.stdout, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return frame
    except Exception as e:
        print(f"ffmpeg fallback failed: {e}")
    
    return None


def capture_stream_frame(url, referer):
    """Capture a single frame from HLS stream with fallback."""
    print(f"Attempting to capture frame from stream...")
    print(f"URL: {url}")
    
    frame = get_frame_from_stream_opencv(url)
    
    if frame is None:
        print("cv2.VideoCapture failed, trying ffmpeg fallback...")
        try:
            import numpy as np
            frame = get_frame_from_stream_ffmpeg(url, referer)
        except ImportError:
            print("numpy not available for ffmpeg fallback")
    
    if frame is None:
        raise RuntimeError("Failed to capture frame from stream")
    
    print(f"Successfully captured frame: {frame.shape}")
    return frame


def load_test_image(image_path):
    """Load a local test image."""
    if not os.path.isabs(image_path):
        image_path = os.path.join(BASE_DIR, image_path)
    
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Failed to load image: {image_path}")
    
    print(f"Loaded image: {image_path}")
    return img


def detect_vehicles(frame, model):
    """Run YOLOv8 detection and return vehicle count dict."""
    results = model(frame)
    
    vehicle_counts = {
        "car": 0,
        "motorcycle": 0,
        "bus": 0,
        "truck": 0
    }
    
    annotated_frame = frame.copy()
    
    for result in results:
        boxes = result.boxes
        for box in boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            
            if cls_id in VEHICLE_CLASSES:
                label = VEHICLE_CLASSES[cls_id]
                vehicle_counts[label] += 1
                
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                
                cv2.rectangle(
                    annotated_frame,
                    (x1, y1),
                    (x2, y2),
                    (0, 255, 0),
                    2
                )
                
                cv2.putText(
                    annotated_frame,
                    f"{label} {conf:.2f}",
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2
                )
                
                print(f"Detected: {label} ({conf:.2f})")
    
    return vehicle_counts, annotated_frame


def save_output(annotated_frame, output_filename):
    """Save the annotated frame to output file."""
    output_dir = os.path.dirname(__file__)
    output_path = os.path.join(output_dir, output_filename)
    
    cv2.imwrite(output_path, annotated_frame)
    print(f"Saved annotated frame to: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="YOLO Vehicle Detection Test")
    parser.add_argument(
        "--mode",
        choices=["stream", "image"],
        default="image",
        help="Select input mode: stream (live CCTV) or image (local file)"
    )
    parser.add_argument(
        "--path",
        type=str,
        default=None,
        help="Path to test image (only for image mode)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="output.jpg",
        help="Output filename for annotated frame"
    )
    
    args = parser.parse_args()
    
    print(f"Loading YOLO model: {MODEL_PATH}")
    model = YOLO(MODEL_PATH)
    
    if args.mode == "stream":
        print("\n=== STREAM MODE ===")
        frame = capture_stream_frame(STREAM_URL, REFERER)
    else:
        print("\n=== IMAGE MODE ===")
        if args.path is None:
            args.path = os.path.join("tests", "frames_chunklist_w760075980.m3u8", "chunklist_w760075980.m3u8_3.jpg")
        frame = load_test_image(args.path)
    
    print("\nRunning vehicle detection...")
    vehicle_counts, annotated_frame = detect_vehicles(frame, model)
    
    print("\n=== VEHICLE COUNT ===")
    print(vehicle_counts)
    
    save_output(annotated_frame, args.output)
    
    print("\nDone!")


if __name__ == "__main__":
    main()