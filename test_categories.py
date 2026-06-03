import json

with open("places.json", "r", encoding="utf-8") as file:
    places = json.load(file)

categories = sorted(set(
    place["category"]
    for place in places
))

print(categories)
