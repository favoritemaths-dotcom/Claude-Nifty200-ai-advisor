"""
market_data.py
==============
Fetches all market data:
- Nifty 200 stock list (from NSE)
- Price history and technical indicators
- Fundamentals (P/E, ROE, Debt etc.)
- India VIX and global markets
- NSE official data (FII/DII, bulk deals)

All data from yFinance and NSE official downloads.
No scraping. No API key needed for this file.
"""

import yfinance as yf
import pandas as pd
import numpy as np
import requests
import io
import time
import pytz
from datetime import datetime, timedelta
from config import (
    NIFTY200_FALLBACK, NSE_NIFTY200_URL,
    GLOBAL_MARKETS, ANALYSIS, REGIME
)

IST = pytz.timezone("Asia/Kolkata")

# ─────────────────────────────────────────────────────────────
# 1. NIFTY 200 STOCK LIST
# ─────────────────────────────────────────────────────────────

def get_nifty200_stocks():
    """
    Fetches the current Nifty 200 stock list from NSE Indices.
    Falls back to hardcoded list if NSE is unavailable.
    Returns a list of Yahoo Finance symbols (with .NS suffix).
    """
    print("📋 Fetching Nifty 200 stock list from NSE Indices...")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(NSE_NIFTY200_URL, headers=headers, timeout=15)

        if response.status_code == 200:
            df = pd.read_csv(io.StringIO(response.text))
            # NSE CSV has a 'Symbol' column
            symbols = df["Symbol"].dropna().tolist()
            # Add .NS suffix for Yahoo Finance
            yf_symbols = [f"{s.strip()}.NS" for s in symbols if s.strip()]
            print(f"✅ Live Nifty 200 fetched: {len(yf_symbols)} stocks")
            return yf_symbols
        else:
            print(f"⚠️  NSE returned HTTP {response.status_code}")

    except Exception as e:
        print(f"⚠️  Could not fetch live Nifty 200 list: {e}")
        print("   Using backup stock list instead...")

    print(f"📋 Using backup list: {len(NIFTY200_FALLBACK)} stocks")
    return NIFTY200_FALLBACK


# ─────────────────────────────────────────────────────────────
# 2. PRICE AND TECHNICAL INDICATORS
# ─────────────────────────────────────────────────────────────

def calculate_rsi(prices, period=14):
    """Calculate RSI (Relative Strength Index) - measures momentum."""
    delta = prices.diff()
    gain  = delta.where(delta > 0, 0).rolling(period).mean()
    loss  = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs    = gain / (loss + 1e-10)  # avoid division by zero
    return 100 - (100 / (1 + rs))

def calculate_macd(prices, fast=12, slow=26, signal=9):
    """Calculate MACD - measures trend direction."""
    ema_fast   = prices.ewm(span=fast, adjust=False).mean()
    ema_slow   = prices.ewm(span=slow, adjust=False).mean()
    macd_line  = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram  = macd_line - signal_line
    return macd_line, signal_line, histogram

def get_stock_technicals(symbol, retries=2):
    """
    Fetches 1 year of price data and calculates:
    - RSI, MACD, Moving Averages
    - Volume analysis
    - Price momentum (1M, 3M, 6M returns)

    Returns a dict with all technical data.
    Returns None if data unavailable.

    FIX #4: Added retry logic with exponential backoff for rate-limit errors.
    Previously any error (including HTTP 429 Too Many Requests from Yahoo Finance)
    silently returned None with no log and no retry, causing 60-100+ stocks to
    fail mid-run when Yahoo Finance started throttling, producing a sparse
    briefing that looked successful.
    """
    for attempt in range(retries + 1):
        try:
            ticker = yf.Ticker(symbol)
            hist   = ticker.history(period="1y", auto_adjust=True)

            if hist.empty or len(hist) < 50:
                return None

            close  = hist["Close"]
            volume = hist["Volume"]

            # Moving Averages
            ma20   = close.rolling(20).mean()
            ma50   = close.rolling(50).mean()
            ma200  = close.rolling(200).mean() if len(close) >= 200 else close.rolling(len(close)).mean()

            # RSI
            rsi = calculate_rsi(close)

            # MACD
            macd_line, signal_line, histogram = calculate_macd(close)

            # Volume analysis
            avg_volume_20d = volume.rolling(20).mean()
            volume_ratio   = volume.iloc[-1] / (avg_volume_20d.iloc[-1] + 1)

            # Current values
            current_price  = close.iloc[-1]
            current_rsi    = rsi.iloc[-1]
            current_macd   = macd_line.iloc[-1]
            current_signal = signal_line.iloc[-1]

            # Price returns
            ret_1m  = ((current_price / close.iloc[-22]) - 1) * 100  if len(close) >= 22  else 0
            ret_3m  = ((current_price / close.iloc[-66]) - 1) * 100  if len(close) >= 66  else 0
            ret_6m  = ((current_price / close.iloc[-132]) - 1) * 100 if len(close) >= 132 else 0
            ret_1y  = ((current_price / close.iloc[0]) - 1) * 100

            # Trend detection
            above_ma20  = current_price > ma20.iloc[-1]
            above_ma50  = current_price > ma50.iloc[-1]
            above_ma200 = current_price > ma200.iloc[-1]
            macd_bullish = current_macd > current_signal

            # 52-week high/low
            high_52w = close.max()
            low_52w  = close.min()
            pct_from_high = ((current_price / high_52w) - 1) * 100
            pct_from_low  = ((current_price / low_52w) - 1) * 100

            return {
                "symbol"          : symbol,
                "current_price"   : round(current_price, 2),
                "rsi"             : round(current_rsi, 1),
                "macd_bullish"    : bool(macd_bullish),
                "above_ma20"      : bool(above_ma20),
                "above_ma50"      : bool(above_ma50),
                "above_ma200"     : bool(above_ma200),
                "volume_ratio"    : round(volume_ratio, 2),
                "ret_1m_pct"      : round(ret_1m, 2),
                "ret_3m_pct"      : round(ret_3m, 2),
                "ret_6m_pct"      : round(ret_6m, 2),
                "ret_1y_pct"      : round(ret_1y, 2),
                "high_52w"        : round(high_52w, 2),
                "low_52w"         : round(low_52w, 2),
                "pct_from_high"   : round(pct_from_high, 2),
                "pct_from_low"    : round(pct_from_low, 2),
                "avg_volume_20d"  : int(avg_volume_20d.iloc[-1]),
                "last_volume"     : int(volume.iloc[-1]),
                "data_points"     : len(close),
            }

        except Exception as e:
            err_str = str(e).lower()
            # Detect rate-limiting — back off and retry
            if "429" in err_str or "too many" in err_str or "rate" in err_str:
                wait_secs = 30 * (attempt + 1)  # 30s, then 60s
                print(f"  ⚠ Rate limit on {symbol} (attempt {attempt+1}), waiting {wait_secs}s...")
                time.sleep(wait_secs)
                continue
            else:
                # Non-rate-limit error — log it and give up on this stock
                print(f"  ⚠ Technical data failed for {symbol}: {type(e).__name__}: {e}")
                return None

    # Exhausted retries
    print(f"  ✗ {symbol}: gave up after {retries+1} attempts (persistent rate limit)")
    return None


# ─────────────────────────────────────────────────────────────
# 3. FUNDAMENTAL DATA
# ─────────────────────────────────────────────────────────────

def get_stock_fundamentals(symbol, retries=2):
    """
    Fetches fundamental data from Yahoo Finance:
    - P/E ratio, P/B ratio
    - ROE, ROCE (approximated)
    - Debt to Equity
    - Market Cap
    - Dividend Yield
    - Revenue and Profit growth

    Returns a dict with fundamental data.
    Returns None if data unavailable.

    FIX #4 (same): Added retry + logging for rate-limit errors.
    """
    for attempt in range(retries + 1):
        try:
            ticker = yf.Ticker(symbol)
            info   = ticker.info

            if not info or info.get("regularMarketPrice") is None:
                return None

            # Key fundamental metrics
            pe_ratio       = info.get("trailingPE")        or info.get("forwardPE")
            pb_ratio       = info.get("priceToBook")
            roe            = info.get("returnOnEquity")
            debt_to_equity = info.get("debtToEquity")
            market_cap     = info.get("marketCap")
            dividend_yield = info.get("dividendYield")
            revenue_growth = info.get("revenueGrowth")
            earnings_growth= info.get("earningsGrowth")
            profit_margins = info.get("profitMargins")
            gross_margins  = info.get("grossMargins")
            current_ratio  = info.get("currentRatio")
            book_value     = info.get("bookValue")
            eps            = info.get("trailingEps")
            beta           = info.get("beta")
            sector         = info.get("sector",       "Unknown")
            industry       = info.get("industry",     "Unknown")
            company_name   = info.get("longName",     symbol)

            # Convert to percentage where needed
            roe_pct            = round(roe * 100, 1)            if roe            else None
            dividend_yield_pct = round(dividend_yield * 100, 2) if dividend_yield else None
            revenue_growth_pct = round(revenue_growth * 100, 1) if revenue_growth else None
            earnings_growth_pct= round(earnings_growth * 100, 1)if earnings_growth else None
            profit_margins_pct = round(profit_margins * 100, 1) if profit_margins else None

            return {
                "symbol"             : symbol,
                "company_name"       : company_name,
                "sector"             : sector,
                "industry"           : industry,
                "pe_ratio"           : round(pe_ratio, 1)        if pe_ratio else None,
                "pb_ratio"           : round(pb_ratio, 2)        if pb_ratio else None,
                "roe_pct"            : roe_pct,
                "debt_to_equity"     : round(debt_to_equity, 2)  if debt_to_equity else None,
                "market_cap_cr"      : round(market_cap / 1e7, 0)if market_cap else None,
                "dividend_yield_pct" : dividend_yield_pct,
                "revenue_growth_pct" : revenue_growth_pct,
                "earnings_growth_pct": earnings_growth_pct,
                "profit_margins_pct" : profit_margins_pct,
                "gross_margins_pct"  : round(gross_margins * 100, 1) if gross_margins else None,
                "current_ratio"      : round(current_ratio, 2)   if current_ratio else None,
                "eps"                : round(eps, 2)              if eps else None,
                "beta"               : round(beta, 2)             if beta else None,
                "book_value"         : round(book_value, 2)       if book_value else None,
            }

        except Exception as e:
            err_str = str(e).lower()
            if "429" in err_str or "too many" in err_str or "rate" in err_str:
                wait_secs = 30 * (attempt + 1)
                print(f"  ⚠ Rate limit on {symbol} fundamentals (attempt {attempt+1}), waiting {wait_secs}s...")
                time.sleep(wait_secs)
                continue
            else:
                print(f"  ⚠ Fundamental data failed for {symbol}: {type(e).__name__}: {e}")
                return None

    print(f"  ✗ {symbol} fundamentals: gave up after {retries+1} attempts")
    return None


# ─────────────────────────────────────────────────────────────
# 4. GLOBAL MARKETS AND MACRO DATA
# ─────────────────────────────────────────────────────────────

def get_global_macro():
    """
    Fetches global market data:
    - India VIX (fear index)
    - Global indices (S&P, Nasdaq, Nikkei, Hang Seng)
    - USD/INR exchange rate
    - Crude oil price
    - Gold price

    Returns a dict with all macro data.
    """
    print("🌍 Fetching global macro data...")
    macro = {}

    for name, ticker_sym in GLOBAL_MARKETS.items():
        try:
            t    = yf.Ticker(ticker_sym)
            hist = t.history(period="5d")

            if not hist.empty:
                current   = hist["Close"].iloc[-1]
                prev      = hist["Close"].iloc[-2] if len(hist) >= 2 else current
                chg_pct   = ((current / prev) - 1) * 100

                macro[name] = {
                    "value"      : round(current, 2),
                    "change_pct" : round(chg_pct, 2),
                    "direction"  : "UP" if chg_pct > 0 else "DOWN",
                    "ticker"     : ticker_sym,
                }
        except Exception as e:
            print(f"  ⚠ Macro data failed for {name} ({ticker_sym}): {e}")
            macro[name] = {"value": None, "change_pct": None, "direction": "UNKNOWN"}

    print(f"✅ Global macro fetched for {len(macro)} indicators")
    return macro


# ─────────────────────────────────────────────────────────────
# 5. NSE OFFICIAL DATA DOWNLOADS (Legal, free, official files)
# ─────────────────────────────────────────────────────────────

def get_nse_bhavcopy():
    """
    Downloads NSE's official end-of-day price file (Bhavcopy).
    This is a publicly available CSV that NSE publishes every trading day.
    Returns a DataFrame with all NSE stocks' daily data.
    """
    print("📥 Downloading NSE Bhavcopy (official EOD data)...")
    try:
        today = datetime.now(IST)

        # Try last 5 days (in case of holidays or weekends)
        for days_back in range(1, 6):
            date = today - timedelta(days=days_back)
            if date.weekday() >= 5:  # Skip Saturday(5) and Sunday(6)
                continue

            url = f"https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{date.strftime('%Y%m%d')}_F_0000.csv"

            headers = {
                "User-Agent": "Mozilla/5.0",
                "Referer"   : "https://www.nseindia.com"
            }

            resp = requests.get(url, headers=headers, timeout=20)
            if resp.status_code == 200:
                df = pd.read_csv(io.StringIO(resp.text))
                print(f"✅ Bhavcopy downloaded for {date.strftime('%d %b %Y')}: {len(df)} records")
                return df

        print("⚠️  Could not download Bhavcopy (might be holiday). Using yFinance instead.")
        return None

    except Exception as e:
        print(f"⚠️  Bhavcopy download failed: {e}")
        return None


def get_fii_dii_data():
    """
    Downloads FII/DII institutional flow data from NSE.
    Published every trading day after 6:30 PM.
    Returns a dict with FII and DII net buy/sell figures.
    """
    print("🏦 Fetching FII/DII flow data from NSE...")
    try:
        url     = "https://nsearchives.nseindia.com/web/sites/default/files/inline-files/fii_dii.csv"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer"   : "https://www.nseindia.com"
        }
        resp = requests.get(url, headers=headers, timeout=20)

        if resp.status_code == 200:
            df = pd.read_csv(io.StringIO(resp.text))
            if not df.empty:
                latest = df.iloc[0]
                fii_net = None
                dii_net = None

                # Column names vary — try multiple possibilities
                for col in df.columns:
                    col_lower = col.lower()
                    if "fii" in col_lower and "net" in col_lower:
                        try:
                            fii_net = float(str(latest[col]).replace(",",""))
                        except Exception:
                            pass
                    if "dii" in col_lower and "net" in col_lower:
                        try:
                            dii_net = float(str(latest[col]).replace(",",""))
                        except Exception:
                            pass

                # FIX: Use explicit None checks here too (consistent with regime.py fix)
                result = {
                    "fii_net_cr"  : fii_net,
                    "dii_net_cr"  : dii_net,
                    "fii_signal"  : "BUYING" if (fii_net is not None and fii_net > 0)
                                    else "SELLING" if (fii_net is not None and fii_net < 0)
                                    else "UNKNOWN",
                    "dii_signal"  : "BUYING" if (dii_net is not None and dii_net > 0)
                                    else "SELLING" if (dii_net is not None and dii_net < 0)
                                    else "UNKNOWN",
                    "source"      : "NSE Official",
                }
                print(f"✅ FII: {fii_net} Cr | DII: {dii_net} Cr")
                return result
        else:
            print(f"⚠️  NSE FII/DII returned HTTP {resp.status_code} "
                  f"(normal before 6:30 PM IST or on weekends)")

    except Exception as e:
        print(f"⚠️  FII/DII data unavailable: {e}")

    # Return unknown state if fetch fails
    return {"fii_net_cr": None, "dii_net_cr": None,
            "fii_signal": "UNKNOWN", "dii_signal": "UNKNOWN",
            "source": "unavailable"}


# ─────────────────────────────────────────────────────────────
# 6. BATCH STOCK DATA FETCHER
# ─────────────────────────────────────────────────────────────

def get_all_stocks_data(symbols, max_stocks=None, progress_cb=None):
    """
    Main function — fetches technical + fundamental data for
    all Nifty 200 stocks. Shows progress.

    Returns a list of dicts, one per stock.

    FIX #4 (continued): Increased inter-request delay from 0.3s → 1.0s.
    Yahoo Finance's unofficial API throttles at ~60-100 rapid requests.
    At 0.3s delay, a 200-stock run hits rate limits around stock 60-80,
    silently returning None for the rest. At 1.0s, 200 stocks = ~6-7 min
    of delay total — acceptable given the overall run time.
    """
    if max_stocks:
        symbols = symbols[:max_stocks]

    total    = len(symbols)
    results  = []
    failed   = []
    skipped  = 0

    print(f"\n📊 Fetching data for {total} Nifty 200 stocks...")
    print("   (This takes 10-20 minutes — be patient)\n")

    for i, symbol in enumerate(symbols):
        # Progress indicator every 10 stocks
        if (i + 1) % 10 == 0 or i == 0:
            print(f"   Progress: {i+1}/{total} stocks | "
                  f"Success: {len(results)} | Failed: {len(failed)}")

        tech  = get_stock_technicals(symbol)
        fund  = get_stock_fundamentals(symbol)

        if tech is None and fund is None:
            failed.append(symbol)
            skipped += 1
        else:
            # Merge technical and fundamental data
            stock_data = {}
            if tech:  stock_data.update(tech)
            if fund:  stock_data.update({k: v for k, v in fund.items() if k != "symbol"})

            if stock_data:
                results.append(stock_data)

        if progress_cb and ((i + 1) % 5 == 0 or i + 1 == total):
            try:
                progress_cb(i + 1, total, symbol, len(results), len(failed))
            except Exception:
                pass

        # FIX: Increased delay from 0.3s to 1.0s to avoid Yahoo Finance rate limiting.
        # At 200 stocks × 1.0s = ~3.3 min extra. Worth it to prevent 150+ silent failures.
        time.sleep(1.0)

    print(f"\n✅ Data fetched: {len(results)} stocks successful, {len(failed)} failed")
    if failed:
        print(f"   Failed stocks: {', '.join(failed[:10])}{'...' if len(failed) > 10 else ''}")
        if len(failed) > 30:
            print(f"   ⚠ {len(failed)} failures — likely Yahoo Finance rate limiting.")
            print(f"     Consider re-running or increasing the sleep delay above 1.0s.")

    return results
