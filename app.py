import os
import json
import pandas as pd
import plotly.express as px
import streamlit as st

from main import run_analysis

OUTPUT_DIR = "outputs"


def safe_load_json(path: str):
    try:
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def parse_csv_list(text: str):
    items = []
    for part in (text or "").replace("\n", ",").split(","):
        p = part.strip()
        if p:
            items.append(p)
    # de-dupe
    seen = set()
    out = []
    for x in items:
        k = x.lower()
        if k not in seen:
            out.append(x)
            seen.add(k)
    return out


# ----------------------------
# Streamlit UI
# ----------------------------
st.set_page_config(page_title="MarketMind Dashboard", layout="wide")
st.title("🧠 MarketMind: AI Market Research Assistant")
st.header("📊 MarketMind Insights Dashboard")

st.markdown("""
MarketMind generates **AI-driven market research reports** and dynamic dashboards —
including competitor intelligence, sentiment insights, and growth projections.
""")

os.makedirs(OUTPUT_DIR, exist_ok=True)

with st.expander("⚙️ Configure Product Details", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        product_name = st.text_input("Product Name", "Lao Gan Ma Chili Crisp")
        geography = st.text_input("Target Geography", "US")
    with col2:
        industry = st.text_input("Industry", "Food & Beverage")
        scale = st.selectbox("Business Scale", ["Startup", "SME", "Enterprise"], index=1)

    st.markdown("### 🧩 Custom Comparison Inputs")
    competitors_raw = st.text_area(
        "Competitors (comma or newline separated)",
        "Fly By Jing Sichuan Chili Crisp,\nMomofuku Chili Crunch,\nTrader Joe’s Chili Onion Crunch",
        height=90
    )
    features_raw = st.text_area(
        "Features (comma or newline separated)",
        "Ingredients,\nSpice Level,\nTexture,\nFlavor Profile,\nPackaging,\nPrice",
        height=110
    )

    competitors_list = parse_csv_list(competitors_raw)
    features_list = parse_csv_list(features_raw)

    if len(competitors_list) == 0:
        st.warning("Enter at least 1 competitor.")
    if len(features_list) < 3:
        st.info("Radar works best with 3+ features.")

st.markdown("---")

# ----------------------------
# Run Analysis
# ----------------------------
if st.button("🚀 Run Market Research Analysis"):
    with st.spinner("Running analysis... this can take 1–3 minutes."):
        try:
            result = run_analysis(
                product_name=product_name,
                industry=industry,
                geography=geography,
                scale=scale,
                competitors=competitors_list,
                features=features_list
            )
            st.success("✅ Analysis completed successfully!")

            with st.expander("Files written", expanded=False):
                st.json(result)

        except Exception as e:
            st.error("❌ Error running analysis. Check Render logs.")
            st.exception(e)

st.markdown("---")

# ----------------------------
# Load outputs
# ----------------------------
sources_meta = safe_load_json(os.path.join(OUTPUT_DIR, "sources.json")) or {}
sentiment_json = safe_load_json(os.path.join(OUTPUT_DIR, "sentiment_metrics.json"))
prices_json = safe_load_json(os.path.join(OUTPUT_DIR, "competitor_prices.json"))
scores_json = safe_load_json(os.path.join(OUTPUT_DIR, "feature_scores.json"))
growth_json = safe_load_json(os.path.join(OUTPUT_DIR, "market_growth.json"))

# ----------------------------
# Sentiment
# ----------------------------
st.subheader("💬 Customer Sentiment Overview")
st.caption(f"Sources used for sentiment: {sources_meta.get('sources_count', 0)} (quotes shown only if verified)")

if not sentiment_json:
    st.info("Run analysis to generate sentiment metrics.")
else:
    pos = int(sentiment_json.get("positive", 0))
    neg = int(sentiment_json.get("negative", 0))
    neu = int(sentiment_json.get("neutral", 0))

    if pos == 0 and neg == 0 and neu == 0:
        st.warning("Sentiment is UNVERIFIED (not enough product-linked scraped text). See review_sentiment.md for details.")
    else:
        df_sentiment = pd.DataFrame({
            "Sentiment": ["Positive", "Negative", "Neutral"],
            "Percentage": [pos, neg, neu]
        })

        fig1 = px.pie(
            df_sentiment,
            names="Sentiment",
            values="Percentage",
            hole=0.3,
            title=f"Sentiment Breakdown for {product_name}"
        )
        fig1.update_traces(textinfo="percent+label")
        st.plotly_chart(fig1, use_container_width=True)

st.markdown("---")

# ----------------------------
# Competitor Pricing
# ----------------------------
st.subheader("💰 Competitor Pricing Overview (AI-Estimated)")

if not prices_json:
    st.info("Run analysis to generate AI competitor pricing.")
else:
    rows = prices_json.get("prices", []) or []
    df_price = pd.DataFrame(rows)
    if df_price.empty:
        st.warning("No pricing rows found.")
    else:
        df_price = df_price.rename(columns={"name": "Competitor", "price": "Price ($)"})
        df_price["Price ($)"] = pd.to_numeric(df_price["Price ($)"], errors="coerce")
        df_price = df_price.dropna(subset=["Price ($)"])

        # Keep only competitors user entered (optional)
        allowed = set([c.strip() for c in competitors_list])
        if allowed:
            df_price = df_price[df_price["Competitor"].isin(allowed)]

        if df_price.empty:
            st.warning("No AI prices found for the entered competitors.")
        else:
            fig_price = px.bar(
                df_price,
                x="Competitor",
                y="Price ($)",
                title=f"Competitor Pricing for {product_name}",
                color="Competitor",
            )
            # remove value labels on bars (your request)
            fig_price.update_traces(text=None)
            st.plotly_chart(fig_price, use_container_width=True)

st.markdown("---")

# ----------------------------
# Feature Radar
# ----------------------------
st.subheader("⚙️ Feature Comparison Radar")

rows = (scores_json or {}).get("scores", []) if scores_json else []
expected_products = [product_name] + competitors_list

if not rows:
    st.info("No AI feature scores found. Try running analysis again (ensure OPENAI_API_KEY is set).")
else:
    df_scores = pd.DataFrame(rows)
    df_scores.columns = [c.strip().lower() for c in df_scores.columns]

    required = {"product", "feature", "score"}
    if not required.issubset(set(df_scores.columns)):
        st.error(f"feature_scores.json missing required fields. Found: {list(df_scores.columns)}")
    else:
        df_scores["score"] = pd.to_numeric(df_scores["score"], errors="coerce")
        df_scores = df_scores.dropna(subset=["score"])

        # Debug visibility
        found_products = sorted(df_scores["product"].unique().tolist())
        missing_products = [p for p in expected_products if p not in found_products]
        if missing_products:
            st.warning(
                "Radar missing some competitors in feature_scores.json.\n\n"
                f"Expected: {expected_products}\n"
                f"Found: {found_products}\n"
                f"Missing: {missing_products}"
            )

        # Filter to selected products/features
        df_scores = df_scores[df_scores["product"].isin(expected_products)]
        df_scores = df_scores[df_scores["feature"].isin(features_list)]

        if df_scores.empty:
            st.warning("No feature score rows match your selected competitors/features.")
        else:
            fig3 = px.line_polar(
                df_scores,
                r="score",
                theta="feature",
                color="product",
                line_close=True,
                title=f"Feature Comparison: {product_name} vs Selected Competitors"
            )
            fig3.update_traces(fill="toself", opacity=0.55)
            st.plotly_chart(fig3, use_container_width=True)
# ----------------------------
# Market Growth
# ----------------------------
st.subheader("📈 Market Growth Trend (AI-Estimated)")

if not growth_json:
    st.info("Run analysis to generate AI market growth trend.")
else:
    years = growth_json.get("years", []) or []
    growth = growth_json.get("growth_percent", []) or []
    if not years or not growth or len(years) != len(growth):
        st.warning("Market growth JSON is incomplete.")
    else:
        df_growth = pd.DataFrame({"Year": years, "Market Growth (%)": growth})
        fig_growth = px.line(
            df_growth,
            x="Year",
            y="Market Growth (%)",
            markers=True,
            title=f"Growth Trend in {industry}"
        )
        fig_growth.update_layout(xaxis=dict(type="category"))
        st.plotly_chart(fig_growth, use_container_width=True)

        rationale = growth_json.get("rationale")
        if rationale:
            with st.expander("Why this trend?", expanded=False):
                st.write(rationale)

st.markdown("---")

# ----------------------------
# Reports
# ----------------------------
st.subheader("📘 Full Market Research Reports")

if os.path.exists(OUTPUT_DIR):
    md_files = sorted([f for f in os.listdir(OUTPUT_DIR) if f.endswith(".md")])
    if md_files:
        for md_file in md_files:
            with open(os.path.join(OUTPUT_DIR, md_file), "r", encoding="utf-8") as f:
                content = f.read()
            with st.expander(f"📄 {md_file}", expanded=False):
                st.markdown(content)
    else:
        st.info("No markdown reports found yet. Run analysis first.")

st.sidebar.header("ℹ️ How to Use MarketMind")
st.sidebar.markdown("""
### Steps
1. Enter product + competitors + features  
2. Click **Run Market Research Analysis**  
3. Charts + reports refresh from `/outputs`

### Trust rule
Quotes only appear when the system can verify them from scraped sources.
""")


