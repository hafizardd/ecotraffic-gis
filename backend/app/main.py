from ultralytics import YOLO

model = YOLO("yolov8n.pt")

results = model.predict(source="https://cdn.antaranews.com/cache/1200x800/2025/04/08/Suasana-lalu-lintas-Jakarta-Setelah-Libur-Lebaran-Jakarta-080425-Rn-1.jpg", show=True)