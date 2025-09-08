import sqlite3
import random
import os
from datetime import datetime, timedelta


def init_db():
    """Initialize SQLite database and create registrations table"""
    # Get the project root directory (parent of scripts directory)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(project_root, "registrations.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS registrations (
            user_id TEXT PRIMARY KEY,
            country TEXT NOT NULL,
            reg_timestamp DATETIME NOT NULL
        )
    """
    )

    conn.commit()
    return conn


def generate_sample_data(num_records=5000, last_days=14):
    """
    Generate random sample data and store in database

    Args:
        num_records: Number of records to generate (default: 5000)
        last_days: Number of days to look back (default: 14)

    Returns:
        None
    """
    conn = init_db()
    cursor = conn.cursor()

    countries = ["US", "UK", "DE", "FR", "IT", "ES", "CA", "AU", "JP", "KR"]
    start_date = datetime.now() - timedelta(days=last_days)

    cursor.execute("DELETE FROM registrations")  # Clear existing data

    for i in range(num_records):
        user_id = f"user_{i:04d}"
        country = random.choice(countries)
        # Generate timestamps
        hours_offset = random.randint(0, last_days * 24)
        reg_timestamp = start_date + timedelta(hours=hours_offset)

        cursor.execute(
            """
            INSERT INTO registrations (user_id, country, reg_timestamp)
            VALUES (?, ?, ?)
        """,
            (user_id, country, reg_timestamp),
        )

    conn.commit()
    conn.close()
    print(f"Generated {num_records} sample records")


if __name__ == "__main__":
    generate_sample_data()
    print("Sample data generation completed!")
