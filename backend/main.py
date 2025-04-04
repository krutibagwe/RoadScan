from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import shutil
import os
from process_video import process_video
from database import search_plate, init_db, create_video_table
import sqlite3
import time
import uuid
import json

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "backend/data"
PROCESSED_DIR = "backend/processed"
RESULTS_DIR = "backend/results"
TASKS_DIR = "backend/tasks"  # Directory to store task status

# Ensure necessary folders exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(TASKS_DIR, exist_ok=True)

# Initialize database
init_db()
# Add this line to log database initialization
print("Database initialized successfully")

# Storage for background tasks
processing_tasks = {}

# Upload without processing
@app.post("/upload/no_process")
async def upload_video_without_processing(video: UploadFile = File(...)):
    file_location = os.path.join(UPLOAD_DIR, video.filename)

    # Save the uploaded file
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(video.file, buffer)
    
    return {"message": "Video uploaded successfully", "filename": video.filename}

# Original upload with processing
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

# Process a previously uploaded video
@app.post("/process/{filename}")
async def process_video_endpoint(filename: str, background_tasks: BackgroundTasks):
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Video file {filename} not found")
    
    # Generate a task ID
    task_id = str(uuid.uuid4())
    task_file = os.path.join(TASKS_DIR, f"{task_id}.json")
    
    # Initialize task status
    task_status = {
        "id": task_id,
        "filename": filename,
        "status": "queued",
        "progress": 0,
        "start_time": time.time(),
        "end_time": None
    }
    
    # Save initial task status
    with open(task_file, "w") as f:
        json.dump(task_status, f)
    
    # Store task reference
    processing_tasks[task_id] = task_status
    
    # Start background processing
    background_tasks.add_task(process_video_background_task, filename, task_id)
    
    return {"task_id": task_id, "status": "queued", "filename": filename}

# Function to run video processing in background
def process_video_background_task(filename: str, task_id: str):
    task_file = os.path.join(TASKS_DIR, f"{task_id}.json")
    
    try:
        # Create table for this video first to avoid the "no such table" error
        create_video_table(filename)
        
        # Update task status to processing
        task_status = {
            "id": task_id,
            "filename": filename,
            "status": "processing",
            "progress": 0,
            "start_time": time.time(),
            "end_time": None
        }
        
        with open(task_file, "w") as f:
            json.dump(task_status, f)
        
        # Process the video and capture progress updates
        def progress_callback(percent):
            task_status["progress"] = percent
            with open(task_file, "w") as f:
                json.dump(task_status, f)
        
        plate_data = process_video(filename, progress_callback)
        
        # Mark task as completed
        task_status["status"] = "completed"
        task_status["progress"] = 100
        task_status["end_time"] = time.time()
        task_status["results"] = {
            "plates_detected": len(plate_data)
        }
        
        with open(task_file, "w") as f:
            json.dump(task_status, f)
            
    except Exception as e:
        # Mark task as failed
        error_message = str(e)
        print(f"Processing error for {filename}: {error_message}")
        
        task_status = {
            "id": task_id,
            "filename": filename,
            "status": "failed",
            "progress": 0,
            "error": error_message,
            "end_time": time.time()
        }
        
        with open(task_file, "w") as f:
            json.dump(task_status, f)

# Get processing status
@app.get("/process/status/{task_id}")
async def get_processing_status(task_id: str):
    task_file = os.path.join(TASKS_DIR, f"{task_id}.json")
    
    if not os.path.exists(task_file):
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    with open(task_file, "r") as f:
        task_status = json.load(f)
    
    return task_status

# Download processed video
@app.get("/download/video/{filename}")
async def download_video(filename: str):
    file_path = os.path.join(PROCESSED_DIR, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Processed video {filename} not found")
    
    return FileResponse(
        file_path, 
        media_type="video/mp4",
        filename=f"processed_{filename}"
    )

# Download CSV results
@app.get("/download/csv/{filename}")
async def download_csv(filename: str):
    file_path = os.path.join(RESULTS_DIR, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"CSV file {filename} not found")
    
    return FileResponse(
        file_path, 
        media_type="text/csv",
        filename=f"results_{filename}"
    )

@app.get("/search/{plate_number}")
async def search_plate_endpoint(plate_number: str):
    results = search_plate(plate_number)
    return {"results": [{"video": video, "timestamp": int(timestamp)} for video, timestamp in results]}

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