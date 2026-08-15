import time
import pandas as pd
import requests

BASE_URL = "https://api.fda.gov/device/510k.json"

# Search filter: decision date between Jan 1, 2025 and Dec 31, 2026
# You can append extra filters (e.g., ' AND advisory_committee:"CV"'). Use plain
# spaces here, not '+' — requests URL-encodes the params, so a literal '+' would
# reach the API as %2B instead of a separator.
SEARCH_QUERY = "decision_date:[2025-01-01 TO 2026-12-31]"


def fetch_510k_clearances(query=SEARCH_QUERY, max_records=500, api_key=None):
    records = []
    limit = 100  # API max is 1000 per request
    skip = 0

    headers = {}
    params = {"search": query, "limit": limit, "sort": "decision_date:desc"}
    if api_key:
        params["api_key"] = api_key

    while len(records) < max_records:
        params["skip"] = skip
        response = requests.get(BASE_URL, params=params, headers=headers)

        if response.status_code != 200:
            print(
                f"Request failed (Status {response.status_code}): {response.text}"
            )
            break

        data = response.json()
        results = data.get("results", [])
        if not results:
            break

        for item in results:
            # Extract core fields and openfda harmonized metadata
            openfda_meta = item.get("openfda", {})

            record = {
                "k_number": item.get("k_number"),
                "device_name": item.get("device_name"),
                "applicant": item.get("applicant"),
                "decision_date": item.get("decision_date"),
                "decision_description": item.get("decision_description"),
                "advisory_committee": item.get("advisory_committee"),
                "product_code": item.get("product_code"),
                "regulation_number": openfda_meta.get("regulation_number", [None])[0]
                if openfda_meta
                else None,
                "device_class": openfda_meta.get("device_class", [None])[0]
                if openfda_meta
                else None,
                "medical_specialty": openfda_meta.get(
                    "medical_specialty_description", [None]
                )[0]
                if openfda_meta
                else None,
                "statement_or_summary": item.get("statement_or_summary"),
            }
            records.append(record)

        skip += limit
        total_available = data.get("meta", {}).get("results", {}).get("total", 0)

        print(
            f"Retrieved {len(records)} of {min(total_available, max_records)} records..."
        )

        if skip >= total_available or skip >= 25000:
            break

        # Respect API rate limits (240 requests/min with key, 40 without key)
        time.sleep(0.25)

    return pd.DataFrame(records)


# -------------------------------------------------------------
# Execution & Filtering
# -------------------------------------------------------------
if __name__ == "__main__":
    # Fetch records (set max_records to desired ceiling)
    df = fetch_510k_clearances(max_records=1000)

    # Example In-Memory Filters:
    # 1. Filter by specific medical panel (e.g., Radiology 'RA', Cardiovascular 'CV', Orthopedic 'OR')
    cardio_df = df[df["advisory_committee"] == "CV"]

    # 2. Filter by Device Class (e.g., Class 2 moderate-to-high risk)
    class_2_df = df[df["device_class"] == "2"]

    # 3. Filter by keyword in device name
    ai_devices = df[
        df["device_name"].str.contains(
            "AI|Algorithm|Software|System", case=False, na=False
        )
    ]

    print(f"\nTotal records retrieved: {len(df)}")
    print(df[["k_number", "device_name", "decision_date", "applicant"]].head())

    # Save to CSV
    df.to_csv("fda_510k_clearances_2025_2026.csv", index=False)
