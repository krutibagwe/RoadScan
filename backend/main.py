from fastapi import FastAPI, UploadFile, File, HTTPException
import shutil
import os
import sqlite3
from backend.process_video import process_video
from backend.database import init_db, search_plate

app = FastAPI()

UPLOAD_DIR = "data"
PROCESSED_DIR = "processed"

# Ensure necessary folders exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

# Initialize database on startup
init_db()

@app.post("/upload/")
async def upload_video(video: UploadFile = File(...)):
    try:
        file_location = os.path.join(UPLOAD_DIR, video.filename)

        # Save the uploaded file
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(video.file, buffer)

        # Process the video
        success = process_video(video.filename)
        if not success:
            raise HTTPException(status_code=500, detail="Video processing failed.")

        return {"message": "Processing completed!", "filename": video.filename}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/search/{plate_number}")
async def get_plate(plate_number: str):
    try:
        results = search_plate(plate_number)

        if not results:
            raise HTTPException(status_code=404, detail="No matching plates found.")

        return {"plates": results}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
