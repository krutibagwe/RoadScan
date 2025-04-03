from fastapi import FastAPI, UploadFile, File, HTTPException
import shutil
import os
from process_video import process_video
from database import search_plate, init_db
import sqlite3

app = FastAPI()

UPLOAD_DIR = "backend/data"
PROCESSED_DIR = "backend/processed"
RESULTS_DIR = "backend/results"

# Ensure necessary folders exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

# Initialize database
init_db()

@app.post("/upload/")
async def upload_video(video: UploadFile = File(...)):
    file_location = os.path.join(UPLOAD_DIR, video.filename)

    # Save the uploaded file
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(video.file, buffer)

    try:
        # Process the video
        plate_data = process_video(video.filename)
        return {"message": "Processing completed!", "filename": video.filename, "plates_detected": len(plate_data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing video: {str(e)}")

@app.get("/search/{plate_number}")
async def search_plate_endpoint(plate_number: str):
    results = search_plate(plate_number)
    return {"results": [{"video": video, "timestamp": timestamp} for video, timestamp in results]}

@app.get("/video/{video_name}/results")
async def get_video_results(video_name: str):
    csv_path = os.path.join(RESULTS_DIR, f"{video_name.split('.')[0]}.csv")
    
    if not os.path.exists(csv_path):
        raise HTTPException(status_code=404, detail=f"Results for video {video_name} not found")
        
    try:
        import pandas as pd
        data = pd.read_csv(csv_path).to_dict('records')
        return {"video": video_name, "results": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading results: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
