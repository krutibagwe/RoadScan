import sqlite3

DB_PATH = "backend/data/database.db"

# Initialize database with floating-point timestamp
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS plates")

    # Create a new table with REAL type for timestamp (supports decimals)
    cursor.execute('''
        CREATE TABLE plates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_name TEXT,
            plate_number TEXT,
            timestamp REAL  -- REAL type supports floating-point values
        )
    ''')
    conn.commit()
    conn.close()

# Insert plate detection data with precise timestamps
def insert_plate(video_name, plate_number, timestamp):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO plates (video_name, plate_number, timestamp) VALUES (?, ?, ?)",
                   (video_name, plate_number, timestamp))
    conn.commit()
    conn.close()

# Search plates by number (supports partial matches)
def search_plate(plate_number):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT video_name, timestamp FROM plates WHERE plate_number LIKE ?", (f"%{plate_number}%",))
    results = cursor.fetchall()
    conn.close()
    return results

if __name__ == "__main__":
    init_db()  # Run this to create/reset the database
    print("✅ Database initialized successfully!")
