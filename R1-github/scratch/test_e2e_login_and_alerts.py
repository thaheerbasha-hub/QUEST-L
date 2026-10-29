import sys
import os
sys.path.insert(0, os.path.abspath("."))
import unittest
from unittest.mock import MagicMock
import tempfile
import shutil

class MockSessionState(dict):
    pass

import streamlit as st
st.session_state = MockSessionState()
st.toast = MagicMock()

import edu_db
import notifications

class TestE2ELoginAndAlerts(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        edu_db.set_data_dir(self.test_dir, username="test_user")
        st.session_state.clear()
        st.toast.reset_mock()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_daily_login_and_streak_progression(self):
        # Day 1: First login
        prog = edu_db.load_progress()
        prog["activity_dates"] = ["2026-10-01"]
        edu_db.save_progress(prog)
        streak, is_new = edu_db.record_daily_login("test_user")
        
        # Test simulated sequence with calculate_streak
        # Simulated Day 1
        s1 = edu_db.calculate_streak(["2026-10-01"], today_str="2026-10-01")
        self.assertEqual(s1, 1)

        # Simulated Day 2
        s2 = edu_db.calculate_streak(["2026-10-01", "2026-10-02"], today_str="2026-10-02")
        self.assertEqual(s2, 2)

        # Simulated Day 3 (consecutive)
        s3 = edu_db.calculate_streak(["2026-10-01", "2026-10-02", "2026-10-03"], today_str="2026-10-03")
        self.assertEqual(s3, 3)

        # Day 4 missed, logging in on Day 5
        s5 = edu_db.calculate_streak(["2026-10-01", "2026-10-02", "2026-10-03", "2026-10-05"], today_str="2026-10-05")
        self.assertEqual(s5, 1) # Reset to 1

        # Day 5 was active, Day 6 morning (grace period before login on Day 6)
        s6_grace = edu_db.calculate_streak(["2026-10-05"], today_str="2026-10-06")
        self.assertEqual(s6_grace, 1)

    def test_news_alert_matching_and_deduplication(self):
        class MockAsset:
            def __init__(self, identifier, name):
                self.identifier = identifier
                self.name = name

        assets = [MockAsset("RELIANCE.NS", "Reliance Industries")]

        # Mock news archive in news_sentiment
        import news_sentiment
        original_get_archive = news_sentiment.get_archived_articles
        news_sentiment.get_archived_articles = lambda: {
            "RELIANCE.NS": [
                {
                    "title": "Reliance Q2 Profit Jumps 15% On Strong Retail Growth",
                    "url": "https://example.com/reliance-q2",
                    "date": "2026-10-22"
                }
            ],
            "TCS.NS": [
                {
                    "title": "TCS Wins Mega Deal",
                    "url": "https://example.com/tcs-deal",
                    "date": "2026-10-22"
                }
            ]
        }

        try:
            # 1. Trigger news alert
            fired = notifications.check_portfolio_news_alerts(assets, username="test_user")
            self.assertEqual(len(fired), 1)
            self.assertIn("Reliance Q2 Profit", fired[0])
            self.assertEqual(st.toast.call_count, 1)
            call_msg = st.toast.call_args[0][0]
            self.assertIn("RELIANCE", call_msg)
            self.assertIn("Reliance Q2 Profit Jumps 15%", call_msg)

            # 2. Re-trigger in same session -> Deduplicated by session
            fired_again = notifications.check_portfolio_news_alerts(assets, username="test_user")
            self.assertEqual(len(fired_again), 0)
            self.assertEqual(st.toast.call_count, 1)

            # 3. Simulate new session: persistent storage in edu_progress.json must prevent duplicate
            st.session_state.clear()
            st.toast.reset_mock()
            fired_new_session = notifications.check_portfolio_news_alerts(assets, username="test_user")
            self.assertEqual(len(fired_new_session), 0)
            self.assertEqual(st.toast.call_count, 0)
        finally:
            news_sentiment.get_archived_articles = original_get_archive

if __name__ == '__main__':
    unittest.main()
