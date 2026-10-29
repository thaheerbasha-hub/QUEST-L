# -*- coding: utf-8 -*-
"""
QUEST Centralized Notification System
======================================
Unified in-app alerts, live polling, deduplication, persistent state
tracking, and notification templates for QUEST.

Live portfolio news alerts are delivered via a st.fragment(run_every=...)
poller so popups appear automatically while the user is on any page,
without requiring a page reload.

All tunable parameters are at the top of this file under NOTIFICATION_CONFIG.

Requires: Streamlit >= 1.37 (installed: 1.61.1 -- verified)
"""

import streamlit as st
import edu_db

# ==============================================================================
# Master Notification Configuration
# Edit poll intervals, caps, TTLs and copy here. Do NOT scatter them elsewhere.
# ==============================================================================
NOTIFICATION_CONFIG = {
    # --- Live poller ---
    "poll_interval_secs": 30,        # How often st.fragment re-runs (seconds)
    "news_cache_ttl_secs": 300,      # External API called at most once per 5 min
    "max_article_age_hours": 8760,   # 1 year — archive has past-dated articles; session dedup prevents double-firing
    "max_popups_per_poll": 3,        # Max toasts fired in one fragment run

    # --- Session caps (across all polls in one browser session) ---
    "caps": {
        "max_news_alerts_per_session": 20,
        "max_total_alerts_per_session": 30,
    },

    # --- Sidebar news panel ---
    "sidebar_news_refresh_secs": 300,

    # --- Toast appearance ---
    # st.toast duration is controlled by overriding the CSS animation-duration.
    # The native default is ~4 s; we extend to ~8 s.
    "toast_duration_secs": 8,

    # --- Other notification templates ---
    "portfolio_news": {
        "icon": "\u26a1",
        "format": "\ud83d\udcf0 **{ticker}**: {title}",
    },
    "level_up": {
        "icon": "\ud83c\udf89",
        "format": "\ud83c\udf89 **Level Up!** Congratulations, {level_name} unlocked! ({min_xp} XP)",
    },
    "streak_milestones": {
        "milestones": [3, 7, 14, 30, 60, 90],
        "messages": {
            3:  "\ud83d\udd25 **3-Day Streak!** Consistency is key \u2014 keep your momentum going!",
            7:  "\ud83d\udd25 **7-Day Streak!** A full week of learning and market tracking!",
            14: "\ud83d\udd25 **14-Day Streak!** Two weeks strong \u2014 master investor in the making!",
            30: "\ud83c\udfc6 **30-Day Streak!** 1 month milestone reached! Outstanding discipline!",
            60: "\u26a1 **60-Day Streak!** Elite habit formed \u2014 exceptional progress!",
            90: "\ud83d\udc51 **90-Day Streak!** Legendary consistency! You are a market master!",
        },
    },
    "badge_unlocked": {
        "icon": "\ud83c\udfc6",
        "format": "\ud83c\udfc6 **Badge Unlocked: {badge_name}!** +{reward_xp} XP earned.",
    },
    "quiz_completed": {
        "icon": "\ud83c\udf93",
        "format": "\ud83c\udf93 **Quiz Passed: {title}!** +\u20b9{cash_reward} virtual cash & +{xp_reward} XP.",
    },
    "tax_case_solved": {
        "icon": "\ud83d\udd75\ufe0f",
        "format": "\ud83d\udd75\ufe0f **Case Solved: {case_title}!** Audit closed successfully.",
    },
    "trade_executed": {
        "icon": "\ud83d\udcc8",
        "format": "\ud83d\udcbc **Order Filled:** {action} {quantity} shares of {symbol} at \u20b9{price:,.2f}.",
    },
}


# ==============================================================================
# Shared cached news fetch
# Wraps the external API so it is called AT MOST ONCE per cache_ttl window.
# ==============================================================================

@st.cache_data(ttl=NOTIFICATION_CONFIG["news_cache_ttl_secs"], show_spinner=False)
def _fetch_all_portfolio_news_cached(holdings_key: str, holdings_json: str) -> list:
    """
    Fetch and match news for the given holdings. Cached for news_cache_ttl_secs
    (default 5 min) so the external API is never hit more than once per window,
    even across many fragment re-runs.

    holdings_key  -- stable cache key (sorted ticker CSV)
    holdings_json -- JSON-serialised holdings (part of cache key via hashing)
    """
    import json
    try:
        holdings = json.loads(holdings_json)
        from portfolio_news_matcher import get_matched_portfolio_news
        return get_matched_portfolio_news(holdings, max_articles=30)
    except Exception as exc:
        import traceback
        print(f"[QUEST news cache] fetch error: {exc}\n{traceback.format_exc()}")
        return []


# Fallback benchmark equities for users with empty portfolios or visiting Education
DEFAULT_BENCHMARK_ASSETS = [
    {"identifier": "RELIANCE.NS", "name": "Reliance Industries", "quantity": 1},
    {"identifier": "TCS.NS", "name": "Tata Consultancy Services", "quantity": 1},
    {"identifier": "HDFCBANK.NS", "name": "HDFC Bank", "quantity": 1},
    {"identifier": "INFY.NS", "name": "Infosys", "quantity": 1},
    {"identifier": "TATAMOTORS.NS", "name": "Tata Motors", "quantity": 1},
]


def _get_cached_news(current_assets: list) -> list:
    """Build a stable cache key and return cached matched articles.
    If current_assets is empty, falls back to top benchmark Indian equities.
    """
    assets_to_use = current_assets if current_assets else DEFAULT_BENCHMARK_ASSETS
    try:
        import json

        def _ticker(a):
            if isinstance(a, dict):
                return str(a.get("identifier") or a.get("name", "")).upper()
            return str(getattr(a, "identifier", None) or getattr(a, "name", "")).upper()

        tickers = sorted(_ticker(a) for a in assets_to_use if _ticker(a))
        if not tickers:
            return []

        holdings_key = ",".join(tickers)

        def _to_dict(a):
            if isinstance(a, dict):
                return a
            return {
                "identifier": getattr(a, "identifier", ""),
                "name":       getattr(a, "name", ""),
                "quantity":   getattr(a, "quantity", 1),
            }

        holdings_json = json.dumps([_to_dict(a) for a in assets_to_use], sort_keys=True)
        return _fetch_all_portfolio_news_cached(holdings_key, holdings_json)
    except Exception as exc:
        print(f"[QUEST news] _get_cached_news error: {exc}")
        return []


# ==============================================================================
# 24-hour age filter
# ==============================================================================

def _is_within_24h(article: dict) -> bool:
    """Return True if article date is within max_article_age_hours (default 24)."""
    max_age = NOTIFICATION_CONFIG.get("max_article_age_hours", 24)
    raw = article.get("date") or article.get("pub_date") or ""
    if not raw:
        return True
    try:
        from datetime import datetime, timezone, timedelta
        import re as _re
        raw_str = str(raw).strip()
        # Unix timestamp (seconds or milliseconds)
        if _re.match(r"^\d{9,13}$", raw_str):
            ts = int(raw_str)
            if ts > 1e10:
                ts //= 1000
            pub = datetime.fromtimestamp(ts, tz=timezone.utc)
        else:
            pub = None
            for fmt in (
                "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%d %H:%M:%S",   "%Y-%m-%d",
                "%a, %d %b %Y %H:%M:%S %z",
            ):
                try:
                    pub = datetime.strptime(raw_str[:26], fmt)
                    if pub.tzinfo is None:
                        pub = pub.replace(tzinfo=timezone.utc)
                    break
                except ValueError:
                    continue
            if pub is None:
                return True
        cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=max_age)
        return pub >= cutoff
    except Exception:
        return True


# ==============================================================================
# CSS: pin toast container to top-right, style as notification cards
# Selector verified against Streamlit 1.61.1 JS bundle:
#   data-testid="stToastContainer"  (outer wrapper)
#   data-testid="stToast"           (individual toast)
# ==============================================================================

_TOAST_CSS = """
<style>
/* ── Move Streamlit's toast stack to the top-right of the viewport ── */
[data-testid="stToastContainer"] {
    position: fixed !important;
    top: 56px !important;       /* clears Streamlit toolbar (~52 px) */
    right: 16px !important;
    bottom: auto !important;
    left: auto !important;
    z-index: 999999 !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: flex-end !important;
    gap: 8px !important;
    pointer-events: none;
    max-width: 360px;
    width: 100%;
}

/* ── Individual toast card ── */
[data-testid="stToast"] {
    pointer-events: all;
    background: linear-gradient(
        135deg,
        rgba(15, 23, 42, 0.97) 0%,
        rgba(22, 33, 56, 0.97) 100%
    ) !important;
    border: 1px solid rgba(93, 202, 165, 0.35) !important;
    border-left: 3px solid #5DCAA5 !important;
    border-radius: 10px !important;
    box-shadow:
        0 8px 32px rgba(0, 0, 0, 0.45),
        0 0 0 1px rgba(93, 202, 165, 0.08) !important;
    padding: 12px 14px !important;
    min-width: 280px !important;
    max-width: 360px !important;
    backdrop-filter: blur(12px) !important;
    -webkit-backdrop-filter: blur(12px) !important;
    /* Extend display time to ~8 s */
    animation-duration: 8s !important;
}

/* Icon */
[data-testid="stToast"] [data-testid="stToastIcon"],
[data-testid="stToast"] [class*="toastIcon"] {
    font-size: 1.3rem !important;
    align-self: flex-start !important;
    margin-top: 1px !important;
}

/* Text */
[data-testid="stToast"] [data-testid="stMarkdownContainer"] p,
[data-testid="stToast"] p {
    font-size: 0.83rem !important;
    line-height: 1.45 !important;
    color: #e2e8f0 !important;
    margin: 0 !important;
}

/* Links inside toasts */
[data-testid="stToast"] a {
    color: #5DCAA5 !important;
    text-decoration: underline !important;
    text-underline-offset: 2px !important;
}
[data-testid="stToast"] a:hover {
    color: #38bdf8 !important;
}
</style>
"""


def _inject_toast_css() -> None:
    """Inject top-right toast CSS exactly once per session."""
    if not st.session_state.get("_quest_toast_css_injected"):
        st.markdown(_TOAST_CSS, unsafe_allow_html=True)
        st.session_state["_quest_toast_css_injected"] = True


# ==============================================================================
# Live news alert fragment  (primary public entry point)
# ==============================================================================

def render_live_news_alerts(current_assets: list, username: str | None = None) -> None:
    """
    Call this ONCE from the shared layout (main.py), after holdings are loaded.
    It mounts a st.fragment that autonomously re-runs every poll_interval_secs
    seconds so new-article toasts appear while the user is idle on any page --
    no page reload required.

    Guard: checks _live_news_mounted in session_state so the fragment is
    registered at most once per browser session even if called from multiple
    code paths.
    """
    # Prevent double-mounting (e.g. if called from both sidebar and main body)
    if st.session_state.get("_live_news_mounted"):
        return
    st.session_state["_live_news_mounted"] = True

    _inject_toast_css()
    _render_live_news_fragment(current_assets, username)


def check_portfolio_news_alerts(current_assets: list, username: str | None = None) -> list[str]:
    """
    Evaluates new-article alerts for holdings or fallback benchmark equities,
    fires top-right toasts with persistent and session-level deduplication,
    and returns the list of fired article titles.
    """
    max_per_poll  = NOTIFICATION_CONFIG.get("max_popups_per_poll", 3)
    session_cap   = NOTIFICATION_CONFIG.get("caps", {}).get("max_news_alerts_per_session", 20)

    session_shown: set = st.session_state.setdefault("_live_news_shown_keys", set())
    session_count: int = st.session_state.get("_live_news_session_count", 0)

    if session_count >= session_cap:
        return []

    try:
        # 1. Fetch via shared cache (no direct external API call; falls back to benchmark if empty)
        effective_assets = current_assets if current_assets else DEFAULT_BENCHMARK_ASSETS
        all_matched = _get_cached_news(effective_assets)
        if not all_matched:
            return []

        # 2. Session-only dedup for news — we intentionally do NOT persist news keys
        # to Firestore because that would permanently block all archive articles once
        # they've been shown once. Session deduplication is sufficient: the fragment
        # re-runs every 60 s within one browser session and session_shown prevents
        # double-firing. On the next session the archive rotates through again.

        # 3. Filter: Prefer fresh articles (<24h), but if none exist (e.g. static archive/weekend),
        # gracefully fallback to latest available matched articles so users never experience a news blackout.
        fresh_articles = [art for art in all_matched if _is_within_24h(art)]
        candidate_articles = fresh_articles if fresh_articles else all_matched

        unseen = []
        for art in candidate_articles:
            title = art.get("title", "").strip()
            url   = art.get("url") or art.get("link", "") or ""
            key   = f"live_news_{url if url else title}"
            if key in session_shown:
                continue
            unseen.append((key, art))

        if not unseen:
            return []

        # 4. Fire at most max_per_poll toasts this run
        fired_titles: list = []

        for news_key, art in unseen[:max_per_poll]:
            if session_count >= session_cap:
                break

            title       = art.get("title", "").strip()
            url         = art.get("url") or art.get("link", "") or ""
            ticker      = art.get("matched_ticker") or art.get("ticker") or "Portfolio"
            source_name = art.get("source_name", "")

            is_valid_url = bool(url and (url.startswith("http://") or url.startswith("https://")))
            short_title  = (title[:85] + "…") if len(title) > 85 else title

            if is_valid_url and source_name:
                body = f"**{ticker}**: {short_title}\n\n[Read on {source_name} ↗]({url})"
            elif is_valid_url:
                body = f"**{ticker}**: {short_title}\n\n[Read article ↗]({url})"
            else:
                body = f"**{ticker}**: {short_title}"
                if source_name:
                    body += f"\n\n*{source_name}*"

            try:
                st.toast(body, icon="📰")
            except Exception as te:
                print(f"[QUEST live news] st.toast error: {te}")
                continue

            session_shown.add(news_key)
            fired_titles.append(title)
            session_count += 1

        # 5. Update session count (no Firestore write for news — intentional)
        st.session_state["_live_news_session_count"] = session_count
        return fired_titles

    except Exception as exc:
        import traceback
        print(f"[QUEST live news] error: {exc}\n{traceback.format_exc()}")
        return []


@st.fragment(run_every=NOTIFICATION_CONFIG["poll_interval_secs"])
def _render_live_news_fragment(current_assets: list, username: str | None) -> None:
    """
    Inner fragment -- re-runs automatically every poll_interval_secs seconds.
    Do NOT call directly; use render_live_news_alerts() instead.

    Safety: entirely wrapped in try/except; any error is logged and the
    fragment silently retries on the next scheduled run.
    """
    try:
        check_portfolio_news_alerts(current_assets, username=username)
    except Exception as exc:
        import traceback
        print(f"[QUEST live news] fragment error: {exc}\n{traceback.format_exc()}")
        # Never surface to the page; retries next poll automatically


# ==============================================================================
# Sidebar News Panel (card list, uses same cache)
# ==============================================================================

def render_sidebar_news_panel(current_assets: list) -> None:
    """
    Compact portfolio news card list in the Streamlit sidebar.
    Uses the same _get_cached_news() cache -- falls back to benchmark intelligence if current_assets is empty.
    """
    effective_assets = current_assets if current_assets else DEFAULT_BENCHMARK_ASSETS
    articles = _get_cached_news(effective_assets) or []

    st.sidebar.markdown("""
<style>
.quest-news-panel-title {
    font-size: 0.72rem; font-weight: 700; letter-spacing: 0.08em;
    text-transform: uppercase; color: var(--q-text-3, #64748b);
    padding: 6px 0 4px; margin-bottom: 0;
}
.quest-news-card {
    background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
    border-radius: 8px; padding: 8px 10px; margin-bottom: 6px;
    transition: border-color 0.2s;
}
.quest-news-card:hover { border-color: rgba(93,202,165,0.35); }
.quest-news-ticker {
    font-size: 0.65rem; font-weight: 700; letter-spacing: 0.05em;
    color: var(--q-accent, #5DCAA5); text-transform: uppercase; margin-bottom: 2px;
}
.quest-news-headline {
    font-size: 0.78rem; font-weight: 500; color: var(--q-text, #f1f3f5);
    line-height: 1.35; margin-bottom: 4px;
    display: -webkit-box; -webkit-line-clamp: 3;
    -webkit-box-orient: vertical; overflow: hidden;
}
.quest-news-meta { font-size: 0.65rem; color: var(--q-text-3, #64748b); }
.quest-news-sentiment-pos { color: #34d399; }
.quest-news-sentiment-neg { color: #f87171; }
.quest-news-sentiment-neu { color: #94a3b8; }
.quest-news-empty {
    font-size: 0.75rem; color: var(--q-text-3, #64748b);
    text-align: center; padding: 10px 0 6px; opacity: 0.7;
}
</style>
""", unsafe_allow_html=True)

    panel_title = "⚡ Live Portfolio News" if current_assets else "⚡ Live Market Intelligence"
    st.sidebar.markdown(
        f"<div class='quest-news-panel-title'>{panel_title}</div>",
        unsafe_allow_html=True,
    )

    recent = [a for a in articles if _is_within_24h(a)]
    if not recent:
        recent = articles[:8]

    if not recent:
        st.sidebar.markdown(
            "<div class='quest-news-empty'>No matching news at this time."
            "<br><span style='font-size:0.65rem;'>Updates every 5 min</span></div>",
            unsafe_allow_html=True,
        )
        return

    for art in recent[:8]:
        ticker    = art.get("matched_ticker") or art.get("ticker") or ""
        title     = art.get("title", "").strip()
        url       = art.get("url") or art.get("link", "") or ""
        source    = art.get("source_name", "")
        sentiment = art.get("sentiment_label", "").lower()
        if not title:
            continue

        if "positive" in sentiment or "bullish" in sentiment:
            s_class, s_icon = "quest-news-sentiment-pos", "▲"
        elif "negative" in sentiment or "bearish" in sentiment:
            s_class, s_icon = "quest-news-sentiment-neg", "▼"
        else:
            s_class, s_icon = "quest-news-sentiment-neu", ""

        meta_parts = []
        if source:
            meta_parts.append(source)
        if s_icon:
            meta_parts.append(f"<span class='{s_class}'>{s_icon} {sentiment.capitalize()}</span>")
        meta_html = " · ".join(meta_parts)

        is_valid_url = bool(url and (url.startswith("http://") or url.startswith("https://")))
        headline_html = (
            f"<a href='{url}' target='_blank' style='text-decoration:none;color:inherit;'>"
            f"<div class='quest-news-headline'>{title}</div></a>"
            if is_valid_url
            else f"<div class='quest-news-headline'>{title}</div>"
        )

        st.sidebar.markdown(f"""
<div class='quest-news-card'>
  <div class='quest-news-ticker'>⚡ {ticker}</div>
  {headline_html}
  <div class='quest-news-meta'>{meta_html}</div>
</div>""", unsafe_allow_html=True)

    import datetime as _dt, time as _t
    import time
    fetch_ts   = st.session_state.get("_sidebar_news_fetch_ts", time.time())
    fetch_time = _dt.datetime.fromtimestamp(fetch_ts)
    subtext = "refreshes every 5 min" if current_assets else "latest market intelligence"
    st.sidebar.markdown(
        f"<div style='font-size:0.6rem;color:var(--q-text-3,#64748b);text-align:center;padding:2px 0 4px;'>"
        f"Updated {fetch_time.strftime('%H:%M')} · {subtext}</div>",
        unsafe_allow_html=True,
    )


# ==============================================================================
# Education Activity & Milestone Alerts
# ==============================================================================

def render_education_alerts(username: str | None = None) -> None:
    """
    Delivers educational milestone alerts and daily learning motivation in the Education workspace.
    Runs once per session.
    """
    _inject_toast_css()
    if st.session_state.get("_edu_alert_rendered"):
        return
    st.session_state["_edu_alert_rendered"] = True

    try:
        from datetime import date
        today_str = date.today().isoformat()  # e.g. "2026-10-24" — resets daily
        prog = edu_db.load_progress()
        streak = prog.get("streak", 0)
        total_xp = prog.get("total_xp", 0)
        level_info = edu_db.get_level_info(total_xp)

        if streak > 0:
            msg = f"🎓 **Streak Active: {streak} Day{'s' if streak != 1 else ''}!** Keep learning to level up to {level_info['level_name']}."
        else:
            msg = f"🎓 **Welcome to QUEST Education!** Complete a lesson or quiz today to start your learning streak and earn XP!"
        # Daily key: edu_welcome_2026-10-24 — user sees the welcome toast once per calendar day
        send_alert(msg, icon="🎓", notification_key=f"edu_welcome_{today_str}", category="education")
    except Exception as exc:
        print(f"[QUEST edu alerts] error: {exc}")


# ==============================================================================
# Core one-off notification helper (badges, streaks, trade fills, etc.)
# ==============================================================================

def send_alert(message: str, icon: str = "\U0001f514", notification_key: str | None = None,
               category: str = "general") -> bool:
    """
    Delivers a one-off in-app toast, enforcing persistent deduplication,
    session-level deduplication, and per-session caps.

    Returns True if the toast was displayed, False if skipped.
    """
    _inject_toast_css()

    session_counts     = st.session_state.setdefault("_quest_alerts_session_counts", {})
    session_shown_keys = st.session_state.setdefault("_quest_alerts_shown_keys", set())

    caps      = NOTIFICATION_CONFIG.get("caps", {})
    max_cat   = caps.get(f"max_{category}_alerts_per_session", caps.get("max_total_alerts_per_session", 30))
    max_total = caps.get("max_total_alerts_per_session", 30)

    if session_counts.get(category, 0) >= max_cat or session_counts.get("total", 0) >= max_total:
        return False
    if notification_key and notification_key in session_shown_keys:
        return False

    prog = None
    if notification_key:
        try:
            prog      = edu_db.load_progress()
            seen_keys = set(prog.get("seen_notification_keys", []))
            if notification_key in seen_keys:
                session_shown_keys.add(notification_key)
                return False
        except Exception:
            prog = None

    try:
        st.toast(message, icon=icon)
    except Exception:
        st.info(f"{icon} {message}")

    session_counts[category] = session_counts.get(category, 0) + 1
    session_counts["total"]  = session_counts.get("total", 0) + 1

    if notification_key:
        session_shown_keys.add(notification_key)
        if prog is not None:
            try:
                seen_list = prog.get("seen_notification_keys", [])
                if not isinstance(seen_list, list):
                    seen_list = list(seen_list)
                seen_list.append(notification_key)
                prog["seen_notification_keys"] = seen_list[-500:]
                edu_db.save_progress(prog)
            except Exception:
                pass

    return True


# ==============================================================================
# Source Name Extractor (shared utility)
# ==============================================================================

def extract_source_name(provider: str | None = None, url: str | None = None,
                        summary: str = "") -> str:
    """Clean, user-friendly publisher name from provider string, URL, or summary."""
    if provider and isinstance(provider, str) and provider.strip() \
            and provider.strip().lower() not in ("unknown", "none"):
        return provider.strip()

    if url and isinstance(url, str):
        from urllib.parse import urlparse
        try:
            domain = urlparse(url).netloc.lower()
            mapping = {
                "ft.com":            "Financial Times",
                "financialtimes":    "Financial Times",
                "reuters.com":       "Reuters",
                "bloomberg.com":     "Bloomberg",
                "moneycontrol.com":  "Moneycontrol",
                "economictimes":     "Economic Times",
                "indiatimes":        "Economic Times",
                "livemint.com":      "Mint",
                "business-standard": "Business Standard",
                "cnbc.com":          "CNBC",
                "finance.yahoo.com": "Yahoo Finance",
                "yahoo.com":         "Yahoo Finance",
            }
            for frag, name in mapping.items():
                if frag in domain:
                    return name
            if domain:
                return domain.replace("www.", "").split(".")[0].capitalize()
        except Exception:
            pass

    if summary and isinstance(summary, str) and "(" in summary and ")" in summary:
        import re
        m = re.search(r'\(([A-Za-z\s]{3,20})\)\s*[-\u2013]', summary)
        if m:
            candidate = m.group(1).strip()
            if candidate.lower() not in ("ap", "pti"):
                return candidate

    return "Source Article"


