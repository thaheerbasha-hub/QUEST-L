import pandas as pd
import numpy as np
from datetime import datetime

# Standard Residential Tiered Tariff Slabs (INR / kWh)
DEFAULT_SLABS = [
    {"limit": 100, "rate": 3.50, "label": "0 - 100 Units (Subsidized)"},
    {"limit": 200, "rate": 5.20, "label": "101 - 200 Units (Standard)"},
    {"limit": 400, "rate": 7.50, "label": "201 - 400 Units (High Consumption)"},
    {"limit": float('inf'), "rate": 9.80, "label": "> 400 Units (Heavy User)"}
]

FIXED_CHARGE = 120.0  # Monthly meter & fixed grid charge in INR

def load_data(file_or_path):
    """Loads meter reading CSV into a standardized DataFrame."""
    if isinstance(file_or_path, str):
        df = pd.read_csv(file_or_path)
    else:
        df = pd.read_csv(file_or_path)

    # Ensure required columns
    df.columns = [c.strip().lower() for c in df.columns]
    if "timestamp" not in df.columns or "kwh" not in df.columns:
        raise ValueError("CSV must contain 'timestamp' and 'kwh' columns.")

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    df["kwh"] = pd.to_numeric(df["kwh"], errors="coerce").fillna(0.0)

    # Enrich time fields
    df["date"] = df["timestamp"].dt.date
    df["hour"] = df["timestamp"].dt.hour
    df["day_name"] = df["timestamp"].dt.day_name()
    df["month_year"] = df["timestamp"].dt.to_period("M")

    return df

def calculate_bill_amount(total_kwh, slabs=DEFAULT_SLABS, fixed_charge=FIXED_CHARGE):
    """Calculates total bill amount in INR based on tiered slabs."""
    rem = total_kwh
    breakdown = []
    energy_cost = 0.0
    prev_limit = 0

    for slab in slabs:
        limit = slab["limit"]
        rate = slab["rate"]
        slab_units = limit - prev_limit

        if rem > 0:
            units_in_slab = min(rem, slab_units)
            cost = units_in_slab * rate
            energy_cost += cost
            breakdown.append({
                "slab": slab["label"],
                "units": round(units_in_slab, 1),
                "rate": rate,
                "cost": round(cost, 2)
            })
            rem -= units_in_slab
            prev_limit = limit
        else:
            break

    total_bill = energy_cost + fixed_charge
    return {
        "energy_cost": round(energy_cost, 2),
        "fixed_charge": round(fixed_charge, 2),
        "total_bill": round(total_bill, 2),
        "breakdown": breakdown
    }
