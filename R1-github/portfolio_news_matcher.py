"""
QUEST Portfolio News Matcher
============================
Shared module for strictly matching news items to a user's held stocks.
Used identically by:
1. In-app alerts (quest_app/main.py & notifications.py)
2. Scheduled email digest delivery (send_portfolio_news_emails.py)
"""

import re
from typing import Any

# Suffixes to strip when finding base company keywords
CORP_SUFFIXES = [
    r"\bltd\b\.?",
    r"\blimited\b",
    r"\bcorp\b\.?",
    r"\bcorporation\b",
    r"\bindustries\b",
    r"\bservices\b",
    r"\bholdings\b",
    r"\benterprises\b",
    r"\bco\b\.?",
    r"\bcompany\b",
]

# Common aliases for popular Indian equities
KNOWN_ALIASES = {
    "JIOFIN": ["jio financial", "jfsl", "jio-blackrock", "jio blackrock"],
    "ETERNAL": ["zomato", "blinkit", "eternal"],
    "RELIANCE": ["reliance", "ril", "jio", "reliance retail"],
    "TATASTEEL": ["tata steel"],
    "TATAMOTORS": ["tata motors", "jaguar land rover", "jlr"],
    "HDFCBANK": ["hdfc bank", "hdfc"],
    "ICICIBANK": ["icici bank", "icici"],
    "SBIN": ["state bank of india", "sbi"],
    "INFY": ["infosys"],
    "TCS": ["tata consultancy services", "tcs"],
    "BHARTIARTL": ["bharti airtel", "airtel"],
    "IRCTC": ["irctc", "indian railway catering"],
    "RECLTD": ["rec limited", "rural electrification corporation"],
    "BEL": ["bharat electronics", "bel"],
}


def extract_holding_profile(holding: Any) -> dict | None:
    """
    Extracts standardized matching tokens from a holding (Asset object or dict).
    Returns None if holding is invalid or has 0 quantity.
    """
    if holding is None:
        return None

    # Handle both Asset object and dictionary
    if isinstance(holding, dict):
        ident = str(holding.get("identifier") or "").strip()
        name = str(holding.get("name") or "").strip()
        qty = float(holding.get("quantity", 1) or 0)
    else:
        ident = str(getattr(holding, "identifier", "") or "").strip()
        name = str(getattr(holding, "name", "") or "").strip()
        qty = float(getattr(holding, "quantity", 1) or 0)

    if not ident and not name:
        return None
    if qty <= 0:
        return None

    # Clean ticker: e.g. "RELIANCE.NS" -> "RELIANCE"
    clean_ticker = ident.upper().split(".")[0].strip() if ident else ""
    full_ident = ident.upper()

    # Collect aliases & search tokens
    tokens = set()
    if clean_ticker:
        tokens.add(clean_ticker.lower())

    if name:
        clean_name = name.lower()
        tokens.add(clean_name)

        # Extract words inside parentheses e.g. "Eternal (Zomato)" -> "zomato"
        paren_matches = re.findall(r"\((.*?)\)", name)
        for pm in paren_matches:
            pm_clean = pm.strip().lower()
            if len(pm_clean) >= 3:
                tokens.add(pm_clean)

        # Base name without corporate suffixes
        base_name = clean_name
        for suff in CORP_SUFFIXES:
            base_name = re.sub(suff, "", base_name, flags=re.IGNORECASE).strip()
        if len(base_name) >= 3:
            tokens.add(base_name)

    # Add known dictionary aliases
    if clean_ticker in KNOWN_ALIASES:
        for al in KNOWN_ALIASES[clean_ticker]:
            tokens.add(al.lower())

    return {
        "identifier": full_ident,
        "clean_ticker": clean_ticker,
        "name": name,
        "tokens": [t for t in tokens if len(t) >= 3],
    }


def is_article_matching_holding(article: dict, holding: Any) -> tuple[bool, str, str]:
    """
    Checks if an article strictly matches a specific holding.
    
    Returns:
        (is_match: bool, matched_ticker: str, matched_reason: str)
    """
    profile = extract_holding_profile(holding)
    if not profile:
        return False, "", ""

    clean_ticker = profile["clean_ticker"]
    ident = profile["identifier"]
    name = profile["name"]

    # 1. Match direct ticker field in article metadata
    art_ticker = str(article.get("ticker", "")).strip().upper()
    if art_ticker:
        clean_art_ticker = art_ticker.split(".")[0].strip()
        if clean_art_ticker == clean_ticker or art_ticker == ident:
            return True, clean_ticker, "direct_ticker"

    # 2. Match stock_name in article metadata
    art_stock_name = str(article.get("stock_name", "")).strip().lower()
    if art_stock_name and name:
        if art_stock_name in name.lower() or name.lower() in art_stock_name:
            return True, clean_ticker, "stock_name_metadata"

    title = str(article.get("title", "")).strip()
    title_lower = title.lower()
    title_upper = title.upper()
    summary = str(article.get("summary", "")).strip().lower()

    # 3. Match ticker symbol in headline (word boundary)
    if clean_ticker and len(clean_ticker) >= 3:
        if re.search(r"\b" + re.escape(clean_ticker) + r"\b", title_upper):
            return True, clean_ticker, "ticker_in_headline"

    # 4. Match search tokens & aliases in headline
    for token in profile["tokens"]:
        if re.search(r"\b" + re.escape(token) + r"\b", title_lower):
            return True, clean_ticker, f"alias_in_headline:{token}"

    # 5. Match full company name or alias in summary (strict: requires len >= 4)
    for token in profile["tokens"]:
        if len(token) >= 5 and re.search(r"\b" + re.escape(token) + r"\b", summary):
            return True, clean_ticker, f"alias_in_summary:{token}"

    return False, "", ""


def get_matched_portfolio_news(holdings: list, articles: list | None = None,
                               max_articles: int = 15) -> list[dict]:
    """
    Filters a list of articles strictly against a user's holdings.
    
    CRITICAL RULES:
    1. If user has no holdings (or empty portfolio), returns empty list [].
       NEVER falls back to generic, macro, or random benchmark news.
    2. Only includes news items that genuinely match a stock the user holds.
    3. Attaches clean 'matched_ticker' and 'source_name' to each matched item.
    """
    if not holdings:
        return []

    # Filter out invalid / 0 quantity holdings
    valid_profiles = [extract_holding_profile(h) for h in holdings]
    valid_profiles = [p for p in valid_profiles if p is not None]
    if not valid_profiles:
        return []

    # If articles not provided, pull from local news archive
    if articles is None:
        try:
            import news_sentiment
            archive = news_sentiment.get_archived_articles()
            raw_articles = []
            for ticker, arts in archive.items():
                for a in arts:
                    item = dict(a)
                    if "ticker" not in item:
                        item["ticker"] = ticker
                    raw_articles.append(item)
            articles = raw_articles
        except Exception:
            articles = []

    if not articles:
        return []

    seen_urls = set()
    matched_results = []

    for art in articles:
        if not isinstance(art, dict):
            continue
        title = art.get("title", "").strip()
        url = art.get("url") or art.get("link", "") or ""
        if not title:
            continue

        # Deduplicate within this fetch run
        unique_key = url if url else title
        if unique_key in seen_urls:
            continue

        # Check against each holding
        for profile in valid_profiles:
            is_match, matched_ticker, reason = is_article_matching_holding(art, profile)
            if is_match:
                seen_urls.add(unique_key)
                enriched_article = dict(art)
                enriched_article["matched_ticker"] = matched_ticker
                enriched_article["matched_company"] = profile["name"]
                enriched_article["url"] = url
                enriched_article["link"] = url
                
                # Ensure source_name is available
                from notifications import extract_source_name
                provider = art.get("provider") or art.get("source_name")
                enriched_article["source_name"] = extract_source_name(provider, url, art.get("summary", ""))

                matched_results.append(enriched_article)
                break

        if len(matched_results) >= max_articles:
            break

    return matched_results
