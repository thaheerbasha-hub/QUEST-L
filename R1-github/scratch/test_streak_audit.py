import datetime as _dt
import pytz

def calculate_streak_existing(active_dates: set[str], today: _dt.date) -> int:
    current_streak = 0
    check_day = today
    if check_day.isoformat() in active_dates:
        while check_day.isoformat() in active_dates:
            current_streak += 1
            check_day -= _dt.timedelta(days=1)
    else:
        check_day = today - _dt.timedelta(days=1)
        while check_day.isoformat() in active_dates:
            current_streak += 1
            check_day -= _dt.timedelta(days=1)
    return current_streak

# Test 1: Consecutive days ending today
today = _dt.date(2026, 10, 22)
dates_consecutive = {"2026-10-20", "2026-10-21", "2026-10-22"}
print("Test 1 (3 consecutive ending today):", calculate_streak_existing(dates_consecutive, today))

# Test 2: Consecutive days ending yesterday (today not logged in yet)
dates_yesterday = {"2026-10-20", "2026-10-21"}
print("Test 2 (2 days ending yesterday, today pending):", calculate_streak_existing(dates_yesterday, today))

# Test 3: Missed day yesterday, logged in today
dates_missed_yesterday = {"2026-10-19", "2026-10-20", "2026-10-22"}
print("Test 3 (missed yesterday, logged in today):", calculate_streak_existing(dates_missed_yesterday, today))

# Test 4: Missed day 2 days ago, not logged in today
dates_missed_and_no_today = {"2026-10-19", "2026-10-20"}
print("Test 4 (missed yesterday and today):", calculate_streak_existing(dates_missed_and_no_today, today))

# Test 5: Timezone mismatch (UTC vs IST)
# 2026-10-22 01:00:00 IST is 2026-10-21 19:30:00 UTC
ist_tz = pytz.timezone("Asia/Kolkata")
dt_ist = ist_tz.localize(_dt.datetime(2026, 10, 22, 1, 0, 0))
dt_utc = dt_ist.astimezone(pytz.utc)
print(f"IST date: {dt_ist.date().isoformat()}, UTC date: {dt_utc.date().isoformat()}")
print(f"Mismatch when naive date.today() runs on UTC server at 1 AM IST: {dt_ist.date() != dt_utc.date()}")
