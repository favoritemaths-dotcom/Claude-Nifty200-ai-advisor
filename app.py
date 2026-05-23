"""
app.py
======
The Streamlit dashboard — what you open every morning at 9 AM.
Shows the complete AI briefing in a clean, easy-to-read format.

To run locally: streamlit run app.py
Deployed on: Streamlit Community Cloud (free)
"""

import streamlit as st
import json
import os
import subprocess
import sys
from datetime import datetime
import pytz

# ── Page config (must be first Streamlit command) ────────────
st.set_page_config(
    page_title = "Nifty 200 AI Advisor",
    page_icon  = "📈",
    layout     = "wide",
    initial_sidebar_state = "expanded",
)

IST = pytz.timezone("Asia/Kolkata")

# ── Load the briefing data ───────────────────────────────────
def load_briefing():
    try:
        if os.path.exists("latest_briefing.json"):
            with open("latest_briefing.json", "r") as f:
                return json.load(f)
    except Exception as e:
        st.error(f"Error loading briefing: {e}")
    return None

# ── Custom CSS ───────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1a3a6e, #2d7a4f);
        color: white; padding: 20px; border-radius: 10px;
        margin-bottom: 20px; text-align: center;
    }
    .regime-box {
        padding: 15px; border-radius: 8px;
        color: white; margin-bottom: 15px;
    }
    .stock-card {
        background: #f8f9fa; border: 1px solid #dee2e6;
        border-radius: 8px; padding: 15px; margin-bottom: 10px;
    }
    .buy-badge  { background:#1B5E20; color:white; padding:3px 10px; border-radius:12px; font-weight:bold; }
    .watch-badge{ background:#E65100; color:white; padding:3px 10px; border-radius:12px; font-weight:bold; }
    .avoid-badge{ background:#8B0000; color:white; padding:3px 10px; border-radius:12px; font-weight:bold; }
    .score-high { color:#1B5E20; font-size:24px; font-weight:bold; }
    .score-mid  { color:#E65100; font-size:24px; font-weight:bold; }
    .score-low  { color:#8B0000; font-size:24px; font-weight:bold; }
    .evidence-box {
        background:#e8f0fe; border-left:4px solid #1a3a6e;
        padding:10px; border-radius:4px; margin:8px 0;
        font-size:13px;
    }
    .anomaly-box {
        background:#fff3e0; border-left:4px solid #E65100;
        padding:10px; border-radius:4px; margin:8px 0;
        font-size:13px;
    }
    .metric-card {
        background:white; border:1px solid #dee2e6;
        border-radius:8px; padding:12px; text-align:center;
    }
</style>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════════
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/5/5e/NSE_logo.svg/200px-NSE_logo.svg.png",
             width=150, caption="Nifty 200 Coverage")
    st.markdown("---")
    st.markdown("### 🤖 AI Advisor Controls")

    # Manual run button
    if st.button("▶️ Run Analysis Now", type="primary", use_container_width=True):
        with st.spinner("Running analysis... (10-15 minutes for full run)"):
            try:
                result = subprocess.run(
                    [sys.executable, "agent.py", "--quick"],
                    capture_output=True, text=True, timeout=1800
                )
                if result.returncode == 0:
                    st.success("✅ Analysis complete! Refresh the page.")
                else:
                    st.error(f"Analysis failed: {result.stderr[:500]}")
            except subprocess.TimeoutExpired:
                st.error("Analysis timed out after 30 minutes")
            except Exception as e:
                st.error(f"Error: {e}")

    st.markdown("---")

    # Quick test button
    if st.button("⚡ Quick Test (30 stocks)", use_container_width=True):
        with st.spinner("Quick test running..."):
            try:
                result = subprocess.run(
                    [sys.executable, "agent.py", "--quick"],
                    capture_output=True, text=True, timeout=600
                )
                if result.returncode == 0:
                    st.success("✅ Done! Refresh page.")
                else:
                    st.error(result.stderr[:300])
            except Exception as e:
                st.error(f"Error: {e}")

    st.markdown("---")
    st.markdown("### ℹ️ About")
    st.markdown("""
    **Nifty 200 AI Advisor**
    - Covers all Nifty 200 stocks
    - Runs daily at 8:30 AM IST
    - Powered by Google Gemini AI
    - Data from Fyers + NSE + yFinance
    
    *Not financial advice. Always apply
    your own judgment before trading.*
    """)


# ════════════════════════════════════════════════════════════
# MAIN HEADER
# ════════════════════════════════════════════════════════════
st.markdown("""
<div class="main-header">
    <h1>📈 Nifty 200 AI Advisor</h1>
    <p style="margin:0; opacity:0.9">Your Personal Institutional-Grade Research Intelligence</p>
</div>
""", unsafe_allow_html=True)

# Load data
briefing = load_briefing()

if not briefing:
    st.info("""
    ### 👋 Welcome! No briefing found yet.

    **To generate your first briefing:**
    1. Click **'Quick Test (30 stocks)'** in the sidebar to test with 30 stocks
    2. Wait 5-10 minutes for it to complete
    3. Refresh this page

    **For full Nifty 200 analysis:**
    - Click **'Run Analysis Now'** (takes 15-20 minutes)
    - Or wait for automatic 8:30 AM run

    **First time? Make sure you've added your API keys in Streamlit Secrets!**
    """)
    st.stop()

# ════════════════════════════════════════════════════════════
# STATUS BAR
# ════════════════════════════════════════════════════════════
status      = briefing.get("status", "unknown")
gen_time    = briefing.get("generated_at_str", "Unknown")
stocks_done = briefing.get("stocks_scored", 0)
duration    = briefing.get("duration_minutes", 0)

col1, col2, col3, col4 = st.columns(4)
with col1:
    icon = "✅" if status == "success" else "⚠️" if status == "no_trade" else "❌"
    st.metric("Status", f"{icon} {status.upper()}")
with col2:
    st.metric("Generated At", gen_time.split(",")[1].strip() if "," in gen_time else gen_time)
with col3:
    st.metric("Stocks Analysed", f"{stocks_done}/200")
with col4:
    st.metric("Run Duration", f"{duration} min")

st.markdown("---")

# ════════════════════════════════════════════════════════════
# NO TRADE DAY
# ════════════════════════════════════════════════════════════
if status == "no_trade":
    reason = briefing.get("no_trade_reason", "Market conditions unfavourable")
    st.error(f"""
    ## ⛔ NO TRADE TODAY

    **{reason}**

    The AI has determined that market conditions do not support new positions today.
    This is not a failure — knowing when NOT to trade is as important as knowing when to trade.

    Come back tomorrow morning for the next briefing.
    """)

# ════════════════════════════════════════════════════════════
# MARKET REGIME
# ════════════════════════════════════════════════════════════
regime = briefing.get("market_regime", {})
if regime:
    regime_color = regime.get("color", "#795548")
    st.markdown(f"""
    <div class="regime-box" style="background:{regime_color}">
        <h3 style="margin:0; color:white">Market Regime: {regime.get('label','Unknown')}</h3>
        <p style="margin:5px 0 0 0; color:rgba(255,255,255,0.9)">{regime.get('description','')}</p>
        <p style="margin:8px 0 0 0; color:white; font-weight:bold">
        💡 {regime.get('recommendation','')}
        </p>
    </div>
    """, unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# GLOBAL MACRO PANEL
# ════════════════════════════════════════════════════════════
macro = briefing.get("global_macro", {})
if macro:
    st.subheader("🌍 Global Macro Snapshot")
    cols = st.columns(len(macro))
    for i, (name, data) in enumerate(macro.items()):
        with cols[i % len(cols)]:
            val = data.get("value")
            chg = data.get("change_pct", 0) or 0
            if val:
                delta_color = "normal" if chg >= 0 else "inverse"
                st.metric(
                    label = name,
                    value = f"{val:,.2f}",
                    delta = f"{chg:+.2f}%",
                    delta_color = delta_color
                )
    st.markdown("---")

# ════════════════════════════════════════════════════════════
# FII/DII FLOWS
# ════════════════════════════════════════════════════════════
fii_dii = briefing.get("fii_dii", {})
if fii_dii and fii_dii.get("fii_net_cr") is not None:
    fii_net = fii_dii.get("fii_net_cr", 0)
    dii_net = fii_dii.get("dii_net_cr", 0)
    fii_col = "#1B5E20" if fii_net > 0 else "#8B0000"
    dii_col = "#1B5E20" if dii_net and dii_net > 0 else "#8B0000"

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""<div class="metric-card">
        <div style="font-size:12px; color:#666">FII (Foreign Investors)</div>
        <div style="font-size:22px; font-weight:bold; color:{fii_col}">
            {'▲' if fii_net > 0 else '▼'} ₹{abs(fii_net):,.0f} Cr
        </div>
        <div style="font-size:12px; color:{fii_col}">{fii_dii.get('fii_signal','')}</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        if dii_net:
            st.markdown(f"""<div class="metric-card">
            <div style="font-size:12px; color:#666">DII (Domestic Institutions)</div>
            <div style="font-size:22px; font-weight:bold; color:{dii_col}">
                {'▲' if dii_net > 0 else '▼'} ₹{abs(dii_net):,.0f} Cr
            </div>
            <div style="font-size:12px; color:{dii_col}">{fii_dii.get('dii_signal','')}</div>
            </div>""", unsafe_allow_html=True)
    with col3:
        net_total = (fii_net or 0) + (dii_net or 0)
        net_col   = "#1B5E20" if net_total > 0 else "#8B0000"
        st.markdown(f"""<div class="metric-card">
        <div style="font-size:12px; color:#666">Net Combined Flow</div>
        <div style="font-size:22px; font-weight:bold; color:{net_col}">
            {'▲' if net_total > 0 else '▼'} ₹{abs(net_total):,.0f} Cr
        </div>
        <div style="font-size:12px; color:{net_col}">
            {'Market Supported' if net_total > 0 else 'Market Under Pressure'}
        </div>
        </div>""", unsafe_allow_html=True)
    st.markdown("---")

# ════════════════════════════════════════════════════════════
# AI MACRO CONTEXT
# ════════════════════════════════════════════════════════════
macro_ctx = briefing.get("macro_context")
if macro_ctx and not macro_ctx.get("parse_error"):
    with st.expander("🤖 AI Macro & Geopolitical Analysis — Click to Expand", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 📰 Today's Key Themes")
            themes = macro_ctx.get("key_themes", [])
            for theme in themes:
                st.info(f"• {theme}")

            geo = macro_ctx.get("geopolitical_reading", {})
            if geo:
                st.markdown("#### 🌐 Geopolitical Reading")
                if geo.get("active_themes"):
                    st.write(f"**Active Themes:** {geo['active_themes']}")
                if geo.get("india_specific_impact"):
                    st.write(f"**India Impact:** {geo['india_specific_impact']}")
                if geo.get("historical_parallel"):
                    st.markdown(f"""<div class="evidence-box">
                    📚 Historical Parallel: {geo['historical_parallel']}
                    </div>""", unsafe_allow_html=True)

        with col2:
            sectors = macro_ctx.get("sector_impacts", {})
            if sectors:
                st.markdown("#### ✅ Sectors Benefiting Today")
                for s in sectors.get("positive_sectors", []):
                    stocks_str = ", ".join(s.get("example_stocks", []))
                    st.success(f"**{s.get('sector','')}** — {s.get('reason','')}\n*Examples: {stocks_str}*")

                st.markdown("#### ❌ Sectors Under Pressure")
                for s in sectors.get("negative_sectors", []):
                    stocks_str = ", ".join(s.get("example_stocks", []))
                    st.error(f"**{s.get('sector','')}** — {s.get('reason','')}\n*Examples: {stocks_str}*")

        guidance = macro_ctx.get("trading_guidance", {})
        if guidance:
            bias  = guidance.get("overall_bias", "NEUTRAL")
            b_col = "#1B5E20" if "BULL" in bias else "#8B0000" if "BEAR" in bias else "#795548"
            st.markdown(f"""
            <div style="background:{b_col}; color:white; padding:12px; border-radius:8px; margin-top:10px">
            <b>Overall Bias: {bias}</b> &nbsp;|&nbsp;
            ⚠️ Key Risk: {guidance.get('key_risk','')} &nbsp;|&nbsp;
            💡 Opportunity: {guidance.get('opportunity','')}
            </div>
            """, unsafe_allow_html=True)

st.markdown("---")

# ════════════════════════════════════════════════════════════
# TOP PICKS
# ════════════════════════════════════════════════════════════
top_picks = briefing.get("top_picks", [])

st.subheader(f"🎯 Top Picks — {len(top_picks)} Stocks Analysed by AI")

if not top_picks:
    st.info("No picks generated yet. Run the analysis first.")
else:
    for i, pick in enumerate(top_picks, 1):
        symbol    = pick.get("symbol", "")
        company   = pick.get("company_name", symbol)
        score     = pick.get("score", 0)
        signal    = pick.get("signal", "WATCH")
        sector    = pick.get("sector", "Unknown")
        price     = pick.get("current_price")
        pe        = pick.get("pe_ratio")
        rsi       = pick.get("rsi")
        ret1m     = pick.get("ret_1m_pct")
        anomalies = pick.get("anomalies", [])
        ai        = pick.get("ai_analysis") or {}

        # Score color
        s_class = "score-high" if score >= 70 else "score-mid" if score >= 50 else "score-low"
        sig_class = f"{signal.lower()}-badge"

        with st.expander(
            f"#{i}  {company} ({symbol})  |  Score: {score}/100  |  {signal}  |  {sector}",
            expanded=(i <= 3)
        ):
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown(f'<div class="{s_class}">{score}/100</div>', unsafe_allow_html=True)
                st.markdown(f'<span class="{sig_class}">{signal}</span>', unsafe_allow_html=True)
            with col2:
                if price: st.metric("Price", f"₹{price:,.2f}")
            with col3:
                if pe: st.metric("P/E Ratio", f"{pe:.1f}x")
            with col4:
                if rsi: st.metric("RSI", f"{rsi:.1f}")

            # Anomaly warnings
            if anomalies:
                for anomaly in anomalies:
                    st.markdown(f'<div class="anomaly-box">{anomaly}</div>', unsafe_allow_html=True)

            # AI Analysis
            if ai and not ai.get("parse_error"):
                tab1, tab2, tab3, tab4 = st.tabs(["📋 Summary", "🐂 Bull Case", "🐻 Bear Case", "🔍 Self-Questioning"])

                with tab1:
                    summary = ai.get("summary", "")
                    if summary:
                        st.write(summary)

                    verdict = ai.get("final_verdict", {})
                    if verdict:
                        conf = verdict.get("confidence_pct", "N/A")
                        st.markdown(f"""
                        **Confidence:** {conf}%  
                        **Time Horizon:** {verdict.get('time_horizon','N/A')}  
                        **Entry Strategy:** {verdict.get('entry_strategy','N/A')}
                        """)
                        if verdict.get("what_changes_view"):
                            st.markdown(f"""<div class="evidence-box">
                            🔄 <b>What changes this view:</b> {verdict['what_changes_view']}
                            </div>""", unsafe_allow_html=True)

                with tab2:
                    bull = ai.get("bull_case", {})
                    if bull:
                        st.success(f"**Main Argument:** {bull.get('main_argument','')}")
                        for pt in bull.get("supporting_points", []):
                            st.write(f"✅ {pt}")
                        for ev in bull.get("evidence_cited", []):
                            st.markdown(f'<div class="evidence-box">📎 {ev}</div>', unsafe_allow_html=True)

                with tab3:
                    bear = ai.get("bear_case", {})
                    if bear:
                        st.error(f"**Main Concern:** {bear.get('main_argument','')}")
                        for pt in bear.get("supporting_points", []):
                            st.write(f"⚠️ {pt}")
                        for ev in bear.get("evidence_cited", []):
                            st.markdown(f'<div class="anomaly-box">⚠️ {ev}</div>', unsafe_allow_html=True)

                with tab4:
                    sq = ai.get("self_questioning", {})
                    if sq:
                        items = [
                            ("Assumptions Being Made", sq.get("assumptions_being_made","")),
                            ("What Could Be Wrong",    sq.get("what_could_be_wrong","")),
                            ("Data Gaps",              sq.get("data_gaps","")),
                            ("Recency Bias Check",     sq.get("recency_bias_check","")),
                        ]
                        for label, val in items:
                            if val:
                                st.markdown(f"**{label}:**")
                                st.info(val)

                    macro_imp = ai.get("macro_impact", {})
                    if macro_imp:
                        st.markdown("**Macro Impact on This Stock:**")
                        for k, v in macro_imp.items():
                            if v:
                                st.write(f"• **{k.replace('_',' ').title()}:** {v}")

            elif ai and ai.get("parse_error"):
                st.write(ai.get("raw_response", "AI response unavailable"))
            else:
                # No AI — show evidence trace
                st.markdown("**Evidence Trail (Scoring Breakdown):**")
                evidence = pick.get("evidence", [])
                for ev in evidence[:8]:
                    st.markdown(f'<div class="evidence-box">📎 {ev}</div>', unsafe_allow_html=True)

st.markdown("---")

# ════════════════════════════════════════════════════════════
# FULL SCORES TABLE
# ════════════════════════════════════════════════════════════
all_scores = briefing.get("all_scores", [])
if all_scores:
    with st.expander(f"📊 All {len(all_scores)} Stocks — Full Score Table"):
        import pandas as pd
        df = pd.DataFrame(all_scores)

        # Select and rename columns for display
        display_cols = ["symbol","company_name","sector","score","signal",
                        "current_price","pe_ratio","roe_pct","rsi","ret_1m_pct","ret_3m_pct"]
        display_cols = [c for c in display_cols if c in df.columns]
        df_display   = df[display_cols].copy()

        df_display.columns = ["Symbol","Company","Sector","Score","Signal",
                               "Price (₹)","P/E","ROE%","RSI","1M Ret%","3M Ret%"][:len(display_cols)]

        # Color rows by signal
        def color_signal(val):
            if val == "BUY":   return "background-color: #c8e6c9"
            if val == "WATCH": return "background-color: #fff9c4"
            if val == "AVOID": return "background-color: #ffcdd2"
            return ""

        st.dataframe(
            df_display.style.applymap(color_signal, subset=["Signal"]),
            use_container_width=True,
            height=400,
        )

        # Download button
        csv = df_display.to_csv(index=False)
        st.download_button(
            "📥 Download as CSV",
            data    = csv,
            file_name = f"nifty200_scores_{datetime.now().strftime('%Y%m%d')}.csv",
            mime    = "text/csv",
        )

# ════════════════════════════════════════════════════════════
# SYSTEM HEALTH
# ════════════════════════════════════════════════════════════
with st.expander("🔧 System Health"):
    errors = briefing.get("errors", [])
    if errors:
        for err in errors:
            st.error(f"❌ {err}")
    else:
        st.success("✅ No errors in last run")

    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Generated:** {briefing.get('generated_at_str','N/A')}")
        st.write(f"**Completed:** {briefing.get('completed_at_str','N/A')}")
        st.write(f"**Duration:** {briefing.get('duration_minutes','N/A')} minutes")
    with col2:
        st.write(f"**Stocks in list:** {briefing.get('total_stocks','N/A')}")
        st.write(f"**Stocks scored:** {briefing.get('stocks_scored','N/A')}")
        st.write(f"**News articles:** {briefing.get('market_news_count','N/A')}")

st.markdown("---")
st.markdown(
    "<p style='text-align:center; color:#999; font-size:12px'>"
    "⚠️ This tool is for personal research only. Not financial advice. "
    "Always apply independent judgment before trading. "
    "Past performance does not guarantee future results."
    "</p>",
    unsafe_allow_html=True
)
