from ultralytics import YOLO

model = YOLO("yamero999/chess-piece-detection-yolo11n")
results = model("chess_board.jpg", imgsz=416, conf=0.5)

# Display results
print(results[0].show())