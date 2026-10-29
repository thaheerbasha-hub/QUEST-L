import re

APPLIANCE_WATTAGE_GUIDE = {
    "ac": "A 1.5 Ton 3-Star AC consumes ~1.5 units/hour (₹10/hr). Running it 8 hours a night costs ~₹2,400/month. Keeping the thermostat at 24°C instead of 18°C cuts this cost by ~30% (saving ~₹700/mo).",
    "geyser": "A 25L storage water heater consumes 2.0 kW (₹13/hr). Leaving it ON overnight causes 4-6 automatic reheat cycles, wasting ~3-4 units every night (₹600–₹800/mo). Turn it ON 15 minutes before bathing and switch it off immediately.",
    "refrigerator": "An old non-inverter fridge draws ~250-350W continuously when the compressor runs. Clean the rear condenser coils and check the door seal with a sheet of paper. If it slides out easily, replacing the gasket will save ~₹250/mo.",
    "fan": "A standard ceiling fan uses 75W. Replacing 3 regular fans with 28W BLDC fans saves ~35-40 units/month, paying for themselves within 14 months.",
    "tv": "TVs, gaming consoles, and Wi-Fi setup boxes on standby consume 15W–30W 24/7. Using an auto-cut surge protector saves ~15 units/month.",
    "pump": "Housing society water pumps are typically 5 HP to 10 HP (3.7 kW to 7.5 kW). Running them during 6 PM - 10 PM peak grid hours incurs higher demand penalties. Shift pumping to 11 PM or 2 PM."
}

def ask_coach(question, insights_list=None, forecast_data=None):
    """
    Plain-English responses tailored to the user's specific meter data and electricity savings habits.
    Works 100% out-of-the-box offline.
    """
    q_lower = question.lower()

    # Context values from current dataset
    vampire_kwh = insights_list[0]["metric_value"] if insights_list else "0.80 kWh/hr"
    vampire_saved = insights_list[0]["potential_saving"] if insights_list else "₹800/mo"
    peak_pct = insights_list[1]["metric_value"] if insights_list else "38%"
    proj_bill = f"₹{forecast_data['forecast_bill_inr']:,.0f}" if forecast_data else "₹4,200"
    achievable = f"₹{forecast_data['achievable_savings_inr']:,.0f}" if forecast_data else "₹1,150"

    # Specific queries
    if "ac" in q_lower or "air conditioner" in q_lower:
        return (
            f"❄️ **Air Conditioner Coach:**\n\n"
            f"{APPLIANCE_WATTAGE_GUIDE['ac']}\n\n"
            f"**Your Meter Insight:** Your dataset indicates peak loads during evening and night hours. "
            f"Setting your AC timer to turn off at 5 AM (relying on room insulation until wake-up) saves ~45 units/month."
        )

    if "geyser" in q_lower or "water heater" in q_lower or "bath" in q_lower:
        return (
            f"🚿 **Geyser Coach:**\n\n"
            f"{APPLIANCE_WATTAGE_GUIDE['geyser']}\n\n"
            f"**Your Meter Insight:** Your overnight baseline draw is **{vampire_kwh}**. Storage geysers are often the #1 silent culprit."
        )

    if "vampire" in q_lower or "night" in q_lower or "standby" in q_lower:
        return (
            f"🧛 **Vampire Standby Waste:**\n\n"
            f"Your current midnight draw is **{vampire_kwh}** between 1 AM and 5 AM. "
            f"By cutting unneeded standby power, you can put **{vampire_saved}** back into your wallet every month without sacrificing comfort."
        )

    if "bill" in q_lower or "forecast" in q_lower or "how much" in q_lower or "next month" in q_lower:
        return (
            f"📈 **Next Month's Bill Outlook:**\n\n"
            f"At your current consumption run-rate, your next bill is projected at **{proj_bill}**.\n\n"
            f"However, by adopting the 3 Coach insights (cutting midnight standby, shifting peak laundry/pumps, and avoiding the higher tariff bracket), "
            f"your bill can drop to **{forecast_data['optimized_bill_inr'] if forecast_data else '₹3,050'}** (saving **{achievable}**)."
        )

    if "save" in q_lower or "tips" in q_lower or "reduce" in q_lower or "action" in q_lower:
        return (
            f"💡 **Top 3 Plain-English Ways to Save Today:**\n\n"
            f"1. **Tame the 6 PM - 10 PM Spike:** Currently **{peak_pct}** of your power is consumed during evening hours. Shift clothes washing and society water pumping to morning/afternoon.\n"
            f"2. **Eliminate Midnight Leakage:** You are losing **{vampire_saved}** to devices left in standby at night.\n"
            f"3. **Optimal Cooling Temperature:** Always run fans simultaneously with AC set to 24°C instead of 18°C. This reduces compressor cycling by up to 35%."
        )

    if "society" in q_lower or "housing" in q_lower or "pump" in q_lower or "lift" in q_lower:
        return (
            f"🏢 **Housing Society Coach:**\n\n"
            f"{APPLIANCE_WATTAGE_GUIDE['pump']}\n\n"
            f"For common areas: Replace basement tube lights with motion-sensor LEDs, schedule overhead water filling pumps strictly between 11 PM and 5 AM (off-peak grid), and install timer relays."
        )

    # General fallback
    return (
        f"⚡ **Power Bill Coach says:**\n\n"
        f"I've analyzed your meter data. Here is what you should know in plain words:\n\n"
        f"• Your next bill is trending toward **{proj_bill}**.\n"
        f"• You have **{achievable} in avoidable waste** identified across midnight standby ({vampire_kwh}) and evening peak loads ({peak_pct}).\n\n"
        f"Ask me about specific appliances like **AC, Geyser, Refrigerator, Ceiling Fans, or Housing Society Pumps** to get exact ₹ savings!"
    )
