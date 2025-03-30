import sqlite3

# Initialize database connection
def init_db():
    conn = sqlite3.connect("backend/data/plates.db")  # Database file location
    cursor = conn.cursor()

    # Create table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS plates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_name TEXT,
            plate_number TEXT,
            timestamp TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Function to insert a detected plate
def insert_plate(video_name, plate_number, timestamp):
    conn = sqlite3.connect("backend/data/plates.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO plates (video_name, plate_number, timestamp) VALUES (?, ?, ?)",
                   (video_name, plate_number, timestamp))
    conn.commit()
    conn.close()

# Function to search for a plate number
def search_plate(plate_number):
    conn = sqlite3.connect("backend/data/plates.db")
    cursor = conn.cursor()
    cursor.execute("SELECT video_name, timestamp FROM plates WHERE plate_number = ?", (plate_number,))
    results = cursor.fetchall()
    conn.close()
    return results
