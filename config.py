"""
config.py
=========
All settings for your Nifty 200 AI Advisor.
This is the ONLY file you need to edit to customise the system.
DO NOT put your actual API keys here - use Streamlit Secrets instead.
"""

import os
import streamlit as st

# ============================================================
# STEP 1: API KEYS
# These are loaded from Streamlit Secrets (safe) or .env (local)
# You will add these keys to Streamlit Cloud - instructions below
# ============================================================

def get_secret(key, default=""):
    """Safely get a secret from Streamlit Secrets or environment variables."""
    try:
        return st.secrets.get(key, os.getenv(key, default))
    except Exception:
        return os.getenv(key, default)

GEMINI_API_KEY = lambda: get_secret("GEMINI_API_KEY")
GROQ_API_KEY   = lambda: get_secret("GROQ_API_KEY")  # Backup AI

# ============================================================
# STEP 2: YOUR PERSONAL RISK PROFILE
# Edit these to match your investing style
# ============================================================

RISK_PROFILE = {
    "risk_appetite"       : "moderate",   # Options: "conservative", "moderate", "aggressive"
    "preferred_horizon"   : "short_term",  # Options: "intraday", "short_term", "long_term"
    "min_market_cap_cr"   : 5000,         # Minimum market cap in Crores (5000 = large cap focus)
    "max_pe_ratio"        : 60,           # Avoid stocks with P/E above this
    "min_roe_percent"     : 10,           # Avoid stocks with ROE below this
    "sectors_to_avoid"    : [],           # Example: ["Gambling", "Tobacco"]
    "stocks_already_held" : [],           # Example: ["RELIANCE.NS", "TCS.NS"]
    "max_single_stock_pct": 20,           # No single stock > 10% of portfolio
    "max_sector_pct"      : 40,           # No single sector > 30% of portfolio
}

# ============================================================
# STEP 3: SCORING WEIGHTS (must add up to 100)
# These weights decide how important each factor is
# ============================================================

SCORING_WEIGHTS = {
    "technical"      : 25,  # RSI, trend, moving averages, volume
    "fundamental"    : 25,  # P/E ratio, ROE, debt, profit growth
    "momentum"       : 20,  # Recent price performance vs Nifty
    "fii_activity"   : 15,  # Institutional buying/selling
    "news_sentiment" : 15,  # News tone for this stock
}

# ============================================================
# STEP 4: MARKET REGIME THRESHOLDS
# India VIX (fear index) levels that define the market mood
# ============================================================

REGIME = {
    "vix_calm"       : 13,    # Below 13 = very calm market
    "vix_normal"     : 17,    # 13-17 = normal market
    "vix_caution"    : 21,    # 17-21 = be careful
    "vix_panic"      : 25,    # Above 25 = panic, stay in cash
    "fii_sell_alarm" : -3000, # FII selling above Rs 3000 Cr = bearish
    "fii_buy_signal" : 2000,  # FII buying above Rs 2000 Cr = bullish
}

# ============================================================
# STEP 5: ANALYSIS SETTINGS
# ============================================================

ANALYSIS = {
    "top_picks_to_show"      : 10,  # Show top 10 stocks in briefing
    "min_score_for_buy"      : 65,  # Score >= 65 = BUY signal
    "min_score_for_watch"    : 50,  # Score 50-64 = WATCH
    "stocks_for_ai_analysis" : 20,  # Send top 20 to Gemini for deep analysis
    "lookback_days"          : 365, # 1 year of historical data
    "rsi_oversold"           : 35,  # RSI below this = potentially oversold
    "rsi_overbought"         : 70,  # RSI above this = potentially overbought
    "volume_spike_factor"    : 1.5, # Volume 1.5x average = unusual activity
    "news_articles_per_stock": 5,   # Fetch 5 recent news per stock
}

# ============================================================
# STEP 6: GLOBAL MARKET TRACKERS
# Yahoo Finance tickers for global signals
# ============================================================

GLOBAL_MARKETS = {
    "India VIX"         : "^INDIAVIX",
    "Nifty 50"          : "^NSEI",
    "S&P 500 (USA)"     : "^GSPC",
    "Nasdaq (USA)"      : "^IXIC",
    "Nikkei (Japan)"    : "^N225",
    "Hang Seng (HK)"    : "^HSI",
    "USD/INR"           : "INR=X",
    "Crude Oil (Brent)" : "BZ=F",
    "Gold"              : "GC=F",
}

# ============================================================
# STEP 7: NEWS SOURCES (RSS Feeds - all free)
# ============================================================

NEWS_FEEDS = {
    "Economic Times Markets" : "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "Moneycontrol Markets"   : "https://www.moneycontrol.com/rss/MCtopnews.xml",
    "NSE India Circulars"    : "https://nsearchives.nseindia.com/corporate/content/rss_corp_updates.xml",
    "Business Standard"      : "https://www.business-standard.com/rss/markets-106.rss",
    "LiveMint Markets"       : "https://www.livemint.com/rss/markets",
}

# ============================================================
# STEP 8: NIFTY 200 STOCK LIST
# Primary: fetched live from NSE Indices (most up to date)
# Backup: hardcoded list below (used if NSE fetch fails)
# ============================================================

NSE_NIFTY200_URL = "https://niftyindices.com/IndexConstituent/ind_nifty200list.csv"

# These are the Yahoo Finance symbols for Nifty 200 stocks
# NSE stocks use .NS suffix on Yahoo Finance
# This list is used as fallback if live fetch fails
NIFTY200_FALLBACK = [
    # Large Cap - Nifty 50 core
    "RELIANCE.NS","TCS.NS","HDFCBANK.NS","ICICIBANK.NS","INFY.NS",
    "HINDUNILVR.NS","KOTAKBANK.NS","BAJFINANCE.NS","SBIN.NS","BHARTIARTL.NS",
    "ASIANPAINT.NS","AXISBANK.NS","MARUTI.NS","HCLTECH.NS","SUNPHARMA.NS",
    "TITAN.NS","ULTRACEMCO.NS","WIPRO.NS","NESTLEIND.NS","POWERGRID.NS",
    "TECHM.NS","NTPC.NS","M&M.NS","ONGC.NS","TATASTEEL.NS",
    "JSWSTEEL.NS","COALINDIA.NS","HINDALCO.NS","DIVISLAB.NS","BPCL.NS",
    "DRREDDY.NS","CIPLA.NS","GRASIM.NS","SHREECEM.NS","BRITANNIA.NS",
    "BAJAJFINSV.NS","BAJAJ-AUTO.NS","TATACONSUM.NS","HEROMOTOCO.NS","EICHERMOT.NS",
    "ADANIPORTS.NS","SBILIFE.NS","HDFCLIFE.NS","INDUSINDBK.NS","APOLLOHOSP.NS",
    "UPL.NS","TATAMOTORS.NS","LT.NS","ICICIGI.NS","LTIM.NS",
    # Mid Cap additions
    "PIDILITIND.NS","GODREJCP.NS","MARICO.NS","DABUR.NS","BERGEPAINT.NS",
    "COLPAL.NS","HAVELLS.NS","VOLTAS.NS","BATAINDIA.NS","PAGEIND.NS",
    "MUTHOOTFIN.NS","CHOLAFIN.NS","DMART.NS","TRENT.NS","VBL.NS",
    "VEDL.NS","HINDZINC.NS","NMDC.NS","SAIL.NS","CONCOR.NS",
    "ADANIENT.NS","SIEMENS.NS","ABB.NS","CUMMINSIND.NS","THERMAX.NS",
    "BHEL.NS","BEL.NS","HAL.NS","MOTHERSON.NS","BOSCHLTD.NS",
    "BALKRISIND.NS","APOLLOTYRE.NS","MRF.NS","ESCORTS.NS","TVSMOTOR.NS",
    "PIIND.NS","LICHSGFIN.NS","RECLTD.NS","PFC.NS","PNB.NS",
    "BANKBARODA.NS","CANARABANK.NS","FEDERALBNK.NS","IDFCFIRSTB.NS","BANDHANBNK.NS",
    "LTF.NS","SHRIRAMFIN.NS","SUNDARMFIN.NS","HDFCAMC.NS","ABCAPITAL.NS",
    "IRCTC.NS","NAUKRI.NS","ZOMATO.NS","PERSISTENT.NS","MPHASIS.NS",
    "COFORGE.NS","KPIT.NS","TATAELXSI.NS","LTTS.NS","DIXON.NS",
    "POLYCAB.NS","KEI.NS","SRF.NS","ATUL.NS","DEEPAKNI.NS",
    "TATACHEM.NS","IPCA.NS","GRANULES.NS","ALKEM.NS","AUROPHARMA.NS",
    "TORNTPHARM.NS","METROPOLIS.NS","LALPATHLAB.NS","MAXHEALTH.NS","FORTIS.NS",
    "IGL.NS","MGL.NS","PETRONET.NS","GAIL.NS","IOC.NS","HPCL.NS",
    "ADANIGREEN.NS","ATGL.NS","GODREJPROP.NS","OBEROIRLTY.NS","PRESTIGE.NS",
    "PHOENIXLTD.NS","SOBHA.NS","MAHLIFE.NS","BRIGADE.NS","DLF.NS",
    "NYKAA.NS","ANGELONE.NS","BSE.NS","CDSL.NS","MCX.NS","IEX.NS",
    "INDUSTOWER.NS","TATACOMM.NS","HFCL.NS","ROUTE.NS","TANLA.NS",
    "JSWENERGY.NS","TORNTPOWER.NS","ADANIPOWER.NS","CESC.NS","TATAPOWER.NS",
    "NHPC.NS","SJVN.NS","IREDA.NS","IRFC.NS","HUDCO.NS",
    "MAPMYINDIA.NS","CARTRADE.NS","EASEMYTRIP.NS","DELHIVERY.NS","INDIGO.NS",
"""
config.py
=========
All settings for your Nifty 200 AI Advisor.
This is the ONLY file you need to edit to customise the system.

DO NOT put your actual API keys here - use Streamlit Secrets instead.
"""

import os
import streamlit as st

# ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
# STEP 1: API KEYS
# These are loaded from Streamlit Secrets (safe) or .env (local)
# You will add these keys to Streamlit Cloud - instructions below
# ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■

def get_secret(key, default=""):
    """Safely get a secret from Streamlit Secrets or environment variables."""
    try:
        return st.secrets.get(key, os.getenv(key, default))
    except Exception:
        return os.getenv(key, default)

GEMINI_API_KEY = lambda: get_secret("GEMINI_API_KEY")
GROQ_API_KEY   = lambda: get_secret("GROQ_API_KEY")  # Backup AI

# ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
# STEP 2: YOUR PERSONAL RISK PROFILE
# Edit these to match your investing style
# ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■

RISK_PROFILE = {
    "risk_appetite"      : "moderate",   # Options: conservative/moderate/aggressive
    "preferred_horizon"  : "long_term",  # Options: intraday/short_term/long_term
    "min_market_cap_cr"  : 5000,
    "max_pe_ratio"       : 60,
    "min_roe_percent"    : 10,
    "sectors_to_avoid"   : [],
    "stocks_already_held": [],
    "max_single_stock_pct": 10,
    "max_sector_pct"     : 30,
}

# ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
# STEP 3: SCORING WEIGHTS (must add up to 100)
# ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■

SCORING_WEIGHTS = {
    "technical"      : 25,
    "fundamental"    : 25,
    "momentum"       : 20,
    "fii_activity"   : 15,
    "news_sentiment" : 15,
}

# ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
# STEP 4: MARKET REGIME THRESHOLDS
# ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■

REGIME = {
    "vix_calm"       : 13,
    "vix_normal"     : 17,
    "vix_caution"    : 21,
    "vix_panic"      : 25,
    "fii_sell_alarm" : -3000,
    "fii_buy_signal" : 2000,
}

# ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
# STEP 5: ANALYSIS SETTINGS
# ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■

ANALYSIS = {
    "top_picks_to_show"    : 10,
    "min_score_for_buy"    : 65,
    "min_score_for_watch"  : 50,
    "stocks_for_ai_analysis": 20,
    "lookback_days"        : 365,
    "rsi_oversold"         : 35,
    "rsi_overbought"       : 70,
    "volume_spike_factor"  : 1.5,
    "news_articles_per_stock": 5,
}

# ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
# STEP 6: GLOBAL MARKET TRACKERS
# ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■

GLOBAL_MARKETS = {
    "India VIX"        : "^INDIAVIX",
    "Nifty 50"         : "^NSEI",
    "S&P 500 (USA)"    : "^GSPC",
    "Nasdaq (USA)"     : "^IXIC",
    "Nikkei (Japan)"   : "^N225",
    "Hang Seng (HK)"   : "^HSI",
    "USD/INR"          : "INR=X",
    "Crude Oil (Brent)": "BZ=F",
    "Gold"             : "GC=F",
}

# ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
# STEP 7: NEWS SOURCES (RSS Feeds)
# ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■

NEWS_FEEDS = {
    "Economic Times Markets":
        "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",

    "Moneycontrol Markets":
        "https://www.moneycontrol.com/rss/MCtopnews.xml",

    "NSE India Circulars":
        "https://nsearchives.nseindia.com/corporate/content/rss_corp_updates.xml",

    "Business Standard":
        "https://www.business-standard.com/rss/markets-106.rss",

    "LiveMint Markets":
        "https://www.livemint.com/rss/markets",
}

# ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
# STEP 8: NIFTY 200 STOCK LIST
# ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■

NSE_NIFTY200_URL = "https://niftyindices.com/IndexConstituent/ind_nifty200list.csv"

NIFTY200_FALLBACK = [
    "RELIANCE.NS","TCS.NS","HDFCBANK.NS","ICICIBANK.NS","INFY.NS",
    "HINDUNILVR.NS","KOTAKBANK.NS","BAJFINANCE.NS","SBIN.NS","BHARTIARTL.NS",
    "ASIANPAINT.NS","AXISBANK.NS","MARUTI.NS","HCLTECH.NS","SUNPHARMA.NS",
    "TITAN.NS","ULTRACEMCO.NS","WIPRO.NS","NESTLEIND.NS","POWERGRID.NS",
    "TECHM.NS","NTPC.NS","M&M.NS","ONGC.NS","TATASTEEL.NS",
    "JSWSTEEL.NS","COALINDIA.NS","HINDALCO.NS","DIVISLAB.NS","BPCL.NS",
    "DRREDDY.NS","CIPLA.NS","GRASIM.NS","SHREECEM.NS","BRITANNIA.NS",
    "BAJAJFINSV.NS","BAJAJ-AUTO.NS","TATACONSUM.NS","HEROMOTOCO.NS","EICHERMOT.NS",
    "ADANIPORTS.NS","SBILIFE.NS","HDFCLIFE.NS","INDUSINDBK.NS","APOLLOHOSP.NS",
    "UPL.NS","TATAMOTORS.NS","LT.NS","ICICIGI.NS","LTIM.NS",

    "PIDILITIND.NS","GODREJCP.NS","MARICO.NS","DABUR.NS","BERGEPAINT.NS",
    "COLPAL.NS","HAVELLS.NS","VOLTAS.NS","BATAINDIA.NS","PAGEIND.NS",
    "MUTHOOTFIN.NS","CHOLAFIN.NS","DMART.NS","TRENT.NS","VBL.NS",
    "VEDL.NS","HINDZINC.NS","NMDC.NS","SAIL.NS","CONCOR.NS",
    "ADANIENT.NS","SIEMENS.NS","ABB.NS","CUMMINSIND.NS","THERMAX.NS",
    "BHEL.NS","BEL.NS","HAL.NS","MOTHERSON.NS","BOSCHLTD.NS",
    "BALKRISIND.NS","APOLLOTYRE.NS","MRF.NS","ESCORTS.NS","TVSMOTOR.NS",
    "PIIND.NS","LICHSGFIN.NS","RECLTD.NS","PFC.NS","PNB.NS",
    "BANKBARODA.NS","CANARABANK.NS","FEDERALBNK.NS","IDFCFIRSTB.NS","BANDHANBNK.NS",
    "LTF.NS","SHRIRAMFIN.NS","SUNDARMFIN.NS","HDFCAMC.NS","ABCAPITAL.NS",
    "IRCTC.NS","NAUKRI.NS","ZOMATO.NS","PERSISTENT.NS","MPHASIS.NS",
    "COFORGE.NS","KPIT.NS","TATAELXSI.NS","LTTS.NS","DIXON.NS",
    "POLYCAB.NS","KEI.NS","SRF.NS","ATUL.NS","DEEPAKNI.NS",
    "TATACHEM.NS","IPCA.NS","GRANULES.NS","ALKEM.NS","AUROPHARMA.NS",
    "TORNTPHARM.NS","METROPOLIS.NS","LALPATHLAB.NS","MAXHEALTH.NS","FORTIS.NS",
    "IGL.NS","MGL.NS","PETRONET.NS","GAIL.NS","IOC.NS","HPCL.NS",
    "ADANIGREEN.NS","ATGL.NS","GODREJPROP.NS","OBEROIRLTY.NS","PRESTIGE.NS",
    "PHOENIXLTD.NS","SOBHA.NS","MAHLIFE.NS","BRIGADE.NS","DLF.NS",
    "NYKAA.NS","ANGELONE.NS","BSE.NS","CDSL.NS","MCX.NS","IEX.NS",
    "INDUSTOWER.NS","TATACOMM.NS","HFCL.NS","ROUTE.NS","TANLA.NS",
    "JSWENERGY.NS","TORNTPOWER.NS","ADANIPOWER.NS","CESC.NS","TATAPOWER.NS",
    "NHPC.NS","SJVN.NS","IREDA.NS","IRFC.NS","HUDCO.NS",
    "MAPMYINDIA.NS","CARTRADE.NS","EASEMYTRIP.NS","DELHIVERY.NS","INDIGO.NS",
    "SPICEJET.NS","GMRINFRA.NS","IRB.NS","KNR.NS","AHLUCONT.NS",
    "NATCOPHARM.NS","JBCHEPHARM.NS","FDC.NS","GLAXO.NS","PFIZER.NS",
    "GLAND.NS","ERIS.NS","SEQUENT.NS","CLEAN.NS","NEOGEN.NS",
    "GUJGASLTD.NS","AEGISCHEM.NS","CASTROLIND.NS","MRPL.NS","CHENNPETRO.NS",
    "MFSL.NS","STARHEALTH.NS","NIACL.NS","GICRE.NS","MAXFINSERV.NS",
    "AAVAS.NS","CANFINHOME.NS","HOMEFIRST.NS","APTUS.NS","RBLBANK.NS",
    "KARURVYSYA.NS","SOUTHBANK.NS","DCBBANK.NS","UJJIVANSFB.NS","EQUITASBNK.NS",
]

# ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
# STEP 9: AI PROMPT SETTINGS
# ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■

AI_SETTINGS = {
    "model"        : "gemini-1.5-flash",
    "temperature"  : 0.2,
    "max_tokens"   : 2048,
    "backup_model" : "llama3-70b-8192",
}

# Timezone
TIMEZONE = "Asia/Kolkata"
