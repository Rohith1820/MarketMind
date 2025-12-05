import os, re, shutil, subprocess
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="MarketMind Dashboard", layout="wide")
st.title("🧠 MarketMind: AI Market Research Assistant")
st.header("📊 MarketMind Insights Dashboard")

st.markdown("""
MarketMind generates **AI-driven market research reports** and dashboards —
including competitor intelligence, sentiment insights, and growth projections.
""")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")

# ------------------ Input ------------------
with st.expander("⚙️ Configure Product Details", expanded=True):
    c1, c2 = st.columns(2)
    with c1:
        product = st.text_input("Product", "EcoWave Smart Bottle")
        geo = st.text_input("Target Geography", "Global")
    with c2:
        industry = st.text_input("Industry", "Consumer Goods")
        scale = st.selectbox("Business Scale", ["Startup", "SME", "Enterprise"], 1)

# ------------------ Helpers ------------------
def extract_sentiment_summary(fp):
    if not os.path.exists(fp): return (60,30,10)
    txt = open(fp,"r",encoding="utf-8").read().lower()
    get = lambda k,d: int(re.search(k+r"[^0-9]*([0-9]{1,3})%",txt).group(1)) if re.search(k+r"[^0-9]*([0-9]{1,3})%",txt) else d
    return (get("positive",60), get("negative",30), get("neutral",10))

def clean_name(x:str)->str:
    x = re.sub(r"\[.*?\]|\(.*?\)","",x)
    x = re.sub(r"(?i)(company\s*name|competitor|company)[:\-]*","",x)
    x = x.split("|")[0].split(" - ")[0]
    return x.strip()

def is_name(line:str)->bool:
    l=line.strip().lower()
    if not l or len(l)>60 or l.endswith("."): return False
    return not any(re.search(p,l) for p in ["offers","provides","uses","features","equipped","designed"])

def parse_competitors(path:str, product:str)->pd.DataFrame:
    rows=[]
    if os.path.exists(path):
        lines=open(path,"r",encoding="utf-8").readlines()
        for i,l in enumerate(lines):
            m=re.search(r"([₹$]|rs\.?\s*)?([0-9][0-9,\.]*)",l,re.I)
            if not m: continue
            price=float(m.group(2).replace(",",""))
            cand=[lines[j].strip() for j in range(i-1,max(-1,i-6),-1) if lines[j].strip()]
            head=next((c for c in cand if is_name(c)), cand[0]) if cand else product
            head=re.sub(r"^[#\-\*\d\.\)\s]+|\*\*","",head)
            rows.append({"Competitor":clean_name(head),"Price ($)":price})
    if not rows:
        rows=[{"Competitor":"HydraSmart Bottle","Price ($)":799},
              {"Competitor":"PureSip Tech Flask","Price ($)":699},
              {"Competitor":"SmartHydrate 2.0","Price ($)":999},
              {"Competitor":product,"Price ($)":1099}]
    df=pd.DataFrame(rows).head(5)
    df["Competitor"]=df["Competitor"].apply(clean_name)
    return df

# ------------------ Run Analysis ------------------
if st.button("🚀 Run Market Research Analysis"):
    with st.spinner("Running analysis... please wait..."):
        if os.path.exists(OUTPUT_DIR): shutil.rmtree(OUTPUT_DIR)
        os.makedirs(OUTPUT_DIR,exist_ok=True)
        env={**os.environ,"PRODUCT_NAME":product,"INDUSTRY":industry,"GEOGRAPHY":geo,"SCALE":scale}
        p=subprocess.run(["python3","main.py"],text=True,capture_output=True,env=env,cwd=BASE_DIR)
        if p.returncode!=0:
            st.error("❌ Analysis failed."); st.code(p.stderr or p.stdout)
        else:
            st.success(f"✅ Completed successfully for **{product}**!")

st.markdown("---")

# ------------------ Sentiment ------------------
pos,neg,neu=extract_sentiment_summary(os.path.join(OUTPUT_DIR,"review_sentiment.md"))
fig1=px.pie(pd.DataFrame({"Sentiment":["Positive","Negative","Neutral"],"Pct":[pos,neg,neu]}),
            names="Sentiment",values="Pct",hole=0.3,
            color_discrete_map={"Positive":"#2ecc71","Negative":"#e74c3c","Neutral":"#95a5a6"},
            title=f"Sentiment Breakdown for {product}")
st.plotly_chart(fig1,use_container_width=True)

# ------------------ Competitor Pricing ------------------
dfp=parse_competitors(os.path.join(OUTPUT_DIR,"competitor_analysis.md"),product)
fig2=px.bar(dfp,x="Competitor",y="Price ($)",text="Price ($)",color="Competitor",
            title=f"{product} vs Competitors",color_discrete_sequence=px.colors.qualitative.Safe)
st.plotly_chart(fig2,use_container_width=True)
with st.expander("🔍 Parsed competitor data"): st.dataframe(dfp,use_container_width=True)

# ------------------ Radar ------------------
comps=[c for c in dfp["Competitor"] if c!=product][:2] or ["CompA","CompB"]
rad=pd.DataFrame({"Feature":["Design","Performance","Battery","Integration","Price Value"],
                  product:[9,8,7,9,6],comps[0]:[8,7,6,7,7],comps[1]:[7,6,8,6,8]})
f3=px.line_polar(rad.melt(id_vars="Feature",var_name="Product",value_name="Score"),
                 r="Score",theta="Feature",color="Product",line_close=True,
                 title=f"Feature Comparison: {product} vs {comps[0]}, {comps[1]}")
f3.update_traces(fill="toself",opacity=.6)
st.plotly_chart(f3,use_container_width=True)

# ------------------ Market Trend ------------------
trend=pd.DataFrame({"Year":["2023","2024","2025","2026"],"Growth":[12,18,24,33]})
trend["Upper"]=trend["Growth"]*1.12
ft=px.line(trend,x="Year",y="Growth",title=f"Projected Growth in {industry}",markers=True)
fa=px.area(trend,x="Year",y="Upper").update_traces(fill="tonexty",fillcolor="rgba(26,188,156,0.18)",line=dict(color="rgba(0,0,0,0)"))
ft.add_traces(fa.data); ft.update_layout(showlegend=False,plot_bgcolor="white")
st.plotly_chart(ft,use_container_width=True)

# ------------------ Reports ------------------
st.subheader("📘 Reports")
if os.path.exists(OUTPUT_DIR):
    mds=[f for f in os.listdir(OUTPUT_DIR) if f.endswith(".md")]
    if mds:
        for f in mds:
            with open(os.path.join(OUTPUT_DIR,f),"r",encoding="utf-8") as r:
                c=r.read()
            with st.expander(f"📄 {f}",expanded=False): st.markdown(c)
    else: st.info("⚠️ No reports found.")
else: st.warning("Outputs folder missing.")

st.sidebar.header("ℹ️ How to Use")
st.sidebar.markdown("1️⃣ Enter details\n\n2️⃣ Run analysis\n\n3️⃣ View visuals & reports.")
