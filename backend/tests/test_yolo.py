from ultralytics import YOLO
import cv2
import requests
import numpy as np
import os

# Load YOLOv8 model
model = YOLO("yolo/yolov8l.pt")

test_image_url = "https://cdn.antaranews.com/cache/1200x800/2025/04/08/Suasana-lalu-lintas-Jakarta-Setelah-Libur-Lebaran-Jakarta-080425-Rn-1.jpg"

# Download image bytes and decode to array (cv2.imread can't read URLs)
resp = requests.get(test_image_url, timeout=15)
resp.raise_for_status()
img_array = np.frombuffer(resp.content, np.uint8)
img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
if img is None:
    raise RuntimeError("Failed to load image from URL")

# Run detection on the image (pass image array to model)
results = model(img)

# COCO vehicle classes we care about
vehicle_classes = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck"
}

# Process detections
for result in results:
    boxes = result.boxes

    for box in boxes:
        cls_id = int(box.cls[0])
        conf = float(box.conf[0])

        if cls_id in vehicle_classes:
            label = vehicle_classes[cls_id]

            x1, y1, x2, y2 = map(int, box.xyxy[0])

            # Draw bounding box
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)

            text = f"{label} {conf:.2f}"

            cv2.putText(
                img,
                text,
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2
            )

            print(f"Detected: {label} ({conf:.2f})")

# Save output next to this test file
out_path = os.path.join(os.path.dirname(__file__), "output.jpg")
cv2.imwrite(out_path, img)

print(f"\nDone. Check {out_path}")