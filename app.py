import os
import re
import shutil
import subprocess

import pandas as pd
import plotly.express as px
import streamlit as st

# ==========================================
# ⚙️ Streamlit Page Configuration
# ==========================================
st.set_page_config(page_title="MarketMind Dashboard", layout="wide")
st.title("🧠 MarketMind: AI Market Research Assistant")
st.header("📊 MarketMind Insights Dashboard")

st.markdown(
    """
MarketMind generates **AI-driven market research reports** and dynamic dashboards —
including competitor intelligence, sentiment insights, and growth opportunities —
based on the product and market context you provide.
"""
)

# ==========================================
# 📂 Paths & Session State
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")

if "run_ok" not in st.session_state:
    st.session_state["run_ok"] = False

if "df_price" not in st.session_state:
    st.session_state["df_price"] = None

if "sentiment" not in st.session_state:
    # (pos, neg, neu)
    st.session_state["sentiment"] = (60, 30, 10)

if "last_product_name" not in st.session_state:
    st.session_state["last_product_name"] = ""


# ==========================================
# 🔧 Helper Functions
# ==========================================
def build_competitor_df(output_dir: str, product_name: str) -> pd.DataFrame:
    """
    Parse outputs/competitor_analysis.md to extract competitor names & prices.
    Falls back to a default list if parsing fails or file missing.
    """
    pricing_file = os.path.join(output_dir, "competitor_analysis.md")
    competitor_data = []

    if os.path.exists(pricing_file):
        with open(pricing_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        competitor_name = None

        for line in lines:
            # Example expected format:
            # ### Competitor: **Brand X**
            header_match = re.search(r"###\s*Competitor:\s*\*\*(.*?)\*\*", line)
            if header_match:
                competitor_name = header_match.group(1).strip()
                continue

            # Example expected format:
            # - Price: $999
            price_match = re.search(r"Price:\s*\$([0-9]+)", line)
            if price_match and competitor_name:
                price_value = int(price_match.group(1))
                competitor_data.append(
                    {"Competitor": competitor_name, "Price ($)": price_value}
                )
                competitor_name = None  # reset for the next block

    # Fallback if nothing parsed
    if not competitor_data:
        competitor_data = [
            {"Competitor": "HydraSmart Bottle", "Price ($)": 799},
            {"Competitor": "PureSip Tech Flask", "Price ($)": 699},
            {"Competitor": "SmartHydrate 2.0", "Price ($)": 999},
            {"Competitor": product_name, "Price ($)": 1099},
        ]

    return pd.DataFrame(competitor_data)


def extract_sentiment_summary(sentiment_file: str):
    """
    Parse outputs/review_sentiment.md to get positive/negative/neutral percentages.
    Falls back to (60, 30, 10) if parsing fails.
    """
    default = (60, 30, 10)

    if not os.path.exists(sentiment_file):
        return default

    with open(sentiment_file, "r", encoding="utf-8") as f:
        text = f.read()

    # Try some flexible regex patterns
    pos_match = re.search(r"Positive[^0-9]*([0-9]+)", text, re.IGNORECASE)
    neg_match = re.search(r"Negative[^0-9]*([0-9]+)", text, re.IGNORECASE)
    neu_match = re.search(r"Neutral[^0-9]*([0-9]+)", text, re.IGNORECASE)

    try:
        pos = int(pos_match.group(1)) if pos_match else default[0]
        neg = int(neg_match.group(1)) if neg_match else default[1]
        neu = int(neu_match.group(1)) if neu_match else default[2]
    except Exception:
        return default

    total = pos + neg + neu
    if total == 0:
        return default

    # Normalize to percentages (just in case)
    pos = round(100 * pos / total)
    neg = round(100 * neg / total)
    neu = 100 - pos - neg  # ensure sum=100

    return (pos, neg, neu)


# ==========================================
# 🎛️ User Inputs
# ==========================================
st.sidebar.header("🧾 Input: Product & Market Context")

product_name = st.sidebar.text_input(
    "Product Name",
    value="Smart Hydration Bottle",
    help="Name of the product you want to analyze.",
)

industry = st.sidebar.text_input(
    "Industry / Category",
    value="Smart consumer electronics",
    help="e.g., energy drink, smart bottle, skincare serum, etc.",
)

geography = st.sidebar.text_input(
    "Target Geography / Region",
    value="United States",
    help="e.g., India, North America, EU, etc.",
)

scale = st.sidebar.selectbox(
    "Business Scale",
    options=["Startup", "SMB", "Enterprise"],
    index=0,
)

st.sidebar.markdown(
    "Click **Run Market Research Analysis** after updating these fields."
)

# ==========================================
# 🚀 Run Market Research Analysis
# ==========================================
st.markdown("---")
st.subheader("🚀 Run AI Market Research Pipeline")

if st.button("Run Market Research Analysis"):
    with st.spinner("Running AI-driven market analysis... this may take a minute."):

        # 1️⃣ Clear and recreate outputs ONLY when we actually run the pipeline
        if os.path.exists(OUTPUT_DIR):
            shutil.rmtree(OUTPUT_DIR)
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        # 2️⃣ Prepare environment for child process
        env = os.environ.copy()
        env["PRODUCT_NAME"] = product_name
        env["INDUSTRY"] = industry
        env["GEOGRAPHY"] = geography
        env["SCALE"] = scale

        # 3️⃣ Run main.py and capture result (for internal use; no logs shown in UI)
        process = subprocess.run(
            ["python3", "main.py"],
            text=True,
            capture_output=True,
            env=env,
            cwd=BASE_DIR,  # important for Render so paths resolve correctly
        )

        if process.returncode != 0:
            st.session_state["run_ok"] = False
            st.error(
                "❌ Analysis failed on the server. "
                "Check your Render logs and environment variables (e.g., OPENAI_API_KEY, dependencies)."
            )
        else:
            # ✅ Successful run – refresh data from new outputs
            st.session_state["run_ok"] = True
            st.session_state["last_product_name"] = product_name

            # Competitor pricing
            st.session_state["df_price"] = build_competitor_df(
                OUTPUT_DIR, product_name
            )

            # Sentiment
            sentiment_file = os.path.join(OUTPUT_DIR, "review_sentiment.md")
            st.session_state["sentiment"] = extract_sentiment_summary(sentiment_file)

            st.success(
                f"✅ Analysis completed successfully for **{product_name}**! Scroll down for insights."
            )


# ==========================================
# 📈 Visualizations – Sentiment & Competitor Pricing
# ==========================================
display_product = (
    st.session_state.get("last_product_name") or product_name or "Your Product"
)

st.markdown("---")
col1, col2 = st.columns(2)

# ---- Sentiment Pie Chart ----
with col1:
    st.subheader("💬 Customer Sentiment Overview")

    pos, neg, neu = st.session_state.get("sentiment", (60, 30, 10))

    df_sentiment = pd.DataFrame(
        {
            "Sentiment": ["Positive", "Negative", "Neutral"],
            "Percentage": [pos, neg, neu],
        }
    )

    fig_sentiment = px.pie(
        df_sentiment,
        names="Sentiment",
        values="Percentage",
        hole=0.3,
        title=f"Sentiment Breakdown for {display_product}",
    )
    st.plotly_chart(fig_sentiment, use_container_width=True)

# ---- Competitor Pricing Bar Chart ----
with col2:
    st.subheader("💰 Competitor Pricing Overview")

    if st.session_state.get("run_ok") and st.session_state.get("df_price") is not None:
        df_price = st.session_state["df_price"]

        fig_price = px.bar(
            df_price,
            x="Competitor",
            y="Price ($)",
            text="Price ($)",
            title=f"Price Comparison: {display_product} vs Competitors",
        )
        fig_price.update_traces(textposition="outside")
        fig_price.update_layout(yaxis_title="Price ($)")
        st.plotly_chart(fig_price, use_container_width=True)
    else:
        st.info(
            "Run the analysis to see competitor pricing based on the latest AI-generated report."
        )


# ==========================================
# ⚙️ Feature Comparison Radar
# ==========================================
st.subheader("⚙️ Feature Comparison Radar")

# Build competitor list from df_price (if available)
if st.session_state.get("df_price") is not None:
    df_price_for_radar = st.session_state["df_price"]
    # All competitor names except the main product
    comp_candidates = [
        c for c in df_price_for_radar["Competitor"].unique()
        if c != display_product
    ]
else:
    comp_candidates = []

# Ensure we have exactly 2 competitors for the radar (fallback if needed)
if len(comp_candidates) < 2:
    comp_radar = ["Competitor A", "Competitor B"]
else:
    comp_radar = comp_candidates[:2]

radar_data = pd.DataFrame({
    "Feature": ["Design", "Performance", "Battery", "Integration", "Price Value"],
    display_product: [9, 8, 7, 9, 6],
    comp_radar[0]: [8, 7, 6, 7, 7],
    comp_radar[1]: [7, 6, 8, 6, 8]
})

fig3 = px.line_polar(
    radar_data.melt(id_vars="Feature", var_name="Product", value_name="Score"),
    r="Score",
    theta="Feature",
    color="Product",
    line_close=True,
    template="plotly_white",
    title=f"Feature Comparison: {display_product} vs {comp_radar[0]}, {comp_radar[1]}"
)

fig3.update_traces(fill="toself", opacity=0.6)
fig3.update_layout(title_x=0.5)

st.plotly_chart(fig3, use_container_width=True)

# ==========================================
# 📈 Market Trend Forecast
# ==========================================
st.subheader("📈 Market Growth Trend (2023–2026)")

market_trend = pd.DataFrame({
    "Year": ["2023", "2024", "2025", "2026"],
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
)

# Add only the upper shaded band
fig_trend.add_traces(px.area(
    market_trend,
    x="Year",
    y="Upper Bound"
).update_traces(
    fill="tonexty",
    line=dict(color="rgba(0,0,0,0)")
).data)

# Final formatting
fig_trend.update_layout(
    xaxis_title="Year",
    yaxis_title="Market Growth (%)",
    xaxis=dict(
        type="category",
        tickmode="array",
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

if os.path.exists(OUTPUT_DIR):
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
4. Scroll down to view full reports  

---

### 💡 Tips
- Try different industries to get different competitor profiles.  
- Use reports directly in presentations or decks.  
""")
