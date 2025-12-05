import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
import streamlit as st
import os
import subprocess
import shutil
import re

# ==========================================
# ⚙️ Streamlit Page Configuration
# ==========================================
st.set_page_config(page_title="MarketMind Dashboard", layout="wide")
st.title("🧠 MarketMind: AI Market Research Assistant")
st.header("📊 MarketMind Insights Dashboard")

st.markdown("""
MarketMind generates **AI-driven market research reports** and dynamic dashboards —
including competitor intelligence, sentiment insights, and growth projections.
""")

# ==========================================
# 🧩 Product Configuration Section
# ==========================================
with st.expander("⚙️ Configure Product Details", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        product_name = st.text_input("Enter Product Name", "EcoWave Smart Bottle")
        geography = st.text_input("Target Geography", "Global")
    with col2:
        industry = st.text_input("Industry", "Consumer Goods")
        scale = st.selectbox("Business Scale", ["Startup", "SME", "Enterprise"], index=1)

# ==========================================
# 📂 Paths & basic state
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")  # <-- use this everywhere

if "analysis_done" not in st.session_state:
    st.session_state["analysis_done"] = False

# ==========================================
# 🚀 Run Market Research Analysis
# ==========================================
if st.button("🚀 Run Market Research Analysis"):
    with st.spinner("Running AI-driven market analysis... please wait 1–2 minutes."):

        os.environ["PRODUCT_NAME"] = product_name
        os.environ["INDUSTRY"] = industry
        os.environ["GEOGRAPHY"] = geography
        os.environ["SCALE"] = scale

        process = subprocess.run(
            ["python3", "main.py"],
            text=True,
            capture_output=True
        )

        if process.returncode != 0:
            st.error("❌ Error running analysis. Check logs in main.py.")
        else:
            st.success(f"✅ Analysis completed successfully for **{product_name}**!")

st.markdown("---")

# ==========================================
# 🧩 Helper Function — Extract Sentiment %
# ==========================================
def extract_sentiment_summary(file_path):
    if not os.path.exists(file_path):
        return 60, 30, 10

    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read().lower()

    pos = int(re.search(r"positive[^0-9]*([0-9]{1,3})%", text).group(1)) if re.search(r"positive[^0-9]*([0-9]{1,3})%", text) else 60
    neg = int(re.search(r"negative[^0-9]*([0-9]{1,3})%", text).group(1)) if re.search(r"negative[^0-9]*([0-9]{1,3})%", text) else 30
    neu = int(re.search(r"neutral[^0-9]*([0-9]{1,3})%", text).group(1)) if re.search(r"neutral[^0-9]*([0-9]{1,3})%", text) else 10

    return pos, neg, neu

# ==========================================
# 💬 Sentiment Analysis Visualization
# ==========================================
st.subheader("💬 Customer Sentiment Overview")

sentiment_path = os.path.join(OUTPUT_DIR, "review_sentiment.md")
pos, neg, neu = extract_sentiment_summary(sentiment_path)

df_sentiment = pd.DataFrame({
    "Sentiment": ["Positive", "Negative", "Neutral"],
    "Percentage": [pos, neg, neu]
})

fig1 = px.pie(
    df_sentiment,
    names="Sentiment",
    values="Percentage",
    color="Sentiment",
    hole=0.3,
    title=f"Sentiment Breakdown for {product_name}",
    color_discrete_map={
        "Positive": "#2ecc71",
        "Negative": "#e74c3c",
        "Neutral": "#95a5a6"
    }
)

fig1.update_traces(textinfo="percent+label", pull=[0.02, 0.05, 0])
fig1.update_layout(title_x=0.5)

st.plotly_chart(fig1, use_container_width=True)

# ==========================================
# Helper to clean competitor name
# ==========================================
def clean_competitor_name(name: str) -> str:
    if not isinstance(name, str):
        name = str(name)

    # Remove any "Company name:" prefix
    name = re.sub(r"(?i)company\s*name[:\-]*", "", name)

    # Remove any [bracketed] or (parenthesized) noise
    name = re.sub(r"\[.*?\]", "", name)
    name = re.sub(r"\(.*?\)", "", name)

    # If there is extra description separated by "|", keep only the first part
    if "|" in name:
        name = name.split("|")[0].strip()

    # If there is extra description separated by " - ", keep only the first part
    if " - " in name:
        name = name.split(" - ")[0].strip()

    return name.strip()

# ==========================================
# 💰 Competitor Pricing (Dynamic if available)
# ==========================================
st.subheader("💰 Competitor Pricing Overview")

pricing_file = os.path.join(OUTPUT_DIR, "competitor_analysis.md")  # <-- FIXED
competitor_data = []

# ---- Extract competitors from markdown if available ----
if os.path.exists(pricing_file):
    with open(pricing_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    competitor_name = None
    price_value = None

    for line in lines:

        # Detect competitor header
        header_match = re.search(r"###\s*Competitor:\s*\*\*(.*?)\*\*", line)
        if header_match:
            competitor_name = clean_competitor_name(header_match.group(1).strip())
            price_value = None  # reset
            continue

        # Detect price line
        price_match = re.search(r"Price:\s*\$([0-9]+)", line)
        if price_match and competitor_name:
            price_value = int(price_match.group(1))
            competitor_data.append(
                {"Competitor": competitor_name, "Price ($)": price_value}
            )
            competitor_name = None  # reset for next competitor

# ---- Use fallback sample if nothing extracted ----
if not competitor_data:
    competitor_data = [
        {"Competitor": "HydraSmart Bottle", "Price ($)": 799},
        {"Competitor": "PureSip Tech Flask", "Price ($)": 699},
        {"Competitor": "SmartHydrate 2.0", "Price ($)": 999},
        {"Competitor": product_name, "Price ($)": 1099}
    ]

# Limit to max 5 competitors
competitor_data = competitor_data[:5]

# ---- Build DataFrame ----
df_price = pd.DataFrame(competitor_data)

# ---- Plot chart ----
fig2 = px.bar(
    df_price,
    x="Competitor",
    y="Price ($)",
    color="Competitor",
    text="Price ($)",
    title=f"Price Comparison: {product_name} vs Competitors",
    color_discrete_sequence=px.colors.qualitative.Safe
)

st.plotly_chart(fig2, use_container_width=True)

# ==========================================
# ⚙️ Feature Comparison Radar
# ==========================================
st.subheader("⚙️ Feature Comparison Radar")

competitors = [c["Competitor"] for c in competitor_data if c["Competitor"] != product_name][:2]
if len(competitors) < 2:
    competitors = ["Competitor A", "Competitor B"]

radar_data = pd.DataFrame({
    "Feature": ["Design", "Performance", "Battery", "Integration", "Price Value"],
    product_name: [9, 8, 7, 9, 6],
    competitors[0]: [8, 7, 6, 7, 7],
    competitors[1]: [7, 6, 8, 6, 8]
})

fig3 = px.line_polar(
    radar_data.melt(id_vars="Feature", var_name="Product", value_name="Score"),
    r="Score",
    theta="Feature",
    color="Product",
    line_close=True,
    template="plotly_white",
    title=f"Feature Comparison: {product_name} vs {competitors[0]}, {competitors[1]}"
)

fig3.update_traces(fill='toself', opacity=0.6)
fig3.update_layout(title_x=0.5)

st.plotly_chart(fig3, use_container_width=True)

# ==========================================
# 📈 Market Trend Forecast
# ==========================================
st.subheader("📈 Market Growth Trend (2023–2026)")

market_trend = pd.DataFrame({
    "Year": ["2023", "2024", "2025", "2026"],  # <-- string years remove midpoints
    "Market Growth (%)": [12, 18, 24, 33],
})

# Calculate upper confidence band (12% above)
market_trend["Upper Bound"] = market_trend["Market Growth (%)"] * 1.12

# Main line chart
fig_trend = px.line(
    market_trend,
    x="Year",
    y="Market Growth (%)",
    title=f"Projected Market Growth in {industry}",
    markers=True,
    color_discrete_sequence=["#1ABC9C"]
)

# Add only the upper shaded band
fig_trend.add_traces(px.area(
    market_trend,
    x="Year",
    y="Upper Bound"
).update_traces(
    fill='tonexty',
    fillcolor='rgba(26, 188, 156, 0.18)',
    line=dict(color='rgba(0,0,0,0)')
).data)

# Final formatting
fig_trend.update_layout(
    xaxis_title="Year",
    yaxis_title="Market Growth (%)",
    xaxis=dict(
        type='category',          # <-- prevents midpoints
        tickmode='array',
        tickvals=market_trend["Year"],
        ticktext=market_trend["Year"]
    ),
    showlegend=False,
    plot_bgcolor="white",
    margin=dict(l=40, r=30, t=60, b=40)
)

st.plotly_chart(fig_trend, use_container_width=True)

# ==========================================
# 📊 Key Market Indicators (Dynamic)
# ==========================================
st.subheader("📊 Key Market Indicators")
col1, col2, col3 = st.columns(3)
col1.metric("Positive Sentiment", f"{pos}%", "↑ vs last month")
col2.metric("Negative Sentiment", f"{neg}%", "↓ slightly")
col3.metric("Neutral Sentiment", f"{neu}%", " ")

st.markdown("---")

# ==========================================
# 🧾 Full Market Research Reports
# ==========================================
st.subheader("📘 Full Market Research Reports")

if os.path.exists(OUTPUT_DIR):   # <-- FIXED
    md_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith(".md")]

    if md_files:
        for md_file in md_files:
            with open(os.path.join(OUTPUT_DIR, md_file), "r", encoding="utf-8") as f:
                content = f.read()
            with st.expander(f"📄 {md_file}", expanded=False):
                st.markdown(content)
    else:
        st.info("⚠️ No markdown reports found. Please run analysis first.")
else:
    st.warning("Outputs directory not found. Please run analysis.")

# ==========================================
# 📘 Sidebar — How to Use
# ==========================================
st.sidebar.header("ℹ️ How to Use MarketMind")

st.sidebar.markdown("""
### 📌 Steps to Run the Analysis

1. **Enter your product details**  
2. **Click 'Run Market Research Analysis'**  
3. Dashboard visuals update automatically  
4. Scroll down to download your reports  

---

### 💡 Tips
- Try different industries to get different competitor profiles.  
- Use reports directly in presentations or decks.  
""")
