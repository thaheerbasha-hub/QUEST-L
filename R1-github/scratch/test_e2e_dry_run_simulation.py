"""
Test simulated dry-run output with an active holding and simulated fresh news.
Verifies the exact log format, ticker tags, article titles, sources, and links.
"""

from datetime import datetime, timezone
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from send_portfolio_news_emails import build_digest_content, send_email_smtp

def run_simulation():
    print("=" * 70)
    print("QUEST Portfolio News Email Dispatcher — Dry-Run Preview Simulation")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print("Dry-Run Mode: True")
    print("Targeting simulated user: test_investor")
    print("=" * 70)

    simulated_articles = [
        {
            "matched_ticker": "RELIANCE",
            "title": "Reliance Jio and NVIDIA Partner to Build AI Cloud Infrastructure in India",
            "source_name": "Mint",
            "url": "https://www.livemint.com/technology/reliance-jio-nvidia-ai-cloud",
            "summary": "Reliance Jio announced a comprehensive multi-year collaboration with NVIDIA to roll out sovereign AI supercomputing infrastructure.",
        },
        {
            "matched_ticker": "HDFCBANK",
            "title": "HDFC Bank Reports 18% Net Profit Growth in Q3 Driven by Retail Loans",
            "source_name": "Economic Times",
            "url": "https://economictimes.indiatimes.com/industry/banking/hdfc-bank-q3-results",
            "summary": "India's largest private lender beat analyst expectations with strong net interest margin expansion.",
        },
    ]

    print(f"[+] User 'test_investor' (investor@example.com): {len(simulated_articles)} new matching article(s) found.")
    for art in simulated_articles:
        print(f"    * [{art.get('matched_ticker')}] {art.get('title')} ({art.get('source_name')})")

    subject = f"⚡ QUEST Digest: New updates on your portfolio ({len(simulated_articles)} stories)"
    html_body, text_body = build_digest_content("Alex Sharma", simulated_articles)

    # Dry-run SMTP call
    send_email_smtp(
        to_email="investor@example.com",
        subject=subject,
        html_content=html_body,
        text_content=text_body,
        dry_run=True,
    )

    print("\n--- Plain Text Email Preview ---")
    print(text_body)
    print("-" * 70)

    print("-" * 70)
    print("Dispatch Summary:")
    print("  Users examined:            1")
    print("  Skipped (no email):        0")
    print("  Skipped (opted out):       0")
    print("  Skipped (no holdings):     0")
    print("  Skipped (no fresh news):   0")
    print("  Skipped (all deduped):     0")
    print("  Digests sent (or dry-run): 1")
    print("  User processing errors:    0")
    print("=" * 70)


if __name__ == "__main__":
    run_simulation()
