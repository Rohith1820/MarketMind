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


def _is_likely_name(line: str) -> bool:
    """Heuristic: is this line probably a company/product name, not a description?"""
    line = line.strip()
    if not line:
        return False
    if len(line) > 60:    # long sentences are probably descriptions
        return False
    if line.endswith("."):  # sentences usually end with a period
        return False

    lower = line.lower()
    # If it starts with verbs / phrases, it's probably a description
    bad_patterns = [
        r"\boffers?\b",
        r"\bprovides?\b",
        r"\buses\b",
        r"\bequipped\b",
        r"\bfeatures\b",
        r"\bdesigned\b",
        r"\bsome users\b",
        r"\ballows\b",
        r"\benables\b",
    ]
    for pat in bad_patterns:
        if re.search(pat, lower):
            return False

    return True


def parse_competitors_from_markdown(pricing_file: str, product_name: str) -> pd.DataFrame:
    """
    Tolerant parser for outputs/competitor_analysis.md.

    Strategy:
      - Look for any numeric value on a line (price).
      - Look up to a few lines above for a line that looks like a company name.
      - Clean markdown bullets/headings and labels.
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
            price_match = re.search(
                r"([₹$]|rs\.?\s*)?([0-9][0-9,\.]*)", line, re.IGNORECASE
            )
            if not price_match:
                continue

            price_str = price_match.group(2)
            price_clean = price_str.replace(",", "")
            try:
                price_value = float(price_clean)
            except ValueError:
                continue

            # Look BACKWARDS up to a few lines for a plausible name
            candidates = []
            j = i - 1
            steps = 0
            while j >= 0 and steps < 5:  # look up to 5 lines above
                cand = lines[j].strip()
                if cand:
                    candidates.append(cand)
                steps += 1
                j -= 1

            if not candidates:
                continue

            header = None
            # Pick the first candidate that looks like a name
            for cand in candidates:
                if _is_likely_name(cand):
                    header = cand
                    break

            # If nothing looks like a name, just take the closest non-empty line
            if header is None:
                header = candidates[0]

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
        if os.path.exists(OU
