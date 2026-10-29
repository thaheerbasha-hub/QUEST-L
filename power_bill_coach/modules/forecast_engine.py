import pandas as pd
import numpy as np
from datetime import timedelta
from modules.data_loader import calculate_bill_amount

def forecast_next_bill(df, savings_potential_rupees=0.0):
    """
    Computes a 30-day forward forecast of electricity consumption and bill amount (INR)
    using 14-day exponential weighted moving average (EWMA) and weekday/weekend seasonality.
    """
    daily = df.groupby("date")["kwh"].sum().reset_index()
    daily["date"] = pd.to_datetime(daily["date"])
    daily = daily.sort_values("date").reset_index(drop=True)

    if len(daily) < 7:
        avg_daily = daily["kwh"].mean() if not daily.empty else 10.0
        daily_std = daily["kwh"].std() if len(daily) > 1 else 1.5
    else:
        # Use EWMA for recent trend weighting
        daily["ewma"] = daily["kwh"].ewm(span=14, adjust=False).mean()
        avg_daily = daily["ewma"].iloc[-1]
        daily_std = daily["kwh"].tail(14).std()

    # Day-of-week factor
    daily["dow"] = daily["date"].dt.dayofweek
    dow_multipliers = daily.groupby("dow")["kwh"].mean() / (daily["kwh"].mean() or 1.0)
    dow_dict = dow_multipliers.to_dict()

    # Generate 30 days forecast
    last_date = daily["date"].max()
    future_dates = [last_date + timedelta(days=i) for i in range(1, 31)]
    
    forecast_records = []
    total_forecast_kwh = 0.0

    for f_date in future_dates:
        dow = f_date.dayofweek
        dow_factor = dow_dict.get(dow, 1.0)
        # Projected daily value
        proj_val = max(1.0, avg_daily * dow_factor)
        lower_bound = max(0.5, proj_val - (1.64 * (daily_std or 1.0)))
        upper_bound = proj_val + (1.64 * (daily_std or 1.0))
        
        total_forecast_kwh += proj_val
        forecast_records.append({
            "date": f_date,
            "forecast_kwh": round(proj_val, 2),
            "lower_bound": round(lower_bound, 2),
            "upper_bound": round(upper_bound, 2)
        })

    df_forecast = pd.DataFrame(forecast_records)

    # Calculate monetary bill
    bill_details = calculate_bill_amount(total_forecast_kwh)
    current_projected_total = bill_details["total_bill"]

    # Optimized bill after applying coach recommendations
    optimized_bill = max(bill_details["fixed_charge"], current_projected_total - savings_potential_rupees)
    achievable_savings = current_projected_total - optimized_bill

    return {
        "daily_history": daily,
        "forecast_df": df_forecast,
        "forecast_kwh": round(total_forecast_kwh, 1),
        "forecast_bill_inr": round(current_projected_total, 2),
        "optimized_bill_inr": round(optimized_bill, 2),
        "achievable_savings_inr": round(achievable_savings, 2),
        "bill_breakdown": bill_details["breakdown"],
        "fixed_charge": bill_details["fixed_charge"],
        "energy_cost": bill_details["energy_cost"]
    }
