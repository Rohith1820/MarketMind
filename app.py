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
    """Simplify noisy competitor names."""
    name = re.sub(r"\[.*?\]|\(.*?\)", "", str(name))
    name = re.sub(r"(?i)company\s*name[:\-]*|company[:\-]*|competitor[:\-]*", "", name)
    if "|" in name:
        name = name.split("|")[0]
    if " - " in name:
        name = name.split(" - ")[0]
    return name.strip()


def _is_likely_name(line: str) -> bool:
    """Check if line looks like a competitor name (not a description)."""
    line = line.strip()
    if not line or len(line) > 60 or line.endswith("."):
        return False
    bad_patterns = [
        r"\boffers?\b", r"\bprovides?\b", r"\buses\b", r"\bequipped\b",
        r"\bfeatures\b", r"\bdesigned\b", r"\ballows\b", r"\benables\b",
    ]
    return not any(re.search(p, line.lower()) for p in bad_patterns)


def parse_competitors_from_markdown(pricing_file: str, product_name: str) -> pd.DataFrame:
    """Extract clean competitor–price pairs."""
    rows = []
    if os.path.exists(pricing_file):
        with open(pricing_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for i, line in enumerate(lines):
            price_match = re.search(r"([₹$]|rs\.?\s*)?([0-9][0-9,\.]*)", line, re.I)
            if not price_match:
                continue
            price_value = float(price_match.group(2).replace(",", ""))
            candidates = [lines[j].strip() for j in range(i-1, max(-1, i-6), -1) if lines[j].strip()]
            header = next((c for c in candidates if _is_likely_name(c)), candidates[0])
            name = re.sub(r"^[#\-\*\d\.\)\s]+|\*\*", "", header)
            name = clean_competitor_label(name)
            if name:
                rows.append({"Competitor": name, "Price ($)": price_value})

    if not rows:
        rows = [
            {"Competitor": "HydraSmart Bottle", "Price ($)": 799},
            {"Competitor": "PureSip Tech Flask", "Price ($)": 699},
            {"Competitor": "SmartHydrate 2.0", "Price ($)": 999},
            {"Competitor": product_name, "Price ($)": 1099},
        ]
    df = pd.DataFrame(rows).head(5)
    df["Competitor"] = df["Competitor"].apply(clean_competitor_label)
    return df

# ==========================================
# 🚀 Run Market Research Analysis
# ==========================================
if st.button("🚀 Run Market Research Analysis"):
    with st.spinner("Running AI-driven market analysis... please wait..."):
        if os.path.exists(OUTPUT_DIR):
            shutil.rmtree(OUTPUT_DIR)
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        env = {**os.environ, "PRODUCT_NAME": product_name, "INDUSTRY": industry,
               "GEOGRAPHY": geography, "SCALE": scale}

        process = subprocess.run(["python3", "main.py"], text=True, capture_output=True,
                                 env=env, cwd=BASE_DIR)

        if process.returncode != 0:
            st.error("❌ Analysis failed. Check logs below.")
            st.code(process.stderr or process.stdout or "No output")
        else:
            st.success(f"✅ Analysis completed successfully for **{product_name}**!")
            st.session_state["analysis_done"] = True

st.markdown("---")

# ==========================================
# 💬 Sentiment Analysis Visualization
# ==========================================
st.subheader("💬 Customer Sentiment Overview")

pos, neg, neu = extract_sentiment_summary(os.path.join(OUTPUT_DIR, "review_sentiment.md"))
fig1 = px.pie(
    pd.DataFrame({"Sentiment": ["Positive", "Negative", "Neutral"], "Percentage": [pos, neg, neu]}),
    names="Sentiment", values="Percentage", hole=0.3,
    color_discrete_map={"Positive": "#2ecc71", "Negative": "#e74c3c", "Neutral": "#95a5a6"},
    title=f"Sentiment Breakdown for {product_name}"
)
fig1.update_traces(textinfo="percent+label", pull=[0.02, 0.05, 0])
st.plotly_chart(fig1, use_container_width=True)

# ==========================================
# 💰 Competitor Pricing (Dynamic)
# ==========================================
st.subheader("💰 Competitor Pricing Overview")

df_price = parse_competitors_from_markdown(os.path.join(OUTPUT_DIR, "competitor_analysis.md"), product_name)
fig2 = px.bar(df_price, x="Competitor", y="Price ($)", color="Competitor",
              text="Price ($)", title=f"Price Comparison: {product_name} vs Competitors",
              color_discrete_sequence=px.colors.qualitative.Safe)
st.plotly_chart(fig2, use_container_width=True)

with st.expander("🔍 Parsed competitor data"):
    st.dataframe(df_price, use_container
