from fastapi import FastAPI, UploadFile, File, HTTPException
import shutil
import os
import sqlite3
from backend.process_video import process_video

app = FastAPI()

UPLOAD_DIR = "data"
PROCESSED_DIR = "processed"
DB_PATH = "database.db"

# Ensure necessary folders exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

# Initialize SQLite database
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS plates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video TEXT,
            timestamp INTEGER,
            plate TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()  # Call this function on startup

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
async def search_plate(plate_number: str):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT video, timestamp FROM plates WHERE plate LIKE ?", (f"%{plate_number}%",))
        results = cursor.fetchall()
        conn.close()

        if not results:
            raise HTTPException(status_code=404, detail="No matching plates found.")

        return {"plates": results}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
