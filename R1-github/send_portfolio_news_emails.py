"""
QUEST - Scheduled Portfolio News Email Dispatcher
=================================================
Standalone scheduled worker that dispatches email digests of market news
matching each user's active holdings.

Key Characteristics:
- Standalone execution (no Streamlit runtime dependencies or st.secrets).
- Strictly matches news using portfolio_news_matcher.get_matched_portfolio_news.
- Independent per-user deduplication in Firestore (users/{username}/data/news_notifications).
- At most ONE digest email per run per user (max MAX_ITEMS_PER_EMAIL articles).
- Links included ONLY if a genuine http(s) URL exists. Never invents URLs.
- Gmail SMTP SSL (port 465) or STARTTLS (port 587) with credentials from env vars only.
- CLI flags: --dry-run / -d (no email sent, no DB updates) and --user / -u (target specific user).
"""

import argparse
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json
import os
import re
import smtplib
import sys
from typing import Any, Dict, List, Tuple

# Ensure stdout and stderr handle UTF-8 characters gracefully on all operating systems (e.g. Windows cp1252)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import firebase_admin
from firebase_admin import credentials, firestore

from portfolio_news_matcher import get_matched_portfolio_news

# ──────────────────────────────────────────────────────────────────────────────
# Configurable Named Constants
# ──────────────────────────────────────────────────────────────────────────────

MAX_NEWS_AGE_HOURS: int = 24
MAX_ITEMS_PER_EMAIL: int = 5
MAX_ARTICLES_FETCHED: int = 30
MAX_EMAILED_KEY_HISTORY: int = 500
CRON_INTERVAL_HOURS: int = 3
DEFAULT_SMTP_HOST: str = "smtp.gmail.com"
DEFAULT_SMTP_PORT: int = 465


# ──────────────────────────────────────────────────────────────────────────────
# Firebase Admin Initialization (Standalone)
# ──────────────────────────────────────────────────────────────────────────────

def init_firebase_standalone():
    """
    Initialize Firebase Admin SDK for standalone CLI / cron execution.
    Checks:
    1. Already initialized app (firebase_admin.get_app())
    2. FIREBASE_SERVICE_ACCOUNT_KEY env var (JSON string or path to JSON file)
    3. .streamlit/firebase_key.json (local workspace development)
    """
    try:
        return firebase_admin.get_app()
    except ValueError:
        pass

    # 1. Environment variable (for GitHub Actions or production cron)
    env_key = os.environ.get("FIREBASE_SERVICE_ACCOUNT_KEY", "").strip()
    if env_key:
        if os.path.isfile(env_key):
            cred = credentials.Certificate(env_key)
            return firebase_admin.initialize_app(cred)
        try:
            key_dict = json.loads(env_key)
            if "private_key" in key_dict:
                key_dict["private_key"] = key_dict["private_key"].replace("\\n", "\n")
            cred = credentials.Certificate(key_dict)
            return firebase_admin.initialize_app(cred)
        except Exception as exc:
            print(f"[Warning] Failed parsing FIREBASE_SERVICE_ACCOUNT_KEY env var: {exc}", file=sys.stderr)

    # 2. Local fallback for development testing
    here = os.path.dirname(os.path.abspath(__file__))
    local_key = os.path.join(here, ".streamlit", "firebase_key.json")
    if os.path.exists(local_key):
        cred = credentials.Certificate(local_key)
        return firebase_admin.initialize_app(cred)

    raise RuntimeError(
        "Could not initialize Firebase Admin SDK. Please set FIREBASE_SERVICE_ACCOUNT_KEY "
        "environment variable or provide .streamlit/firebase_key.json."
    )


def get_firestore_db():
    """Returns initialized Firestore client."""
    init_firebase_standalone()
    return firestore.client()


# ──────────────────────────────────────────────────────────────────────────────
# News Freshness & Deduplication Helpers
# ──────────────────────────────────────────────────────────────────────────────

def is_within_max_age(article: dict, max_age_hours: int = MAX_NEWS_AGE_HOURS) -> bool:
    """Return True if article date is within max_age_hours."""
    raw = article.get("date") or article.get("pub_date") or ""
    if not raw:
        return True
    try:
        raw_str = str(raw).strip()
        pub = None

        # 1. Unix timestamp
        if re.match(r"^\d{9,13}$", raw_str):
            ts = int(raw_str)
            if ts > 1e10:
                ts //= 1000
            pub = datetime.fromtimestamp(ts, tz=timezone.utc)

        # 2. ISO 8601 string (handles .isoformat() with offsets, Z, microseconds)
        if pub is None:
            try:
                clean_iso = raw_str.replace("Z", "+00:00")
                pub = datetime.fromisoformat(clean_iso)
                if pub.tzinfo is None:
                    pub = pub.replace(tzinfo=timezone.utc)
            except Exception:
                pass

        # 3. Common RSS / HTTP date formats
        if pub is None:
            for fmt in (
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d",
                "%a, %d %b %Y %H:%M:%S %z",
                "%a, %d %b %Y %H:%M:%S GMT",
                "%d %b %Y %H:%M:%S",
            ):
                try:
                    pub = datetime.strptime(raw_str[:32], fmt)
                    if pub.tzinfo is None:
                        pub = pub.replace(tzinfo=timezone.utc)
                    break
                except ValueError:
                    continue

        if pub is None:
            return True

        cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=max_age_hours)
        return pub >= cutoff
    except Exception:
        return True


def article_email_key(article: dict) -> str:
    """
    Generate stable deduplication key for email channel.
    Uses 'email_' prefix to keep channel dedupe separate from popup channel.
    """
    url = (article.get("url") or article.get("link") or "").strip()
    title = (article.get("title") or "").strip()
    return f"email_{url if url else title}"


def is_valid_url(url: str | None) -> bool:
    """Check if URL is a genuine http(s) web link."""
    if not url or not isinstance(url, str):
        return False
    url = url.strip()
    return url.startswith("http://") or url.startswith("https://")


def get_emailed_keys(db, username: str) -> set[str]:
    """Retrieve keys of articles previously emailed to this user."""
    try:
        doc = db.collection("users").document(username).collection("data").document("news_notifications").get()
        if doc.exists:
            return set(doc.to_dict().get("emailed_article_keys", []))
    except Exception as exc:
        print(f"[Warning] Could not load emailed keys for {username}: {exc}")
    return set()


def record_emailed_keys(db, username: str, new_keys: list[str]) -> bool:
    """Persist newly emailed article keys in Firestore."""
    try:
        doc_ref = db.collection("users").document(username).collection("data").document("news_notifications")
        existing_doc = doc_ref.get()
        existing_keys = []
        if existing_doc.exists:
            existing_keys = existing_doc.to_dict().get("emailed_article_keys", [])
        combined = list(dict.fromkeys(existing_keys + new_keys))[-MAX_EMAILED_KEY_HISTORY:]
        doc_ref.set({
            "emailed_article_keys": combined,
            "last_email_sent_at": datetime.now(timezone.utc).isoformat(),
        }, merge=True)
        return True
    except Exception as exc:
        print(f"[Error] Failed saving emailed news keys for {username}: {exc}", file=sys.stderr)
        return False


def get_user_holdings(db, username: str) -> list:
    """Read holdings for given user from Firestore."""
    try:
        doc = db.collection("users").document(username).collection("data").document("holdings").get()
        if doc.exists:
            return doc.to_dict().get("holdings", [])
    except Exception as exc:
        print(f"[Warning] Could not load holdings for {username}: {exc}")
    return []


# ──────────────────────────────────────────────────────────────────────────────
# Email Formatting (HTML & Plain Text)
# ──────────────────────────────────────────────────────────────────────────────

def build_digest_content(display_name: str, articles: List[Dict[str, Any]]) -> Tuple[str, str]:
    """
    Build responsive HTML and plain-text email bodies.
    Links are rendered only if valid http(s) URL exists. Never invents URLs.
    Includes clear unsubscribe instructions referencing QUEST > Settings > Notifications.
    """
    date_str = datetime.now().strftime("%B %d, %Y")

    # Plain text version
    text_lines = [
        "QUEST PORTFOLIO NEWS DIGEST",
        f"Date: {date_str}",
        f"Hello {display_name},",
        "",
        "Here are the latest market headlines matching stocks in your active portfolio:",
        "=" * 60,
    ]

    for art in articles:
        ticker = art.get("matched_ticker", "PORTFOLIO")
        title = art.get("title", "")
        source = art.get("source_name", "Market News")
        url = (art.get("url") or art.get("link") or "").strip()
        summary = art.get("summary", "")

        text_lines.append(f"\n[{ticker}] {title}")
        text_lines.append(f"Source: {source}")
        if is_valid_url(url):
            text_lines.append(f"Read Story: {url}")
        if summary:
            clean_summary = summary.replace("\n", " ").strip()
            text_lines.append(f"Summary: {clean_summary[:200]}...")

    text_lines.append("\n" + "=" * 60)
    text_lines.append("Notification Preferences:")
    text_lines.append("You received this digest because email notifications are enabled.")
    text_lines.append("To adjust settings or unsubscribe, open QUEST > Settings > Notifications.")
    text_content = "\n".join(text_lines)

    # HTML cards
    items_html = []
    for art in articles:
        ticker = art.get("matched_ticker", "PORTFOLIO")
        title = art.get("title", "")
        source = art.get("source_name", "Market News")
        url = (art.get("url") or art.get("link") or "").strip()
        summary = (art.get("summary") or "").replace("\n", " ").strip()

        link_btn = ""
        if is_valid_url(url):
            link_btn = (
                f'<a href="{url}" target="_blank" rel="noopener noreferrer" '
                f'style="display:inline-block;margin-top:10px;padding:6px 14px;background:#1e293b;'
                f'color:#5DCAA5;font-size:12px;font-weight:600;text-decoration:none;'
                f'border-radius:6px;border:1px solid rgba(93,202,165,0.3);">'
                f'Read on {source} &rarr;</a>'
            )

        summary_p = ""
        if summary:
            summary_p = f'<p style="color:#94a3b8;font-size:13px;line-height:1.5;margin:0 0 10px 0;">{summary[:240]}...</p>'

        items_html.append(f"""
        <div style="background:#161922;border:1px solid #262e3d;border-left:4px solid #5DCAA5;border-radius:10px;padding:16px;margin-bottom:14px;">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                <span style="background:rgba(93,202,165,0.15);color:#5DCAA5;font-size:11px;font-weight:700;padding:2px 8px;border-radius:4px;letter-spacing:0.5px;">
                    {ticker}
                </span>
                <span style="color:#64748b;font-size:12px;">&bull; {source}</span>
            </div>
            <h3 style="color:#f1f5f9;font-size:15px;line-height:1.4;margin:0 0 8px 0;font-weight:600;">
                {title}
            </h3>
            {summary_p}
            {link_btn}
        </div>
        """)

    articles_block = "\n".join(items_html)

    html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>QUEST Portfolio News Digest</title>
</head>
<body style="margin:0;padding:24px 0;background-color:#0d0e12;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
<div style="max-width:620px;margin:0 auto;background:#111318;border:1px solid #232733;border-radius:16px;overflow:hidden;box-shadow:0 12px 36px rgba(0,0,0,0.6);">
    <!-- Header -->
    <div style="background:linear-gradient(135deg, #161a24 0%, #1c2230 100%);padding:24px;border-bottom:1px solid #232733;">
        <div style="font-size:20px;font-weight:800;color:#f8fafc;letter-spacing:-0.5px;">
            <span style="color:#5DCAA5;">&#9889;</span> QUEST
        </div>
        <div style="font-size:12px;color:#64748b;margin-top:2px;">Quantitative Unified Equity Surveillance Tracker</div>
        <div style="margin-top:16px;font-size:15px;color:#f1f5f9;font-weight:600;">
            Portfolio Market Intelligence &bull; {date_str}
        </div>
        <div style="font-size:13px;color:#94a3b8;margin-top:4px;">
            Hello <strong>{display_name}</strong>, here are latest headlines matching your active stock holdings.
        </div>
    </div>

    <!-- Articles List -->
    <div style="padding:24px;">
        {articles_block}
    </div>

    <!-- Footer -->
    <div style="padding:20px 24px;background:#0d0e12;border-top:1px solid #232733;font-size:11px;color:#64748b;line-height:1.6;">
        <p style="margin:0 0 6px 0;">
            <strong>Notification Preferences:</strong> You received this digest because email notifications are enabled for your portfolio.
        </p>
        <p style="margin:0;">
            To unsubscribe or adjust delivery preferences, open <strong>QUEST &rarr; Settings &rarr; Notifications</strong>.
        </p>
    </div>
</div>
</body>
</html>"""

    return html_content, text_content


# ──────────────────────────────────────────────────────────────────────────────
# SMTP Delivery
# ──────────────────────────────────────────────────────────────────────────────

def send_email_smtp(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: str,
    dry_run: bool = False,
) -> bool:
    """
    Sends email via SMTP (Gmail App Password, port 465 SSL or port 587 STARTTLS).
    All configuration is read from environment variables.
    """
    if dry_run:
        print(f"    [Dry-Run SMTP] Would dispatch to: {to_email}")
        print(f"    [Dry-Run SMTP] Subject: {subject}")
        return True

    smtp_host = os.environ.get("SMTP_HOST", DEFAULT_SMTP_HOST).strip()
    smtp_port_raw = os.environ.get("SMTP_PORT", str(DEFAULT_SMTP_PORT)).strip()
    try:
        smtp_port = int(smtp_port_raw)
    except ValueError:
        smtp_port = DEFAULT_SMTP_PORT

    smtp_user = os.environ.get("SMTP_USER", "").strip()
    smtp_pass = os.environ.get("SMTP_PASSWORD", "").strip()
    from_addr = os.environ.get("EMAIL_FROM", "").strip() or smtp_user

    if not smtp_user or not smtp_pass:
        print(
            "[Configuration Error] SMTP_USER and SMTP_PASSWORD environment variables are required to send emails.",
            file=sys.stderr,
        )
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = to_email

        part1 = MIMEText(text_content, "plain", "utf-8")
        part2 = MIMEText(html_content, "html", "utf-8")
        msg.attach(part1)
        msg.attach(part2)

        if smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=20) as server:
                server.login(smtp_user, smtp_pass)
                server.sendmail(from_addr, [to_email], msg.as_string())
        else:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(from_addr, [to_email], msg.as_string())

        print(f"    [Success] Delivered email digest to {to_email} via {smtp_host}:{smtp_port}")
        return True
    except Exception as exc:
        print(f"    [SMTP Error] Delivery failed to {to_email}: {exc}", file=sys.stderr)
        return False


# ──────────────────────────────────────────────────────────────────────────────
# Main Processing Flow
# ──────────────────────────────────────────────────────────────────────────────

def process_portfolio_news_emails(dry_run: bool = False, target_user: str | None = None) -> dict:
    """
    Main scheduled execution:
    1. Initializes Firebase Admin SDK.
    2. Streams users from Firestore.
    3. Respects user opt-in (email_notifications).
    4. Fetches active holdings and runs shared portfolio news matcher.
    5. Filters fresh (<= MAX_NEWS_AGE_HOURS) and deduplicates against Firestore history.
    6. Sends at most ONE digest email per user with up to MAX_ITEMS_PER_EMAIL articles.
    7. Updates sent history in Firestore (unless dry-run).
    8. Handles errors per user so one user's failure never blocks others.
    """
    db = get_firestore_db()

    print("=" * 70)
    print(f"QUEST Portfolio News Email Dispatcher")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print(f"Dry-Run Mode: {dry_run}")
    if target_user:
        print(f"Targeting single user: {target_user}")
    print("=" * 70)

    users_ref = db.collection("users")
    if target_user:
        user_docs = [users_ref.document(target_user).get()]
    else:
        user_docs = list(users_ref.stream())

    stats = {
        "users_examined": 0,
        "users_skipped_no_email": 0,
        "users_skipped_opt_out": 0,
        "users_skipped_no_holdings": 0,
        "users_skipped_no_news": 0,
        "users_skipped_all_deduped": 0,
        "emails_dispatched": 0,
        "user_errors": 0,
    }

    for u_doc in user_docs:
        stats["users_examined"] += 1
        username = u_doc.id

        if not u_doc.exists:
            print(f"[-] User '{username}' doc not found.")
            continue

        try:
            profile = u_doc.to_dict() or {}

            # 1. Check registered email
            email = (profile.get("email") or "").strip()
            if not email or "@" not in email:
                print(f"[-] User '{username}': skipped (no valid registered email)")
                stats["users_skipped_no_email"] += 1
                continue

            # 2. Check notification preference
            email_enabled = profile.get("email_notifications", True)
            if not email_enabled:
                print(f"[-] User '{username}': skipped (email notifications disabled in settings)")
                stats["users_skipped_opt_out"] += 1
                continue

            # 3. Read holdings
            holdings = get_user_holdings(db, username)
            if not holdings:
                print(f"[-] User '{username}': skipped (no active portfolio holdings)")
                stats["users_skipped_no_holdings"] += 1
                continue

            # 4. Read already emailed keys from Firestore
            already_emailed = get_emailed_keys(db, username)

            # 5. Strictly match news against holdings via shared matcher
            matched = get_matched_portfolio_news(holdings, max_articles=MAX_ARTICLES_FETCHED)
            if not matched:
                print(f"[-] User '{username}': skipped (no news matched {len(holdings)} holdings)")
                stats["users_skipped_no_news"] += 1
                continue

            # 6. Apply freshness filter (<= MAX_NEWS_AGE_HOURS)
            fresh_articles = [a for a in matched if is_within_max_age(a, MAX_NEWS_AGE_HOURS)]
            if not fresh_articles:
                print(f"[-] User '{username}': skipped (all {len(matched)} matched articles are older than {MAX_NEWS_AGE_HOURS}h)")
                stats["users_skipped_no_news"] += 1
                continue

            # 7. Deduplicate against previously emailed keys
            unsent_articles = []
            new_keys = []
            for art in fresh_articles:
                key = article_email_key(art)
                if key not in already_emailed:
                    unsent_articles.append(art)
                    new_keys.append(key)

            if not unsent_articles:
                print(f"[-] User '{username}': skipped (all {len(fresh_articles)} fresh articles already emailed)")
                stats["users_skipped_all_deduped"] += 1
                continue

            # Cap digest to top MAX_ITEMS_PER_EMAIL
            digest_articles = unsent_articles[:MAX_ITEMS_PER_EMAIL]
            keys_to_save = new_keys[:MAX_ITEMS_PER_EMAIL]

            display_name = profile.get("display_name") or username
            subject = f"[QUEST Digest] Portfolio updates ({len(digest_articles)} stories)"

            print(f"[+] User '{username}' ({email}): {len(digest_articles)} new matching article(s) found.")
            for art in digest_articles:
                print(f"    * [{art.get('matched_ticker')}] {art.get('title')} ({art.get('source_name')})")

            html_body, text_body = build_digest_content(display_name, digest_articles)

            # 8. Send digest email
            sent = send_email_smtp(
                to_email=email,
                subject=subject,
                html_content=html_body,
                text_content=text_body,
                dry_run=dry_run,
            )

            if sent:
                stats["emails_dispatched"] += 1
                if not dry_run:
                    record_emailed_keys(db, username, keys_to_save)
                    print(f"    [Saved] Recorded {len(keys_to_save)} deduplication key(s) in Firestore for '{username}'.")

        except Exception as exc:
            stats["user_errors"] += 1
            print(f"[!] Error processing user '{username}': {exc}", file=sys.stderr)
            continue

    print("-" * 70)
    print("Dispatch Summary:")
    print(f"  Users examined:            {stats['users_examined']}")
    print(f"  Skipped (no email):        {stats['users_skipped_no_email']}")
    print(f"  Skipped (opted out):       {stats['users_skipped_opt_out']}")
    print(f"  Skipped (no holdings):     {stats['users_skipped_no_holdings']}")
    print(f"  Skipped (no fresh news):   {stats['users_skipped_no_news']}")
    print(f"  Skipped (all deduped):     {stats['users_skipped_all_deduped']}")
    print(f"  Digests sent (or dry-run): {stats['emails_dispatched']}")
    print(f"  User processing errors:    {stats['user_errors']}")
    print("=" * 70)

    return stats


# ──────────────────────────────────────────────────────────────────────────────
# CLI Entrypoint
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="QUEST Portfolio News Email Dispatcher")
    parser.add_argument(
        "--dry-run", "-d",
        action="store_true",
        help="Print digest plan and email content preview without sending emails or updating Firestore",
    )
    parser.add_argument(
        "--user", "-u",
        type=str,
        default=None,
        help="Target a specific username for testing",
    )
    args = parser.parse_args()

    process_portfolio_news_emails(dry_run=args.dry_run, target_user=args.user)
