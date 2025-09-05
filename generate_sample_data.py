import sqlite3
import random
from datetime import datetime, timedelta

def init_db():
    """Initialize SQLite database and create registrations table"""
    conn = sqlite3.connect('registrations.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS registrations (
            user_id TEXT PRIMARY KEY,
            country TEXT NOT NULL,
            reg_timestamp DATETIME NOT NULL
        )
    ''')

    conn.commit()
    return conn

def generate_sample_data(num_records=1000, last_days=3):
    """
    Generate random sample data and store in database

    Args:
        num_records: Number of records to generate
        last_days: Number of days to look back

    Returns:
        None
    """
    conn = init_db()
    cursor = conn.cursor()

    countries = ['US', 'UK', 'DE', 'FR', 'IT', 'ES', 'CA', 'AU', 'JP', 'KR']
    start_date = datetime.now() - timedelta(days=last_days)

    cursor.execute('DELETE FROM registrations')  # Clear existing data

    for i in range(num_records):
        user_id = f"user_{i:04d}"
        country = random.choice(countries)
        # Generate timestamps
        hours_offset = random.randint(0, last_days*24)
        reg_timestamp = start_date + timedelta(hours=hours_offset)

        cursor.execute('''
            INSERT INTO registrations (user_id, country, reg_timestamp)
            VALUES (?, ?, ?)
        ''', (user_id, country, reg_timestamp))

    conn.commit()
    conn.close()
    print(f"Generated {num_records} sample records")

if __name__ == "__main__":
    generate_sample_data()
    print("Sample data generation completed!")
