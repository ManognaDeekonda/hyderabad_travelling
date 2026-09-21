import json
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

# PostgreSQL connection details
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "hyderabad_trip_planner"
DB_USER = "postgres"
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")

# Load JSON
with open("places.json", "r", encoding="utf-8") as f:
    places = json.load(f)

print(f"Loaded {len(places)} places from places.json")

# Connect to PostgreSQL
conn = psycopg2.connect(
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD
)

cursor = conn.cursor()

# Insert places
insert_query = """
    INSERT INTO places (
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
    )
    VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
    )
"""

for place in places:
    cursor.execute(
        insert_query,
        (
            place.get("name"),
            place.get("area"),
            place.get("category"),
            place.get("subcategory"),
            place.get("price_range"),
            place.get("best_time"),
            place.get("mood_tags"),
            place.get("company_tags"),
            place.get("time_needed"),
            place.get("rating"),
            place.get("maps_link"),
            place.get("youtube_link"),
        )
    )

conn.commit()

print(f"Successfully inserted {len(places)} places into PostgreSQL.")

cursor.close()
conn.close()