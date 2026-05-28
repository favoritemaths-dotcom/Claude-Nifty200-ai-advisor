"""
agent.py
========
The main orchestrator — runs the complete analysis pipeline.
This is what GitHub Actions triggers every morning at 8:30 AM IST.

Pipeline:
1. Fetch Nifty 200 stock list
2. Get all stock data (prices, technicals, fundamentals)
3. Fetch global macro data (VIX, crude, global indices)
4. Download NSE official data (FII/DII, bulk deals)
5. Detect market regime
6. Score all 200 stocks (0-100)
7. Fetch news for top stocks
8. Run AI analysis on top stocks
9. Save briefing to JSON file
10. Done — Streamlit reads the JSON and displays it

Run this file with: python agent.py
"""

import json
import os
import sys
import traceback
from datetime import datetime
import pytz

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config          import ANALYSIS, RISK_PROFILE, AI_SETTINGS
from market_data     import (
    get_nifty200_stocks, get_all_stocks_data,
    get_global_macro, get_fii_dii_data
)
from news_fetcher    import get_market_news, get_news_for_top_stocks
from scoring         import score_all_stocks
from regime          import detect_market_regime, should_generate_recommendations
from ai_brain        import setup_gemini, analyse_top_stocks, get_macro_context

IST = pytz.timezone("Asia/Kolkata")

PROGRESS_FILE = "agent_progress.json"


# ─────────────────────────────────────────────────────────────
# LIVE PROGRESS TRACKER
# Writes a small JSON file at every step so app.py can display
# exactly what is happening in real time.
# ─────────────────────────────────────────────────────────────

def write_progress(step, total_steps, message, status="running", detail=""):
    """
    Writes current progress to agent_progress.json.
    app.py reads this file and shows it in the sidebar.

    Args:
        step:        current step number (e.g. 3)
        total_steps: total steps (9)
        message:     short step description shown in UI
        status:      "running" | "done" | "error"
        detail:      extra detail line (e.g. "Fetched 187/200 stocks")
    """
    now = datetime.now(IST)
    progress = {
        "step"        : step,
        "total_steps" : total_steps,
        "message"     : message,
        "status"      : status,
        "detail"      : detail,
        "pct"         : int((step / total_steps) * 100),
        "updated_at"  : now.strftime("%I:%M:%S %p IST"),
        "updated_ts"  : now.isoformat(),
    }
    try:
        with open(PROGRESS_FILE, "w") as f:
            json.dump(progress, f)
    except Exception:
        pass  # Non-fatal — don't let progress writing crash the agent


def clear_progress():
    """Removes the progress file once the run is complete."""
    try:
        if os.path.exists(PROGRESS_FILE):
            os.remove(PROGRESS_FILE)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────
# HELPER: GET API KEY (works on both local and Streamlit Cloud)
# ─────────────────────────────────────────────────────────────

def get_api_key():
    """Get Gemini API key from environment or Streamlit secrets."""
    # Try environment variable first (GitHub Actions)
    key = os.getenv("GEMINI_API_KEY", "")
    if key:
        return key
    # Try Streamlit secrets (when running via Streamlit)
    try:
        import streamlit as st
        return st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        return ""


# ─────────────────────────────────────────────────────────────
# HELPER: SAVE BRIEFING
# ─────────────────────────────────────────────────────────────

def save_briefing(briefing_data, filename="latest_briefing.json"):
    """Saves the briefing to a JSON file that Streamlit reads."""
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(briefing_data, f, indent=2, ensure_ascii=False, default=str)
        print(f"\n💾 Briefing saved to {filename}")
        return True
    except Exception as e:
        print(f"❌ Could not save briefing: {e}")
        return False


def load_briefing(filename="latest_briefing.json"):
    """Loads the latest briefing from JSON file."""
    try:
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"⚠️  Could not load briefing: {e}")
    return None


# ─────────────────────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────────────────────

def run_agent(quick_mode=False):
    """
    MAIN FUNCTION: Runs the complete analysis pipeline.

    Args:
        quick_mode: If True, only analyses top 30 stocks (faster for testing)

    Returns:
        briefing dict (also saved to JSON file)
    """
    TOTAL_STEPS = 9
    start_time  = datetime.now(IST)

    print(f"\n{'='*60}")
    print(f"🤖 NIFTY 200 AI ADVISOR — Starting Analysis")
    print(f"⏰  Time: {start_time.strftime('%d %b %Y, %I:%M %p IST')}")
    print(f"{'='*60}\n")

    briefing = {
        "generated_at"    : start_time.isoformat(),
        "generated_at_str": start_time.strftime("%d %b %Y, %I:%M %p IST"),
        "status"          : "running",
        "errors"          : [],
    }

    try:
        # ── STEP 1: Get stock list ───────────────────────────
        write_progress(1, TOTAL_STEPS, "📋 Fetching Nifty 200 stock list from NSE…")
        print("STEP 1: Getting Nifty 200 stock list...")
        stocks = get_nifty200_stocks()
        if quick_mode:
            stocks = stocks[:30]
            print(f"   (Quick mode: using {len(stocks)} stocks)")
        briefing["total_stocks"] = len(stocks)
        write_progress(1, TOTAL_STEPS, "📋 Stock list ready",
                       detail=f"{len(stocks)} stocks loaded")

        # ── STEP 2: Fetch global macro ───────────────────────
        write_progress(2, TOTAL_STEPS, "🌍 Fetching global macro data (VIX, crude, indices)…")
        print("\nSTEP 2: Fetching global macro data...")
        global_macro = get_global_macro()
        briefing["global_macro"] = global_macro
        write_progress(2, TOTAL_STEPS, "🌍 Global macro ready",
                       detail=f"{len(global_macro)} indicators fetched")

        # ── STEP 3: FII/DII data ─────────────────────────────
        write_progress(3, TOTAL_STEPS, "🏦 Fetching FII/DII institutional flows from NSE…")
        print("\nSTEP 3: Fetching FII/DII institutional flows...")
        fii_dii_data = get_fii_dii_data()
        briefing["fii_dii"] = fii_dii_data
        fii_val = fii_dii_data.get("fii_net_cr")
        write_progress(3, TOTAL_STEPS, "🏦 FII/DII data ready",
                       detail=f"FII: ₹{fii_val} Cr" if fii_val is not None else "FII data unavailable (normal before 6:30 PM)")

        # ── STEP 4: Detect market regime ─────────────────────
        write_progress(4, TOTAL_STEPS, "🔍 Detecting market regime…")
        print("\nSTEP 4: Detecting market regime...")
        regime = detect_market_regime(global_macro, fii_dii_data)
        briefing["market_regime"] = regime
        print(f"   Regime: {regime['label']}")
        write_progress(4, TOTAL_STEPS, "🔍 Market regime detected",
                       detail=regime.get("label", ""))

        # ── STEP 5: Check if we should trade today ───────────
        should_trade, no_trade_reason = should_generate_recommendations(regime)
        if not should_trade:
            write_progress(TOTAL_STEPS, TOTAL_STEPS,
                           "⛔ No Trade Day — analysis complete",
                           status="done", detail=no_trade_reason)
            print(f"\n⛔ NO TRADE TODAY: {no_trade_reason}")
            briefing["status"]          = "no_trade"
            briefing["no_trade_reason"] = no_trade_reason
            briefing["top_picks"]       = []
            briefing["macro_context"]   = None
            save_briefing(briefing)
            clear_progress()
            return briefing

        # ── STEP 6: Fetch market news ─────────────────────────
        write_progress(5, TOTAL_STEPS, "📰 Fetching market news from RSS feeds…")
        print("\nSTEP 5: Fetching market news...")
        market_news = get_market_news(max_per_feed=8)
        briefing["market_news_count"] = len(market_news)
        write_progress(5, TOTAL_STEPS, "📰 News fetched",
                       detail=f"{len(market_news)} articles loaded")

        # ── STEP 7: Get all stock data ───────────────────────
        n_stocks = 30 if quick_mode else len(stocks)
        write_progress(6, TOTAL_STEPS,
                       f"📊 Fetching price & fundamental data for {n_stocks} stocks…",
                       detail="This is the slowest step — ~1 sec per stock")
        print(f"\nSTEP 6: Fetching stock data for {n_stocks} stocks...")
        stocks_data = get_all_stocks_data(stocks, max_stocks=30 if quick_mode else None)

        if not stocks_data:
            raise ValueError(
                "No stock data fetched. "
                "Possible causes: (1) Yahoo Finance rate-limited, "
                "(2) No internet access from Streamlit Cloud, "
                "(3) All symbols returned empty history."
            )
        write_progress(6, TOTAL_STEPS, "📊 Stock data ready",
                       detail=f"{len(stocks_data)}/{n_stocks} stocks fetched successfully")

        # ── STEP 8: Score all stocks ─────────────────────────
        write_progress(7, TOTAL_STEPS, "🎯 Scoring all stocks (0–100)…")
        print("\nSTEP 7: Scoring all stocks...")
        scored_stocks = score_all_stocks(
            stocks_data,
            fii_dii_data=fii_dii_data,
            sentiment_scores={}
        )

        # Save all scores
        briefing["all_scores"] = [
            {
                "symbol"       : s["symbol"],
                "company_name" : s["company_name"],
                "sector"       : s["sector"],
                "score"        : s["score"],
                "signal"       : s["signal"],
                "confidence"   : s["confidence"],
                "current_price": s["current_price"],
                "pe_ratio"     : s["pe_ratio"],
                "roe_pct"      : s["roe_pct"],
                "rsi"          : s["rsi"],
                "ret_1m_pct"   : s["ret_1m_pct"],
                "ret_3m_pct"   : s["ret_3m_pct"],
                "anomalies"    : s["anomalies"],
            }
            for s in scored_stocks
        ]

        buy_ct   = sum(1 for s in scored_stocks if s["signal"] == "BUY")
        watch_ct = sum(1 for s in scored_stocks if s["signal"] == "WATCH")
        write_progress(7, TOTAL_STEPS, "🎯 Scoring complete",
                       detail=f"BUY: {buy_ct} | WATCH: {watch_ct} | AVOID: {len(scored_stocks)-buy_ct-watch_ct}")

        # Top stocks for AI analysis
        n_for_ai   = ANALYSIS["stocks_for_ai_analysis"]
        top_stocks = [s for s in scored_stocks if s["signal"] in ["BUY", "WATCH"]][:n_for_ai]

        # ── STEP 9: Fetch news for top stocks ────────────────
        write_progress(8, TOTAL_STEPS,
                       f"📰 Fetching news for top {len(top_stocks)} stocks…")
        print(f"\nSTEP 8: Fetching news for top {len(top_stocks)} stocks...")
        news_map, sentiment_scores = get_news_for_top_stocks(
            top_stocks_data=top_stocks,
            max_per_stock  =3
        )

        # Re-score with sentiment
        scored_stocks = score_all_stocks(
            stocks_data,
            fii_dii_data    =fii_dii_data,
            sentiment_scores=sentiment_scores
        )
        top_stocks = [s for s in scored_stocks if s["signal"] in ["BUY", "WATCH"]][:n_for_ai]

        # ── STEP 10: AI Analysis ──────────────────────────────
        api_key = get_api_key()

        if api_key:
            write_progress(9, TOTAL_STEPS,
                           f"🤖 Running Gemini AI analysis on top {len(top_stocks)} stocks…",
                           detail=f"Model: {AI_SETTINGS['model']}")
            print("\nSTEP 9: Running Gemini AI analysis...")
            model = setup_gemini(api_key)

            macro_context = get_macro_context(model, market_news, global_macro, regime)
            briefing["macro_context"] = macro_context

            top_picks_with_ai = analyse_top_stocks(
                model       = model,
                top_stocks  = top_stocks,
                news_map    = news_map,
                regime      = regime,
                global_macro= global_macro,
                max_stocks  = ANALYSIS["stocks_for_ai_analysis"]
            )
            briefing["top_picks"] = top_picks_with_ai

        else:
            write_progress(9, TOTAL_STEPS,
                           "⚠️ No Gemini API key — skipping AI analysis",
                           detail="Add GEMINI_API_KEY to Streamlit Secrets to enable AI")
            print("\n⚠️  No Gemini API key found — skipping AI analysis")
            briefing["top_picks"] = [
                {
                    "symbol"       : s["symbol"],
                    "company_name" : s["company_name"],
                    "sector"       : s["sector"],
                    "score"        : s["score"],
                    "signal"       : s["signal"],
                    "current_price": s["current_price"],
                    "evidence"     : s["evidence"],
                    "anomalies"    : s["anomalies"],
                    "ai_analysis"  : None,
                }
                for s in top_stocks[:ANALYSIS["top_picks_to_show"]]
            ]
            briefing["macro_context"] = None

        # ── FINAL ─────────────────────────────────────────────
        end_time = datetime.now(IST)
        duration = (end_time - start_time).seconds // 60

        briefing["status"]           = "success"
        briefing["completed_at"]     = end_time.isoformat()
        briefing["completed_at_str"] = end_time.strftime("%d %b %Y, %I:%M %p IST")
        briefing["duration_minutes"] = duration
        briefing["stocks_scored"]    = len(scored_stocks)

        write_progress(TOTAL_STEPS, TOTAL_STEPS,
                       "✅ Analysis complete! Refresh the page to see results.",
                       status="done",
                       detail=f"{len(scored_stocks)} stocks scored in {duration} min")

        print(f"\n{'='*60}")
        print(f"✅ ANALYSIS COMPLETE in {duration} minutes")
        print(f"   Stocks analysed: {len(scored_stocks)}")
        print(f"   Top picks: {len(briefing.get('top_picks', []))}")
        print(f"{'='*60}\n")

    except Exception as e:
        error_msg = traceback.format_exc()
        print(f"\n❌ CRITICAL ERROR: {e}")
        print(error_msg)
        write_progress(0, TOTAL_STEPS,
                       f"❌ Error: {str(e)[:120]}",
                       status="error",
                       detail=error_msg[:300])
        briefing["status"] = "error"
        briefing["errors"].append(str(e))
        briefing["top_picks"]     = []
        briefing["macro_context"] = None

    # Always save (even on error)
    save_briefing(briefing)
    # Keep progress file for a moment then let app.py decide when to clear it
    return briefing


# ─────────────────────────────────────────────────────────────
# RUN DIRECTLY
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    quick = "--quick" in sys.argv or "-q" in sys.argv

    if quick:
        print("🚀 Running in QUICK MODE (30 stocks only — for testing)")
    else:
        print("🚀 Running FULL analysis (all Nifty 200 stocks)")

    result = run_agent(quick_mode=quick)

    print(f"\n📊 FINAL STATUS: {result.get('status', 'unknown').upper()}")
    if result.get("top_picks"):
        print(f"   Top picks: {len(result['top_picks'])}")
        for pick in result["top_picks"][:5]:
            print(f"   {pick['score']:3d}/100  {pick['signal']:5s}  {pick['symbol']}")
