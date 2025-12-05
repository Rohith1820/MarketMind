import os
import re
import shutil
import subprocess

import pandas as pd
import matplotlib.pyplot as plt  # optional
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
    neu_match = re.search(r"neu_
