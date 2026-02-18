# app.py
import os
import json
import zipfile
from io import BytesIO
from datetime import datetime
from itertools import cycle

import pandas as pd
import plotly.express as px
import streamlit as st

from main import run_analysis

OUTPUT_DIR = "outputs"

# ----------------------------
# Helpers
# ----------------------------
def ensure_outputs_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

def safe_load_json(path: str):
    try:
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def safe_read_text(path: str):
    try:
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return None

def parse_csv_list(text: str):
    items = []
    for part in (text or "").replace("\n", ",").split(","):
        p = part.strip()
        if p:
            items.append(p)

    seen = set()
    out = []
    for x in items:
        k = x.lower()
        if k not in seen:
            out.append(x)
            seen.add(k)
    return out

def to_float(x):
    try:
        return float(x)
    except Exception:
        return None

def list_md_files():
    if not os.path.exists(OUTPUT_DIR):
        return []
    return sorted([f for f in os.listdir(OUTPUT_DIR) if f.endswith(".md")])

def make_outputs_zip_bytes():
    ensure_outputs_dir()
    mem = BytesIO()
    with zipfile.ZipFile(mem, mode="w", compression=zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(OUTPUT_DIR):
            for fn in files:
                full = os.path.join(root, fn)
                rel = os.path.relpath(full, OUTPUT_DIR)
                z.write(full, arcname=rel)
    mem.seek(0)
    return mem.read()

# ----------------------------
# Page + Styles
# ----------------------------
st.set_page_config(page_title="MarketMind", page_icon="🧠", layout="wide")

CUSTOM_CSS = """
<style>
/* Layout */
.block-container { padding-top: 1.0rem; padding-bottom: 2rem; }
section[data-testid="stSidebar"] { border-right: 1px solid rgba(255,255,255,0.06); }

/* Hero */
.mm-hero {
  padding: 18px 18px;
  border-radius: 18px;
  border: 1px solid rgba(255,255,255,0.10);
  background: radial-gradient(1200px circle at 10% 20%, rgba(59,130,246,0.22), transparent 40%),
              radial-gradient(900px circle at 90% 10%, rgba(236,72,153,0.16), transparent 45%),
              rgba(255,255,255,0.03);
}
.mm-hero h1 { margin: 0; font-size: 2.05rem; letter-spacing: -0.5px; }
.mm-hero p { margin: .35rem 0 0; opacity: .86; font-size: 1.0rem; }

/* Cards */
.mm-card {
  padding: 14px 14px;
  border-radius: 16px;
  border: 1px solid rgba(255,255,255,0.10);
  background: rgba(255,255,255,0.03);
}
.mm-muted { opacity: .74; font-size: 0.9rem; }

/* Buttons */
div.stButton > button, div.stDownloadButton > button {
  border-radius: 12px !important;
  padding: 0.62rem 1rem !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] button { font-size: 0.98rem; }

/* Expanders */
div[data-testid="stExpander"] details { border-radius: 14px; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

ensure_outputs_dir()

# ----------------------------
# Hero
# ----------------------------
st.markdown(
    """
<div class="mm-hero">
  <h1>🧠 MarketMind</h1>
  <p>AI market research reports + dashboards for competitor pricing, source-aware sentiment, feature benchmarking, and product trend.</p>
</div>
""",
    unsafe_allow_html=True,
)
st.write("")

# ----------------------------
# Brand palette (shared)
# ----------------------------
# Use the same palette family across charts
MM_PALETTE = [
    "#3B82F6",  # blue
    "#EC4899",  # pink
    "#8B5CF6",  # purple
    "#22C55E",  # green
    "#F59E0B",  # amber
    "#06B6D4",  # cyan
]

# ----------------------------
# Sidebar (form)
# ----------------------------
with st.sidebar:
    st.markdown("### ⚙️ Configure your analysis")
    st.caption("Recommended: 2–4 competitors, 4–7 features.")

    with st.form("mm_form", clear_on_submit=False):
        product_name = st.text_input("Product Name", value="Lao Gan Ma Chili Crisp")
        industry = st.text_input("Industry", value="Food & Beverage")
        geography = st.text_input("Geography", value="US")
        scale = st.selectbox("Business Scale", ["Startup", "SME", "Enterprise"], index=1)

        st.markdown("---")
        st.markdown("#### 🧩 Custom comparison inputs")

        competitors_raw = st.text_area(
            "Competitors (comma or newline separated)",
            value="Fly By Jing Sichuan Chili Crisp, Momofuku Chili Crunch, Trader Joe’s Chili Onion Crunch",
            height=84,
        )
        features_raw = st.text_area(
            "Features (comma or newline separated)",
            value="Ingredients, Spice Level, Texture, Flavor Profile, Packaging, Price",
            height=84,
        )

        run_btn = st.form_submit_button("🚀 Run Market Research")

    st.markdown("---")
    st.markdown("### 📦 Outputs")
    if os.path.exists(OUTPUT_DIR) and any(os.listdir(OUTPUT_DIR)):
        st.download_button(
            "⬇️ Download outputs (ZIP)",
            data=make_outputs_zip_bytes(),
            file_name="marketmind_outputs.zip",
            mime="application/zip",
            use_container_width=True,
        )
        st.caption("Includes JSON + Markdown reports.")
    else:
        st.caption("Run analysis to generate downloadable outputs.")

# Parse lists
competitors_list = parse_csv_list(competitors_raw)
features_list = parse_csv_list(features_raw)

# ----------------------------
# Run Analysis
# ----------------------------
if run_btn:
    if len(competitors_list) < 1:
        st.error("Please enter at least 1 competitor.")
    else:
        with st.spinner("Running analysis…"):
            try:
                result = run_analysis(
                    product_name=product_name,
                    industry=industry,
                    geography=geography,
                    scale=scale,
                    competitors=competitors_list,
                    features=features_list,
                )
                st.session_state["last_run"] = datetime.utcnow().isoformat()
                st.session_state["last_files"] = result.get("files_written", [])
                st.success("✅ Analysis completed successfully")
            except Exception as e:
                st.error("❌ Error running analysis. Check Render logs for details.")
                st.exception(e)

# ----------------------------
# Load Outputs
# ----------------------------
prices_json = safe_load_json(os.path.join(OUTPUT_DIR, "competitor_prices.json"))
scores_json = safe_load_json(os.path.join(OUTPUT_DIR, "feature_scores.json"))
growth_json = safe_load_json(os.path.join(OUTPUT_DIR, "market_growth.json"))
sentiment_metrics = safe_load_json(os.path.join(OUTPUT_DIR, "sentiment_metrics.json"))
review_sent_md = safe_read_text(os.path.join(OUTPUT_DIR, "review_sentiment.md"))
feature_table_md = safe_read_text(os.path.join(OUTPUT_DIR, "feature_comparison.md"))

# ----------------------------
# Tabs
# ----------------------------
tab_overview, tab_pricing, tab_features, tab_growth, tab_reports = st.tabs(
    ["🏠 Overview", "💰 Pricing", "⚙️ Features", "📈 Product Trend", "📘 Reports"]
)

# ============================
# Overview
# ============================
with tab_overview:
    left, r1, r2, r3 = st.columns([2.2, 1, 1, 1])

    with left:
        st.markdown("<div class='mm-card'>", unsafe_allow_html=True)
        st.subheader("Study configuration")
        st.markdown(f"**Product:** {product_name}")
        st.markdown(f"**Industry:** {industry}")
        st.markdown(f"**Geography:** {geography}  |  **Scale:** {scale}")
        st.markdown(f"**Competitors:** {', '.join(competitors_list) if competitors_list else '—'}")
        st.markdown(f"**Features:** {', '.join(features_list) if features_list else '—'}")
        if st.session_state.get("last_run"):
            st.caption(f"Last run (UTC): {st.session_state['last_run']}")
        else:
            st.caption("Not run yet. Configure inputs and click **Run Market Research**.")
        st.markdown("</div>", unsafe_allow_html=True)

    # BEFORE analysis: show 0/0/0
    pos = int((sentiment_metrics or {}).get("positive", 0) or 0)
    neg = int((sentiment_metrics or {}).get("negative", 0) or 0)
    neu = int((sentiment_metrics or {}).get("neutral", 0) or 0)

    with r1:
        st.markdown("<div class='mm-card'>", unsafe_allow_html=True)
        st.metric("Positive", f"{pos}%")
        st.markdown("</div>", unsafe_allow_html=True)
    with r2:
        st.markdown("<div class='mm-card'>", unsafe_allow_html=True)
        st.metric("Negative", f"{neg}%")
        st.markdown("</div>", unsafe_allow_html=True)
    with r3:
        st.markdown("<div class='mm-card'>", unsafe_allow_html=True)
        st.metric("Neutral", f"{neu}%")
        st.markdown("</div>", unsafe_allow_html=True)

    st.write("")
    st.subheader("💬 Sentiment overview")

    if not sentiment_metrics:
        st.info("Run the analysis to generate sentiment metrics and the sentiment chart.")
    else:
        df_sent = pd.DataFrame(
            {"Sentiment": ["Positive", "Negative", "Neutral"], "Percentage": [pos, neg, neu]}
        )
        fig_sent = px.pie(
            df_sent,
            names="Sentiment",
            values="Percentage",
            hole=0.38,
            title=f"Sentiment Breakdown for {product_name}",
            color="Sentiment",
            color_discrete_map={
                "Positive": MM_PALETTE[3],
                "Negative": MM_PALETTE[1],
                "Neutral": "#94A3B8",
            },
        )
        fig_sent.update_traces(textinfo="percent+label")
        st.plotly_chart(fig_sent, use_container_width=True)

        # IMPORTANT: remove quotes here (keep them only in review_sentiment.md under Reports)
        st.caption("Quotes and source links are included inside **review_sentiment.md** (Reports tab).")

# ============================
# Pricing
# ============================
with tab_pricing:
    st.subheader("💰 Competitor Pricing (AI-fetched)")
    st.caption("Multi-color bars using the same palette family as sentiment.")

    if not prices_json:
        st.info("Run analysis to generate competitor pricing.")
    else:
        df_price = pd.DataFrame(prices_json.get("prices", []))

        if not df_price.empty:
            if "name" in df_price.columns:
                df_price = df_price.rename(columns={"name": "Competitor"})
            if "price" in df_price.columns:
                df_price = df_price.rename(columns={"price": "Price"})

            df_price["Price"] = df_price["Price"].apply(to_float)
            df_price = df_price.dropna(subset=["Competitor", "Price"])

            allowed = set([product_name] + competitors_list)
            df_price = df_price[df_price["Competitor"].isin(allowed)]

        if df_price.empty:
            st.warning("No verified prices found to plot for your selected competitors/product.")
        else:
            # Build per-competitor colors (cycle palette)
            pal = cycle(MM_PALETTE)
            color_map = {name: next(pal) for name in df_price["Competitor"].unique().tolist()}

            fig_price = px.bar(
                df_price,
                x="Competitor",
                y="Price",
                title=f"Pricing (USD) — {product_name} vs competitors",
                color="Competitor",
                color_discrete_map=color_map,
            )
            # Remove bar labels (hover only)
            fig_price.update_traces(texttemplate=None)
            fig_price.update_layout(yaxis_title="Price (USD)")
            st.plotly_chart(fig_price, use_container_width=True)

            with st.expander("🔎 Raw pricing JSON", expanded=False):
                st.json(prices_json)

# ============================
# Features
# ============================
with tab_features:
    st.subheader("⚙️ Feature Comparison Radar")
    st.caption("Uses ONLY your features. Compares product + each competitor.")

    rows = (scores_json or {}).get("scores", [])
    if not rows:
        st.info("Run analysis to generate AI feature scores for the radar chart.")
    else:
        df_scores = pd.DataFrame(rows)
        df_scores.columns = [c.strip().lower() for c in df_scores.columns]

        required = {"product", "feature", "score"}
        if not required.issubset(set(df_scores.columns)):
            st.error(f"feature_scores.json missing fields. Found: {list(df_scores.columns)}")
        else:
            df_scores["score"] = pd.to_numeric(df_scores["score"], errors="coerce")
            df_scores = df_scores.dropna(subset=["score"])

            selected_products = [product_name] + competitors_list
            df_scores = df_scores[df_scores["product"].isin(selected_products)]
            df_scores = df_scores[df_scores["feature"].isin(features_list)]

            if df_scores.empty:
                st.warning("No matching scores for your selected competitors/features. Try re-running analysis.")
            else:
                fig_radar = px.line_polar(
                    df_scores,
                    r="score",
                    theta="feature",
                    color="product",
                    line_close=True,
                    title=f"Feature Comparison: {product_name} vs Selected Competitors",
                    color_discrete_sequence=MM_PALETTE,
                )
                fig_radar.update_traces(fill="toself", opacity=0.55)
                st.plotly_chart(fig_radar, use_container_width=True)

    st.markdown("---")
    st.subheader("📄 Feature Comparison Report (table)")
    if not feature_table_md:
        st.info("feature_comparison.md not found yet. Run analysis.")
    else:
        st.markdown(feature_table_md)

# ============================
# Product Trend
# ============================
with tab_growth:
    st.subheader("📈 Product Demand / Growth Trend")
    st.caption("This should be product-specific (not generic industry growth).")

    if not growth_json:
        st.info("Run analysis to generate product trend.")
    else:
        years = growth_json.get("years", [])
        growth = growth_json.get("growth_percent", [])

        if not years or not growth or len(years) != len(growth):
            st.warning("market_growth.json is incomplete.")
        else:
            df_growth = pd.DataFrame({"Year": years, "Demand / Growth (%)": growth})
            fig_growth = px.line(
                df_growth,
                x="Year",
                y="Demand / Growth (%)",
                markers=True,
                title=f"{product_name} — Demand / Growth Trend ({geography})",
                color_discrete_sequence=[MM_PALETTE[0]],
            )
            fig_growth.update_layout(xaxis=dict(type="category"))
            st.plotly_chart(fig_growth, use_container_width=True)

            rationale = growth_json.get("rationale")
            if rationale:
                with st.expander("Why this trend?", expanded=False):
                    st.write(rationale)

# ============================
# Reports
# ============================
with tab_reports:
    st.subheader("📘 Full Reports")
    st.caption("All markdown outputs generated by the pipeline.")

    md_files = list_md_files()
    if not md_files:
        st.info("No reports found yet. Run analysis first.")
    else:
        preferred_order = [
            "research_plan.md",
            "customer_analysis.md",
            "review_sentiment.md",
            "feature_comparison.md",
            "final_market_strategy_report.md",
        ]
        ordered = [f for f in preferred_order if f in md_files] + [f for f in md_files if f not in preferred_order]

        for md_file in ordered:
            content = safe_read_text(os.path.join(OUTPUT_DIR, md_file)) or ""
            with st.expander(f"📄 {md_file}", expanded=False):
                st.markdown(content)

        st.markdown("---")
        st.download_button(
            "⬇️ Download outputs (ZIP)",
            data=make_outputs_zip_bytes(),
            file_name="marketmind_outputs.zip",
            mime="application/zip",
            use_container_width=True,
        )


