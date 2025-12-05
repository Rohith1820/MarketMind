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

st.markdown("""
MarketMind generates **AI-driven market research reports** and dynamic dashboards —
including competitor intelligence, sentiment insights, and growth projections.
""")

# ==========================================
# 📂 Paths & basic state
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")

if "analysis_done" not in st.session_state:
    st.session_state["analysis_done"] = False

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
# 🔧 Helper functions
# ==========================================
def extract_sentiment_summary(file_path: str):
    """Parse outputs/review_sentiment.md for Positive/Negative/Neutral %."""
    default = (60, 30, 10)

    if not os.path.exists(file_path):
        return default

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read().lower()
    except Exception:
        return default

    pos_match = re.search(r"positive[^0-9]*([0-9]{1,3})%", text)
    neg_match = re.search(r"negative[^0-9]*([0-9]{1,3})%", text)
    neu_match = re.search(r"neutral[^0-9]*([0-9]{1,3})%", text)

    pos = int(pos_match.group(1)) if pos_match else default[0]
    neg = int(neg_match.group(1)) if neg_match else default[1]
    neu = int(neu_match.group(1)) if neu_match else default[2]

    return pos, neg, neu


def clean_competitor_label(name: str) -> str:
    """
    Clean raw header text into a short competitor name.
    Also strips weird tokens like [company:xxxxx].
    """
    if not isinstance(name, str):
        name = str(name)

    # Remove bracketed/parenthesized junk like [company:xxx], (details...)
    name = re.sub(r"\[.*?\]", "", name)
    name = re.sub(r"\(.*?\)", "", name)

    # Remove leading "Company name:" or "Company:"
    name = re.sub(r"(?i)company\s*name[:\-]*", "", name)
    name = re.sub(r"(?i)company[:\-]*", "", name)

    # If there is extra description separated by "|", keep only the first part
    if "|" in name:
        name = name.split("|")[0].strip()

    # If there is extra description separated by " - ", keep left part
    if " - " in name:
        name = name.split(" - ")[0].strip()

    return name.strip()


def parse_competitors_from_markdown(pricing_file: str, product_name: str) -> pd.DataFrame:
    """
    Very tolerant parser for outputs/competitor_analysis.md.

    Strategy:
      - Look for any numeric value on a line (price).
      - Use the nearest non-empty line *above* it as competitor name.
      - Clean markdown bullets/headings and 'Competitor:' / 'Company name:' text.
      - Limit to max 5 competitors.
    """
    rows = []

    if os.path.exists(pricing_file):
        try:
            with open(pricing_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception:
            lines = []

        for i, line in enumerate(lines):
            # Find a numeric price on this line
            price_match = re.search(r"([₹$]|rs\.?\s*)?([0-9][0-9,\.]*)", line, re.IGNORECASE)
            if not price_match:
                continue

            price_str = price_match.group(2)
            price_clean = price_str.replace(",", "")
            try:
                price_value = float(price_clean)
            except ValueError:
                continue

            # Walk backwards to find nearest non-empty line: header/name
            header = None
            j = i - 1
            while j >= 0:
                cand = lines[j].strip()
                if cand:
                    header = cand
                    break
                j -= 1

            if not header:
                continue

            # Clean markdown header into a name
            name = header
            # Remove leading markdown bullets/headings/numbers
            name = re.sub(r"^[#\-\*\d\.\)\s]+", "", name)
            # Remove bold markers
            name = name.replace("**", "")
            # Remove 'Competitor' label if present
            name = re.sub(r"(?i)competitor[:\-]*", "", name).strip()
            # Final trim
            name = name.strip(":- ").strip()

            if not name:
                continue

            # Extra cleanup for company labels, brackets, etc.
            name = clean_competitor_label(name)

            if not name:
                continue

            rows.append({"Competitor": name, "Price ($)": price_value})

    # Fallback if nothing parsed
    if not rows:
        rows = [
            {"Competitor": "HydraSmart Bottle", "Price ($)": 799},
            {"Competitor": "PureSip Tech Flask", "Price ($)": 699},
            {"Competitor": "SmartHydrate 2.0", "Price ($)": 999},
            {"Competitor": product_name, "Price ($)": 1099},
        ]

    df = pd.DataFrame(rows)

    # Final safety pass on labels
    df["Competitor"] = df["Competitor"].astype(str).apply(clean_competitor_label)

    # ✅ Limit to at most 5 competitors
    if len(df) > 5:
        df = df.head(5)

    return df

# ==========================================
# 🚀 Run Market Research Analysis
# ==========================================
if st.button("🚀 Run Market Research Analysis"):
    with st.spinner("Running AI-driven market analysis... please wait 1–2 minutes."):

        # Clear outputs ONLY when the button is clicked
        if os.path.exists(OUTPUT_DIR):
            shutil.rmtree(OUTPUT_DIR)
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        env = os.environ.copy()
        env["PRODUCT_NAME"] = product_name
        env["INDUSTRY"] = industry
        env["GEOGRAPHY"] = geography
        env["SCALE"] = scale

        process = subprocess.run(
            ["python3", "main.py"],
            text=True,
            capture_output=True,
            env=env,
            cwd=BASE_DIR,
        )

        if process.returncode != 0:
            st.session_state["analysis_done"] = False
            st.error("❌ Error running analysis. Check server logs.")
            st.code(process.stderr or process.stdout or "No output", language="bash")
        else:
            st.session_state["analysis_done"] = True
            st.success(f"✅ Analysis completed successfully for **{product_name}**!")

st.markdown("---")

# ==========================================
# 💬 Sentiment Analysis Visualization
# ==========================================
st.subheader("💬 Customer Sentiment Overview")

sentiment_file = os.path.join(OUTPUT_DIR, "review_sentiment.md")
pos, neg, neu = extract_sentiment_summary(sentiment_file)

df_sentiment = pd.DataFrame(
    {
        "Sentiment": ["Positive", "Negative", "Neutral"],
        "Percentage": [pos, neg, neu],
    }
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

pricing_file = os.path.join(OUTPUT_DIR, "competitor_analysis.md")
df_price = parse_competitors_from_markdown(pricing_file, product_name)
competitor_data = df_price.to_dict("records")  # reuse for radar

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

# Optional: quick view of parsed competitor table
with st.expander("🔍 Parsed competitor data"):
    st.dataframe(df_price, use_container_width=True)

# ==========================================
# ⚙️ Feature Comparison Radar
# ==========================================
st.subheader("⚙️ Feature Comparison Radar")

competitors = [
    c["Competitor"] for c in competitor_data if c["Competitor"] != product_name
][:2]
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
    {"Year": ["2023", "2024", "2025", "2026"], "Market Growth (%)": [12, 18, 24, 33]}
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
area = px.area(market_trend, x="Year", y="Upper Bound").update_traces(
    fill="tonexty",
    fillcolor="rgba(26, 188, 156, 0.18)",
    line=dict(color="rgba(0,0,0,0)"),
)
fig_trend.add_traces(area.data)
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
    st.caption(f"Markdown reports found: {md_files or 'None'}")

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
4. Scroll down to view the detailed markdown reports  

---
### 💡 Tips
- Try different industries to see different competitor profiles.  
- Use reports directly in presentations or decks.  
""")
