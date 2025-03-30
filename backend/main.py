from fastapi import FastAPI, UploadFile, File
import shutil
import os
from backend.process_video import process_video
import sqlite3

app = FastAPI()

UPLOAD_DIR = "backend/data"
PROCESSED_DIR = "backend/processed"

# Ensure necessary folders exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

@app.post("/upload/")
async def upload_video(video: UploadFile = File(...)):
    file_location = os.path.join(UPLOAD_DIR, video.filename)

    # Save the uploaded file
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(video.file, buffer)

    # Process the video
    process_video(video.filename)

    return {"message": "Processing completed!", "filename": video.filename}

@app.get("/search/{plate_number}")
async def search_plate(plate_number: str):
    conn = sqlite3.connect("backend/database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT video, timestamp FROM plates WHERE plate LIKE ?", (f"%{plate_number}%",))
    results = cursor.fetchall()
    conn.close()
    return results


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
