import sys
import os
sys.path.insert(0, os.path.abspath("."))
import unittest
from unittest.mock import MagicMock

# Mock streamlit session state and toast before importing notifications
class MockSessionState(dict):
    pass

import streamlit as st
st.session_state = MockSessionState()
st.toast = MagicMock()

import notifications
import edu_db

class TestNotifications(unittest.TestCase):
    def setUp(self):
        st.session_state.clear()
        st.toast.reset_mock()
        test_dir = os.path.join("scratch", "test_user_notif")
        os.makedirs(test_dir, exist_ok=True)
        edu_db.set_data_dir(test_dir, username="test_notif_user")
        edu_db.save_progress({"seen_notification_keys": []})

    def test_send_alert_deduplication(self):
        # 1. First alert should succeed
        success1 = notifications.send_alert("Test message 1", icon="🔔", notification_key="test_key_1", category="general")
        self.assertTrue(success1)
        self.assertEqual(st.toast.call_count, 1)

        # 2. Duplicate alert with same key in same session should be skipped
        success2 = notifications.send_alert("Test message 1 duplicate", icon="🔔", notification_key="test_key_1", category="general")
        self.assertFalse(success2)
        self.assertEqual(st.toast.call_count, 1)

    def test_session_cap(self):
        st.session_state.clear()
        st.toast.reset_mock()

        # Test news cap with limit of 2 per session
        notifications.NOTIFICATION_CONFIG["caps"]["max_news_alerts_per_session"] = 2
        res1 = notifications.send_alert("News 1", icon="⚡", notification_key="news_1", category="news")
        res2 = notifications.send_alert("News 2", icon="⚡", notification_key="news_2", category="news")
        res3 = notifications.send_alert("News 3", icon="⚡", notification_key="news_3", category="news")

        self.assertTrue(res1)
        self.assertTrue(res2)
        self.assertFalse(res3)  # Exceeds cap
        self.assertEqual(st.toast.call_count, 2)

if __name__ == '__main__':
    unittest.main()
