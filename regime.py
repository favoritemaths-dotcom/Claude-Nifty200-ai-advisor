"""
regime.py
=========
Detects the current market regime (what kind of market today is).
This critically changes what recommendations the AI gives.

Regimes:
  🟢 BULL_TRENDING  - Strong uptrend, momentum strategies work
  🟡 BULL_VOLATILE  - Uptrend but choppy, quality stocks only
  🟠 SIDEWAYS       - No clear direction, be selective
  🔴 RISK_OFF       - Defensive mode, avoid aggressive bets
  ⚫ PANIC          - Stay in cash, no new positions
  🔵 RECOVERY       - Bouncing from bottom, best entry opportunities
"""

from config import REGIME as REGIME_CFG


def detect_market_regime(global_macro, fii_dii_data):
    """
    Determines the current market regime based on:
    - India VIX level (fear indicator)
    - Nifty 50 trend (direction)
    - FII flows (institutional conviction)
    - Global markets (external pressure)

    Returns:
        regime: string (e.g., "BULL_TRENDING")
        label: human-readable label with emoji
        description: what this means for trading
        color: for Streamlit display
        recommendations: how to trade in this regime
    """

    # ── Extract key signals ──────────────────────────────────
    india_vix = None
    nifty_chg = None
    sp500_chg = None
    fii_net   = None

    if global_macro:
        vix_data  = global_macro.get("India VIX", {})
        nifty_data= global_macro.get("Nifty 50", {})
        sp500_data= global_macro.get("S&P 500 (USA)", {})

        india_vix = vix_data.get("value")        if vix_data else None
        nifty_chg = nifty_data.get("change_pct") if nifty_data else None
        sp500_chg = sp500_data.get("change_pct") if sp500_data else None

    if fii_dii_data:
        fii_net = fii_dii_data.get("fii_net_cr")

    # ── Determine regime ─────────────────────────────────────

    # PANIC: VIX > 25 or Nifty down > 3% in a day
    if (india_vix and india_vix > REGIME_CFG["vix_panic"]) or \
       (nifty_chg and nifty_chg < -3.0):
        return {
            "regime"     : "PANIC",
            "label"      : "⚫ PANIC / CRASH MODE",
            "color"      : "#1a1a1a",
            "text_color" : "white",
            "description": (
                f"India VIX at {india_vix} — extreme fear in markets. "
                "Historical pattern: rushing in during panic almost always leads to losses. "
                "Institutions are selling aggressively."
            ),
            "recommendation": (
                "🚫 NO NEW POSITIONS TODAY. "
                "Preserve capital. Markets in panic mode. "
                "Opportunity will come after stabilization. "
                "If you have existing positions, consider whether stop-losses are in place."
            ),
            "signals"    : {
                "vix": india_vix, "nifty_change": nifty_chg,
                "fii_net": fii_net, "sp500_change": sp500_chg
            }
        }

    # RISK_OFF: VIX 21-25 or FIIs selling heavily
    if (india_vix and india_vix > REGIME_CFG["vix_caution"]) or \
       (fii_net and fii_net < REGIME_CFG["fii_sell_alarm"]):
        return {
            "regime"     : "RISK_OFF",
            "label"      : "🔴 RISK-OFF — Defensive Mode",
            "color"      : "#8B0000",
            "text_color" : "white",
            "description": (
                f"VIX elevated at {india_vix}. "
                f"FII selling: ₹{abs(fii_net or 0):,.0f} Cr. "
                "Market under pressure from institutional selling or external shocks."
            ),
            "recommendation": (
                "⚠️ Defensive positioning advised. "
                "Favour: FMCG, Pharma, IT Services (USD earners), Gold. "
                "Avoid: Cyclicals, High-beta, Leveraged companies. "
                "Reduce position sizes by 30-50%. "
                "Only enter stocks scoring 75+ today."
            ),
            "signals"    : {
                "vix": india_vix, "nifty_change": nifty_chg,
                "fii_net": fii_net, "sp500_change": sp500_chg
            }
        }

    # RECOVERY: Low VIX, FIIs buying, recovering from recent falls
    if (india_vix and india_vix < REGIME_CFG["vix_calm"]) and \
       (fii_net and fii_net > REGIME_CFG["fii_buy_signal"]) and \
       (nifty_chg and nifty_chg > 0):
        return {
            "regime"     : "RECOVERY",
            "label"      : "🔵 RECOVERY — Best Entry Opportunities",
            "color"      : "#003580",
            "text_color" : "white",
            "description": (
                f"VIX calm at {india_vix}. "
                f"FII buying ₹{fii_net:,.0f} Cr. "
                "Institutional money flowing in — classic setup for sustained rally."
            ),
            "recommendation": (
                "✅ Good time to build positions in quality stocks. "
                "Focus on stocks with strong fundamentals that were oversold. "
                "Beaten-down quality names often offer the best entries in recovery. "
                "Can deploy 100% of planned capital across 2-3 tranches."
            ),
            "signals"    : {
                "vix": india_vix, "nifty_change": nifty_chg,
                "fii_net": fii_net, "sp500_change": sp500_chg
            }
        }

    # BULL_TRENDING: VIX calm, FIIs buying or neutral, market positive
    if india_vix and india_vix <= REGIME_CFG["vix_normal"] and \
       (nifty_chg is None or nifty_chg >= -0.5):
        if fii_net and fii_net > 0:
            return {
                "regime"     : "BULL_TRENDING",
                "label"      : "🟢 BULL TRENDING — Normal Operations",
                "color"      : "#1B5E20",
                "text_color" : "white",
                "description": (
                    f"VIX at {india_vix} (calm). "
                    f"FII buying ₹{fii_net:,.0f} Cr. "
                    "Healthy bull market conditions. Momentum strategies performing well."
                ),
                "recommendation": (
                    "✅ Standard analysis applies. "
                    "Follow the scoring system recommendations normally. "
                    "Momentum and quality both work in this regime. "
                    "Full position sizes appropriate for high-conviction picks."
                ),
                "signals"    : {
                    "vix": india_vix, "nifty_change": nifty_chg,
                    "fii_net": fii_net, "sp500_change": sp500_chg
                }
            }

    # BULL_VOLATILE: Positive but choppy
    if india_vix and REGIME_CFG["vix_normal"] < india_vix <= REGIME_CFG["vix_caution"]:
        return {
            "regime"     : "BULL_VOLATILE",
            "label"      : "🟡 BULL VOLATILE — Selective Approach",
            "color"      : "#E65100",
            "text_color" : "white",
            "description": (
                f"VIX at {india_vix} — elevated but not alarming. "
                "Market moving but with higher uncertainty. "
                "Quality stocks outperform in this environment."
            ),
            "recommendation": (
                "⚡ Be selective — only stocks scoring 70+ today. "
                "Prefer quality: high ROE, low debt, consistent earnings. "
                "Avoid: speculative, high-beta, news-driven stories. "
                "Reduce individual position sizes by 20-30%."
            ),
            "signals"    : {
                "vix": india_vix, "nifty_change": nifty_chg,
                "fii_net": fii_net, "sp500_change": sp500_chg
            }
        }

    # SIDEWAYS: Default when signals are mixed
    return {
        "regime"     : "SIDEWAYS",
        "label"      : "🟠 SIDEWAYS — Mixed Signals",
        "color"      : "#795548",
        "text_color" : "white",
        "description": (
            f"VIX at {india_vix or 'N/A'}. "
            "No clear directional bias in the market today. "
            "Mixed signals from global and domestic indicators."
        ),
        "recommendation": (
            "🎯 Be highly selective today. "
            "Only act on stocks with very clear, multi-factor setups. "
            "Minimum score 70+ for any new position. "
            "Good day to review existing holdings rather than add new ones."
        ),
        "signals"    : {
            "vix": india_vix, "nifty_change": nifty_chg,
            "fii_net": fii_net, "sp500_change": sp500_chg
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
