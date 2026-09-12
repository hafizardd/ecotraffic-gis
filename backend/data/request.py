from pathlib import Path
import requests
import json
import os

from dotenv import load_dotenv
import pandas as pd


# ============================================================
# Configuration
# ============================================================

load_dotenv()

api_url = os.getenv("MAPID_API_URL")
api_token = os.getenv("MAPID_API_KEY_MISSION")

BASE_DIR = Path(__file__).parent
PAYLOAD_PATH = BASE_DIR / "activities_payload.json"
OUTPUT_DIR = BASE_DIR / "output"

OUTPUT_DIR.mkdir(exist_ok=True)


# ============================================================
# Load request payload
# ============================================================

with PAYLOAD_PATH.open("r", encoding="utf-8") as file:
    payload = json.load(file)


# ============================================================
# Request API
# ============================================================

headers = {
    "Content-Type": "application/json",
    "x-api-key": api_token,
}

response = requests.post(
    api_url,
    headers=headers,
    json=payload,
)

print("Status:", response.status_code)

response.raise_for_status()


# ============================================================
# Get JSON response
# ============================================================

data = response.json()

print("Response received successfully.")


# ============================================================
# Export JSON
# ============================================================

json_path = OUTPUT_DIR / "activities.json"

with json_path.open("w", encoding="utf-8") as file:
    json.dump(data, file, ensure_ascii=False, indent=2)

print(f"JSON exported to: {json_path}")


# ============================================================
# Convert JSON → CSV
# ============================================================

activities = data["data"]["activities"]

rows = []

for activity in activities:
    rows.append({
        "id": activity.get("_id"),
        "title": activity.get("title"),
        "description": activity.get("description"),

        # Keep coordinates as one column
        "geometry.coordinates": json.dumps(
            activity.get("geometry", {}).get("coordinates"),
            ensure_ascii=False
        ),

        # Keep medias as one column
        "medias": json.dumps(
            activity.get("medias", []),
            ensure_ascii=False
        ),

        "total_comment": activity.get("total_comment"),
        "created_at": activity.get("created_at"),
        "likes": json.dumps(
            activity.get("likes", []),
            ensure_ascii=False
        ),

        "user_name": activity.get("user_name"),
        "user_full_name": activity.get("user_full_name"),

        # Keep profile object as one column
        "user_profile_picture": json.dumps(
            activity.get("user_profile_picture"),
            ensure_ascii=False
        ),

        "community_name": activity.get("community_name"),
        "community_picture": activity.get("community_picture"),
        "community_description": activity.get("community_description"),
    })

df = pd.DataFrame(rows)

csv_path = OUTPUT_DIR / "activities.csv"

df.to_csv(
    csv_path,
    index=False,
    encoding="utf-8-sig",
)

print(f"CSV exported to: {csv_path}")
print(f"Rows: {len(df)}")
print(f"Columns: {len(df.columns)}")