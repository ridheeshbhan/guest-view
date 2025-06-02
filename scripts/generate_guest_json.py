import pandas as pd
import requests
import os
import json
from datetime import datetime
from icalendar import Calendar

# === Load property list CSV ===
df = pd.read_csv("property_list.csv")
df = df.dropna(subset=["Property", "URL"])

# === Load the shared info template ===
with open("scripts/template_info.json", "r") as f:
    info_template = json.load(f)

# === Ensure data output directory exists ===
os.makedirs("data", exist_ok=True)

# === Today's date for comparison ===
today = datetime.today()

for _, row in df.iterrows():
    property_name = row["Property"]
    ical_url = row["URL"]
    property_key = property_name.lower().replace(" ", "-")

    try:
        res = requests.get(ical_url)
        cal = Calendar.from_ical(res.text)

        upcoming_event = None
        for component in cal.walk():
            if component.name == "VEVENT":
                start = component.get("dtstart").dt
                end = component.get("dtend").dt
                name = str(component.get("summary"))
                status = str(component.get("status"))

                if status == "CONFIRMED" and isinstance(start, datetime) and start >= today:
                    if not upcoming_event or start < upcoming_event["start"]:
                        upcoming_event = {
                            "name": name,
                            "checkin": start,
                            "checkout": end
                        }

        if not upcoming_event:
            continue

        # Format dates
        checkin_str = upcoming_event["checkin"].strftime("%B %d, %Y, %I:%M %p")
        checkout_str = upcoming_event["checkout"].strftime("%B %d, %Y, %I:%M %p")
        nights = (upcoming_event["checkout"] - upcoming_event["checkin"]).days

        # === Guest JSON ===
        guest_data = {
            "name": upcoming_event["name"],
            "checkin": checkin_str,
            "checkout": checkout_str,
            "nights": nights
        }

        with open(f"data/{property_key}-guest.json", "w") as f:
            json.dump(guest_data, f, indent=2)

        # === Info JSON ===
        info_data = info_template.copy()
        info_data["property"] = property_name

        with open(f"data/{property_key}-info.json", "w") as f:
            json.dump(info_data, f, indent=2)

        print(f"✓ Processed {property_name}")

    except Exception as e:
        print(f"✗ Error processing {property_name}: {e}")
