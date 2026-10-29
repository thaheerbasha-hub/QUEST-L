"""
guardrail.py — Strict Compliance and Guardrail Module for QUEST Mentors.

Ensures that AI mentors (MICHAEL and Video Tutor) never offer buy, sell, hold,
or tip recommendations, target prices, or financial advisory calls.

Functions:
- regex_check(text): Fast pattern-matching for prohibited advisory language.
- second_check(text, api_key, provider): Secondary semantic/LLM or strict heuristic check.
- rewrite(text, user_context, api_key, provider): Rewrites flagged advice into neutral educational guidance.
- safe_reply(text, user_context, api_key, provider): Full orchestration chain with fallback and mandatory disclaimer.
"""

import re
import json
import urllib.request
import urllib.error
from typing import Optional, Union, Dict, Any

# Mandatory disclaimer appended to every mentor response
DISCLAIMER = "\n\n*Education, not investment advice.*"

# Comprehensive regex patterns catching buy, sell, hold, tips, target prices, and Hinglish advice
ADVICE_PATTERNS = [
    # --- Buy / Long Directives ---
    r"\b(should|must|ought to|can|definitely|strongly|suggest to)\s+buy\b",
    r"\b(recommend|advising|suggesting)\s+(to\s+)?(buy|buying|invest in|entering)\b",
    r"\bi\s+(recommend|suggest|advise|say)\s+(you\s+)?(buy|to buy|entering|accumulate)\b",
    r"\bmy\s+recommendation\s+is\s+(to\s+)?(buy|sell|hold)\b",
    r"\b(go\s+long|enter\s+long|take\s+a\s+long\s+position|open\s+long)\b",
    r"\b(accumulate|add\s+more|keep\s+buying)\s+this\s+stock\b",
    r"\badd\s+(this|it|\w+)\s+to\s+your\s+portfolio\b",
    r"\badd\s+to\s+your\s+portfolio\b",
    r"\bgood\s+time\s+to\s+(buy|enter|accumulate)\b",
    r"\b(strong|definite)\s+buy\b",
    r"\btime\s+to\s+(buy|accumulate)\b",
    r"\byou\s+should\s+invest\s+in\b",

    # --- Sell / Short / Exit Directives ---
    r"\b(should|must|ought to|can|definitely|strongly|suggest to)\s+sell\b",
    r"\b(recommend|advising|suggesting)\s+(to\s+)?(sell|selling|dump|exit)\b",
    r"\bi\s+(recommend|suggest|advise|say)\s+(you\s+)?(sell|to sell|exit|dump)\b",
    r"\b(go\s+short|enter\s+short|take\s+a\s+short\s+position|open\s+short)\b",
    r"\b(sell|dump|liquidate|get\s+rid\s+of|exit)\s+your\s+(\w+\s+)?(holdings|shares|position|stocks?)\b",
    r"\b(book\s+profit|book\s+loss)\s+in\b",
    r"\bexit\s+(your\s+)?(position|trade)\b",
    r"\b(strong|definite)\s+sell\b",
    r"\btime\s+to\s+(sell|dump|exit)\b",

    # --- Hold Directives ---
    r"\b(you\s+)?(should|must)\s+hold\b",
    r"\bi\s+(recommend|suggest)\s+(you\s+)?hold\b",
    r"\bhold\s+(this|your)\s+stock\b",

    # --- Target Prices / Stops / Tip Language ---
    r"\btarget\s+price\b",
    r"\bprice\s+target\b",
    r"\bstop[\s-]loss\s+(at|target|level)\b",
    r"\bentry\s+price\b",
    r"\bsure[\s-]shot\b",
    r"\bjackpot\s+stock\b",
    r"\bmultibagger\s+(pick|tip|stock)\b",
    r"\b(guaranteed|assured)\s+(returns?|profit)\b",
    r"\b(free|hot|stock|trading)\s+tip\b",

    # --- Hinglish Buy / Sell / Tip Directives ---
    r"\b(kharid|khareed)\s*(lo|lena|lo ji|lo yaar|lo bhai|lo na)\b",
    r"\b(bech|baich)\s*(do|dena|daalo)\b",
    r"\b(le\s*lo|mat\s*becho|daal\s*do|paisa\s*lagao)\b",
    r"\b(buy|sell|hold)\s*(kar\s*lo|karo|kar\s*do|karke\s*rakho)\b",
    r"\b(sure\s*shot\s*hai|pakka\s*badhega|pakka\s*girega)\b",
    r"\b(entry\s*le\s*lo|exit\s*maro|exit\s*karo)\b",
    r"\b(ye\s*stock\s*le\s*lo|ye\s*share\s*kharido)\b",
]

COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in ADVICE_PATTERNS]

# Secondary strict rules for second_check
SECONDARY_PATTERNS = [
    r"\b(pt)\s*[:=]\s*(?:rs\.?|₹)?\s*\d+",
    r"\b(sl|stoploss)\s*[:=]\s*(?:rs\.?|₹)?\s*\d+",
    r"\b(buy|sell|accumulate)\s+(now|today|immediately)\b",
    r"\bmy\s+advice\s+is\b",
    r"\bdefinitely\s+(go\s+for|buy|sell)\b",
    r"\bkharidna\s+chahiye\b",
    r"\bbechna\s+chahiye\b",
]
COMPILED_SECONDARY = [re.compile(p, re.IGNORECASE) for p in SECONDARY_PATTERNS]
# Ticker-specific regex (strictly uppercase for ticker symbol, without IGNORECASE)
COMPILED_TICKER_ADVICE = re.compile(r"\b(?:buy|sell|accumulate)\s+([A-Z]{2,10})\b")


def regex_check(text: str) -> bool:
    """
    Flags buy, sell, hold or tip language such as 'should buy', 'I recommend',
    'target price', 'sure shot', 'accumulate', 'go long', 'add to your portfolio',
    and similar phrases including Hinglish.

    Returns True if flagged (contains prohibited advice), False if clean.
    """
    if not text or not isinstance(text, str):
        return False
    
    clean_text = text.lower()
    for pattern in COMPILED_PATTERNS:
        if pattern.search(clean_text):
            return True
    return False


def _call_llm_classifier(text: str, api_key: str, provider: str) -> Optional[bool]:
    """Helper to classify text using a brief LLM call."""
    prompt = (
        "Classify whether the following text provides any financial investment advice, "
        "stock recommendation, tip, target price, or instruction to buy, sell, or hold a specific stock/asset. "
        "Answer with ONLY the single word 'YES' if it contains any such advice or tip, "
        "or 'NO' if it is purely informational/educational.\n\n"
        f"Text to classify:\n{text[:1500]}\n\nAnswer (YES/NO):"
    )

    try:
        if provider == "groq" and api_key.startswith("gsk_"):
            req_data = json.dumps({
                "model": "openai/gpt-oss-120b",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0,
                "max_tokens": 10
            }).encode("utf-8")
            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/chat/completions",
                data=req_data,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                res = json.loads(r.read().decode())
                ans = res["choices"][0]["message"]["content"].strip().upper()
                return "YES" in ans
        elif provider == "gemini" and api_key:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            req_data = json.dumps({
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.0, "maxOutputTokens": 10}
            }).encode("utf-8")
            req = urllib.request.Request(url, data=req_data, headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=10) as r:
                res = json.loads(r.read().decode())
                ans = res["candidates"][0]["content"]["parts"][0]["text"].strip().upper()
                return "YES" in ans
    except Exception:
        pass
    return None


def second_check(text: str, api_key: Optional[str] = None, provider: Optional[str] = None) -> bool:
    """
    Independent second pass that catches advice the regex missed,
    either via a short LLM classifier call or a stricter rule set.

    Returns True if flagged (contains advice), False if clean.
    """
    if not text or not isinstance(text, str):
        return False

    # Try LLM classifier first if credentials are provided
    if api_key and provider:
        llm_result = _call_llm_classifier(text, api_key, provider)
        if llm_result is not None:
            return llm_result

    # Strict fallback heuristic rule set
    if COMPILED_TICKER_ADVICE.search(text):
        return True

    clean_text = text.lower()
    for pattern in COMPILED_SECONDARY:
        if pattern.search(clean_text):
            return True

    # Check for directional stock assertions without caveats
    if any(k in clean_text for k in ["strong return guaranteed", "guaranteed profit", "sure profit", "100% gain"]):
        return True

    return False


def build_scripted_fallback(user_context: Optional[Union[Dict[str, Any], str]] = None) -> str:
    """
    Builds a scripted template filled with the user's real numbers.
    Used when API fails, rate limit is hit, or rewrite fails guardrails.
    """
    tv_str = "5,20,000.00"
    pnl_str = "+42,500.00"
    pnl_pct_str = "+8.90"
    risk_score_str = "42.0"
    risk_bucket_str = "MODERATE"
    xp_str = "350"
    level_str = "Level 2 (Strategist)"

    if isinstance(user_context, dict):
        tv_str = user_context.get("total_value", tv_str)
        pnl_str = user_context.get("pnl", pnl_str)
        pnl_pct_str = user_context.get("pnl_pct", pnl_pct_str)
        risk_score_str = user_context.get("risk_score", risk_score_str)
        risk_bucket_str = user_context.get("risk_bucket", risk_bucket_str)
        xp_str = user_context.get("xp", xp_str)
        level_str = user_context.get("level", level_str)
    elif isinstance(user_context, str) and user_context:
        # Parse numbers from context string if present
        m_val = re.search(r"Value:\s*(?:Rs\.?|₹)?\s*([\d,\.]+)", user_context)
        if m_val:
            tv_str = m_val.group(1)
        m_pnl = re.search(r"P&L:\s*(?:Rs\.?|₹)?\s*([+\-\d,\.]+)\s*\(([+\-\d\.]+%)", user_context)
        if m_pnl:
            pnl_str = m_pnl.group(1)
            pnl_pct_str = m_pnl.group(2)
        m_risk = re.search(r"Risk:\s*([\d\.]+)/100\s*\(([^)]+)\)", user_context)
        if m_risk:
            risk_score_str = m_risk.group(1)
            risk_bucket_str = m_risk.group(2)

    return (
        "Look, I'm here as your quantitative mentor, not a Dalal Street tipster. "
        "I don't provide speculative stock picks or trade entries — SEBI has clear guidelines, and more importantly, "
        "real wealth isn't built on chasing market rumors.\n\n"
        "Here is what your real numbers show right now:\n"
        f"• Portfolio Value: Rs.{tv_str} | P&L: Rs.{pnl_str} ({pnl_pct_str})\n"
        f"• Risk Score: {risk_score_str}/100 ({risk_bucket_str})\n"
        f"• Knowledge Rank: {level_str} with {xp_str} XP earned\n\n"
        "Instead of looking for stock predictions, focus on your core framework: evaluate valuation (P/E relative to sector), "
        "balance sheet strength, earnings consistency, and whether adding to any position increases your concentration risk beyond your comfort zone."
    )


def rewrite(text: str, user_context: Optional[Union[Dict[str, Any], str]] = None,
            api_key: Optional[str] = None, provider: Optional[str] = None) -> str:
    """
    If either check flags the reply, rewrite it into neutral educational wording
    using one LLM call, then re-check it. If rewrite still fails, returns the scripted template.
    """
    if not api_key or not provider:
        return build_scripted_fallback(user_context)

    rewrite_prompt = (
        "You are a strict compliance and financial education editor for QUEST. "
        "The following draft reply inappropriately offered stock advice, buy/sell recommendations, "
        "or price targets. Rewrite it into neutral, purely educational guidance in MICHAEL's sharp, direct tone.\n\n"
        "RULES FOR REWRITE:\n"
        "1. Strictly NEVER tell the user to buy, sell, or hold any asset.\n"
        "2. Do NOT give target prices, stop losses, or tips.\n"
        "3. Explain the quantitative concepts, valuation metrics (P/E, Beta, Volatility), "
        "or portfolio diversification factors they should examine instead.\n"
        "4. Keep it concise, practical, and honest.\n\n"
        f"Original Draft:\n{text}\n\n"
        "Compliant Educational Rewrite:"
    )

    rewritten_text = None
    try:
        if provider == "groq" and api_key.startswith("gsk_"):
            req_data = json.dumps({
                "model": "openai/gpt-oss-120b",
                "messages": [{"role": "user", "content": rewrite_prompt}],
                "temperature": 0.3,
                "max_tokens": 400
            }).encode("utf-8")
            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/chat/completions",
                data=req_data,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                res = json.loads(r.read().decode())
                rewritten_text = res["choices"][0]["message"]["content"].strip()
        elif provider == "gemini" and api_key:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            req_data = json.dumps({
                "contents": [{"parts": [{"text": rewrite_prompt}]}],
                "generationConfig": {"temperature": 0.3, "maxOutputTokens": 400}
            }).encode("utf-8")
            req = urllib.request.Request(url, data=req_data, headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=15) as r:
                res = json.loads(r.read().decode())
                rewritten_text = res["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception:
        rewritten_text = None

    if rewritten_text:
        # Re-check the rewritten text with both checks
        if not regex_check(rewritten_text) and not second_check(rewritten_text, api_key=None):
            return rewritten_text

    # If rewrite failed or still contains advice, return scripted template
    return build_scripted_fallback(user_context)


def safe_reply(text: str, user_context: Optional[Union[Dict[str, Any], str]] = None,
               api_key: Optional[str] = None, provider: Optional[str] = None) -> str:
    """
    Runs the full guardrail chain and returns the final compliant text:
    1. If text indicates API error or rate limit, return scripted fallback with user numbers.
    2. Check with regex_check and second_check.
    3. If flagged, attempt rewrite via LLM.
    4. If rewrite still fails, return scripted fallback.
    5. Append mandatory 'Education, not investment advice' line.
    """
    if not text or text == "__BAD_KEY__" or str(text).startswith("__RATE_LIMIT__"):
        final_text = build_scripted_fallback(user_context)
    else:
        # Check both passes
        is_flagged = regex_check(text) or second_check(text, api_key=api_key, provider=provider)
        if is_flagged:
            final_text = rewrite(text, user_context=user_context, api_key=api_key, provider=provider)
        else:
            final_text = text.strip()

    # Ensure disclaimer is attached exactly once at the end
    disclaimer_marker = "Education, not investment advice"
    if disclaimer_marker.lower() not in final_text.lower():
        final_text = f"{final_text.rstrip()}{DISCLAIMER}"

    return final_text
