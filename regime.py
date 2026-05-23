"""
regime.py
=========
Detects the current market regime (what kind of market today is).
This critically changes what recommendations the AI gives.

Regimes:
  BULL_TRENDING - Strong uptrend, momentum strategies work
  BULL_VOLATILE - Uptrend but choppy, quality stocks only
  SIDEWAYS      - No clear direction, be selective
  RISK_OFF      - Defensive mode, avoid aggressive bets
  PANIC         - Stay in cash, no new positions
  RECOVERY      - Bouncing from bottom, best entry opportunities
"""

from config import REGIME as REGIME_CFG

# ============================================================
# MAIN REGIME DETECTOR
# ============================================================

def detect_market_regime(global_macro, fii_dii_data):
    """
    Determines the current market regime based on:
    - India VIX level (fear indicator)
    - Nifty 50 trend (direction)
    - FII flows (institutional conviction)
    - Global markets (external pressure)

    Returns:
        regime      : string (e.g., "BULL_TRENDING")
        label       : human-readable label with emoji
        description : what this means for trading
        color       : for Streamlit display
        recommendations: how to trade in this regime
    """
    # Extract key signals
    india_vix = None
    nifty_chg = None
    sp500_chg = None
    fii_net   = None

    if global_macro:
        vix_data  = global_macro.get("India VIX", {})
        nifty_data= global_macro.get("Nifty 50", {})
        sp500_data= global_macro.get("S&P 500 (USA)", {})
        india_vix = vix_data.get("value")  if vix_data  else None
        nifty_chg = nifty_data.get("change_pct") if nifty_data else None
        sp500_chg = sp500_data.get("change_pct") if sp500_data else None

    if fii_dii_data:
        fii_net = fii_dii_data.get("fii_net_cr")

    # ── PANIC: VIX > 25 or Nifty down > 3% in a day ──────────
    if (india_vix and india_vix > REGIME_CFG["vix_panic"]) or \
       (nifty_chg and nifty_chg < -3.0):
        return {
            "regime"        : "PANIC",
            "label"         : "🔴 PANIC / CRASH MODE",
            "color"         : "#1a1a1a",
            "text_color"    : "white",
            "description"   : (
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
            "signals": {
                "vix": india_vix, "nifty_change": nifty_chg,
                "fii_net": fii_net, "sp500_change": sp500_chg
            }
        }

    # ── RISK_OFF: VIX 21-25 or FIIs selling heavily ──────────
    if (india_vix and india_vix > REGIME_CFG["vix_caution"]) or \
       (fii_net and fii_net < REGIME_CFG["fii_sell_alarm"]):
        return {
            "regime"        : "RISK_OFF",
            "label"         : "🟠 RISK-OFF — Defensive Mode",
            "color"         : "#8B0000",
            "text_color"    : "white",
            "description"   : (
                f"VIX elevated at {india_vix}. "
                f"FII selling: ₹{abs(fii_net or 0):,.0f} Cr. "
                "Market under pressure from institutional selling or external shocks."
            ),
            "recommendation": (
                "⚠ Reduce position sizes by 50%. "
                "Only highest-conviction stocks (score >= 75). "
                "Prefer defensive sectors: FMCG, Pharma, IT (USD earners). "
                "Avoid leveraged positions. Keep 40% in cash."
            ),
            "signals": {
                "vix": india_vix, "nifty_change": nifty_chg,
                "fii_net": fii_net, "sp500_change": sp500_chg
            }
        }

    # ── RECOVERY: Nifty bouncing (up > 1.5%) after risk-off ──
    if nifty_chg and nifty_chg > 1.5 and \
       india_vix and india_vix > REGIME_CFG["vix_normal"]:
        return {
            "regime"        : "RECOVERY",
            "label"         : "🟡 RECOVERY — Bouncing from Bottom",
            "color"         : "#4B5320",
            "text_color"    : "white",
            "description"   : (
                f"Market bouncing +{nifty_chg:.1f}% with VIX still elevated at {india_vix}. "
                "Classic recovery pattern — early buyers get best prices but "
                "confirmation not yet complete."
            ),
            "recommendation": (
                "✅ Begin selective buying — quality first. "
                "Stocks with score >= 70 AND strong fundamentals. "
                "Start with 25-50% of intended position. "
                "Add more only after VIX falls below 17 and FII buying confirms."
            ),
            "signals": {
                "vix": india_vix, "nifty_change": nifty_chg,
                "fii_net": fii_net, "sp500_change": sp500_chg
            }
        }

    # ── BULL_VOLATILE: VIX normal but FII mixed ───────────────
    if india_vix and india_vix > REGIME_CFG["vix_calm"] and \
       india_vix <= REGIME_CFG["vix_normal"]:
        fii_signal = "neutral"
        if fii_net:
            fii_signal = "buying" if fii_net > 500 else \
                         "selling" if fii_net < -500 else "neutral"
        return {
            "regime"        : "BULL_VOLATILE",
            "label"         : "🟡 BULL VOLATILE — Selective Mode",
            "color"         : "#8B6914",
            "text_color"    : "white",
            "description"   : (
                f"VIX at {india_vix} — normal-to-elevated range. "
                f"FII flows: {fii_signal}. "
                "Market moving but with noise. Quality matters more than momentum."
            ),
            "recommendation": (
                "✅ Selective buying recommended. "
                "Focus on quality stocks (score >= 65, ROE > 15%, low debt). "
                "Avoid high-beta cyclicals. "
                "Keep position sizes moderate — 60-70% deployment. "
                "Prefer pharma, private banks, quality IT."
            ),
            "signals": {
                "vix": india_vix, "nifty_change": nifty_chg,
                "fii_net": fii_net, "sp500_change": sp500_chg
            }
        }

    # ── BULL_TRENDING: VIX calm + FII buying ─────────────────
    if india_vix and india_vix <= REGIME_CFG["vix_calm"] and \
       fii_net and fii_net > REGIME_CFG["fii_buy_signal"]:
        return {
            "regime"        : "BULL_TRENDING",
            "label"         : "🟢 BULL TRENDING — Full Deployment",
            "color"         : "#1B4332",
            "text_color"    : "white",
            "description"   : (
                f"VIX very low at {india_vix} — extreme calm. "
                f"FII buying ₹{fii_net:,.0f} Cr — institutional conviction high. "
                "Best conditions for full deployment across quality stocks."
            ),
            "recommendation": (
                "✅ Full deployment recommended. "
                "All BUY-rated stocks (score >= 65) are valid. "
                "Momentum and quality both work in this regime. "
                "Can hold existing winners. "
                "Watch for complacency — VIX this low can spike suddenly."
            ),
            "signals": {
                "vix": india_vix, "nifty_change": nifty_chg,
                "fii_net": fii_net, "sp500_change": sp500_chg
            }
        }

    # ── SIDEWAYS: Default when nothing else matches ───────────
    return {
        "regime"        : "SIDEWAYS",
        "label"         : "⚪ SIDEWAYS — No Clear Direction",
        "color"         : "#2C3E50",
        "text_color"    : "white",
        "description"   : (
            f"VIX at {india_vix} — normal range. "
            f"FII flow: ₹{fii_net:,.0f} Cr. "
            "No strong directional signal. Market in consolidation phase."
        ),
        "recommendation": (
            "✅ Selective positions in high-conviction stocks only (score >= 70). "
            "Avoid chasing momentum. "
            "Focus on fundamentally strong companies. "
            "Keep 30-40% cash available for better opportunities."
        ),
        "signals": {
            "vix": india_vix, "nifty_change": nifty_chg,
            "fii_net": fii_net, "sp500_change": sp500_chg
        }
    }


# ============================================================
# REGIME SUMMARY FOR DISPLAY
# ============================================================

def get_regime_summary(regime_result):
    """
    Returns a concise summary string for display in briefings.
    Used by the AI prompt to understand current conditions.
    """
    r       = regime_result.get("regime", "UNKNOWN")
    label   = regime_result.get("label", "Unknown")
    signals = regime_result.get("signals", {})
    vix     = signals.get("vix", "N/A")
    fii     = signals.get("fii_net", "N/A")
    nifty_c = signals.get("nifty_change", "N/A")

    summary = f"""
MARKET REGIME: {label}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
India VIX    : {vix}
Nifty Change : {f'{nifty_c:+.2f}%' if isinstance(nifty_c, (int, float)) else 'N/A'}
FII Net Flow : {f'₹{fii:,.0f} Cr' if isinstance(fii, (int, float)) else 'N/A'}
Recommendation: {regime_result.get('recommendation', '')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    return summary.strip()
