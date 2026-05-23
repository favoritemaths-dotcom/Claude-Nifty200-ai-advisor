"""
ai_brain.py
===========
Connects to Google Gemini AI (primary) and Groq (backup).
Sends stock data + scores + news to the AI and gets back
structured analysis in JSON format.

The AI's job is to EXPLAIN the scores, not invent new ones.
All numbers come from scoring.py — the AI adds narrative,
bull/bear cases, and self-questioning.

Functions:
  setup_gemini()        - Initialise Gemini model
  call_gemini()         - Single API call with retry logic
  analyse_top_stocks()  - Runs AI on top N stocks
  get_macro_context()   - Gets AI interpretation of today's macro
  get_briefing_summary()- Generates the overall day summary
"""

import json
import time
import re
from config import AI_SETTINGS, ANALYSIS

# ============================================================
# 1. SETUP GEMINI
# ============================================================

def setup_gemini(api_key):
    """
    Initialises the Gemini AI model.
    Returns the model object ready for use.
    """
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name   = AI_SETTINGS["model"],
            generation_config = {
                "temperature"     : AI_SETTINGS["temperature"],
                "max_output_tokens": AI_SETTINGS["max_tokens"],
            }
        )
        print(f"✓ Gemini model ready: {AI_SETTINGS['model']}")
        return model
    except Exception as e:
        print(f"✗ Could not initialise Gemini: {e}")
        return None


# ============================================================
# 2. SINGLE API CALL WITH RETRY
# ============================================================

def call_gemini(model, prompt, retries=3, delay=20):
    """
    Makes a single call to Gemini with automatic retry on failure.
    
    Gemini free tier: 15 requests/minute, 1M tokens/day.
    If rate limited, waits and retries automatically.
    
    Returns:
        response text (string) or None if all retries fail
    """
    for attempt in range(retries):
        try:
            response = model.generate_content(prompt)
            if response and response.text:
                return response.text.strip()
            return None
        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "quota" in error_str or "rate" in error_str:
                wait_time = delay * (attempt + 1)   # 20s, 40s, 60s
                print(f"  ⚠ Rate limited. Waiting {wait_time}s before retry {attempt+1}/{retries}...")
                time.sleep(wait_time)
            elif "timeout" in error_str:
                print(f"  ⚠ Timeout on attempt {attempt+1}. Retrying...")
                time.sleep(10)
            else:
                print(f"  ✗ Gemini error: {e}")
                return None
    print(f"  ✗ All {retries} retries failed.")
    return None


# ============================================================
# 3. GROQ BACKUP (free, fast, no quota issues)
# ============================================================

def call_groq_backup(prompt, groq_api_key):
    """
    Backup AI using Groq (llama3-70b) when Gemini fails.
    Groq is fast and free with generous limits.
    Only called when Gemini is unavailable or rate-limited.
    """
    try:
        from groq import Groq
        client = Groq(api_key=groq_api_key)
        response = client.chat.completions.create(
            model    = AI_SETTINGS["backup_model"],
            messages = [{"role": "user", "content": prompt}],
            temperature = AI_SETTINGS["temperature"],
            max_tokens  = AI_SETTINGS["max_tokens"],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"  ✗ Groq backup also failed: {e}")
        return None


# ============================================================
# 4. PARSE AI JSON RESPONSE
# ============================================================

def parse_ai_response(response_text):
    """
    Extracts and parses the JSON from Gemini's response.
    Gemini sometimes adds markdown code blocks (```json ... ```)
    or extra text before/after the JSON — this handles all of that.
    
    Returns:
        dict (parsed JSON) or None if parsing fails
    """
    if not response_text:
        return None
    try:
        # Remove markdown code blocks if present
        text = response_text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```").strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        
        # Find JSON object boundaries
        start = text.find("{")
        end   = text.rfind("}") + 1
        if start >= 0 and end > start:
            json_str = text[start:end]
            return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"  ⚠ JSON parse error: {e}")
        # Return a minimal fallback
        return {
            "summary"       : response_text[:300] if response_text else "Analysis unavailable",
            "parse_error"   : True,
            "raw_response"  : response_text[:500] if response_text else "",
        }
    return None


# ============================================================
# 5. BUILD PROMPTS (imported from prompt_builder)
# ============================================================
# Prompts are in ai_brain.py itself below this section.
# This keeps all AI logic in one file.

# ============================================================
# MAIN ANALYSIS PROMPT
# ============================================================

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
    symbol     = stock_score["symbol"]
    company    = stock_score["company_name"]
    score      = stock_score["score"]
    signal     = stock_score["signal"]
    components = stock_score["components"]
    evidence   = "
".join(stock_score["evidence"])
    anomalies  = "
".join(stock_score["anomalies"]) if stock_score["anomalies"] else "None detected"

    regime_label = regime.get("label", "Unknown")
    regime_desc  = regime.get("description", "")

    # Format news
    news_text = ""
    if news_articles:
        for i, article in enumerate(news_articles[:5], 1):
            sentiment_word = "Positive" if article.get("sentiment", 0) > 0.1 else \
                             "Negative" if article.get("sentiment", 0) < -0.1 else "Neutral"
            news_text += f"
  {i}. [{sentiment_word}] {article['title']}"
            if article.get("summary"):
                news_text += f"
     Summary: {article['summary'][:200]}"
            if article.get("suspicious"):
                news_text += f"
     ⚠⚠ MANIPULATION FLAG: {', '.join(article.get('flags', []))}"
    else:
        news_text = "
  No recent news found"

    # Format macro context
    vix       = macro.get("India VIX",         {}).get("value", "N/A")
    usd_inr   = macro.get("USD/INR",            {}).get("value", "N/A")
    crude     = macro.get("Crude Oil (Brent)",  {}).get("value", "N/A")
    crude_chg = macro.get("Crude Oil (Brent)",  {}).get("change_pct", 0)
    sp500_chg = macro.get("S&P 500 (USA)",      {}).get("change_pct", 0)
    nifty_chg = macro.get("Nifty 50",           {}).get("change_pct", 0)

    prompt = f"""
You are an experienced Indian stock market analyst with deep expertise in NSE/BSE markets.
Your job is to provide rigorous, evidence-based analysis of {company} ({symbol}).

═══════════════════════════════════════════════════════
QUANTITATIVE SCORES (pre-calculated — DO NOT change these numbers)
═══════════════════════════════════════════════════════
Total Score: {score}/100 → Signal: {signal}

Component Breakdown:
- Technical Score:    {components['technical']}/25
- Fundamental Score:  {components['fundamental']}/25
- Momentum Score:     {components['momentum']}/20
- FII Activity Score: {components['fii_activity']}/15
- News Score:         {components['news']}/15

Detailed Evidence Behind Scores:
{evidence}

Anomaly Flags:
{anomalies}

═══════════════════════════════════════════════════════
MARKET CONTEXT
═══════════════════════════════════════════════════════
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

═══════════════════════════════════════════════════════
YOUR ANALYSIS TASK — Follow this EXACT structure:
═══════════════════════════════════════════════════════
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


# ============================================================
# GEOPOLITICAL AND MACRO CONTEXT PROMPT
# ============================================================

def build_macro_context_prompt(market_news, global_macro, regime):
    """
    Asks Gemini to interpret today's macro and geopolitical context
    and explain which sectors/stocks in Nifty 200 benefit or suffer.
    """
    news_headlines = ""
    for article in market_news[:15]:
        news_headlines += f"
  - {article['title']}"

    vix       = global_macro.get("India VIX",        {}).get("value", "N/A")
    crude     = global_macro.get("Crude Oil (Brent)", {}).get("value", "N/A")
    crude_chg = global_macro.get("Crude Oil (Brent)", {}).get("change_pct", 0) or 0
    sp500_chg = global_macro.get("S&P 500 (USA)",     {}).get("change_pct", 0) or 0
    usd_inr   = global_macro.get("USD/INR",           {}).get("value", "N/A")
    gold      = global_macro.get("Gold",              {}).get("value", "N/A")
    nikkei_chg= global_macro.get("Nikkei (Japan)",    {}).get("change_pct", 0) or 0

    regime_label = regime.get("label", "Unknown")

    prompt = f"""
You are a senior Indian equity strategist with 20 years of experience at a Mumbai-based fund.
Today's market regime is: {regime_label}

═══════════════════════════════════════════════════════
TODAY'S GLOBAL MACRO SNAPSHOT
═══════════════════════════════════════════════════════
- India VIX: {vix}
- Crude Oil (Brent): ${crude} ({crude_chg:+.1f}% today)
- S&P 500: {sp500_chg:+.1f}% overnight
- Nikkei: {nikkei_chg:+.1f}%
- USD/INR: {usd_inr}
- Gold: ${gold}

TODAY'S NEWS HEADLINES (top 15):{news_headlines}

═══════════════════════════════════════════════════════
YOUR TASK:
═══════════════════════════════════════════════════════
Analyse today's macro picture for Indian equity markets.
DO NOT add any text outside the JSON.

{{
  "todays_theme": "In 2-3 sentences: What is the dominant theme in markets today?",
  "global_impact_on_india": "How are global movements affecting Indian markets specifically today?",
  "sector_impacts": {{
    "benefiting_sectors": [
      "Sector 1 and WHY (with specific macro reason)",
      "Sector 2 and WHY",
      "Sector 3 and WHY"
    ],
    "suffering_sectors": [
      "Sector 1 and WHY (with specific macro reason)",
      "Sector 2 and WHY"
    ]
  }},
  "crude_oil_analysis": {{
    "current_level": "{crude}",
    "direction": "Rising/Falling/Stable",
    "impact_on_india": "Net impact on Indian economy and markets",
    "stocks_benefiting": ["Stock type 1", "Stock type 2"],
    "stocks_suffering": ["Stock type 1", "Stock type 2"]
  }},
  "fii_behavior_prediction": "Based on today's macro, will FIIs likely buy or sell Indian equities? Why?",
  "key_risks_today": [
    "Risk 1 that could derail markets today",
    "Risk 2",
    "Risk 3"
  ],
  "opportunities": [
    "Opportunity 1 specific to today's context",
    "Opportunity 2"
  ],
  "geopolitical_flags": "Any geopolitical developments in the news that Indian equity investors should watch?",
  "one_line_verdict": "In ONE sentence: What should a Nifty 200 investor's posture be today?"
}}
"""
    return prompt


# ============================================================
# 6. ANALYSE TOP STOCKS — MAIN FUNCTION
# ============================================================

def analyse_top_stocks(model, top_stocks, news_map, regime, global_macro, max_stocks=15):
    """
    Runs Gemini AI analysis on the top scored stocks.
    
    Args:
        model:        Gemini model object (from setup_gemini)
        top_stocks:   list of scored stock dicts
        news_map:     dict mapping symbol -> list of news articles
        regime:       current market regime dict
        global_macro: global macro data dict
        max_stocks:   maximum stocks to analyse (default 15)
    
    Returns:
        list of stock dicts with 'ai_analysis' field added
    """
    results     = []
    stocks_todo = top_stocks[:max_stocks]
    total       = len(stocks_todo)

    print(f"
  🤖 Running AI analysis on {total} stocks...")
    print(f"     (Rate limit: 15 requests/min — adding delays between calls)
")

    for i, stock in enumerate(stocks_todo):
        symbol = stock.get("symbol", "UNKNOWN")
        print(f"  [{i+1}/{total}] Analysing {symbol}...")

        news_articles = news_map.get(symbol, [])
        prompt        = build_stock_analysis_prompt(
            stock_score   = stock,
            news_articles = news_articles,
            regime        = regime,
            macro         = global_macro,
        )

        # Call Gemini
        response_text = call_gemini(model, prompt)
        ai_analysis   = parse_ai_response(response_text)

        # Add AI analysis to stock dict
        stock_with_ai = dict(stock)
        stock_with_ai["ai_analysis"] = ai_analysis
        stock_with_ai["ai_raw"]      = response_text[:200] if response_text else None
        results.append(stock_with_ai)

        # Rate limiting: wait between calls to stay under 15 req/min
        if i < total - 1:
            time.sleep(4)   # 4 seconds between calls = ~15/min max

    print(f"
  ✓ AI analysis complete: {len(results)} stocks processed")
    return results


# ============================================================
# 7. GET MACRO CONTEXT
# ============================================================

def get_macro_context(model, market_news, global_macro, regime):
    """
    Calls Gemini to get today's macro context and sector impacts.
    This is the 'AI Macro Context' section at the top of the briefing.
    
    Returns:
        dict with macro analysis or None if failed
    """
    print("
  🌍 Getting AI macro context...")

    prompt        = build_macro_context_prompt(market_news, global_macro, regime)
    response_text = call_gemini(model, prompt)
    macro_context = parse_ai_response(response_text)

    if macro_context:
        print("  ✓ Macro context received")
    else:
        print("  ✗ Could not get macro context")

    return macro_context


# ============================================================
# 8. GET BRIEFING SUMMARY
# ============================================================

def get_briefing_summary(model, top_picks, regime, global_macro):
    """
    Generates a short 'executive summary' of today's briefing.
    Called after all stock analysis is complete.
    
    Returns:
        string summary for display at top of briefing
    """
    if not top_picks:
        return "No analysis available today."

    top_3 = top_picks[:3]
    top_3_text = ""
    for s in top_3:
        top_3_text += f"
  - {s['company_name']} ({s['symbol']}): Score {s['score']}/100 → {s['signal']}"

    regime_label = regime.get("label", "Unknown")
    vix = global_macro.get("India VIX", {}).get("value", "N/A")

    prompt = f"""
Today's market regime: {regime_label}
India VIX: {vix}
Top 3 stocks today:{top_3_text}

Write a 3-sentence executive summary for a retail investor opening their 9 AM briefing.
Be direct, specific, and actionable. No fluff. Use plain English.
Format: Just the 3 sentences, no JSON, no headers.
"""

    response = call_gemini(model, prompt)
    if response:
        return response.strip()
    return f"Market is in {regime_label} mode. Top picks available below. Review scores and AI analysis before acting."
