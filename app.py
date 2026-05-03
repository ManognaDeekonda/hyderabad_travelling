from flask import Flask, render_template, request
import json
import random
import os

app = Flask(__name__)

# Load data


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
json_path = os.path.join(BASE_DIR, "places.json")

with open(json_path, "r", encoding="utf-8") as file:
    places = json.load(file)

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/planner")
def planner():

    destinations = sorted(list(set(
        place["area"] for place in places
    )))

    return render_template(
        "planner.html",
        destinations=destinations
    )


@app.route("/plan", methods=["POST"])
def plan():

    # Inputs
    current_location = request.form.get("current_location", "")
    destination = request.form.get("destination", "Anywhere").strip()
    interest = request.form.get("interest", "").strip().lower()
    company = request.form.get("company", "").strip().lower()
    mood = request.form.get("mood", "").strip().lower()
    budget = int(request.form.get("budget", 2000))
    duration = request.form.get("duration", "1 Day").lower()

    # Slots
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
    # SMART RECOMMENDATION ENGINE
    # ---------------------------
    matched_places = []

    for place in places:

        score = 0

        area = place["area"].lower()
        category = place["category"].lower()
        price = place["price_range"]
        rating = place["rating"]

        company_tags = [x.lower() for x in place.get("company_tags", [])]
        mood_tags = [x.lower() for x in place.get("mood_tags", [])]

        # Destination match
        if destination.lower() == "anywhere":
            score += 1
        elif area == destination.lower():
            score += 5

        # Interest match
        if category == interest:
            score += 5

        # Company match
        if company in company_tags:
            score += 4

        # Mood match
        if mood in mood_tags:
            score += 4

        # Budget score
        if price <= budget:
            score += 5
        elif price <= budget + 300:
            score += 2

        # Rating score
        if rating >= 4.5:
            score += 3
        elif rating >= 4.0:
            score += 2

        # Hidden gem bonus
        if rating >= 4.2 and price < 300:
            score += 2

        if score >= 7:
            new_place = place.copy()
            new_place["score"] = score
            matched_places.append(new_place)

    # Sort best first
    matched_places = sorted(
        matched_places,
        key=lambda x: x["score"],
        reverse=True
    )

    # ---------------------------
    # BUDGET GROUPS
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

    within_budget = within_budget[:5]
    above_budget = above_budget[:5]
    premium = premium[:5]

    # ---------------------------
    # SMART DIVERSE ITINERARY
    # ---------------------------
    source = within_budget if within_budget else matched_places

    itinerary = []
    used_categories = []

    for slot in slots:

        selected = None

        for place in source:
            if place["category"] not in used_categories:
                selected = place
                used_categories.append(place["category"])
                break

        # If all categories repeated
        if not selected and source:
            selected = random.choice(source)

        if selected:
            itinerary.append({
                "slot": slot,
                "place": selected
            })

    # Total cost
    total_cost = sum(
        item["place"]["price_range"]
        for item in itinerary
    )

    return render_template(
        "result.html",
        current_location=current_location,
        destination=destination,
        interest=interest,
        company=company,
        mood=mood,
        budget=budget,
        duration=duration,
        itinerary=itinerary,
        total_cost=total_cost,
        within_budget=within_budget,
        above_budget=above_budget,
        premium=premium
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)