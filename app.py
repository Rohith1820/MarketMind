import os
import re

import pandas as pd
import plotly.express as px
import streamlit as st

from main import run_analysis


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

# Keep outputs across reruns
if "outputs" not in st.session_state:
    st.session_state["outputs"] = None


# ==========================================
# 🧩 Product Configuration Section
# ==========================================
with st.expander("⚙️ Configure Product Details", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        product_name = st.text_input("Enter Product Name", "EcoBrew Smart Tumbler")
        geography = st.text_input("Target Geography", "Global")
    with col2:
        industry = st.text_input("Industry", "Consumer Goods")
        scale = st.selectbox("Business Scale", ["Startup", "SME", "Enterprise"], index=1)


# ==========================================
# 🚀 Run Market Research Analysis
# ==========================================
if st.button("🚀 Run Market Research Analysis"):
    with st.spinner("Running AI-driven market analysis... please wait 1–2 minutes."):
        try:
            outputs = run_analysis(product_name, industry, geography, scale)
            st.session_state["outputs"] = outputs
            st.success(f"✅ Analysis completed successfully for **{product_name}**!")
        except Exception as e:
            st.error("❌ Error running analysis. Check logs for details.")
            st.exception(e)

st.markdown("---")

outputs = st.session_state["outputs"] or {}


# ==========================================
# 🧩 Helper – sentiment from text
# ==========================================
def extract_sentiment_from_text(text: str):
    if not text:
        return 60, 30, 10

    text_low = text.lower()
    pos_match = re.search(r"positive[^0-9]*([0-9]{1,3})%", text_low)
    neg_match = re.search(r"negative[^0-9]*([0-9]{1,3})%", text_low)
    neu_match = re.search(r"neutral[^0-9]*([0-9]{1,3})%", text_low)

    pos = int(pos_match.group(1)) if pos_match else 60
    neg = int(neg_match.group(1)) if neg_match else 30
    neu = int(neu_match.group(1)) if neu_match else 10
    return pos, neg, neu


# ==========================================
# 💬 Sentiment Analysis Visualization
# ==========================================
st.subheader("💬 Customer Sentiment Overview")

sentiment_text = outputs.get("review_sentiment.md", "")
pos, neg, neu = extract_sentiment_from_text(sentiment_text)

df_sentiment = pd.DataFrame(
    {"Sentiment": ["Positive", "Negative", "Neutral"], "Percentage": [pos, neg, neu]}
)

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
        "Neutral": "#95a5a6",
    },
)
fig1.update_traces(textinfo="percent+label", pull=[0.02, 0.05, 0])
fig1.update_layout(title_x=0.5)
st.plotly_chart(fig1, use_container_width=True)


# ==========================================
# 💰 Competitor Pricing (Dynamic)
# ==========================================
st.subheader("💰 Competitor Pricing Overview")

competitor_text = outputs.get("competitor_analysis.md", "")
competitor_data = []

if competitor_text:
    # 1️⃣ If you later add a structured table section, parse that first
    table_match = re.search(
        r"## Structured Competitor Pricing.*?\n(\|.*\n)+",
        competitor_text,
        re.IGNORECASE,
    )

    if table_match:
        table_text = table_match.group(0)
        lines = [l.strip() for l in table_text.splitlines() if l.strip().startswith("|")]
        data_lines = lines[2:] if len(lines) >= 2 else []
        for line in data_lines:
            cols = [c.strip() for c in line.strip("|").split("|")]
            if len(cols) >= 2:
                name, price_str = cols[0], cols[1]
                try:
                    price = float(price_str)
                    competitor_data.append({"Competitor": name, "Price ($)": price})
                except ValueError:
                    continue

    # 2️⃣ If no table, parse "### Competitor: **Name**" + "Price: $XX" style text
    if not competitor_data:
        lines = competitor_text.splitlines()
        competitor_name = None

        for line in lines:
            header_match = re.search(
                r"###\s*Competitor[:\-\s]*\**(.+?)\**\s*$",
                line,
                re.IGNORECASE,
            )
            if header_match:
                competitor_name = header_match.group(1).strip()
                continue

            price_match = re.search(
                r"price[^$0-9]*\$?\s*([0-9]+(?:\.[0-9]+)?)",
                line,
                re.IGNORECASE,
            )
            if price_match and competitor_name:
                price_value = float(price_match.group(1))
                competitor_data.append(
                    {"Competitor": competitor_name, "Price ($)": price_value}
                )
                competitor_name = None

# 3️⃣ Fallback if nothing parsed
if not competitor_data:
    competitor_data = [
        {"Competitor": "HydraSmart Bottle", "Price ($)": 25},
        {"Competitor": "HidrateSpark PRO Tumbler", "Price ($)": 70},
        {"Competitor": "YETI Rambler 20 oz Tumbler", "Price ($)": 35},
        {"Competitor": "Hydro Flask Tumbler 22 oz", "Price ($)": 30},
        {"Competitor": "Ember Travel Mug 2", "Price ($)": 130},
    ]

df_price = pd.DataFrame(competitor_data)

fig2 = px.bar(
    df_price,
    x="Competitor",
    y="Price ($)",
    color="Competitor",
    text="Price ($)",
    title=f"Price Comparison: {product_name} vs Competitors",
    color_discrete_sequence=px.colors.qualitative.Safe,
)
st.plotly_chart(fig2, use_container_width=True)


# ==========================================
# ⚙️ Feature Comparison Radar
# ==========================================
st.subheader("⚙️ Feature Comparison Radar")

competitors = [c["Competitor"] for c in competitor_data if c["Competitor"] != product_name][:2]
if len(competitors) < 2:
    competitors = ["Competitor A", "Competitor B"]

radar_data = pd.DataFrame(
    {
        "Feature": ["Design", "Performance", "Battery", "Integration", "Price Value"],
        product_name: [9, 8, 7, 9, 6],
        competitors[0]: [8, 7, 6, 7, 7],
        competitors[1]: [7, 6, 8, 6, 8],
    }
)

fig3 = px.line_polar(
    radar_data.melt(id_vars="Feature", var_name="Product", value_name="Score"),
    r="Score",
    theta="Feature",
    color="Product",
    line_close=True,
    template="plotly_white",
    title=f"Feature Comparison: {product_name} vs {competitors[0]}, {competitors[1]}",
)
fig3.update_traces(fill="toself", opacity=0.6)
fig3.update_layout(title_x=0.5)
st.plotly_chart(fig3, use_container_width=True)


# ==========================================
# 📈 Market Trend Forecast
# ==========================================
st.subheader("📈 Market Growth Trend (2023–2026)")

market_trend = pd.DataFrame(
    {
        "Year": ["2023", "2024", "2025", "2026"],
        "Market Growth (%)": [12, 18, 24, 33],
    }
)
market_trend["Upper Bound"] = market_trend["Market Growth (%)"] * 1.12

fig_trend = px.line(
    market_trend,
    x="Year",
    y="Market Growth (%)",
    title=f"Projected Market Growth in {industry}",
    markers=True,
    color_discrete_sequence=["#1ABC9C"],
)
fig_trend.add_traces(
    px.area(market_trend, x="Year", y="Upper Bound")
    .update_traces(
        fill="tonexty",
        fillcolor="rgba(26, 188, 156, 0.18)",
        line=dict(color="rgba(0,0,0,0)"),
    )
    .data
)
fig_trend.update_layout(
    xaxis_title="Year",
    yaxis_title="Market Growth (%)",
    xaxis=dict(
        type="category",
        tickmode="array",
        tickvals=market_trend["Year"],
        ticktext=market_trend["Year"],
    ),
    showlegend=False,
    plot_bgcolor="white",
    margin=dict(l=40, r=30, t=60, b=40),
)
st.plotly_chart(fig_trend, use_container_width=True)


# ==========================================
# 📊 Key Market Indicators
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

if outputs:
    for filename, content in outputs.items():
        with st.expander(f"📄 {filename}", expanded=False):
            st.markdown(content or "_No content generated._")
else:
    st.info("⚠️ No reports yet. Please run the analysis.")
