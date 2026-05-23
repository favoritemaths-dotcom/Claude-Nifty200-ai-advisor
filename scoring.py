"""
scoring.py
==========
Deterministic scoring system: gives every stock a score from 0 to 100.
The AI then EXPLAINS these scores rather than inventing them.

Score breakdown:
  Technical   (0-25 pts) - RSI, trend, volume
  Fundamental (0-25 pts) - P/E, ROE, debt
  Momentum    (0-20 pts) - Price performance
  FII Activity(0-15 pts) - Institutional flow
  News        (0-15 pts) - News sentiment
  Total: 100 points

BUY signal  = score >= 65
WATCH signal= score 50-64
AVOID       = score < 50
"""

from config import ANALYSIS, SCORING_WEIGHTS

# ============================================================
# 1. TECHNICAL SCORE (0 to 25 points)
# ============================================================

def score_technical(stock):
    """
    Scores based on:
    - RSI position (oversold = opportunity, overbought = risk)
    - Moving average alignment (above MA50 + MA200 = strong trend)
    - MACD signal (bullish crossover = positive)
    - Volume analysis (high volume = conviction)
    Returns: score (0-25), breakdown dict
    """
    score    = 0
    breakdown= {}

    rsi = stock.get("rsi")

    # RSI scoring (0-8 points)
    if rsi is not None:
        if 35 <= rsi <= 55:      # Sweet spot - not overbought or oversold
            rsi_score = 8; rsi_label = "Neutral-Good"
        elif 55 < rsi <= 65:     # Mildly overbought but trending
            rsi_score = 6; rsi_label = "Mildly Extended"
        elif 25 <= rsi < 35:     # Oversold - potential bounce
            rsi_score = 7; rsi_label = "Oversold (Bounce Possible)"
        elif rsi > 70:           # Very overbought - caution
            rsi_score = 3; rsi_label = "Overbought"
        elif rsi < 25:           # Very oversold - high risk
            rsi_score = 4; rsi_label = "Very Oversold"
        else:
            rsi_score = 5; rsi_label = "Neutral"
        score += rsi_score
        breakdown["RSI"] = f"{rsi} ({rsi_label}) → {rsi_score}/8 pts"
    else:
        breakdown["RSI"] = "Data unavailable → 0/8 pts"

    # Moving Average scoring (0-10 points)
    above_ma50  = stock.get("above_ma50",  False)
    above_ma200 = stock.get("above_ma200", False)
    above_ma20  = stock.get("above_ma20",  False)
    ma_score = 0
    if above_ma200: ma_score += 4   # Above 200-day MA = strong long-term trend
    if above_ma50:  ma_score += 4   # Above 50-day MA = medium-term trend
    if above_ma20:  ma_score += 2   # Above 20-day MA = short-term trend
    score += ma_score
    breakdown["Moving Averages"] = (
        f"MA20:{'✓' if above_ma20 else '✗'} "
        f"MA50:{'✓' if above_ma50 else '✗'} "
        f"MA200:{'✓' if above_ma200 else '✗'} → {ma_score}/10 pts"
    )

    # MACD scoring (0-4 points)
    macd_bullish = stock.get("macd_bullish", False)
    macd_score   = 4 if macd_bullish else 1
    score += macd_score
    breakdown["MACD"] = f"{'Bullish' if macd_bullish else 'Bearish'} → {macd_score}/4 pts"

    # Volume scoring (0-3 points)
    volume_ratio = stock.get("volume_ratio", 1.0)
    if   volume_ratio >= 2.0: vol_score = 3; vol_label = "Very High (Strong Conviction)"
    elif volume_ratio >= 1.5: vol_score = 3; vol_label = "High (Good Participation)"
    elif volume_ratio >= 0.8: vol_score = 2; vol_label = "Normal"
    else:                      vol_score = 1; vol_label = "Low (Weak Participation)"
    score += vol_score
    breakdown["Volume"] = f"{round(volume_ratio,1)}x avg ({vol_label}) → {vol_score}/3 pts"

    return min(score, 25), breakdown

# ============================================================
# 2. FUNDAMENTAL SCORE (0 to 25 points)
# ============================================================

def score_fundamental(stock):
    """
    Scores based on:
    - P/E ratio (value vs expensive)
    - ROE (returns generated)
    - Debt to Equity (financial health)
    - Earnings growth
    - Profit margins
    Returns: score (0-25), breakdown dict
    """
    score     = 0
    breakdown = {}

    # P/E Ratio scoring (0-7 points)
    pe = stock.get("pe_ratio")
    if pe is not None and pe > 0:
        if   pe < 15: pe_score = 7; pe_label = "Undervalued"
        elif pe < 25: pe_score = 6; pe_label = "Reasonably Valued"
        elif pe < 35: pe_score = 4; pe_label = "Fairly Valued"
        elif pe < 50: pe_score = 2; pe_label = "Expensive"
        else:         pe_score = 1; pe_label = "Very Expensive"
        score += pe_score
        breakdown["P/E Ratio"] = f"{pe} ({pe_label}) → {pe_score}/7 pts"
    elif pe is not None and pe < 0:
        breakdown["P/E Ratio"] = "Negative (Loss-making company) → 0/7 pts"
    else:
        # No P/E data - give neutral score
        score += 3
        breakdown["P/E Ratio"] = "Data unavailable → 3/7 pts (neutral)"

    # ROE scoring (0-8 points)
    roe = stock.get("roe_pct")
    if roe is not None:
        if   roe >= 20: roe_score = 8; roe_label = "Excellent (>20%)"
        elif roe >= 15: roe_score = 6; roe_label = "Good (15-20%)"
        elif roe >= 10: roe_score = 4; roe_label = "Acceptable (10-15%)"
        elif roe >= 5:  roe_score = 2; roe_label = "Weak (5-10%)"
        else:           roe_score = 0; roe_label = "Poor (<5%)"
        score += roe_score
        breakdown["ROE"] = f"{roe}% ({roe_label}) → {roe_score}/8 pts"
    else:
        score += 3
        breakdown["ROE"] = "Data unavailable → 3/8 pts (neutral)"

    # Debt to Equity scoring (0-5 points)
    de = stock.get("debt_to_equity")
    if de is not None:
        if   de < 30:  de_score = 5; de_label = "Very Low Debt (Excellent)"
        elif de < 60:  de_score = 4; de_label = "Low Debt (Good)"
        elif de < 100: de_score = 3; de_label = "Moderate Debt"
        elif de < 150: de_score = 2; de_label = "High Debt (Caution)"
        else:          de_score = 1; de_label = "Very High Debt (Risk)"
        score += de_score
        # Note: Yahoo Finance reports D/E as percentage (e.g., 45 = 0.45x)
        breakdown["Debt/Equity"] = f"{de} ({de_label}) → {de_score}/5 pts"
    else:
        score += 3
        breakdown["Debt/Equity"] = "Data unavailable → 3/5 pts (neutral)"

    # Earnings Growth scoring (0-5 points)
    eg = stock.get("earnings_growth_pct")
    if eg is not None:
        if   eg >= 25: eg_score = 5; eg_label = "Excellent (>25%)"
        elif eg >= 15: eg_score = 4; eg_label = "Good (15-25%)"
        elif eg >= 5:  eg_score = 3; eg_label = "Moderate (5-15%)"
        elif eg >= 0:  eg_score = 2; eg_label = "Flat (0-5%)"
        else:          eg_score = 0; eg_label = "Declining"
        score += eg_score
        breakdown["Earnings Growth"] = f"{eg}% ({eg_label}) → {eg_score}/5 pts"
    else:
        score += 2
        breakdown["Earnings Growth"] = "Data unavailable → 2/5 pts (neutral)"

    return min(score, 25), breakdown

# ============================================================
# 3. MOMENTUM SCORE (0 to 20 points)
# ============================================================

def score_momentum(stock):
    """
    Scores based on price performance:
    - 1-month return vs 0%
    - 3-month return vs 0%
    - Distance from 52-week high (how far from peak)
    Returns: score (0-20), breakdown dict
    """
    score     = 0
    breakdown = {}

    # 1-month return scoring (0-7 points)
    ret_1m = stock.get("ret_1m_pct", 0) or 0
    if   ret_1m >= 10:  r1_score = 7; r1_label = "Strong (+10%+)"
    elif ret_1m >= 5:   r1_score = 6; r1_label = "Good (+5-10%)"
    elif ret_1m >= 2:   r1_score = 5; r1_label = "Positive (+2-5%)"
    elif ret_1m >= 0:   r1_score = 4; r1_label = "Flat (0-2%)"
    elif ret_1m >= -5:  r1_score = 2; r1_label = "Mild Decline (-5-0%)"
    elif ret_1m >= -10: r1_score = 1; r1_label = "Declining (-10 to -5%)"
    else:               r1_score = 0; r1_label = "Sharp Drop (<-10%)"
    score += r1_score
    breakdown["1M Return"] = f"{ret_1m}% ({r1_label}) → {r1_score}/7 pts"

    # 3-month return scoring (0-8 points)
    ret_3m = stock.get("ret_3m_pct", 0) or 0
    if   ret_3m >= 20:  r3_score = 8; r3_label = "Excellent (+20%+)"
    elif ret_3m >= 10:  r3_score = 7; r3_label = "Strong (+10-20%)"
    elif ret_3m >= 5:   r3_score = 6; r3_label = "Good (+5-10%)"
    elif ret_3m >= 0:   r3_score = 4; r3_label = "Flat/Positive"
    elif ret_3m >= -10: r3_score = 2; r3_label = "Declining"
    else:               r3_score = 0; r3_label = "Sharp Fall"
    score += r3_score
    breakdown["3M Return"] = f"{ret_3m}% ({r3_label}) → {r3_score}/8 pts"

    # Distance from 52-week high (0-5 points)
    pct_from_high = stock.get("pct_from_high", -50) or -50
    if   pct_from_high >= -5:  h_score = 5; h_label = "Near 52W High (Strong)"
    elif pct_from_high >= -15: h_score = 4; h_label = "Consolidating (-5 to -15%)"
    elif pct_from_high >= -25: h_score = 3; h_label = "Moderate Pullback"
    elif pct_from_high >= -40: h_score = 2; h_label = "Significant Pullback"
    else:                       h_score = 1; h_label = "Deep Correction"
    score += h_score
    breakdown["52W Position"] = f"{pct_from_high}% from high ({h_label}) → {h_score}/5 pts"

    return min(score, 20), breakdown

# ============================================================
# 4. FII ACTIVITY SCORE (0 to 15 points)
# ============================================================

def score_fii_activity(stock, fii_dii_data):
    """
    Scores based on institutional money flow:
    - FII net buy/sell (market-wide signal)
    - DII activity (domestic institutions)
    Returns: score (0-15), breakdown dict
    """
    score     = 0
    breakdown = {}

    if not fii_dii_data:
        breakdown["FII/DII"] = "Data unavailable → 7/15 pts (neutral)"
        return 7, breakdown

    fii_net = fii_dii_data.get("fii_net_cr")
    dii_net = fii_dii_data.get("dii_net_cr")

    # FII scoring (0-10 points)
    if fii_net is not None:
        if   fii_net >= 3000:  fii_score = 10; fii_label = f"Heavy Buying (+₹{fii_net:,.0f} Cr)"
        elif fii_net >= 1000:  fii_score = 8;  fii_label = f"Buying (+₹{fii_net:,.0f} Cr)"
        elif fii_net >= 0:     fii_score = 6;  fii_label = f"Mild Buying (+₹{fii_net:,.0f} Cr)"
        elif fii_net >= -1000: fii_score = 4;  fii_label = f"Mild Selling (-₹{abs(fii_net):,.0f} Cr)"
        elif fii_net >= -3000: fii_score = 2;  fii_label = f"Selling (-₹{abs(fii_net):,.0f} Cr)"
        else:                   fii_score = 0;  fii_label = f"Heavy Selling (-₹{abs(fii_net):,.0f} Cr)"
        score += fii_score
        breakdown["FII Activity"] = f"{fii_label} → {fii_score}/10 pts"
    else:
        score += 5
        breakdown["FII Activity"] = "Data unavailable → 5/10 pts"

    # DII scoring (0-5 points)
    if dii_net is not None:
        if   dii_net >= 2000: dii_score = 5; dii_label = f"Heavy Buying (+₹{dii_net:,.0f} Cr)"
        elif dii_net >= 500:  dii_score = 4; dii_label = f"Buying (+₹{dii_net:,.0f} Cr)"
        elif dii_net >= 0:    dii_score = 3; dii_label = f"Mild Buying"
        else:                  dii_score = 1; dii_label = f"Selling (-₹{abs(dii_net):,.0f} Cr)"
        score += dii_score
        breakdown["DII Activity"] = f"{dii_label} → {dii_score}/5 pts"
    else:
        score += 2
        breakdown["DII Activity"] = "Data unavailable → 2/5 pts"

    return min(score, 15), breakdown

# ============================================================
# 5. NEWS SENTIMENT SCORE (0 to 15 points)
# ============================================================

def score_news(symbol, sentiment_scores):
    """
    Converts news sentiment to a score.
    sentiment_scores: dict mapping symbol -> sentiment (-1 to +1)
    Returns: score (0-15), breakdown dict
    """
    score     = 0
    breakdown = {}

    if not sentiment_scores or symbol not in sentiment_scores:
        breakdown["News Sentiment"] = "No news data → 7/15 pts (neutral)"
        return 7, breakdown

    sentiment = sentiment_scores.get(symbol, 0)

    if   sentiment >= 0.5:  s_score = 15; s_label = "Very Positive"
    elif sentiment >= 0.2:  s_score = 12; s_label = "Positive"
    elif sentiment >= 0.0:  s_score = 9;  s_label = "Slightly Positive"
    elif sentiment >= -0.2: s_score = 6;  s_label = "Slightly Negative"
    elif sentiment >= -0.5: s_score = 3;  s_label = "Negative"
    else:                    s_score = 0;  s_label = "Very Negative"

    score += s_score
    breakdown["News Sentiment"] = f"Score: {sentiment} ({s_label}) → {s_score}/15 pts"

    return min(score, 15), breakdown

# ============================================================
# 6. COMBINED STOCK SCORER
# ============================================================

def score_stock(stock, fii_dii_data=None, sentiment_scores=None):
    """
    Master scoring function. Combines all 5 components.
    Returns a complete dict with score, signal, evidence trail.
    """
    symbol = stock.get("symbol", "UNKNOWN")

    if sentiment_scores is None:
        sentiment_scores = {}

    # Calculate each component
    tech_score, tech_bd = score_technical(stock)
    fund_score, fund_bd = score_fundamental(stock)
    mom_score,  mom_bd  = score_momentum(stock)
    fii_score,  fii_bd  = score_fii_activity(stock, fii_dii_data)
    news_score, news_bd = score_news(symbol, sentiment_scores)

    total_score = tech_score + fund_score + mom_score + fii_score + news_score

    # Generate signal
    if total_score >= ANALYSIS["min_score_for_buy"]:
        signal     = "BUY"
        confidence = "HIGH" if total_score >= 80 else "MEDIUM"
    elif total_score >= ANALYSIS["min_score_for_watch"]:
        signal     = "WATCH"
        confidence = "MEDIUM" if total_score >= 57 else "LOW"
    else:
        signal     = "AVOID"
        confidence = "LOW"

    # Compile evidence trail
    evidence       = []
    all_breakdowns = {**tech_bd, **fund_bd, **mom_bd, **fii_bd, **news_bd}
    for factor, detail in all_breakdowns.items():
        evidence.append(f"{factor}: {detail}")

    # Anomaly detection flags
    anomalies  = []
    vol_ratio  = stock.get("volume_ratio", 1.0) or 1.0
    rsi        = stock.get("rsi")
    if vol_ratio > 3.0:
        anomalies.append(f"⚠ ANOMALY: Volume is {vol_ratio:.1f}x average — unusual activity detected")
    if rsi and rsi > 80:
        anomalies.append(f"⚠ ANOMALY: RSI at {rsi} — extremely overbought, avoid chasing")
    if rsi and rsi < 20:
        anomalies.append(f"⚠ ANOMALY: RSI at {rsi} — very oversold, check for fundamental reasons")

    return {
        "symbol"       : symbol,
        "company_name" : stock.get("company_name", symbol),
        "sector"       : stock.get("sector", "Unknown"),
        "score"        : total_score,
        "signal"       : signal,
        "confidence"   : confidence,
        "current_price": stock.get("current_price"),
        "components"   : {
            "technical"   : tech_score,
            "fundamental" : fund_score,
            "momentum"    : mom_score,
            "fii_activity": fii_score,
            "news"        : news_score,
        },
        "evidence"     : evidence,
        "anomalies"    : anomalies,
        "breakdown"    : all_breakdowns,
        "pe_ratio"     : stock.get("pe_ratio"),
        "roe_pct"      : stock.get("roe_pct"),
        "rsi"          : stock.get("rsi"),
        "ret_1m_pct"   : stock.get("ret_1m_pct"),
        "ret_3m_pct"   : stock.get("ret_3m_pct"),
        "market_cap_cr": stock.get("market_cap_cr"),
    }

# ============================================================
# 7. BATCH SCORER
# ============================================================

def score_all_stocks(stocks_data, fii_dii_data=None, sentiment_scores=None):
    """
    Scores all stocks and returns them sorted by score (highest first).
    """
    print(f"
✓ Scoring {len(stocks_data)} stocks...")
    scored = []
    for stock in stocks_data:
        try:
            result = score_stock(stock, fii_dii_data, sentiment_scores)
            scored.append(result)
        except Exception as e:
            pass

    # Sort by score descending
    scored.sort(key=lambda x: x["score"], reverse=True)

    # Print quick summary
    buy_count   = sum(1 for s in scored if s["signal"] == "BUY")
    watch_count = sum(1 for s in scored if s["signal"] == "WATCH")
    avoid_count = sum(1 for s in scored if s["signal"] == "AVOID")

    print(f"
✓ Scoring complete:")
    print(f"  ✅ BUY:   {buy_count} stocks")
    print(f"  👀 WATCH: {watch_count} stocks")
    print(f"  ❌ AVOID: {avoid_count} stocks")

    return scored
