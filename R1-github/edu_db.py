import json
import os
import threading
import firebase_sync

_data_dir = None
_username = None
_lock = threading.Lock()
EDU_PROGRESS_FILE = "edu_progress.json"

LEVEL_PROGRESSION = [
    {"level": 1, "id": "level_1", "name": "Level 1 — First ₹1,000", "min_xp": 0, "next_xp": 350, "stage": "Start Investing"},
    {"level": 2, "id": "level_2", "name": "Level 2 — Grow Your Money", "min_xp": 350, "next_xp": 750, "stage": "Start Investing"},
    {"level": 3, "id": "level_3", "name": "Level 3 — Reach Your Goal", "min_xp": 750, "next_xp": 1250, "stage": "Start Investing"},
    {"level": 4, "id": "level_4", "name": "Level 4 — What's Your Style?", "min_xp": 1250, "next_xp": 1850, "stage": "Build Your Portfolio"},
    {"level": 5, "id": "level_5", "name": "Level 5 — Build Your Portfolio", "min_xp": 1850, "next_xp": 2550, "stage": "Build Your Portfolio"},
    {"level": 6, "id": "level_6", "name": "Level 6 — What Happens If...?", "min_xp": 2550, "next_xp": 3350, "stage": "Build Your Portfolio"},
    {"level": 7, "id": "level_7", "name": "Level 7 — News Detective", "min_xp": 3350, "next_xp": 4250, "stage": "Market Detective"},
    {"level": 8, "id": "level_8", "name": "Level 8 — Read the Market", "min_xp": 4250, "next_xp": 5250, "stage": "Market Detective"},
    {"level": 9, "id": "level_9", "name": "Level 9 — Market Storm", "min_xp": 5250, "next_xp": 6500, "stage": "Market Detective"},
    {"level": 10, "id": "level_tax", "name": "Level 10 — Tax & Market Master", "min_xp": 6500, "next_xp": None, "stage": "Standalone Challenge"},
]

def get_level_info(xp: int) -> dict:
    xp_val = int(xp or 0)
    for lvl in reversed(LEVEL_PROGRESSION):
        if xp_val >= lvl["min_xp"]:
            cur_min = lvl["min_xp"]
            nxt = lvl["next_xp"]
            if nxt is not None:
                progress_pct = min(100.0, max(0.0, ((xp_val - cur_min) / (nxt - cur_min)) * 100.0))
                needed_xp = nxt - xp_val
            else:
                progress_pct = 100.0
                needed_xp = 0
            return {
                "level_number": lvl["level"],
                "level_id": lvl["id"],
                "level_name": lvl["name"],
                "stage": lvl["stage"],
                "min_xp": cur_min,
                "next_xp": nxt,
                "needed_xp": needed_xp,
                "progress_pct": progress_pct
            }
    return get_level_info(0)

DEFAULT_PROGRESS = {
    "total_xp": 0,
    "virtual_balance": 15000.0,
    "quest_coins": 0,
    "streak": 0,
    "activity_dates": [],
    "seen_notification_keys": [],
    "entitlements": {},
    "badges": [],
    "completed_levels": [],
    "completed_articles": [],
    "bookmarks": [],
    "liked_videos": [],
    "current_level": "Level 1 — First ₹1,000",
    "last_education_section": "Learning Path",
    "last_portfolio_section": "Overview"
}

def set_data_dir(data_dir: str, username: str = None):
    global _data_dir, _username
    _data_dir = data_dir
    _username = username

def _get_filepath() -> str:
    if not _data_dir:
        raise ValueError("edu_db data directory not set. Call set_data_dir first.")
    return os.path.join(_data_dir, EDU_PROGRESS_FILE)

def _get_global_likes_filepath() -> str:
    if _data_dir:
        parent = os.path.dirname(_data_dir)
        return os.path.join(parent, "global_video_likes.json")
    return "global_video_likes.json"

def _load_global_likes() -> dict:
    fp = _get_global_likes_filepath()
    with _lock:
        if os.path.exists(fp):
            try:
                with open(fp, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

def _save_global_likes(data: dict) -> None:
    fp = _get_global_likes_filepath()
    with _lock:
        try:
            with open(fp, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

def load_progress() -> dict:
    filepath = _get_filepath()
    with _lock:
        if not os.path.exists(filepath):
            return DEFAULT_PROGRESS.copy()
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for k, v in DEFAULT_PROGRESS.items():
                    data.setdefault(k, v)
                return data
        except Exception:
            return DEFAULT_PROGRESS.copy()

def get_video_likes(video_id: str) -> tuple[bool, int]:
    """Returns (is_liked_by_current_user, total_live_user_likes)."""
    prog = load_progress()
    user_liked = video_id in prog.get("liked_videos", [])
    global_likes = _load_global_likes()
    users_who_liked = global_likes.get(video_id, [])
    # Also ensure current user is synced
    if user_liked and _username and _username not in users_who_liked:
        users_who_liked.append(_username)
        global_likes[video_id] = users_who_liked
        _save_global_likes(global_likes)
    return (user_liked, len(users_who_liked))

def toggle_like(video_id: str) -> tuple[bool, int]:
    """Toggles like by current user and returns (is_now_liked, total_live_user_likes)."""
    prog = load_progress()
    liked_vids = prog.get("liked_videos", [])
    global_likes = _load_global_likes()
    users_who_liked = global_likes.get(video_id, [])
    uname = _username or "user"

    if video_id in liked_vids:
        liked_vids.remove(video_id)
        if uname in users_who_liked:
            users_who_liked.remove(uname)
        is_liked = False
    else:
        liked_vids.append(video_id)
        if uname not in users_who_liked:
            users_who_liked.append(uname)
        is_liked = True

    prog["liked_videos"] = liked_vids
    save_progress(prog)
    global_likes[video_id] = users_who_liked
    _save_global_likes(global_likes)
    return (is_liked, len(users_who_liked))

def toggle_bookmark(article_id: str) -> bool:
    """Toggles bookmark status and returns True if now bookmarked, False otherwise."""
    prog = load_progress()
    bms = prog.get("bookmarks", [])
    if article_id in bms:
        bms.remove(article_id)
        is_bookmarked = False
    else:
        bms.append(article_id)
        is_bookmarked = True
    prog["bookmarks"] = bms
    save_progress(prog)
    return is_bookmarked

def complete_article(article_id: str, xp_award: int = 50) -> int:
    """Marks article as completed and awards XP if not already completed. Returns total XP."""
    prog = load_progress()
    comp = prog.get("completed_articles", [])
    if article_id not in comp:
        comp.append(article_id)
        prog["completed_articles"] = comp
        save_progress(prog)
        # Route XP through centralized award_xp for streak + level tracking
        return award_xp(xp_award, "video_watched")
    return prog.get("total_xp", 0)


def get_ist_today() -> str:
    """Returns today's date in IST (Asia/Kolkata) as YYYY-MM-DD."""
    import pytz
    from datetime import datetime
    ist = pytz.timezone("Asia/Kolkata")
    return datetime.now(ist).strftime("%Y-%m-%d")


def calculate_streak(activity_dates: set[str] | list[str], today_str: str | None = None) -> int:
    """Calculates consecutive active days in IST ending today (or yesterday as grace period)."""
    import datetime as _dt
    if today_str is None:
        today_str = get_ist_today()
    today = _dt.date.fromisoformat(today_str)
    dates_set = set(activity_dates)

    current_streak = 0
    check_day = today

    # If today is in activity_dates, count backwards from today
    if check_day.isoformat() in dates_set:
        while check_day.isoformat() in dates_set:
            current_streak += 1
            check_day -= _dt.timedelta(days=1)
    else:
        # Check if yesterday was active (grace period during the current day)
        check_day = today - _dt.timedelta(days=1)
        while check_day.isoformat() in dates_set:
            current_streak += 1
            check_day -= _dt.timedelta(days=1)

    return current_streak


def record_daily_login(username: str = None) -> tuple[int, bool]:
    """Records user login for today in IST.

    Returns (current_streak: int, is_new_login_today: bool).
    Guarantees one entry per calendar day, handles repeated logins cleanly,
    and updates the persistent streak.
    """
    today = get_ist_today()
    prog = load_progress()
    activity_dates = prog.get("activity_dates", [])
    if not isinstance(activity_dates, list):
        activity_dates = list(activity_dates)

    is_new_today = today not in activity_dates
    if is_new_today:
        activity_dates.append(today)
        activity_dates = sorted(list(set(activity_dates)))[-90:]
        prog["activity_dates"] = activity_dates

    streak = calculate_streak(activity_dates, today)
    prev_streak = prog.get("streak", 0)
    prog["streak"] = streak

    if is_new_today or prev_streak != streak:
        save_progress(prog)

    return streak, is_new_today


def award_xp(amount: int, source: str = "general") -> int:
    """Centralized XP award — updates total_xp, level, activity_dates, and syncs.
    
    Sources: 'quiz_pass', 'video_watched', 'trade_executed', 'tax_case_solved',
             'badge_earned', 'first_trade_bonus', 'perfect_score_bonus'
    Returns the new total XP.
    """
    prog = load_progress()
    old_xp = prog.get("total_xp", 0)
    old_level_name = get_level_info(old_xp)["level_name"]
    old_streak = prog.get("streak", 0)

    prog["total_xp"] = old_xp + amount
    # Update level
    level_info = get_level_info(prog["total_xp"])
    prog["current_level"] = level_info["level_name"]
    # Track activity dates for streak calculation (always IST)
    today = get_ist_today()
    activity_dates = prog.get("activity_dates", [])
    if today not in activity_dates:
        activity_dates.append(today)
        # Keep last 90 days only, unique and sorted
        activity_dates = sorted(list(set(activity_dates)))[-90:]
    prog["activity_dates"] = activity_dates
    # Recalculate streak
    new_streak = calculate_streak(activity_dates, today)
    prog["streak"] = new_streak
    # Track XP sources for auditing
    xp_log = prog.get("xp_log", [])
    xp_log.append({"amount": amount, "source": source, "date": today})
    prog["xp_log"] = xp_log[-200:]  # Keep last 200 entries
    save_progress(prog)

    # Trigger Level Up popup if level increased
    if level_info["level_name"] != old_level_name:
        try:
            import notifications
            notifications.send_alert(
                f"🎉 **Level Up!** Congratulations, {level_info['level_name']} unlocked! ({level_info['min_xp']} XP)",
                icon="🎉",
                notification_key=f"level_up_{level_info['level_name']}",
                category="level_up"
            )
        except Exception:
            pass

    # Trigger Streak Milestone popup if reached
    if new_streak in [3, 7, 14, 30, 60, 90] and new_streak != old_streak:
        try:
            import notifications
            streak_messages = {
                3:  "🔥 **3-Day Streak!** Consistency is key — keep your momentum going!",
                7:  "🔥 **7-Day Streak!** A full week of learning and market tracking!",
                14: "🔥 **14-Day Streak!** Two weeks strong — master investor in the making!",
                30: "🏆 **30-Day Streak!** 1 month milestone reached! Outstanding discipline!",
                60: "⚡ **60-Day Streak!** Elite habit formed — exceptional progress!",
                90: "👑 **90-Day Streak!** Legendary consistency! You are a market master!",
            }
            msg = streak_messages.get(new_streak)
            if msg:
                notifications.send_alert(
                    msg,
                    icon="🔥",
                    notification_key=f"streak_{new_streak}_{today}",
                    category="streak"
                )
        except Exception:
            pass

    return prog["total_xp"]


def save_progress(data: dict) -> None:
    filepath = _get_filepath()
    with _lock:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)

    if _username:
        try:
            firebase_sync.trigger_sync(_username, filepath)
        except Exception as e:
            print(f"Warning: Failed to sync edu progress to Firebase: {e}")

def get_last_education_section() -> str:
    """Returns the user's last visited Education sub-page, defaulting to 'Learning Path'."""
    try:
        prog = load_progress()
        sec = prog.get("last_education_section")
        if sec == "Wallet":
            return "Shop"
        valid_edu = ["Learning Path", "Library", "Virtual Trading", "Leaderboard", "Badges", "Tax Detective", "MICHAEL", "Shop"]
        if sec in valid_edu:
            return sec
    except Exception:
        pass
    return "Learning Path"

def set_last_education_section(section: str) -> None:
    """Persists the user's last visited Education sub-page."""
    if section == "Wallet":
        section = "Shop"
    valid_edu = ["Learning Path", "Library", "Virtual Trading", "Leaderboard", "Badges", "Tax Detective", "MICHAEL", "Shop"]
    if section in valid_edu:
        try:
            prog = load_progress()
            if prog.get("last_education_section") != section:
                prog["last_education_section"] = section
                save_progress(prog)
        except Exception:
            pass

def get_last_portfolio_section() -> str:
    """Returns the user's last visited Portfolio sub-page, defaulting to 'Overview'."""
    try:
        prog = load_progress()
        sec = prog.get("last_portfolio_section")
        if sec == "Wallet":
            return "Shop"
        valid_prof = ["Overview", "Planner", "Analytics", "Projections", "Insights", "News", "Activity", "Chat", "MICHAEL", "Shop"]
        if sec in valid_prof:
            return sec
    except Exception:
        pass
    return "Overview"

def set_last_portfolio_section(section: str) -> None:
    """Persists the user's last visited Portfolio sub-page."""
    if section == "Wallet":
        section = "Shop"
    valid_prof = ["Overview", "Planner", "Analytics", "Projections", "Insights", "News", "Activity", "Chat", "MICHAEL", "Shop"]
    if section in valid_prof:
        try:
            prog = load_progress()
            if prog.get("last_portfolio_section") != section:
                prog["last_portfolio_section"] = section
                save_progress(prog)
        except Exception:
            pass

def add_virtual_balance(amount: float) -> float:
    """Adds to the virtual balance and returns the new total."""
    prog = load_progress()
    current = prog.get("virtual_balance", 0.0)
    new_balance = current + amount
    prog["virtual_balance"] = new_balance
    save_progress(prog)
    return new_balance


def is_module_completed(module_id: str = "module_5") -> bool:
    """Return True if every topic in *module_id* is in completed_levels.

    Two pass strategy:
    1. Fast path: if module_id itself appears as a string in completed_levels.
    2. Slow path: load education_catalog.json, find the matching module entry,
       collect every topic["topic"] title, and check all are present.
    Returns False on any exception (missing file, bad JSON, etc.).
    """
    try:
        prog = load_progress()
        completed = prog.get("completed_levels", [])
        if not isinstance(completed, list):
            completed = list(completed) if completed else []

        # Fast path
        if module_id in completed:
            return True

        # Slow path — read catalogue
        import json as _json
        import os as _os
        # edu_db.py lives at <project_root>/edu_db.py;
        # education_catalog.json lives at <project_root>/quest_app/education_catalog.json
        _here = _os.path.dirname(_os.path.abspath(__file__))
        catalog_path = _os.path.join(_here, "quest_app", "education_catalog.json")
        if not _os.path.exists(catalog_path):
            return False

        with open(catalog_path, "r", encoding="utf-8") as _f:
            catalog = _json.load(_f)

        # Find the module entry
        module_entry = None
        for entry in catalog:
            if entry.get("module_id") == module_id or entry.get("level_id") == module_id:
                module_entry = entry
                break

        if module_entry is None:
            return False

        topics = module_entry.get("topics", [])
        if not topics:
            return False

        topic_titles = [t.get("topic", "") for t in topics if t.get("topic")]
        if not topic_titles:
            return False

        return all(title in completed for title in topic_titles)

    except Exception:
        return False
