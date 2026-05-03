import json
import urllib.parse

# Load file
with open("places.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for item in data:
    name = item["name"].strip()
    area = item["area"].strip()

    # Add area if not already in name
    if area.lower() not in name.lower():
        new_name = f"{name} {area}"
        item["name"] = new_name
    else:
        new_name = name

    # Update links
    maps_query = urllib.parse.quote_plus(new_name + " Hyderabad")
    yt_query = urllib.parse.quote_plus(new_name + " Hyderabad review")

    item["maps_link"] = f"https://www.google.com/maps/search/?api=1&query={maps_query}"
    item["youtube_link"] = f"https://www.youtube.com/results?search_query={yt_query}"

# Save updated file
with open("places_updated.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("Updated successfully!")