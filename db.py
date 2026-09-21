import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "hyderabad_trip_planner",
    "user": "postgres",
    "password": os.getenv("POSTGRES_PASSWORD")
}


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def get_all_places():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            name,
            area,
            category,
            subcategory,
            price_range,
            best_time,
            mood_tags,
            company_tags,
            time_needed,
            rating,
            maps_link,
            youtube_link
        FROM places
    """)

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    columns = [
        "id",
        "name",
        "area",
        "category",
        "subcategory",
        "price_range",
        "best_time",
        "mood_tags",
        "company_tags",
        "time_needed",
        "rating",
        "maps_link",
        "youtube_link"
    ]

    return [dict(zip(columns, row)) for row in rows]