"""
ai_brain.py
===========
The AI analysis engine using Google Gemini.
Implements:
1. Self-questioning (Devil's Advocate)
2. Evidence trace on every claim
3. Geopolitical context interpretation
4. Leader statement pattern awareness
5. Confidence scoring with rationale

The AI EXPLAINS the deterministic scores — it doesn't invent them.
"""

from google import genai
from google.genai import types
import json
import re
import time
from config import AI_SETTINGS

# ---------------------------------------------------------------
# SETUP GEMINI
# ---------------------------------------------------------------

def setup_gemini(api_key):
    """Initialise Gemini with your API key."""
    client = genai.Client(api_key=api_key)
    return client

def call_gemini(client, prompt, max_retries=3):
    """
    Calls Gemini with retry logic.
    If Gemini fails, returns a structured error response.
    """
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=AI_SETTINGS["model"],
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=AI_SETTINGS["temperature"],
                    max_output_tokens=AI_SETTINGS["max_tokens"],
                )
            )
            return response.text
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "quota" in error_msg.lower():
                print(f"  ⚠ Rate limit hit. Waiting 60 seconds... (attempt {attempt+1})")
                time.sleep(60)
            elif attempt < max_retries - 1:
                print(f"  ⚠ Gemini error: {e}. Retrying in 10s...")
                time.sleep(10)
            else:
                print(f"  ✗ Gemini failed after {max_retries} attempts: {e}")
                return None
    return None

# ---------------------------------------------------------------
# MAIN ANALYSIS PROMPT
# ---------------------------------------------------------------

def build_stock_analysis_prompt(stock_score, news_articles, regime, macro):
    """
    Builds the structured prompt for Gemini.
    The prompt instructs Gemini to:
    1. Acknowledge the quantitative score
    2. Build the bull case WITH evidence
    3. Build the bear case (devil's advocate) WITH evidence
    4. Question its own assumptions
    5. Give a final verdict with confidence
    """

    symbol       = stock_score["symbol"]
    company      = stock_score["company_name"]
    score        = stock_score["score"]
    signal       = stock_score["signal"]
    components   = stock_score["components"]
    evidence     = "\n".join(stock_score["evidence"])
    anomalies    = "\n".join(stock_score["anomalies"]) if stock_score["anomalies"] else "None detected"
    regime_label = regime.get("label", "Unknown")
    regime_desc  = regime.get("description", "")

    # Format news
    news_text = ""
    if news_articles:
        for i, article in enumerate(news_articles[:5], 1):
            sentiment_word = "Positive" if article.get("sentiment", 0) > 0.1 else \
                             "Negative" if article.get("sentiment", 0) < -0.1 else "Neutral"
            news_text += f"\n  {i}. [{sentiment_word}] {article['title']}"
            if article.get("summary"):
                news_text += f"\n     Summary: {article['summary'][:200]}"
            if article.get("suspicious"):
                news_text += f"\n     ⚠ MANIPULATION FLAG: {', '.join(article.get('flags', []))}"
    else:
        news_text = "\n  No recent news found"

    # Format macro context
    vix        = macro.get("India VIX", {}).get("value", "N/A")
    usd_inr    = macro.get("USD/INR", {}).get("value", "N/A")
    crude      = macro.get("Crude Oil (Brent)", {}).get("value", "N/A")
    crude_chg  = macro.get("Crude Oil (Brent)", {}).get("change_pct", 0)
    sp500_chg  = macro.get("S&P 500 (USA)", {}).get("change_pct", 0)
    nifty_chg  = macro.get("Nifty 50", {}).get("change_pct", 0)

    prompt = f"""
You are an experienced Indian stock market analyst with deep expertise in NSE/BSE markets.
Your job is to provide rigorous, evidence-based analysis of {company} ({symbol}).

=========================================================
QUANTITATIVE SCORES (pre-calculated — DO NOT change these numbers)
=========================================================
Total Score: {score}/100 → Signal: {signal}

Component Breakdown:
- Technical Score:     {components['technical']}/25
- Fundamental Score:   {components['fundamental']}/25
- Momentum Score:      {components['momentum']}/20
- FII Activity Score:  {components['fii_activity']}/15
- News Score:          {components['news']}/15

Detailed Evidence Behind Scores:
{evidence}

Anomaly Flags:
{anomalies}

=========================================================
MARKET CONTEXT
=========================================================
Market Regime: {regime_label}
{regime_desc}

Key Macro Data:
- India VIX: {vix} (fear index)
- USD/INR: {usd_inr}
- Crude Oil Brent: ${crude} ({crude_chg:+.1f}% today)
- S&P 500 (USA): {sp500_chg:+.1f}% overnight
- Nifty 50: {nifty_chg:+.1f}% today

Recent News for {company}:{news_text}

Additional Stock Data:
- Current Price: ₹{stock_score.get('current_price', 'N/A')}
- P/E Ratio: {stock_score.get('pe_ratio', 'N/A')}
- ROE: {stock_score.get('roe_pct', 'N/A')}%
- RSI: {stock_score.get('rsi', 'N/A')}
- 1-Month Return: {stock_score.get('ret_1m_pct', 'N/A')}%
- 3-Month Return: {stock_score.get('ret_3m_pct', 'N/A')}%
- Market Cap: ₹{stock_score.get('market_cap_cr', 'N/A')} Cr
- Sector: {stock_score.get('sector', 'Unknown')}

=========================================================
YOUR ANALYSIS TASK — Follow this EXACT structure:
=========================================================

Provide your analysis in this EXACT JSON format. Every claim MUST cite evidence.
DO NOT add any text outside the JSON.

{{
  "summary": "2-3 sentence plain English summary of this stock right now",

  "bull_case": {{
    "main_argument": "The strongest reason to BUY this stock",
    "supporting_points": [
      "Point 1 with specific numbers from the data",
      "Point 2 with specific numbers from the data",
      "Point 3 with specific numbers from the data"
    ],
    "evidence_cited": ["Evidence 1 from the scores above", "Evidence 2"]
  }},

  "bear_case": {{
    "main_argument": "The strongest reason to be CAUTIOUS or AVOID",
    "supporting_points": [
      "Risk 1 with specific concern",
      "Risk 2 with specific concern",
      "Risk 3 with specific concern"
    ],
    "evidence_cited": ["Concern 1 from data", "Concern 2"]
  }},

  "self_questioning": {{
    "assumptions_being_made": "What assumptions is this analysis making?",
    "what_could_be_wrong": "What important factor might we be missing?",
    "data_gaps": "What data would change this view if we had it?",
    "recency_bias_check": "Are we over-weighting recent news vs long-term fundamentals?"
  }},

  "macro_impact": {{
    "crude_oil_impact": "How does current crude price affect this stock?",
    "usd_inr_impact": "How does USD/INR level affect this stock?",
    "global_markets_impact": "How do global market movements affect this stock?",
    "regime_adjustment": "How does the current market regime change this recommendation?"
  }},

  "final_verdict": {{
    "action": "{signal}",
    "confidence_pct": "Give a number 0-100 for your confidence. Be honest — if data is thin, say so.",
    "confidence_rationale": "Why this confidence level — not higher, not lower",
    "entry_strategy": "When and how to enter (if BUY/WATCH)",
    "risk_factors": "Top 2 things that would make you change this view",
    "time_horizon": "Is this an intraday, short-term (1-4 weeks), or long-term (3+ months) call?",
    "what_changes_view": "Specifically what news or data would change this recommendation"
  }}
}}
"""
    return prompt

# ---------------------------------------------------------------
# GEOPOLITICAL AND MACRO CONTEXT PROMPT
# ---------------------------------------------------------------

def build_macro_context_prompt(market_news, global_macro, regime):
    """
    Asks Gemini to interpret today's macro and geopolitical context
    and explain which sectors/stocks in Nifty 200 benefit or suffer.
    """
    news_headlines = ""
    for article in market_news[:15]:
        news_headlines += f"\n - {article['title']}"

    vix       = global_macro.get("India VIX", {}).get("value", "N/A")
    crude     = global_macro.get("Crude Oil (Brent)", {}).get("value", "N/A")
    crude_chg = global_macro.get("Crude Oil (Brent)", {}).get("change_pct", 0)
    gold      = global_macro.get("Gold", {}).get("value", "N/A")
    usd_inr   = global_macro.get("USD/INR", {}).get("value", "N/A")
    sp500_chg = global_macro.get("S&P 500 (USA)", {}).get("change_pct", 0)
    nikkei_chg= global_macro.get("Nikkei (Japan)", {}).get("change_pct", 0)
    hsi_chg   = global_macro.get("Hang Seng (HK)", {}).get("change_pct", 0)

    prompt = f"""
You are an expert macro strategist covering Indian equity markets.
Analyse today's global and domestic macro context and explain the impact on Indian stocks.

=========================================================
TODAY'S MACRO SNAPSHOT
=========================================================
India VIX: {vix}
Crude Oil Brent: ${crude} ({crude_chg:+.1f}% today)
Gold: ${gold}
USD/INR: {usd_inr}
S&P 500 (USA): {sp500_chg:+.1f}% overnight
Nikkei (Japan): {nikkei_chg:+.1f}% today
Hang Seng (HK): {hsi_chg:+.1f}% today

Market Regime: {regime.get('label', 'Unknown')}

TODAY'S TOP NEWS HEADLINES:{news_headlines}

=========================================================
YOUR TASK
=========================================================
Respond ONLY in this JSON format — no text outside JSON:

{{
  "macro_summary": "2-3 sentence summary of today's macro environment",

  "key_themes": [
    "Theme 1: What is the dominant story today and why it matters",
    "Theme 2: Second most important factor",
    "Theme 3: Third factor"
  ],

  "sector_impacts": {{
    "positive_sectors": [
      {{"sector": "Sector name", "reason": "Why it benefits today", "example_stocks": ["STOCK1", "STOCK2"]}},
      {{"sector": "Sector name", "reason": "Why it benefits today", "example_stocks": ["STOCK1", "STOCK2"]}}
    ],
    "negative_sectors": [
      {{"sector": "Sector name", "reason": "Why it suffers today", "example_stocks": ["STOCK1", "STOCK2"]}},
      {{"sector": "Sector name", "reason": "Why it suffers today", "example_stocks": ["STOCK1", "STOCK2"]}}
    ],
    "neutral_sectors": ["Sector 1", "Sector 2"]
  }},

  "geopolitical_reading": {{
    "active_themes": "What geopolitical events are relevant today?",
    "india_specific_impact": "How does today's geopolitics affect Indian markets specifically?",
    "historical_parallel": "What similar situation happened before and what was the market reaction?"
  }},

  "trading_guidance": {{
    "overall_bias": "BULLISH / BEARISH / NEUTRAL for today",
    "key_risk": "The single biggest risk to watch today",
    "opportunity": "The clearest opportunity given today's context"
  }}
}}
"""
    return prompt

# ---------------------------------------------------------------
# PARSE AI RESPONSE
# ---------------------------------------------------------------

def parse_json_response(text):
    """
    Safely parses JSON from Gemini's response.
    Handles cases where Gemini adds extra text around the JSON.
    """
    if not text:
        return None

    try:
        # Try direct parse first
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find JSON block within the text
    try:
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except (json.JSONDecodeError, AttributeError):
        pass

    # Return raw text if JSON parsing fails
    return {"raw_response": text, "parse_error": True}

# ---------------------------------------------------------------
# MAIN ANALYSIS RUNNER
# ---------------------------------------------------------------

def analyse_top_stocks(client, top_stocks, news_map, regime, global_macro, max_stocks=15):
    """
    Runs AI analysis on the top N scored stocks.
    Returns a list of analysis results.
    """
    results = []
    total = min(len(top_stocks), max_stocks)

    print(f"\n★ Running Gemini AI analysis on top {total} stocks...")

    for i, stock in enumerate(top_stocks[:total]):
        symbol = stock["symbol"]
        print(f"  Analysing {i+1}/{total}: {symbol}...")

        news_articles = news_map.get(symbol, [])

        prompt = build_stock_analysis_prompt(
            stock_score   = stock,
            news_articles = news_articles,
            regime        = regime,
            macro         = global_macro,
        )

        response_text = call_gemini(client, prompt)
        analysis      = parse_json_response(response_text)

        result = {
            "symbol"      : symbol,
            "company_name": stock["company_name"],
            "sector"      : stock["sector"],
            "score"       : stock["score"],
            "signal"      : stock["signal"],
            "current_price": stock.get("current_price"),
            "pe_ratio"    : stock.get("pe_ratio"),
            "rsi"         : stock.get("rsi"),
            "ret_1m_pct"  : stock.get("ret_1m_pct"),
            "anomalies"   : stock.get("anomalies", []),
            "evidence"    : stock.get("evidence", []),
            "ai_analysis" : analysis,
        }
        results.append(result)

        # Delay to avoid rate limits (Gemini free: 15 req/min)
        time.sleep(4)

    print(f"✓ AI analysis complete for {len(results)} stocks")
    return results


def get_macro_context(client, market_news, global_macro, regime):
    """
    Gets Gemini's interpretation of today's macro context.
    """
    print("\n★ Getting AI macro context interpretation...")

    prompt        = build_macro_context_prompt(market_news, global_macro, regime)
    response_text = call_gemini(client, prompt)
    macro_context = parse_json_response(response_text)

    print("✓ Macro context analysis complete")
    return macro_context
