import cv2
import easyocr
import torch
import os
import pandas as pd
from ultralytics import YOLO

# Load YOLO model
model = YOLO("models/best.pt") 

# Load OCR
reader = easyocr.Reader(["en"])

def process_video(video_name):
    video_path = os.path.join("data", video_name)
    output_csv = os.path.join("results", f"{video_name}.csv")
    output_video_path = os.path.join("processed", video_name)

    cap = cv2.VideoCapture(video_path)
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    out = cv2.VideoWriter(output_video_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (frame_width, frame_height))

    plate_data = []

    for i in range(frame_count):
        ret, frame = cap.read()
        if not ret:
            break

        results = model(frame, conf = 0.5)
        result = results[0]  # Extract first result

        for box in result.boxes.data:  # ✅ FIXED: Correct way to access boxes
            x_min, y_min, x_max, y_max, conf, cls = map(int, box[:6])  # Extract bbox

            plate_crop = frame[y_min:y_max, x_min:x_max]

            ocr_results = reader.readtext(plate_crop)
            for bbox, text, prob in ocr_results:
                plate_data.append({"video": video_name, "timestamp": i // fps, "plate": text})
                cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)
                cv2.putText(frame, text, (x_min, y_min - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

        out.write(frame)

    cap.release()
    out.release()
    pd.DataFrame(plate_data).to_csv(output_csv, index=False)
    print(f"Processed {video_name}")
# Change this to the actual video file in data/
process_video("sample2.mp4")  
