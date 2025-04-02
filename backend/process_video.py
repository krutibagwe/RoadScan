import cv2
import easyocr
import os
import pandas as pd
from ultralytics import YOLO
from backend.database import insert_plate

# Ensure necessary folders exist
os.makedirs("data", exist_ok=True)
os.makedirs("results", exist_ok=True)
os.makedirs("processed", exist_ok=True)

# Load YOLO model
model = YOLO("models/license_plate_detector.pt")

# Load OCR
reader = easyocr.Reader(["en"])

def process_video(video_name):
    video_path = os.path.join("data", video_name)
    output_csv = os.path.join("results", f"{video_name}.csv")
    output_video_path = os.path.join("processed", video_name)

    if not os.path.exists(video_path):
        print(f"Error: File '{video_path}' not found!")
        return False

    cap = cv2.VideoCapture(video_path)
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    if not cap.isOpened():
        print(f"Error: Could not open video '{video_path}'")
        return False

    out = cv2.VideoWriter(output_video_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (frame_width, frame_height))

    plate_data = []

    for i in range(frame_count):
        ret, frame = cap.read()
        if not ret:
            break

        results = model(frame, conf=0.5)
        result = results[0]

        for box in result.boxes.data:
            x_min, y_min, x_max, y_max, conf, cls = map(int, box[:6])
            plate_crop = frame[y_min:y_max, x_min:x_max]

            ocr_results = reader.readtext(plate_crop)
            for bbox, text, prob in ocr_results:
                timestamp = round(i / fps, 3)
                plate_data.append({"video": video_name, "timestamp": timestamp, "plate": text})

                # Store in database
                insert_plate(video_name, text, timestamp)

                # Draw bounding box and label on frame
                cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)
                cv2.putText(frame, text, (x_min, y_min - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

        out.write(frame)

    cap.release()
    out.release()

    # Save plate data to CSV
    df = pd.DataFrame(plate_data)
    if not df.empty:
        df.to_csv(output_csv, index=False)

    print(f"✅ Processed {video_name}")
    return True
