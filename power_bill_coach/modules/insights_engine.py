import pandas as pd
import numpy as np

def generate_three_insights(df, slabs=None, avg_rate=6.5):
    """
    Analyzes meter data and produces 3 plain-English, actionable insights 
    identifying waste, cost in Rupees, and exact steps to save.
    """
    # 1. INSIGHT 1: Vampire Load (Midnight Standby Waste)
    # Check 1:00 AM to 5:00 AM
    night_data = df[df["hour"].between(1, 4)]
    night_median_kwh = night_data["kwh"].median() if not night_data.empty else 0.3
    
    # Efficient benchmark is ~0.30 kWh/hr for basic standby (Wi-Fi + basic fridge idle)
    BENCHMARK_STANDBY = 0.30
    excess_hourly = max(0.0, night_median_kwh - BENCHMARK_STANDBY)
    vampire_kwh_monthly = excess_hourly * 4 * 30  # 4 hours per night * 30 days
    vampire_cost_monthly = round(vampire_kwh_monthly * avg_rate, 0)
    
    if excess_hourly > 0.15:
        vampire_status = "High Waste Detected"
        vampire_badge = "🔴 Action Needed"
        vampire_text = (
            f"Your home draws an average of **{night_median_kwh:.2f} units/hour** between 1 AM and 5 AM while everyone is asleep. "
            f"A healthy home uses under 0.30 units/hour. You are burning roughly **{vampire_kwh_monthly:.0f} wasted units** "
            f"every month in standby power alone."
        )
        vampire_action = (
            f"💡 **How to save ₹{vampire_cost_monthly:,.0f}/month:**\n"
            f"- Turn off the water geyser before sleeping (storage geysers reheat water 4-6 times overnight).\n"
            f"- Put TV/setup box and desktop power strips on switchboards rather than leaving them in standby mode.\n"
            f"- If your refrigerator is over 8 years old, inspect the rubber door gasket to ensure it seals tightly."
        )
    else:
        vampire_status = "Healthy Standby"
        vampire_badge = "🟢 Optimal"
        vampire_text = (
            f"Your overnight standby baseline is **{night_median_kwh:.2f} units/hour**, which is well within normal, efficient limits."
        )
        vampire_action = "Keep up the good habits by turning off appliances at the wall socket when not in use."

    insight_1 = {
        "title": "Vampire Power & Midnight Standby Waste",
        "icon": "🧛",
        "status": vampire_status,
        "badge": vampire_badge,
        "metric_value": f"{night_median_kwh:.2f} kWh/hr",
        "metric_label": "Overnight Standby Draw",
        "potential_saving": f"₹{vampire_cost_monthly:,.0f}/mo",
        "saved_rupees": vampire_cost_monthly,
        "explanation": vampire_text,
        "action_plan": vampire_action
    }

    # 2. INSIGHT 2: Peak Hour Concentration & Appliance Overages
    # Peak hours: 6 PM to 10 PM (18:00 to 22:00)
    peak_data = df[df["hour"].between(18, 21)]
    non_peak_data = df[~df["hour"].between(18, 21)]
    
    total_kwh = df["kwh"].sum()
    peak_kwh = peak_data["kwh"].sum()
    peak_percentage = (peak_kwh / total_kwh * 100) if total_kwh > 0 else 0
    avg_peak_hourly = peak_data["kwh"].mean() if not peak_data.empty else 0
    avg_non_peak_hourly = non_peak_data["kwh"].mean() if not non_peak_data.empty else 0
    
    # Peak ratio
    peak_ratio = (avg_peak_hourly / avg_non_peak_hourly) if avg_non_peak_hourly > 0 else 1.0
    shiftable_kwh = max(0.0, (avg_peak_hourly - (avg_non_peak_hourly * 1.3))) * 4 * 30
    peak_saving_rupees = round(shiftable_kwh * avg_rate * 0.4, 0) # 40% efficiency boost / ToD tariff saving

    if peak_ratio > 1.8 or peak_percentage > 35:
        peak_status = "Severe Peak Overload"
        peak_badge = "🟠 Shift Loads"
        peak_text = (
            f"**{peak_percentage:.1f}%** of your total power consumption occurs in the 4-hour evening window (6 PM – 10 PM). "
            f"During this window, your load jumps to **{avg_peak_hourly:.2f} units/hour** (nearly {peak_ratio:.1f}x your normal baseline). "
            f"Running heavy appliances during evening peak adds heat, triggers peak tariffs, and pushes your billing into higher brackets."
        )
        peak_action = (
            f"💡 **How to save ~₹{peak_saving_rupees:,.0f}/month:**\n"
            f"- **Washing Machines & Dishwashers:** Run full loads in the morning (8 AM – 11 AM) or afternoon.\n"
            f"- **Housing Society Pumps / Heaters:** Automate water transfer pumps to run at 2 PM or 11 PM instead of 7 PM.\n"
            f"- **AC Pre-Cooling:** If using AC at night, set thermostat to **24°C or 25°C** with a fan instead of 18°C. Every 1°C higher saves 6% electricity."
        )
    else:
        peak_status = "Balanced Day-Night Distribution"
        peak_badge = "🟢 Balanced"
        peak_text = (
            f"Your evening peak usage is **{peak_percentage:.1f}%** of total consumption, showing a well-distributed daily routine."
        )
        peak_action = "Continue avoiding simultaneous usage of heavy motor appliances in the evening."

    insight_2 = {
        "title": "Evening Peak Spike & Appliance Timing",
        "icon": "⚡",
        "status": peak_status,
        "badge": peak_badge,
        "metric_value": f"{peak_percentage:.1f}%",
        "metric_label": "Consumed in 6 PM - 10 PM",
        "potential_saving": f"₹{peak_saving_rupees:,.0f}/mo",
        "saved_rupees": peak_saving_rupees,
        "explanation": peak_text,
        "action_plan": peak_action
    }

    # 3. INSIGHT 3: Tariff Slab Jump Danger & Run-Rate Bleed
    daily_totals = df.groupby("date")["kwh"].sum()
    avg_daily_kwh = daily_totals.mean() if not daily_totals.empty else 10.0
    projected_monthly_kwh = avg_daily_kwh * 30

    # Determine slab proximity (200 units and 400 units are typical sharp cliff edges)
    slab_target = 200 if projected_monthly_kwh <= 260 else (400 if projected_monthly_kwh <= 480 else None)
    
    if slab_target and projected_monthly_kwh > slab_target:
        overage = projected_monthly_kwh - slab_target
        daily_reduction_needed = overage / 30.0
        # Savings from dropping below the slab limit
        rate_diff = 2.30  # difference between tiers
        slab_penalty_saved = round((overage * rate_diff) + (overage * 5.0), 0)

        slab_status = f"Approaching Tier Jump (> {slab_target} Units)"
        slab_badge = "⚠️ Slab Penalty Risk"
        slab_text = (
            f"At your current consumption rate (**{avg_daily_kwh:.1f} units/day**), your monthly usage is projected to reach "
            f"**{projected_monthly_kwh:.0f} units**. This pushes you over the **{slab_target}-unit threshold** into a much more expensive tariff tier! "
            f"Crossing this slab adds an estimated **₹{slab_penalty_saved:,.0f}** in higher per-unit energy charges."
        )
        slab_action = (
            f"🎯 **Target: Cut {daily_reduction_needed:.1f} units/day to save ₹{slab_penalty_saved:,.0f}:**\n"
            f"- Setting your AC timer to shut off 1 hour earlier at 5 AM saves ~1.5 units/day.\n"
            f"- Turning off unneeded room fans and switching 3 halogen bulbs to 9W LEDs saves ~0.8 units/day.\n"
            f"- This single adjustment will lock your entire bill into the cheaper tariff category."
        )
    else:
        slab_status = "Comfortably Within Current Slab"
        slab_badge = "🟢 Safe Tier"
        slab_penalty_saved = 400.0
        slab_text = (
            f"Your projected monthly usage is **{projected_monthly_kwh:.0f} units**, maintaining a stable tariff bracket."
        )
        slab_action = "Monitoring your daily units prevents accidental surges at month-end."

    insight_3 = {
        "title": "Tariff Slab Cliff-Edge & Run-Rate Warning",
        "icon": "🎯",
        "status": slab_status,
        "badge": slab_badge,
        "metric_value": f"{projected_monthly_kwh:.0f} kWh",
        "metric_label": "Projected 30-Day Units",
        "potential_saving": f"₹{slab_penalty_saved:,.0f}/mo",
        "saved_rupees": slab_penalty_saved,
        "explanation": slab_text,
        "action_plan": slab_action
    }

    total_potential_savings = vampire_cost_monthly + peak_saving_rupees + slab_penalty_saved

    return [insight_1, insight_2, insight_3], total_potential_savings
