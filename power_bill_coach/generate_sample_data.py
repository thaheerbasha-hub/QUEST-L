import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_datasets():
    np.random.seed(42)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    timestamps = pd.date_range(start=start_date, end=end_date, freq='h')

    # 1. Apartment with AC (Heavy night usage)
    records_apt = []
    for ts in timestamps:
        hour = ts.hour
        # Base household standby: 0.25 - 0.45 kWh
        val = np.random.uniform(0.25, 0.45)
        # Morning routine (7 AM - 9 AM): breakfast, geyser
        if 7 <= hour <= 9:
            val += np.random.uniform(0.8, 1.4)
        # Evening lights/TV/cooking (6 PM - 10 PM)
        elif 18 <= hour <= 22:
            val += np.random.uniform(0.7, 1.2)
        # Night AC usage (10 PM - 5 AM): heavy spikes!
        elif hour >= 22 or hour <= 5:
            val += np.random.uniform(1.6, 2.4)
        records_apt.append({"timestamp": ts.strftime("%Y-%m-%d %H:%M"), "kwh": round(val, 3)})

    df_apt = pd.DataFrame(records_apt)
    df_apt.to_csv("power_bill_coach/sample_data/apartment_with_ac.csv", index=False)
    print("Created apartment_with_ac.csv")

    # 2. Family with High Vampire / Standby Load (Old fridge, geyser left on, appliances)
    records_vampire = []
    for ts in timestamps:
        hour = ts.hour
        # Continuous unoptimized standby baseline: 0.9 - 1.3 kWh even at 2-5 AM!
        val = np.random.uniform(0.9, 1.3)
        if 7 <= hour <= 10:
            val += np.random.uniform(0.6, 1.1)
        elif 19 <= hour <= 23:
            val += np.random.uniform(0.8, 1.5)
        records_vampire.append({"timestamp": ts.strftime("%Y-%m-%d %H:%M"), "kwh": round(val, 3)})

    df_vamp = pd.DataFrame(records_vampire)
    df_vamp.to_csv("power_bill_coach/sample_data/family_high_vampire_load.csv", index=False)
    print("Created family_high_vampire_load.csv")

    # 3. Housing Society Common Area (Pumps running during Peak Tariff hours 6 PM - 10 PM)
    records_society = []
    for ts in timestamps:
        hour = ts.hour
        # Base common lighting & lifts: 1.5 - 2.5 kWh
        val = np.random.uniform(1.5, 2.5)
        # Heavy Borewell / Water Pump (6 PM - 9 PM) - Peak Tariff hours!
        if 18 <= hour <= 21:
            val += np.random.uniform(8.5, 11.0)
        # Morning pump (6 AM - 8 AM)
        elif 6 <= hour <= 8:
            val += np.random.uniform(7.0, 9.5)
        records_society.append({"timestamp": ts.strftime("%Y-%m-%d %H:%M"), "kwh": round(val, 3)})

    df_society = pd.DataFrame(records_society)
    df_society.to_csv("power_bill_coach/sample_data/society_common_meters.csv", index=False)
    print("Created society_common_meters.csv")

if __name__ == "__main__":
    generate_datasets()
