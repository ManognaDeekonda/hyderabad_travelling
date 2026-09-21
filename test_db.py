from db import get_all_places

places = get_all_places()

print("Total places:", len(places))
print("First place:")
print(places[0])