import sys
import os
sys.path.insert(0, os.path.abspath("."))
import unittest

class MockAsset:
    def __init__(self, identifier, name, quantity=10):
        self.identifier = identifier
        self.name = name
        self.quantity = quantity

class TestPortfolioNewsMatcher(unittest.TestCase):
    def test_empty_holdings_never_matches(self):
        # Empty holdings must return 0 matches and never fall back to generic news
        from portfolio_news_matcher import get_matched_portfolio_news
        matches = get_matched_portfolio_news(holdings=[], articles=[
            {"title": "Nifty surges 500 points", "url": "https://example.com/nifty", "ticker": "^NSEI"},
            {"title": "Reliance Q2 results", "url": "https://example.com/rel", "ticker": "RELIANCE.NS"}
        ])
        self.assertEqual(len(matches), 0)

    def test_ticker_format_variations(self):
        from portfolio_news_matcher import is_article_matching_holding
        # Holding with .NS suffix
        holding = MockAsset("RELIANCE.NS", "Reliance Industries")
        
        # Article with clean ticker
        art1 = {"title": "Company profits grow", "ticker": "RELIANCE", "url": "https://example.com/1"}
        match, ticker, reason = is_article_matching_holding(art1, holding)
        self.assertTrue(match)
        self.assertEqual(ticker, "RELIANCE")

        # Article with lower-case ticker
        art2 = {"title": "Company profits grow", "ticker": "reliance.ns", "url": "https://example.com/2"}
        match, ticker, reason = is_article_matching_holding(art2, holding)
        self.assertTrue(match)

    def test_company_name_and_aliases(self):
        from portfolio_news_matcher import is_article_matching_holding
        # Holding with alias in parentheses
        holding = {"identifier": "ETERNAL.NS", "name": "Eternal (Zomato)", "quantity": 10}
        
        # Article mentioning Zomato in title
        art1 = {"title": "Zomato launches new high-speed delivery service in Delhi", "ticker": "", "url": "https://example.com/zom"}
        match, ticker, reason = is_article_matching_holding(art1, holding)
        self.assertTrue(match)
        self.assertEqual(ticker, "ETERNAL")

        # Holding with multi-word name
        holding2 = {"identifier": "TATASTEEL.NS", "name": "Tata Steel", "quantity": 10}
        art2 = {"title": "Tata Steel inaugurates hydrogen plant in UK", "ticker": "", "url": "https://example.com/ts"}
        match, ticker, reason = is_article_matching_holding(art2, holding2)
        self.assertTrue(match)
        self.assertEqual(ticker, "TATASTEEL")

    def test_negative_matching_non_held_stocks(self):
        from portfolio_news_matcher import is_article_matching_holding
        holding = MockAsset("RELIANCE.NS", "Reliance Industries")
        
        # News about TCS or Infosys should NOT match Reliance holding
        art = {"title": "TCS reports 12% revenue increase in Q2", "ticker": "TCS.NS", "url": "https://example.com/tcs"}
        match, _, _ = is_article_matching_holding(art, holding)
        self.assertFalse(match)

if __name__ == '__main__':
    unittest.main()
