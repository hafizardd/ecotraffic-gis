import cv2
import os
from urllib.parse import urlparse

url = "https://cctvjss.jogjakota.go.id/atcs/ATCS_Utara-Timur_Gardena_Jl_Urip%20Sumoharjo_V_Timur.stream/chunklist_w760075980.m3u8"

# Extract camera name from URL
parsed = urlparse(url)
print(f"Parsed URL: {parsed}")  # Debug print to check URL parsing

camera_name = os.path.basename(parsed.path).replace(".stream/playlist.m3u8", "")
camera_name = camera_name.replace(".stream", "")

print(f"Camera name: {camera_name}")  # Debug print to check camera name extraction

# Create output folder
output_dir = f"frames_{camera_name}"
os.makedirs(output_dir, exist_ok=True)

# Open stream
cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)

if not cap.isOpened():
    print("Error: Could not open video stream")
    exit()

frame_count = 0
saved_count = 0

# How many frames you want to save
max_frames = 10

# Save every N-th frame
skip_frames = 30

while saved_count < max_frames:
    ret, frame = cap.read()

    if not ret:
        print("Error: Could not read frame")
        break

    frame_count += 1

    # Skip frames to avoid saving near-identical images
    if frame_count % skip_frames != 0:
        continue

    output_path = os.path.join(
        output_dir,
        f"{camera_name}_{saved_count + 1}.jpg"
    )

    cv2.imwrite(output_path, frame)

    print(f"Saved: {output_path}")

    saved_count += 1

cap.release()

print("Done extracting frames")