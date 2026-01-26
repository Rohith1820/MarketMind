import pandas as pd
import plotly.express as px
import streamlit as st
import os
import shutil
import re
import traceback

from main import run_analysis   # 👈 IMPORTANT CHANGE


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

with st.expander("⚙️ Configure Product Details", expanded=True):

     st.markdown("### 🧩 Custom Comparison Inputs")

competitors_raw = st.text_input(
    "Enter Competitors (comma-separated)",
    "HydraSmart Bottle, PureSip Tech Flask, SmartHydrate 2.0"
)

features_raw = st.text_input(
    "Enter Features to Compare (comma-separated)",
    "Design, Performance, Battery, Integration, Price Value"
)

def parse_csv(text: str):
    return [x.strip() for x in text.split(",") if x.strip()]

competitors_list = parse_csv(competitors_raw)
features_list = parse_csv(features_raw)

# Guardrails
if len(competitors_list) == 0:
    st.warning("Please enter at least 1 competitor.")
if len(features_list) < 3:
    st.info("Radar charts look best with 3+ features.")

# ==========================================
# 🧹 Prepare Output Folder
# ==========================================
output_dir = "outputs"
if os.path.exists(output_dir):
    shutil.rmtree(output_dir)
os.makedirs(output_dir, exist_ok=True)


# ==========================================
# 🚀 Run Market Research Analysis (FIXED)
# ==========================================
if st.button("🚀 Run Market Research Analysis"):
    with st.spinner("Running AI-driven market analysis... please wait 1–2 minutes."):
        try:
            result = run_analysis(
                product_name=product_name,
                industry=industry
            )

            st.success(f"✅ Analysis completed successfully for **{product_name}**!")

        except Exception as e:
            st.error("❌ Error running analysis")
            st.code(traceback.format_exc())


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

pos, neg, neu = extract_sentiment_summary("outputs/review_sentiment.md")
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
# 💰 Competitor Pricing
# ==========================================
st.subheader("💰 Competitor Pricing Overview")

# --- Option A: Let customers enter prices too (recommended) ---
st.markdown("Enter competitor prices (optional). If left blank, MarketMind uses placeholders.")

pricing_rows = []
for c in competitors_list:
    price = st.number_input(f"Price for {c} ($)", min_value=0, value=0, step=1)
    if price > 0:
        pricing_rows.append({"Competitor": c, "Price ($)": int(price)})

# Always include your product price (optional)
product_price = st.number_input(f"Price for {product_name} ($)", min_value=0, value=0, step=1)
if product_price > 0:
    pricing_rows.append({"Competitor": product_name, "Price ($)": int(product_price)})

# If user didn’t enter any prices, fallback to placeholders so chart still works
if not pricing_rows:
    pricing_rows = [{"Competitor": c, "Price ($)": 0} for c in competitors_list] + [{"Competitor": product_name, "Price ($)": 0}]

df_price = pd.DataFrame(pricing_rows)

fig2 = px.bar(
    df_price,
    x="Competitor",
    y="Price ($)",
    color="Competitor",
    text="Price ($)",
    title=f"Price Comparison: {product_name} vs Competitors"
)

st.plotly_chart(fig2, use_container_width=True)

# ==========================================
# ⚙️ Feature Comparison Radar
# ==========================================
st.subheader("⚙️ Feature Comparison Radar")

# --- Guardrails ---
if not features_list:
    st.warning("Please enter at least 3 features (comma-separated) to show the radar chart.")
elif len(features_list) < 3:
    st.warning("Please enter 3 or more features for a useful radar chart.")
else:
    entities = [product_name] + competitors_list

    radar_rows = []
    for entity in entities:
        # Skip blank entity names
        if not entity or not entity.strip():
            continue

        st.markdown(f"**{entity}**")
        for feat in features_list:
            if not feat or not feat.strip():
                continue

            score = st.slider(
                f"{entity} — {feat}",
                0, 10, 5,
                key=f"score_{entity}_{feat}"
            )
            radar_rows.append({"Product": entity, "Feature": feat, "Score": score})

    df_radar = pd.DataFrame(radar_rows)

    # --- Final safety check ---
    if df_radar.empty:
        st.error("Radar data is empty. Please check your competitor/feature inputs.")
        st.write("Competitors:", competitors_list)
        st.write("Features:", features_list)
    else:
        fig3 = px.line_polar(
            df_radar,
            r="Score",
            theta="Feature",
            color="Product",
            line_close=True,
            title=f"Feature Comparison: {product_name} vs Selected Competitors"
        )
        fig3.update_traces(fill="toself", opacity=0.6)
        st.plotly_chart(fig3, use_container_width=True)


# ==========================================
# 📈 Market Growth Trend
# ==========================================
st.subheader("📈 Market Growth Trend (2023–2026)")

years = ["2023", "2024", "2025", "2026"]

# Build a smooth growth curve from adjusted CAGR
# Start point depends on scale (optional)
start_growth = 10 if scale == "Startup" else 12 if scale == "SME" else 14

# Growth increases each year but scaled by adjusted CAGR
growth = []
current = start_growth
for i in range(len(years)):
    # yearly increment derived from adjusted CAGR
    increment = adjusted_cagr / 6.0  # tuned so 4 years looks reasonable
    # competitive markets tend to flatten later
    flatten = 1 - (0.12 * i * competitive_intensity)
    current = current + increment * flatten
    growth.append(round(current, 1))

market_trend = pd.DataFrame({
    "Year": years,
    "Market Growth (%)": growth
})

# Upper band for confidence
market_trend["Upper Bound"] = market_trend["Market Growth (%)"] * 1.12

fig_trend = px.line(
    market_trend,
    x="Year",
    y="Market Growth (%)",
    title=f"Projected Market Growth in {industry} (Competitor-adjusted)",
    markers=True
)

fig_trend.add_traces(
    px.area(market_trend, x="Year", y="Upper Bound").update_traces(
        fill="tonexty",
        line=dict(color="rgba(0,0,0,0)")
    ).data
)

fig_trend.update_layout(
    xaxis_title="Year",
    yaxis_title="Market Growth (%)",
    xaxis=dict(type="category"),
    showlegend=False
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
# 📘 Full Market Research Reports
# ==========================================
st.subheader("📘 Full Market Research Reports")

if os.path.exists(output_dir):
    md_files = [f for f in os.listdir(output_dir) if f.endswith(".md")]

    if md_files:
        for md_file in md_files:
            with open(os.path.join(output_dir, md_file), "r", encoding="utf-8") as f:
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
