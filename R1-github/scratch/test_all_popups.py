import sys
import os
sys.path.insert(0, os.path.abspath("."))
import unittest
from unittest.mock import MagicMock

class MockSessionState(dict):
    pass

import streamlit as st
st.session_state = MockSessionState()
st.toast = MagicMock()

import notifications
import edu_db
import quest_app.tabs.badges as badges

class TestAllPopups(unittest.TestCase):
    def setUp(self):
        st.session_state.clear()
        st.toast.reset_mock()
        test_dir = os.path.join("scratch", "test_popups_user")
        os.makedirs(test_dir, exist_ok=True)
        edu_db.set_data_dir(test_dir, username="test_popup_user")
        edu_db.save_progress({
            "total_xp": 0,
            "streak": 0,
            "current_level": "Novice",
            "completed_levels": [],
            "seen_notification_keys": [],
            "badges": [],
        })

    def test_news_popup_with_empty_portfolio(self):
        # Even with empty holdings, benchmark intelligence news should fire toast
        fired = notifications.check_portfolio_news_alerts([], username="test_popup_user")
        self.assertGreater(len(fired), 0)
        self.assertGreaterEqual(st.toast.call_count, 1)

    def test_education_welcome_popup(self):
        notifications.render_education_alerts(username="test_popup_user")
        self.assertEqual(st.toast.call_count, 1)
        # Calling again in same session should deduplicate
        notifications.render_education_alerts(username="test_popup_user")
        self.assertEqual(st.toast.call_count, 1)

    def test_education_level_up_popup(self):
        # Level 1 min_xp is 0, Level 2 requires 350 XP
        st.toast.reset_mock()
        edu_db.award_xp(400, "quiz_pass")
        self.assertGreaterEqual(st.toast.call_count, 1)
        call_msg = st.toast.call_args[0][0]
        self.assertIn("Level Up", call_msg)

    def test_badge_unlocked_popup(self):
        st.toast.reset_mock()
        # Mock an evaluated badge
        mock_evaluated = [{
            "id": "first_lesson",
            "name": "First Step",
            "unlocked": True,
            "reward_xp": 50,
        }]
        user_data = {
            "prog": edu_db.load_progress(),
        }
        badges.sync_and_award_badge_xp(mock_evaluated, user_data)
        self.assertEqual(st.toast.call_count, 1)
        call_msg = st.toast.call_args[0][0]
        self.assertIn("Badge Unlocked", call_msg)

if __name__ == '__main__':
    unittest.main()
