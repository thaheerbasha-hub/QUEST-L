# ⚡ Power Bill Coach

> **Problem Statement P01:** Families and housing societies do not know why their electricity bill jumps. Build a tool that reads sample meter or bill data, finds the waste and tells people in plain words how to save.
> 
> **Deliverables:** A dashboard with three insights from sample data and a forecast of the next bill.

---

## 🌟 Key Features

1. **Pre-Loaded Sample Datasets & File Uploader:**
   - *Apartment with 2 ACs:* Captures evening and late-night cooling spikes.
   - *Family with High Vampire Load:* Identifies continuous 24/7 standby bleed (geysers, old fridge, entertainment setups).
   - *Housing Society Common Meter:* Pinpoints water pumps and common area lighting running during peak grid tariff hours.
   - Custom CSV upload support (`timestamp`, `kwh`).

2. **Three Plain-English Waste Insights:**
   - 🧛 **Insight 1: Vampire Load (Midnight Standby Waste)** — Calculates excess units burned between 1 AM and 5 AM and the ₹ cost lost each month.
   - ⚡ **Insight 2: Evening Peak Spikes (6 PM - 10 PM)** — Shows peak-to-base load ratios and suggests shifting heavy appliances.
   - 🎯 **Insight 3: Tariff Slab Jump Danger** — Alerts when current run-rate is on track to cross expensive tier thresholds (e.g. >200 or >400 units) and gives the exact daily target reduction to stay in the cheaper bracket.

3. **Next Bill Forecast:**
   - 30-Day Forward Forecast Chart with 95% confidence bands based on 14-day EWMA trend and day-of-week seasonality.
   - Tiered slab breakdown (0-100, 101-200, 201-400, >400 units) with fixed grid charges.
   - **"Coach Savings Potential":** Side-by-side comparison of *Current Projected Bill* vs. *Optimized Bill*.

4. **Ask Power Coach (Plain-English AI Chat):**
   - Natural language Q&A about appliance wattages (AC, Geysers, Ceiling Fans, Water Pumps, Refrigerators) and actionable ways to save.

5. **1-Click PDF Energy Audit Report:**
   - Download a comprehensive 1-page Energy Audit & Action Plan.

6. **Instant Evaluator / Guest Access:**
   - 1-Click login designed for hackathons and quick evaluation without account creation.

---

## 🚀 How to Run Locally

```bash
# 1. Navigate to the project directory
cd power_bill_coach

# 2. Run with Streamlit
streamlit run app.py
```

---

## 🌐 Deploy to Streamlit Community Cloud (Free)

1. Push this folder to your GitHub repository.
2. Visit [share.streamlit.io](https://share.streamlit.io) and log in with GitHub.
3. Click **"New App"** $\rightarrow$ select your repo, branch (`main`), and set the main file path to `power_bill_coach/app.py`.
4. Click **Deploy!**
