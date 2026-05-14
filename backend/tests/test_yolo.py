from ultralytics import YOLO
import cv2
import os

# Load model
model = YOLO("yolo/yolov8l.pt")

# Build absolute path safely
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
print(f"Base directory: {BASE_DIR}")  # Debug print to check base directory

test_image_path = os.path.join(
    BASE_DIR,
    "tests",
    "frames_playlist.m3u8",
    "playlist.m3u8_8.jpg"
)
print(f"Constructed test image path: {test_image_path}")  # Debug print to check constructed path

## backend\tests\frames_playlist.m3u8\playlist.m3u8_8.jpg

print("Loading image:", test_image_path)

# Read image
img = cv2.imread(test_image_path)

if img is None:
    raise FileNotFoundError(f"Failed to load image: {test_image_path}")

# Run YOLO
results = model(img)

vehicle_classes = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck"
}

for result in results:
    for box in result.boxes:
        cls_id = int(box.cls[0])
        conf = float(box.conf[0])

        if cls_id in vehicle_classes:
            label = vehicle_classes[cls_id]

            x1, y1, x2, y2 = map(int, box.xyxy[0])

            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)

            cv2.putText(
                img,
                f"{label} {conf:.2f}",
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2
            )

            print(f"Detected: {label} ({conf:.2f})")

# Save output
output_path = os.path.join(os.path.dirname(__file__), "output.jpg")

cv2.imwrite(output_path, img)

print(f"\nDone. Check {output_path}")