"""
regime.py
=========
Market regime detection engine.

This file determines the overall market environment using:
- India VIX (fear index)
- Nifty daily move
- FII/DII institutional flows
- Global market signals

The regime affects:
- Whether recommendations are generated
- Position sizing
- Sector preferences
- Risk management

Possible regimes:
- PANIC
- RISK_OFF
- SIDEWAYS
- BULL_VOLATILE
- RECOVERY
"""

from config import REGIME as REGIME_CFG


# ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
# MAIN REGIME DETECTOR
# ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■

def detect_market_regime(global_macro, fii_dii_data):
    """
    Detects the current market regime based on:
    - India VIX
    - Nifty movement
    - FII flows
    - Global market conditions

    Returns a dict:
    regime: machine-readable regime name
    label: human-readable label with emoji
    description: what this means for trading
    color: for Streamlit display
    recommendations: how to trade in this regime
    """

    # ■■ Extract key signals ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■

    india_vix = None
    nifty_chg = None
    sp500_chg = None
    fii_net = None

    if global_macro:
        vix_data = global_macro.get("India VIX", {})
        nifty_data = global_macro.get("Nifty 50", {})
        sp500_data = global_macro.get("S&P 500 (USA)", {})

        india_vix = vix_data.get("value") if vix_data else None
        nifty_chg = nifty_data.get("change_pct") if nifty_data else None
        sp500_chg = sp500_data.get("change_pct") if sp500_data else None

    if fii_dii_data:
        fii_net = fii_dii_data.get("fii_net_cr")

    # ■■ Determine regime ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■

    # PANIC: VIX > 25 or Nifty down > 3% in a day
    if (india_vix and india_vix > REGIME_CFG["vix_panic"]) or \
       (nifty_chg and nifty_chg < -3.0):

        return {
            "regime": "PANIC",
            "label": "■ PANIC / CRASH MODE",
            "color": "#1a1a1a",
            "text_color": "white",

            "description": (
                f"Extreme fear in markets. India VIX at {india_vix}. "
                "High probability of sharp volatility and forced selling."
            ),

            "recommendation": (
                "■ DO NOT deploy fresh capital today. "
                "Preserve cash. Avoid catching falling knives. "
                "Only existing high-conviction long-term holdings should be retained. "
                "Wait for stability before re-entering."
            ),

            "signals": {
                "vix": india_vix,
                "nifty_change": nifty_chg,
                "fii_net": fii_net,
                "sp500_change": sp500_chg
            }
        }

    # RISK OFF: Elevated VIX + FII selling
    if (india_vix and india_vix > REGIME_CFG["vix_caution"]) and \
       (fii_net and fii_net < REGIME_CFG["fii_sell_alarm"]):

        return {
            "regime": "RISK_OFF",
            "label": "■ RISK-OFF / DEFENSIVE",
            "color": "#8b0000",
            "text_color": "white",

            "description": (
                f"Elevated volatility (VIX {india_vix}) and strong FII selling "
                f"(■{fii_net:,.0f} Cr). Institutions are reducing risk."
            ),

            "recommendation": (
                "■■ Defensive positioning advised. "
                "Favour: FMCG, Pharma, IT Services (USD earners), Gold. "
                "Avoid: Cyclicals, High-beta, Leveraged companies. "
                "Reduce position sizes by 30-50%. "
                "Only enter stocks scoring 75+ today."
            ),

            "signals": {
                "vix": india_vix,
                "nifty_change": nifty_chg,
                "fii_net": fii_net,
                "sp500_change": sp500_chg
            }
        }

    # RECOVERY: Low VIX, FIIs buying, recovering from recent falls
    if (india_vix and india_vix < REGIME_CFG["vix_calm"]) and \
       (fii_net and fii_net > REGIME_CFG["fii_buy_signal"]) and \
       (nifty_chg and nifty_chg > 0):

        return {
            "regime": "RECOVERY",
            "label": "■ RECOVERY — Best Entry Opportunities",
            "color": "#003580",
            "text_color": "white",

            "description": (
                f"VIX calm at {india_vix}. "
                f"FII buying ■{fii_net:,.0f} Cr. "
                "Institutional money flowing in — classic setup for sustained rally."
            ),

            "recommendation": (
                "■ Good time to build positions in quality stocks. "
                "Focus on stocks with strong fundamentals that were oversold. "
                "Beaten-down quality names often offer the best entries in recovery. "
                "Can deploy 100% of planned capital across 2-3 tranches."
            ),

            "signals": {
                "vix": india_vix,
                "nifty_change": nifty_chg,
                "fii_net": fii_net,
                "sp500_change": sp500_chg
            }
        }

    # BULL VOLATILE: Market bullish but volatile
    if (india_vix and india_vix >= REGIME_CFG["vix_normal"]) and \
       (nifty_chg and nifty_chg > 0):

        return {
            "regime": "BULL_VOLATILE",
            "label": "■ BULL MARKET — VOLATILE",
            "color": "#ff9800",
            "text_color": "black",

            "description": (
                f"Markets are bullish but volatility remains elevated "
                f"(VIX {india_vix}). Expect sharp intraday swings."
            ),

            "recommendation": (
                "■ Momentum trades working, but control risk carefully. "
                "Prefer staggered entries instead of all-in positions. "
                "Book partial profits faster than usual. "
                "Focus on leaders showing strong relative strength."
            ),

            "signals": {
                "vix": india_vix,
                "nifty_change": nifty_chg,
                "fii_net": fii_net,
                "sp500_change": sp500_chg
            }
        }

    # SIDEWAYS: Default neutral market
    return {
        "regime": "SIDEWAYS",
        "label": "■ SIDEWAYS / MIXED MARKET",
        "color": "#808080",
        "text_color": "white",

        "description": (
            f"VIX at {india_vix or 'N/A'}. "
            "No clear directional bias in the market today. "
            "Mixed signals from global and domestic indicators."
        ),

        "recommendation": (
            "■ Be highly selective today. "
            "Only act on stocks with very clear, multi-factor setups. "
            "Minimum score 70+ for any new position. "
            "Good day to review existing holdings rather than add new ones."
        ),

        "signals": {
            "vix": india_vix,
            "nifty_change": nifty_chg,
            "fii_net": fii_net,
            "sp500_change": sp500_chg
        }
    }


def should_generate_recommendations(regime_data):
    """
    Returns True if the market regime supports making recommendations.
    Returns False (with reason) if today is a "No Trade" day.
    """

    regime = regime_data.get("regime", "SIDEWAYS")

    if regime == "PANIC":
        return False, "Market in PANIC mode — no recommendations today. Preserve capital."

    return True, None
