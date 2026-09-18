from flask import Flask, render_template, request
import requests
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from flask import send_file,session
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
import re
from urllib.parse import quote_plus
from math import radians, sin, cos, sqrt, atan2
import itertools
from flask_session import Session
from io import BytesIO

# ============================================================
# DESTINATION COORDINATES
# Latitude and longitude of the selected Hyderabad destination
# ============================================================

DESTINATION_COORDINATES = {
    "anywhere": (17.3850, 78.4867),

    "ameerpet": (17.4375, 78.4482),

    "banjara hills": (17.4156, 78.4347),

    "begumpet": (17.4435, 78.4676),

    "charminar": (17.3616, 78.4747),

    "gachibowli": (17.4401, 78.3489),

    "golconda": (17.3833, 78.4011),

    "hitech city": (17.4483, 78.3915),

    "jubilee hills": (17.4326, 78.4071),

    "kondapur": (17.4697, 78.3657),

    "kukatpally": (17.4849, 78.4138),

    "madhapur": (17.4486, 78.3908),

    "secunderabad": (17.4399, 78.4983),

    "tank bund": (17.4239, 78.4738),

    "uppal": (17.4058, 78.5591),
}

# ============================================================
# RATING HELPER
# ============================================================

def normalize_rating(value):
    """
    Convert a rating into a valid float between 0 and 5.
    """

    if value is None:
        return 0.0

    try:
        rating = float(value)
    except (TypeError, ValueError):
        return 0.0

    return max(0.0, min(rating, 5.0))


def normalize_price(place):
    """
    Extract and normalize the price of a place.

    Supports:
    - price_range
    - price
    - cost
    - estimated_cost
    """

    if not isinstance(place, dict):
        return 0

    possible_prices = [
        place.get("price_range"),
        place.get("price"),
        place.get("cost"),
        place.get("estimated_cost")
    ]

    for value in possible_prices:

        if value is None or value == "":
            continue

        try:
            return max(0, int(float(value)))
        except (TypeError, ValueError):
            continue

    # Fallback based on category
    category = str(
        place.get("category", "")
    ).strip().lower()

    return PRICE_BY_CATEGORY.get(category, 500)



# ============================================================
# SAFE RATING EXTRACTION
# ============================================================

def extract_rating(properties):
    """
    Extract rating from JSON places and Geoapify places.

    Supports:
    - Direct rating
    - stars
    - user_rating
    - datasource.raw.rating
    - datasource.raw.stars
    - datasource.raw.user_rating
    """

    if not isinstance(properties, dict):
        return 0.0

    datasource = properties.get("datasource", {})
    if not isinstance(datasource, dict):
        datasource = {}

    raw = datasource.get("raw", {})
    if not isinstance(raw, dict):
        raw = {}

    possible_ratings = [
        # Direct JSON / Geoapify fields
        properties.get("rating"),
        properties.get("stars"),
        properties.get("user_rating"),

        # Geoapify raw fields
        raw.get("rating"),
        raw.get("stars"),
        raw.get("user_rating"),
    ]

    for value in possible_ratings:
        rating = normalize_rating(value)

        if rating > 0:
            return rating

    return 0.0


app = Flask(__name__)
app.secret_key = os.getenv(
    "FLASK_SECRET_KEY",
    "development-secret-key-change-this"
)
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

def normalize_place_name(name):
    """
    Normalize a place name for duplicate comparison.
    """

    name = str(name or "").lower().strip()

    # Remove punctuation
    name = re.sub(r"[^a-z0-9]+", " ", name)

    # Remove common words that may cause duplicate variations
    words_to_remove = {
        "restaurant",
        "cafe",
        "coffee",
        "shop",
        "hotel",
        "bar",
        "the"
    }

    words = [
        word
        for word in name.split()
        if word not in words_to_remove
    ]

    return " ".join(words)


def remove_duplicates(places):
    """
    Remove duplicate places based on normalized name.

    Curated places are preferred over Geoapify places.
    """

    unique_places = {}

    for place in places:

        name = normalize_place_name(
            place.get("name", "")
        )

        if not name:
            continue

        duplicate_key = name

        if duplicate_key not in unique_places:

            unique_places[duplicate_key] = place

        else:

            existing_place = unique_places[
                duplicate_key
            ]

            existing_source = str(
                existing_place.get("source", "")
            ).strip().lower()

            current_source = str(
                place.get("source", "")
            ).strip().lower()

            # Prefer curated places over Geoapify places
            if (
                existing_source == "geoapify"
                and current_source != "geoapify"
            ):

                unique_places[duplicate_key] = place

    return list(unique_places.values())



# ---------------------------
# LOAD DATA SAFELY
# ---------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
json_path = os.path.join(BASE_DIR, "places.json")

try:

    with open(json_path, "r", encoding="utf-8") as file:
        places = json.load(file)

    for place in places:

        place["rating"] = extract_rating(place)

        # Normalize all possible price field names
        raw_price = (
            place.get("price_range")
            if place.get("price_range") is not None
            else place.get("price")
        )

        if raw_price is None:
            raw_price = place.get("cost")

        if raw_price is None:
            raw_price = place.get("estimated_cost")

        try:
            place["price_range"] = max(
                0,
                int(float(raw_price))
            )
        except (TypeError, ValueError):
            place["price_range"] = 500

        place["source"] = "places.json"

except Exception as e:

    app.logger.error(
        f"Failed to load places.json: {e}"
    )

    places = []


from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer
)
from reportlab.lib.styles import getSampleStyleSheet



# ---------------------------
# GEOAPIFY CONFIG
# ---------------------------
BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")

GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API_KEY")

print("GEOAPIFY API KEY LOADED:", bool(GEOAPIFY_API_KEY))

CATEGORY_MAP = {
    "food": "catering.restaurant,catering.cafe",
    "history": "heritage,religion",
    "nature": "leisure.park",
    "entertainment": "entertainment",
    "shopping": "commercial.shopping_mall",
    "nightlife": "catering.bar"
}
PRICE_BY_CATEGORY = {
    "food": 400,
    "history": 200,
    "nature": 100,
    "entertainment": 800,
    "shopping": 2000,
    "nightlife": 1500
}

def generate_summary(
    destination,
    interest,
    mood,
    budget,
    company
):

    return (
        f"Enjoy a {mood} {interest} outing in "
        f"{destination.title()} with your {company}. "
        f"This itinerary has been curated to maximize "
        f"experiences while staying close to your "
        f"Rs.{budget} budget."
    )


def calculate_distance_km(
    lat1,
    lon1,
    lat2,
    lon2
):
    """
    Calculate distance between two coordinates
    using the Haversine formula.
    """

    earth_radius_km = 6371.0

    lat1 = radians(float(lat1))
    lon1 = radians(float(lon1))
    lat2 = radians(float(lat2))
    lon2 = radians(float(lon2))

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        sin(dlat / 2) ** 2
        + cos(lat1)
        * cos(lat2)
        * sin(dlon / 2) ** 2
    )

    c = 2 * atan2(
        sqrt(a),
        sqrt(1 - a)
    )

    return earth_radius_km * c


def create_google_maps_link(place, current_location="Hyderabad"):
    name = str(place.get("name", "")).strip()
    address = str(place.get("address", "")).strip()

    latitude = place.get("lat")     # <-- fixed key, see Bug #2
    longitude = place.get("lon")    # <-- fixed key, see Bug #2

    if latitude is not None and longitude is not None:
        destination = f"{latitude},{longitude}"
    else:
        destination = f"{name}, {address}, Hyderabad" if address else f"{name}, Hyderabad"

    origin = current_location.strip() if current_location else "Hyderabad"

    return (
        "https://www.google.com/maps/dir/?api=1"
        f"&origin={quote_plus(origin)}"
        f"&destination={quote_plus(destination)}"
        "&travelmode=driving"
    )



# ---------------------------
# FETCH LIVE PLACES
# ---------------------------
def get_live_places(interest, destination):
    """
    Fetch live places from Geoapify for the selected interest
    and destination.

    Each place gets its own:
    - name
    - area
    - coordinates
    - Google Maps link
    - YouTube link
    """

    print("\n================ GEOAPIFY SEARCH ================")
    print("Destination Selected:", destination)
    print("Interest Selected:", interest)

    # Normalize destination
    destination_key = str(destination).strip().lower()

    # Get coordinates for the selected destination
    coordinates = DESTINATION_COORDINATES.get(destination_key)

    if coordinates is None:
        print(
            f"❌ No coordinates found for destination: "
            f"{destination_key}"
        )
        return []

    latitude, longitude = coordinates

    print("Search Latitude:", latitude)
    print("Search Longitude:", longitude)

    # Search radius
    if destination_key == "anywhere":
        radius = 5000
    else:
        radius = 4000

    # Geoapify API URL
    url = "https://api.geoapify.com/v2/places"

    # API parameters
    params = {
            "categories": CATEGORY_MAP.get(
                interest,
                "catering.restaurant,catering.cafe"
            ),
            "filter": (
                f"circle:{longitude},{latitude},{radius}"
            ),
            # Prefer places close to the selected destination
            "bias": (
                f"proximity:{longitude},{latitude}"
            ),
            "limit": 50,
            "apiKey": GEOAPIFY_API_KEY
        }

    try:

        # Call Geoapify API
        response = requests.get(
            url,
            params=params,
            timeout=20
        )

        print(
            "Geoapify Status Code:",
            response.status_code
        )

        response.raise_for_status()

        # Convert response to JSON
        data = response.json()

        features = data.get(
            "features",
            []
        )

        print(
            "Geoapify Features Returned:",
            len(features)
        )

        live_places = []

        # Process each Geoapify place separately
        for feature in features:

            properties = feature.get(
                "properties",
                {}
            )

            if not isinstance(properties, dict):
                continue


            # ------------------------------------------------
            # 1. Get THIS place's name
            # ------------------------------------------------
            place_name = str(
                properties.get("name")
                or properties.get("address_line1")
                or ""
            ).strip()

            if not place_name:
                continue


            # ------------------------------------------------
            # STRICT INTEREST FILTER
            # ------------------------------------------------
            geo_categories = str(
                properties.get("categories", "")
            ).lower()

            allowed_categories = {
                "food": [
                    "catering.restaurant",
                    "catering.cafe",
                    "catering.fast_food",
                    "catering.food_court"
                ],
                "history": [
                    "heritage",
                    "tourism.sights",
                    "religion"
                ],
                "nature": [
                    "leisure.park",
                    "leisure.garden"
                ],
                "entertainment": [
                    "entertainment",
                    "tourism.attraction"
                ],
                "shopping": [
                    "commercial.shopping_mall",
                    "commercial.marketplace",
                    "commercial"
                ],
                "nightlife": [
                    "catering.bar",
                    "entertainment.nightclub"
                ]
            }

            valid_categories = allowed_categories.get(
                str(interest).strip().lower(),
                []
            )

            if valid_categories:

                category_matches = any(
                    category.strip() in geo_categories
                    or geo_categories.startswith(category.strip())
                    for category in valid_categories
                )

                if not category_matches:

                    print(
                        "Skipped wrong-interest place:",
                        place_name,
                        "| Categories:",
                        geo_categories
                    )

                    continue

            
            # ------------------------------------------------
            # 2. Remove obviously irrelevant places
            # ------------------------------------------------
            place_name_lower = place_name.lower()

            irrelevant_words = [
                "parking",
                "car park",
                "parking lot",
                "bike parking",
                "hostel",
                "women hostel",
                "womens hostel",
                "university",
                "college",
                "school",
                "institute",
                "office",
                "apartment",
                "residential",
                "pg accommodation"
            ]

            if any(
                word in place_name_lower
                for word in irrelevant_words
            ):
                print(
                    "Skipped irrelevant place:",
                    place_name
                )
                continue

            # ------------------------------------------------
            # 3. Strict Nature filter
            # ------------------------------------------------
            if str(interest).strip().lower() == "nature":

                geo_categories = str(
                    properties.get("categories", "")
                ).lower()

                nature_keywords = [
                    "park",
                    "garden",
                    "lake",
                    "nature_reserve",
                    "botanical",
                    "national_park"
                ]

                is_nature_place = (
                    any(
                        keyword in place_name_lower
                        for keyword in nature_keywords
                    )
                    or any(
                        keyword in geo_categories
                        for keyword in nature_keywords
                    )
                )

                if not is_nature_place:
                    print(
                        "Skipped non-nature place:",
                        place_name
                    )
                    continue
            # ------------------------------------------------
            # 2. Get THIS place's coordinates
            # ------------------------------------------------
            place_latitude = properties.get("lat")
            place_longitude = properties.get("lon")

            if (
                place_latitude is None
                or place_longitude is None
            ):
                continue

            # ------------------------------------------------
            # Check distance from selected destination
            # ------------------------------------------------
            distance_km = calculate_distance_km(
                latitude,
                longitude,
                place_latitude,
                place_longitude
            )

            # Maximum allowed distance
            if destination_key == "anywhere":
                max_distance_km = 5
            else:
                max_distance_km = 4

            if distance_km > max_distance_km:
                print(
                    "Skipped far place:",
                    place_name,
                    "| Distance:",
                    round(distance_km, 2),
                    "km"
                )
                continue

            # ------------------------------------------------
            # 3. Get THIS place's area
            # ------------------------------------------------
            actual_area = (
                properties.get("suburb")
                or properties.get("district")
                or properties.get("city")
                or properties.get("county")
                or destination
            )

            actual_area = str(
                actual_area
            ).strip()

            # ------------------------------------------------
            # 4. Get THIS place's address
            # ------------------------------------------------
            address = (
                properties.get("formatted")
                or properties.get("address_line2")
                or actual_area
            )

            # ------------------------------------------------
            # 5. Get THIS place's rating
            # ------------------------------------------------
            rating = extract_rating(properties)

            # ------------------------------------------------
            # 6. Create Google Maps search link for THIS place
            # ------------------------------------------------

            formatted_address = (
                properties.get("formatted")
                or properties.get("address_line2")
                or properties.get("address_line1")
                or actual_area
                or "Hyderabad"
            )

            maps_query = (
                f"{place_name}, "
                f"{formatted_address}, "
                f"Hyderabad"
            )

            maps_link = (
                "https://www.google.com/maps/search/?api=1&query="
                f"{quote_plus(maps_query)}"
            )
            # ------------------------------------------------
            # 7. Create YouTube link for THIS place
            # ------------------------------------------------
            youtube_query = (
                f"{place_name} "
                f"{actual_area} "
                f"Hyderabad review"
            )

            youtube_link = (
                "https://www.youtube.com/results?search_query="
                f"{quote_plus(youtube_query)}"
            )

            # ------------------------------------------------
            # 8. Create the final place dictionary
            # ------------------------------------------------
            place = {
                "name": place_name,
                "area": actual_area,
                "address": address,
                "category": interest,
                "price_range": PRICE_BY_CATEGORY.get(
                    interest,
                    500
                ),
                "rating": rating,
                "company_tags": [
                    "friends",
                    "family",
                    "couple"
                ],
                "mood_tags": [
                    "fun",
                    "relaxed"
                ],
                "time_needed": "2 hours",
                "lat": place_latitude,
                "lon": place_longitude,
                "source": "Geoapify",
                "maps_link": maps_link,
                "youtube_link": youtube_link
            }
            # ------------------------------------------------
            # 9. Debug the exact links created for this place
            # ------------------------------------------------
            print("\nCreated Geoapify Place:")
            print("Name:", place["name"])
            print("Area:", place["area"])
            print("Latitude:", place["lat"])
            print("Longitude:", place["lon"])
            print("Maps Link:", place["maps_link"])
            print("YouTube Link:", place["youtube_link"])

            # Add this place to the result list
            live_places.append(place)


        print(
            "\nLive Places Created:",
            len(live_places)
        )

        return live_places

    except Exception as e:

        print(
            "Geoapify Error:",
            e
        )

        return []

@app.route("/test-api")
def test_api():

    if not GEOAPIFY_API_KEY:
        return {
            "error": "Geoapify API key is not configured"
        }, 500

    url = (
        "https://api.geoapify.com/v2/places?"
        "categories=catering.restaurant"
        "&filter=circle:78.4867,17.3850,5000"
        "&limit=5"
        f"&apiKey={GEOAPIFY_API_KEY}"
    )

    response = requests.get(url, timeout=10)
    response.raise_for_status()

    return response.json()

# ---------------------------
# HOME PAGE
# ---------------------------
@app.route("/")
def home():
    return render_template("index.html")


# ---------------------------
# PLANNER PAGE
# ---------------------------
@app.route("/planner")
def planner():

    destinations = sorted(
        DESTINATION_COORDINATES.keys()
    )
    return render_template(
        "planner.html",
        destinations=destinations
    )


# ---------------------------
# MAIN PLANNER LOGIC
# ---------------------------
@app.route("/plan", methods=["POST"])
def plan():
    print("========== /plan ROUTE CALLED ==========", flush=True)
    print("PLAN ROUTE CALLED", flush=True)
    print("========== PLAN ROUTE CALLED ==========", flush=True)

    # ---------------------------
    # USER INPUTS
    # ---------------------------
    current_location = request.form.get("current_location", "")
    destination = request.form.get("destination", "Anywhere").strip().lower()
    interest = request.form.get("interest", "").strip().lower()
    company = request.form.get("company", "").strip().lower()
    mood = request.form.get("mood", "").strip().lower()
    try:
       budget = int(request.form.get("budget", 2000))
    except (ValueError, TypeError):
       budget = 2000
    duration = request.form.get("duration", "1 day").lower()

    # ---------------------------
    # TIME SLOTS
    # ---------------------------
    if duration == "weekend":
        slots = [
            "Day 1 Morning",
            "Day 1 Afternoon",
            "Day 1 Evening",
            "Day 2 Morning",
            "Day 2 Afternoon",
            "Day 2 Evening"
        ]

    elif duration == "night":
        slots = ["Evening", "Dinner", "Night"]

    else:
        slots = ["Morning", "Brunch", "Afternoon", "Evening", "Dinner"]

    # ---------------------------
    # SMART MATCHING ENGINE
    # ---------------------------
    matched_places = []

    live_places = get_live_places(
    interest,
    destination
    )
    print("=" * 50)
    print("Interest Selected:", interest)
    print("Live Places Found:", len(live_places))

    for place in live_places[:5]:
        print(place["name"])

    print("=" * 50)

    app.logger.info(f"Interest: {interest}")
    app.logger.info(f"Live Places Found: {len(live_places)}")

    all_places = places + live_places

    for place in all_places:
        place["rating"] = extract_rating(place)

    all_places = remove_duplicates(all_places)
    print("\nUNIQUE PLACES AFTER DUPLICATE REMOVAL:\n")

    for place in all_places:
        print(
            place.get("name"),
            "|",
            place.get("area"),
            "|",
            place.get("source")
        )

    # ============================================================
    # FILTER PLACES BY DESTINATION
    # ============================================================

    destination = str(
        destination
    ).strip().lower()

    print("\n============================================================")
    print("DESTINATION FILTER STARTED")
    print("Selected destination:", destination)
    print("Places before filtering:", len(all_places))
    print("============================================================")


    # ============================================================
    # ANYWHERE: DO NOT FILTER BY DESTINATION
    # ============================================================

    if destination == "anywhere":

        print(
            "🌍 Destination is 'anywhere'. "
            "Skipping destination filtering."
        )

    else:

        # --------------------------------------------------------
        # GET SELECTED DESTINATION COORDINATES
        # --------------------------------------------------------

        selected_coordinates = DESTINATION_COORDINATES.get(
            destination
        )

        if selected_coordinates is None:

            print(
                f"❌ No coordinates found for destination: "
                f"{destination}"
            )

            all_places = []

        else:

            selected_latitude, selected_longitude = (
                selected_coordinates
            )

            print(
                "Selected destination coordinates:",
                selected_latitude,
                selected_longitude
            )

            filtered_places = []

            # ----------------------------------------------------
            # FILTER EVERY PLACE
            # ----------------------------------------------------

            for place in all_places:

                place_name = str(
                    place.get("name", "")
                ).strip()

                area = str(
                    place.get("area", "")
                ).strip().lower()

                source_name = str(
                    place.get("source", "")
                ).strip().lower()

                print(
                    "\nCHECK:",
                    place_name,
                    "| Area:",
                    area,
                    "| Source:",
                    source_name
                )

                # =================================================
                # GEOAPIFY PLACES
                # =================================================

                if source_name == "geoapify":

                    place_lat = place.get("lat")
                    place_lon = place.get("lon")

                    # Skip Geoapify places without coordinates
                    if (
                        place_lat is None
                        or place_lon is None
                    ):

                        print(
                            "❌ SKIPPED: Missing coordinates for",
                            place_name
                        )

                        continue

                    try:

                        distance = calculate_distance_km(
                            selected_latitude,
                            selected_longitude,
                            place_lat,
                            place_lon
                        )

                    except (
                        TypeError,
                        ValueError
                    ) as error:

                        print(
                            "❌ SKIPPED: Invalid coordinates for",
                            place_name,
                            "| Error:",
                            error
                        )

                        continue

                    # Store distance for displaying/debugging
                    place["distance_km"] = round(
                        distance,
                        2
                    )

                    print(
                        f"📍 {place_name} | "
                        f"Distance: {distance:.2f} km"
                    )

                    # Keep only Geoapify places within 3 km
                    if distance <= 3:

                        print(
                            f"✅ KEPT GEOAPIFY PLACE: "
                            f"{place_name}"
                        )

                        filtered_places.append(
                            place
                        )

                    else:

                        print(
                            f"❌ REMOVED GEOAPIFY PLACE: "
                            f"{place_name} | "
                            f"{distance:.2f} km away"
                        )

                # =================================================
                # CURATED JSON PLACES
                # =================================================

                else:

                    # Curated places are filtered using their area
                    if destination in area:

                        print(
                            f"✅ KEPT CURATED PLACE: "
                            f"{place_name}"
                        )

                        filtered_places.append(
                            place
                        )

                    else:

                        print(
                            f"❌ REMOVED CURATED PLACE: "
                            f"{place_name}"
                        )

            # ----------------------------------------------------
            # UPDATE ALL PLACES AFTER FILTERING
            # ----------------------------------------------------

            all_places = filtered_places

            # ====================================================
            # PRINT FILTERED RESULTS
            # ====================================================

            print("\n============================================================")
            print("FILTERED PLACES")
            print("============================================================")

            if not all_places:

                print(
                    "⚠️ No places remained after destination filtering."
                )

            else:

                for place in all_places[:20]:

                    print(
                        place.get("name", ""),
                        "| Area:",
                        place.get("area", ""),
                        "| Source:",
                        place.get("source", ""),
                        "| Distance:",
                        place.get("distance_km", "N/A"),
                        "km"
                    )

            # ====================================================
            # PRINT SOURCE COUNTS
            # ====================================================

            geoapify_count = sum(
                1
                for place in all_places
                if str(
                    place.get("source", "")
                ).strip().lower() == "geoapify"
            )

            curated_count = sum(
                1
                for place in all_places
                if str(
                    place.get("source", "")
                ).strip().lower() != "geoapify"
            )

            print(
                "\nTotal places remaining:",
                len(all_places)
            )

            print(
                "Geoapify places remaining:",
                geoapify_count
            )

            print(
                "Curated places remaining:",
                curated_count
            )

            print("\nEND DESTINATION FILTER\n")


    # ============================================================
    # LOG PLACE COUNTS
    # ============================================================
    app.logger.info(f"JSON Places: {len(places)}")
    app.logger.info(f"Live Places: {len(live_places)}")
    app.logger.info(f"Total Places: {len(all_places)}")

    for place in all_places:

        score = 0

        area = str(place.get("area", "") or "").lower()
        category = str(place.get("category", "") or "").lower()
        price = normalize_price(place)
        rating = place.get("rating", 0)

        try:
            rating = float(rating)
        except (TypeError, ValueError):
            rating = 0.0

        rating = max(0.0, min(rating, 5.0))

        company_tags = [
            str(x).lower()
            for x in place.get("company_tags", [])
        ]

        mood_tags = [
            str(x).lower()
            for x in place.get("mood_tags", [])
        ]

        # Destination match
        if destination == "anywhere":
            if str(place.get("source", "")).strip().lower() == "geoapify":
                score += 8
            else:
                score += 1
        elif str(place.get("source", "")).strip().lower() == "geoapify":
            score += 8
        elif destination in area:
            score += 8


        # Interest match
        if interest and category == interest:
            score += 5

        # Company match
        if company and company in company_tags:
            score += 4

        # Mood match
        if mood and mood in mood_tags:
            score += 4

        # Budget scoring
        if price <= budget:
            score += 5
        elif price <= budget + 300:
            score += 2

        # Rating scoring: maximum 8 points
        score += min(rating * 2, 8)

        # Hidden gem bonus
        if rating >= 4.2 and price < 300:
            score += 2
        
        # Live place bonus
        if str(place.get("source", "")).strip().lower() == "geoapify":
            score += 1

        if score >= 7:
            new_place = place.copy()
            new_place["score"] = score
            app.logger.info(
                f"MATCHED: {new_place['name']} | "
                f"Source: {new_place.get('source','unknown')} | "
                f"Score: {score}"
            )

            matched_places.append(new_place)

    # Sort best first
    matched_places.sort(key=lambda x: x["score"], reverse=True)
    
    print("\nTOP MATCHED PLACES\n")


    for p in matched_places[:20]:

        print(
            p["name"],
            "|",
            p["area"],
            "|",
            p["source"],
            "|",
            p["score"]
        )

    print("\nEND MATCHED PLACES\n")

    # ---------------------------
    # REMOVE DUPLICATES (GLOBAL)
    # ---------------------------

    matched_places = remove_duplicates(
        matched_places
    )

    print("\nAFTER DEDUP\n")

    for p in matched_places[:20]:

        print(
            p.get("name"),
            "|",
            p.get("area"),
            "|",
            p.get("source")
        )

    print("\nEND AFTER DEDUP\n")

    print(
        "After Dedup:",
        len(matched_places)
    )
    # ---------------------------
    # BUDGET GROUPING
    # ---------------------------
    within_budget = []
    above_budget = []
    premium = []

    for place in matched_places:
        cost = place.get("price_range", 500)

        if cost <= budget:
            within_budget.append(place)
        elif cost <= budget + 500:
            above_budget.append(place)
        else:
            premium.append(place)

    # Limit results
    json_budget = [
    p for p in within_budget
    if p["source"] == "places.json"
    ]

    geo_budget = [
        p for p in within_budget
        if p["source"] == "Geoapify"
    ]

    within_budget = []
    for j, g in itertools.zip_longest(json_budget[:7], geo_budget[:3]):
        if j: within_budget.append(j)
        if g: within_budget.append(g)
    within_budget = within_budget[:10]

    for p in within_budget:
        print(
            p["name"],
            "|",
            p["source"]
        )

    print("\nEND FINAL WITHIN BUDGET\n")
    above_budget = above_budget[:10]
    premium = premium[:10]
    print(
    "Within Budget Count:",
    len(within_budget)
    )

    # ---------------------------
    # SMART ITINERARY SOURCE
    # ---------------------------

    source = (
    within_budget
    + above_budget
    + premium
    )

    if not source:
        source = matched_places

    # Remove duplicates again before itinerary creation
    source = remove_duplicates(source)

    geo_places = [
        p for p in source
        if p.get("source") == "Geoapify"
    ]

    json_places = [
        p for p in source
        if p.get("source") == "places.json"
    ]

    # Prefer curated places, then add Geoapify places
    source = []
    for j, g in itertools.zip_longest(json_places[:6], geo_places[:6]):
        if j: source.append(j)
        if g: source.append(g)
    # Final safety deduplication
    source = remove_duplicates(source)

    print("\nITINERARY SOURCE\n")

    for p in source:

        print(
            p.get("name"),
            "|",
            p.get("area"),
            "|",
            p.get("source")
        )

    print("\nEND ITINERARY SOURCE\n")

    # Shuffle for variety
    # random.shuffle(source)

    itinerary = []

    used_categories = set()
    used_places = set()

    # Fixed order of categories
    CATEGORY_ORDER = [
        "history",
        "nature",
        "food",
        "shopping",
        "entertainment",
        "nightlife"
    ]

    # Select one unique place from each category
    for slot in slots:

        selected = None

        # Use the slot index to choose the required category
        slot_index = slots.index(slot)

        if slot_index < len(CATEGORY_ORDER):
            required_category = CATEGORY_ORDER[slot_index]
        else:
            required_category = None

        # Priority 1:
        # Select a new place from the required category
        if required_category:

            for place in source:

                category = str(
                    place.get("category", "")
                ).strip().lower()

                normalized_name = normalize_place_name(
                    place.get("name")
                )

                if (
                    category == required_category
                    and category not in used_categories
                    and normalized_name not in used_places
                ):

                    selected = place

                    used_categories.add(category)
                    used_places.add(normalized_name)

                    break

        # Priority 2:
        # If that category is unavailable, select any new place
        if not selected:

            for place in source:

                normalized_name = normalize_place_name(
                    place.get("name")
                )

                if normalized_name not in used_places:

                    selected = place
                    used_places.add(normalized_name)

                    break

        # Add selected place to itinerary


        if selected:

            itinerary.append({
                "slot": slot,
                "place": selected
            })

    # ============================================================
    # FINAL GOOGLE MAPS LINKS
    # ============================================================

    # Add correct links to itinerary places
    for item in itinerary:
        if item["place"].get("source") == "Geoapify":
            item["place"]["maps_link"] = create_google_maps_link(item["place"], current_location)
        # else: it's from places.json — its maps_link is already correct, don't touch it
        
    for place in within_budget:
        if place.get("source") == "Geoapify":
            place["maps_link"] = create_google_maps_link(place, current_location)

    for place in above_budget:
            if place.get("source") == "Geoapify":
                        place["maps_link"] = create_google_maps_link(place, current_location)

    for place in premium:
            if place.get("source") == "Geoapify":
                        place["maps_link"] = create_google_maps_link(place, current_location)

    
    # ---------------------------
    # TOTAL COST
    # ---------------------------
    total_cost = sum(
        item["place"]["price_range"]
        for item in itinerary
    )

    print("\nWITHIN BUDGET\n")

    for p in within_budget:
        print(
            p["name"],
            "|",
            p["source"],
            "|",
            p["score"]
        )

    print("\nEND WITHIN BUDGET\n")

        
    
    summary = generate_summary(
    destination,
    interest,
    mood,
    budget,
    company
    )
    # -----------------------------------
    # SAVE PDF DATA
    # -----------------------------------

    session["pdf_data"] = {
    "destination": destination,
    "budget": budget,
    "interest": interest,
    "company": company,
    "mood": mood,
    "summary": summary,
    "total_cost": total_cost,

    "itinerary": [
        {
            "slot": item["slot"],
            "name": item["place"]["name"],
            "area": item["place"]["area"],
            "price": item["place"]["price_range"],
            "rating": item["place"]["rating"]
        }
        for item in itinerary
    ],

    "within_budget": [
    {
        "name": p["name"],
        "rating": p["rating"],
        "cost": p["price_range"],
        "area": p["area"]
    }
    for p in within_budget[:10]
   ],

    "above_budget": [
    {
        "name": p["name"],
        "rating": p["rating"],
        "cost": p["price_range"],
        "area": p["area"]
    }
    for p in above_budget[:10]
   ],

    "premium": [
    {
        "name": p["name"],
        "rating": p["rating"],
        "cost": p["price_range"],
        "area": p["area"]
    }
    for p in premium[:10]
   ],
  }
    # ---------------------------
    # RENDER RESULT
    # ---------------------------
    return render_template(
        "result.html",
        current_location=current_location,
        destination=destination,
        interest=interest,
        company=company,
        mood=mood,
        budget=budget,
        summary=summary,
        duration=duration,
        itinerary=itinerary,
        total_cost=total_cost,
        within_budget=within_budget,
        above_budget=above_budget,
        premium=premium
    )

# -------------------
# PDF DOWNLOAD
# -------------------
@app.route("/download-pdf")
def download_pdf():

    data = session.get("pdf_data")

    if not data:
        return "No itinerary found"

    buffer = BytesIO()   # CHANGED: was pdf_file = os.path.abspath("travel_plan.pdf")

    doc = SimpleDocTemplate(
    buffer,               # CHANGED: was pdf_file
    pagesize=A4,
    rightMargin=10,
    leftMargin=10,
    topMargin=10,
    bottomMargin=10
    )

    styles = getSampleStyleSheet()
    styles["Normal"].fontSize = 8
    styles["Normal"].leading = 9

    styles["Heading2"].fontSize = 11
    styles["Heading2"].leading = 12
    styles["Heading2"].spaceBefore = 3
    styles["Heading2"].spaceAfter = 3

    content = []

    # ---------------------------
    # TITLE
    # ---------------------------
    title_style = ParagraphStyle(
    "CustomTitle",
    parent=styles["Title"],
    fontSize=20,
    leading=22,
    alignment=1,
    spaceAfter=4
    )
    content.append(
        Paragraph(
            "Hyderabad Smart Travel Plan",
            title_style
        )
    )

    content.append(Spacer(1, 6))

    # ---------------------------
    # TRIP DETAILS
    # ---------------------------

    content.append(
        Paragraph(
            f"Destination: {data['destination'].title()}",
            styles["Normal"]
        )
    )

    content.append(
        Paragraph(
            f"Budget: Rs. {data['budget']}",
            styles["Normal"]
        )
    )

    content.append(
        Paragraph(
            f"Interest: {data['interest'].title()}",
            styles["Normal"]
        )
    )

    content.append(
        Paragraph(
            f"Company: {data['company'].title()}",
            styles["Normal"]
        )
    )

    content.append(
        Paragraph(
            f"Mood: {data['mood'].title()}",
            styles["Normal"]
        )
    )

    content.append(Spacer(1, 5))

    # ---------------------------
    # AI SUMMARY
    # ---------------------------

    content.append(
        Paragraph(
            "Trip Overview",
            styles["Heading2"]
        )
    )

    content.append(
        Paragraph(
            f"<b>{data['summary']}</b>",
            styles["Normal"]
        )
    )

    content.append(Spacer(1, 5))

    # ---------------------------
    # ITINERARY
    # ---------------------------

    content.append(
        Paragraph(
            "Recommended Itinerary",
            styles["Heading2"]
        )
    )

    content.append(Spacer(1, 3))

    table_data = [
    ["Time", "Place", "Rating", "Cost"]
   ]

    for item in data["itinerary"]:

        table_data.append([
            item["slot"],
            item["name"],
            f"{item['rating']}/5",
            f"Rs. {item['price']}"
        ])

    itinerary_table = Table(
        table_data,
        colWidths=[90, 300, 80, 90]
    )
    itinerary_table.hAlign = "CENTER"


    itinerary_table.setStyle(
    TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("LEADING", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3)
    ])
)

    content.append(itinerary_table)

    # ---------------------------
    # WITHIN BUDGET
    # ---------------------------

    if data.get("within_budget"):

        content.append(Spacer(1, 10))

        content.append(
            Paragraph(
                "Within Budget",
                styles["Heading2"]
            )
        )

        budget_table_data = [
    ["Place", "Area", "Rating", "Cost"]
    ]

        for place in data["within_budget"]:
            budget_table_data.append([
                place["name"],
                place["area"],
                f"{place['rating']}/5",
                f"Rs. {place['cost']}"
            ])

        budget_table = Table(
            budget_table_data,
            colWidths=[280, 120, 70, 90]
        )
        budget_table.hAlign = "CENTER"

        budget_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgreen),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ])
        )

        content.append(budget_table)

    # ---------------------------
    # UPGRADE PICKS
    # ---------------------------

    if data.get("above_budget"):

        content.append(Spacer(1, 10))

        content.append(
            Paragraph(
                "Upgrade Picks",
                styles["Heading2"]
            )
        )

        upgrade_table_data = [
            ["Place", "Area", "Rating", "Cost"]
        ]

        for place in data["above_budget"]:

            upgrade_table_data.append([
                place["name"],
                place["area"],
                f"{place['rating']}/5",
                f"Rs. {place['cost']}"
            ])

        upgrade_table = Table(
            upgrade_table_data,
            colWidths=[280, 120, 70, 90]
        )

        upgrade_table.hAlign = "CENTER"

        upgrade_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightyellow),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold")
            ])
        )

        content.append(upgrade_table)
        

    # ---------------------------
    # PREMIUM
    # ---------------------------

    if data.get("premium"):

        content.append(Spacer(1, 10))

        content.append(
            Paragraph(
                "Premium Picks",
                styles["Heading2"]
            )
        )

        premium_table_data = [
    ["Place", "Area", "Rating", "Cost"]
    ]
        for place in data["premium"]:

            premium_table_data.append([
                place["name"],
                place["area"],
                f"{place['rating']}/5",
                f"Rs. {place['cost']}"
            ])

        premium_table = Table(
            premium_table_data,
           colWidths=[280, 120, 70, 90]
        )
        premium_table.hAlign = "CENTER"
        

        premium_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.pink),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold")
            ])
        )

        content.append(premium_table)

    # ---------------------------
    # TOTAL COST
    # ---------------------------

    content.append(Spacer(1, 5))

    content.append(
        Paragraph(
            f"<b>Estimated Total Cost: Rs. {data['total_cost']}</b>",
            styles["Heading2"]
        )
    )
    doc.build(content)

    buffer.seek(0)   # NEW: rewind buffer to the start before sending

    return send_file(
    buffer,          # CHANGED: was pdf_file
    as_attachment=True,
    download_name="hyderabad_travel_plan.pdf",
    mimetype="application/pdf"
)
# ---------------------------
# RUN APP
# ---------------------------

@app.route("/test-log")
def test_log():
    print("========== TEST LOG ROUTE CALLED ==========", flush=True)
    app.logger.warning("TEST LOG ROUTE CALLED")
    return "Flask logging is working"

print("REGISTERED ROUTES:", app.url_map, flush=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)