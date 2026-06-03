from flask import Flask, render_template, request
import requests
import json
import random
import os
from flask import send_file,session
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle

app = Flask(__name__)
app.secret_key = "hyderabad_trip_planner"

# ---------------------------
# LOAD DATA SAFELY
# ---------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
json_path = os.path.join(BASE_DIR, "places.json")

try:

    with open(json_path, "r", encoding="utf-8") as file:
        places = json.load(file)

    for place in places:
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
GEOAPIFY_API_KEY = "b004f1e885d54804abfcbff89df66fb0"
CATEGORY_MAP = {
    "food": "catering.restaurant,catering.cafe",
    "history": "heritage,religion",
    "nature": "natural,leisure.park",
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
AREA_COORDS = {
    "madhapur": (78.3915, 17.4483),
    "hitech city": (78.3818, 17.4435),
    "gachibowli": (78.3489, 17.4401),
    "banjara hills": (78.4381, 17.4126),
    "jubilee hills": (78.4070, 17.4326),
    "charminar": (78.4747, 17.3616),
    "kondapur": (78.3618, 17.4698)
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
# ---------------------------
# FETCH LIVE PLACES
# ---------------------------
def get_live_places(
    category,
    destination
):
    
    print(
    "Destination Selected:",
    destination
    )

    geo_category = CATEGORY_MAP.get(
    category,
    "tourism.attraction"
)

    lon, lat = AREA_COORDS.get(
        destination,
        (78.4867, 17.3850)
    )

    url = (
        f"https://api.geoapify.com/v2/places?"
        f"categories={geo_category}"
        f"&filter=circle:{lon},{lat},3000"
        f"&limit=10"
        f"&apiKey={GEOAPIFY_API_KEY}"
    )

    try:

        response = requests.get(url, timeout=10)

        print("Geoapify Status Code:", response.status_code)

        response.raise_for_status()

        data = response.json()

        print(
            "Geoapify Features Returned:",
            len(data.get("features", []))
        )

        live_places = []

        for item in data.get("features", []):

            props = item.get("properties", {})

            lat = props.get("lat")
            lon = props.get("lon")
            name = props.get("name")
            if not name:
                continue
            area = (
                    props.get("suburb")
                    or props.get("district")
                    or props.get("city")
                    or props.get("county")
                    or "Hyderabad"
                )
            if lat and lon:
               maps_link = f"https://www.google.com/maps?q={lat},{lon}"
            else:
                maps_link = (
                    f"https://www.google.com/maps/search/?api=1&query="
                    f"{name}+{area}+Hyderabad"
                )
            youtube_link = (
                f"https://www.youtube.com/results?search_query="
                f"{name}+{area}+Hyderabad"
            )
        

            live_places.append({
                "name": name,
                "area": area,
                "category": category,
                "price_range": PRICE_BY_CATEGORY.get(category, 500),
                "rating": round(random.uniform(3.8, 4.8), 1),
                "company_tags": ["friends", "family", "couple"],
                "mood_tags": ["fun", "relaxed"],
                "time_needed": "2 hours",
                "lat": props.get("lat"),
                "lon": props.get("lon"),
                "source": "Geoapify",
                "maps_link": maps_link,
                "youtube_link": youtube_link
            })
        print(
            "Live Places Created:",
            len(live_places)
            )
        for p in live_places[:5]:
            print(
                p["name"],
                "|",
                p["area"],
                "|",
                p["lat"],
                "|",
                p["lon"]
            )
        return live_places

    except Exception as e:

        print("Geoapify Error:", e)

        return []


@app.route("/test-api")
def test_api():

    url = "https://api.geoapify.com/v2/places?categories=catering.restaurant&filter=circle:78.4867,17.3850,5000&limit=5&apiKey=b004f1e885d54804abfcbff89df66fb0"

    response = requests.get(url, timeout=10)

    response.raise_for_status()
    data = response.json()
    return data

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

    destinations = sorted(list(set(
        place["area"] for place in places
    )))

    return render_template(
        "planner.html",
        destinations=destinations
    )


# ---------------------------
# MAIN PLANNER LOGIC
# ---------------------------
@app.route("/plan", methods=["POST"])
def plan():

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
    if destination != "anywhere":

        filtered_places = []

        for place in all_places:

            area = place.get(
                "area",
                ""
            ).strip().lower()
            print(
                "CHECK:",
                place["name"],
                "|",
                area,
                "|",
                place.get("source")
            )

            if (
                destination in area
                or place.get("source") == "Geoapify"
            ):
               print("ADDED:", place["name"])
               filtered_places.append(place)

        print("\nFILTERED PLACES\n")

        for p in filtered_places[:20]:

            print(
                p["name"],
                "|",
                p["area"],
                "|",
                p["source"]
            )

        print("\nEND FILTERED\n")

        if filtered_places:
            all_places = filtered_places

    app.logger.info(f"JSON Places: {len(places)}")
    app.logger.info(f"Live Places: {len(live_places)}")
    app.logger.info(f"Total Places: {len(all_places)}")

    for place in all_places:

        score = 0

        area = place.get("area", "").lower()
        category = place.get("category", "").lower()
        price = place.get("price_range", 500)
        rating = place.get("rating", 4.0)

        company_tags = [x.lower() for x in place.get("company_tags", [])]
        mood_tags = [x.lower() for x in place.get("mood_tags", [])]

        # Destination match
        if destination == "anywhere":
            score += 1
        elif area == destination:
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

        # Rating scoring
        if rating >= 4.5:
            score += 3
        elif rating >= 4.0:
            score += 2

        # Hidden gem bonus
        if rating >= 4.2 and price < 300:
            score += 2
        
        # Live place bonus
        if place.get("source") == "Geoapify":
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
    unique_places = {}
    for place in matched_places:
        name = (
            place.get("name", "")
            .lower()
            .strip()
        )
        area = (
            place.get("area", "")
            .lower()
            .strip()
        )
        clean_name = (
            name.replace(area, "")
            .strip()
        )
        # First occurrence
        if clean_name not in unique_places:
            unique_places[clean_name] = place
        # Prefer Geoapify over places.json
        elif (
            place.get("source") == "Geoapify"
            and unique_places[clean_name].get("source") != "Geoapify"
        ):
            unique_places[clean_name] = place
    matched_places = list(unique_places.values())
    print("\nAFTER DEDUP\n")
    for p in matched_places[:20]:
        print(
            p["name"],
            "|",
            p["source"]
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
        cost = place["price_range"]

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

    within_budget = (
        json_budget[:7]
        + geo_budget[:3]
    )
    print("\nFINAL WITHIN BUDGET\n")

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
    # SMART ITINERARY (NO DUPLICATES)
    # ---------------------------
    source = within_budget if within_budget else matched_places

    geo_places = [
        p for p in source
        if p.get("source") == "Geoapify"
    ]

    json_places = [
        p for p in source
        if p.get("source") == "places.json"
    ]

    source = json_places[:3] + geo_places[:2]

    print("\nITINERARY SOURCE\n")

    for p in source:
        print(
            p["name"],
            "|",
            p["source"]
        )

    print("\nEND ITINERARY SOURCE\n")

    # Shuffle for variety
    # random.shuffle(source)

    itinerary = []
    used_categories = []
    used_places = set()

    for slot in slots:

        selected = None

        # Priority 1: new category + new place
        for place in source:
            if (
                place["category"] not in used_categories
                and place["name"] not in used_places
            ):
                selected = place
                used_categories.append(place["category"])
                used_places.add(place["name"])
                break

        # Priority 2: allow same category but not same place
        if not selected:
            for place in source:
                if place["name"] not in used_places:
                    selected = place
                    used_places.add(place["name"])
                    break

        # Fallback (rare)
        if not selected and source:
            selected = random.choice(source)

        if selected:
            itinerary.append({
                "slot": slot,
                "place": selected
            })

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

    for place in matched_places:

        lat = place.get("lat")
        lon = place.get("lon")

        if lat and lon:

            place["maps_link"] = (
                "https://www.google.com/maps/dir/?api=1"
                f"&origin={current_location}"
                f"&destination={lat},{lon}"
            )

        else:

            destination_query = (
                f"{place['name']} {place['area']} Hyderabad"
            )

            place["maps_link"] = (
                "https://www.google.com/maps/dir/?api=1"
                f"&origin={current_location}"
                f"&destination={destination_query}"
            )
    
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

    pdf_file = "travel_plan.pdf"

    doc = SimpleDocTemplate(
    pdf_file,
    pagesize=A4,
    rightMargin=15,
    leftMargin=15,
    topMargin=20,
    bottomMargin=20
    )

    styles = getSampleStyleSheet()

    content = []

    # ---------------------------
    # TITLE
    # ---------------------------
    title_style = ParagraphStyle(
    "CustomTitle",
    parent=styles["Title"],
    fontSize=28,
    leading=34,
    alignment=1
    )
    content.append(
        Paragraph(
            "Hyderabad Smart Travel Plan",
            title_style
        )
    )

    content.append(Spacer(1, 20))

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

    content.append(Spacer(1, 15))

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

    content.append(Spacer(1, 20))

    # ---------------------------
    # ITINERARY
    # ---------------------------

    content.append(
        Paragraph(
            "Recommended Itinerary",
            styles["Heading2"]
        )
    )

    content.append(Spacer(1, 10))

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
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE")
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
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold")
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

    content.append(
        Paragraph(
            f"Estimated Total Cost: Rs. {data['total_cost']}",
            styles["Heading2"]
        )
    )

    doc.build(content)

    return send_file(
        pdf_file,
        as_attachment=True
    )
# ---------------------------
# RUN APP
# ---------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)