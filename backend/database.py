import sqlite3

def init_db():
    """Initialize the main database file without creating tables"""
    conn = sqlite3.connect("backend/data/plates.db")
    conn.close()

def create_video_table(video_name):
    """Create a separate table for each video"""
    conn = sqlite3.connect("backend/data/plates.db")
    cursor = conn.cursor()
    
    # Remove file extension and sanitize name for SQL
    table_name = video_name.split('.')[0].replace('-', '_')
    
    # Create table if it doesn't exist
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS "{table_name}" (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plate_number TEXT,
            timestamp TEXT
        )
    ''')
    conn.commit()
    conn.close()
    return table_name

def insert_plate(video_name, plate_number, timestamp):
    """Insert a plate into the video-specific table"""

    table_name = video_name.split('.')[0].replace('-', '_')
    
    # Ensure table exists
    create_video_table(video_name)
    
    conn = sqlite3.connect("backend/data/plates.db")
    cursor = conn.cursor()
    cursor.execute(f'INSERT INTO "{table_name}" (plate_number, timestamp) VALUES (?, ?)',
                   (plate_number, timestamp))
    conn.commit()
    conn.close()

def search_plate(plate_number):
    """Search for a plate across all video tables"""
    conn = sqlite3.connect("backend/data/plates.db")
    cursor = conn.cursor()
    
    # Get all tables in the database
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    
    results = []
    for table in tables:
        # Skip system tables
        if table.startswith('sqlite_'):
            continue
            
        # Search in this table
        try:
            cursor.execute(f'SELECT timestamp FROM "{table}" WHERE plate_number = ?', (plate_number,))
            timestamps = cursor.fetchall()
            for timestamp in timestamps:
                # Reconstruct video name from table name (add extension)
                video_name = f"{table}.mp4"
                results.append((video_name, timestamp[0]))
        except sqlite3.Error as e:
            print(f"Error searching in table {table}: {e}")
    
    conn.close()
    return results