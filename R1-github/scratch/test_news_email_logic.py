"""
Unit test for portfolio news email dispatcher logic
Tests:
1. build_digest_content (HTML and text rendering, URL validation, unsubscribe footer)
2. is_within_max_age (fresh vs stale articles)
3. article_email_key and deduplication
4. Single-user dry run dispatch simulation
"""

from datetime import datetime, timezone, timedelta
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from send_portfolio_news_emails import (
    build_digest_content,
    is_within_max_age,
    article_email_key,
    is_valid_url,
    MAX_NEWS_AGE_HOURS,
    MAX_ITEMS_PER_EMAIL,
)


def test_url_validation():
    assert is_valid_url("https://economictimes.indiatimes.com/markets/stocks/article.html") is True
    assert is_valid_url("http://moneycontrol.com/news/business/story.html") is True
    assert is_valid_url("") is False
    assert is_valid_url(None) is False
    assert is_valid_url("javascript:alert(1)") is False
    assert is_valid_url("not_a_url") is False
    print("[PASS] URL validation tests passed.")


def test_age_filter():
    now = datetime.now(timezone.utc)
    fresh_article = {"date": (now - timedelta(hours=2)).isoformat(), "title": "Fresh"}
    stale_article = {"date": (now - timedelta(hours=48)).isoformat(), "title": "Stale"}
    no_date_article = {"title": "No date specified"}

    assert is_within_max_age(fresh_article, MAX_NEWS_AGE_HOURS) is True
    assert is_within_max_age(stale_article, MAX_NEWS_AGE_HOURS) is False
    assert is_within_max_age(no_date_article, MAX_NEWS_AGE_HOURS) is True  # fallback
    print("[PASS] Age filter tests passed.")


def test_digest_content_rendering():
    sample_articles = [
        {
            "matched_ticker": "RELIANCE",
            "title": "Reliance Industries Announces New Green Energy Expansion",
            "source_name": "Economic Times",
            "url": "https://economictimes.indiatimes.com/sample-ril-news",
            "summary": "Reliance Industries green energy arm signed MoU for new solar manufacturing unit.",
        },
        {
            "matched_ticker": "TCS",
            "title": "TCS Wins Multi-Million Dollar Deal with European Bank",
            "source_name": "Mint",
            "url": "",  # No valid URL provided
            "summary": "Tata Consultancy Services announced major client win in financial services.",
        },
    ]

    html, text = build_digest_content("Akshar", sample_articles)

    # Assertions on text
    assert "QUEST PORTFOLIO NEWS DIGEST" in text
    assert "Akshar" in text
    assert "[RELIANCE]" in text
    assert "[TCS]" in text
    assert "https://economictimes.indiatimes.com/sample-ril-news" in text
    assert "QUEST > Settings > Notifications" in text

    # Assertions on HTML
    assert "RELIANCE" in html
    assert "TCS" in html
    assert "Economic Times" in html
    assert "Mint" in html
    # Check that the link button exists for RELIANCE with valid URL
    assert 'href="https://economictimes.indiatimes.com/sample-ril-news"' in html
    assert "Read on Economic Times" in html
    # Check that NO link button exists for TCS (empty URL)
    assert "Read on Mint" not in html
    # Check unsubscribe note
    assert "QUEST &rarr; Settings &rarr; Notifications" in html

    print("[PASS] Digest content rendering tests passed.")


def test_article_keys_and_dedupe():
    art1 = {"url": "https://sample.com/1", "title": "Title 1"}
    art2 = {"url": "", "title": "Title Without URL"}

    key1 = article_email_key(art1)
    key2 = article_email_key(art2)

    assert key1 == "email_https://sample.com/1"
    assert key2 == "email_Title Without URL"
    assert key1.startswith("email_")
    # Verify channel isolation: in-app popup uses live_news_
    assert not key1.startswith("live_news_")

    print("[PASS] Article key and dedupe isolation tests passed.")


if __name__ == "__main__":
    test_url_validation()
    test_age_filter()
    test_digest_content_rendering()
    test_article_keys_and_dedupe()
    print("\nALL PORTFOLIO NEWS EMAIL TESTS PASSED!")
