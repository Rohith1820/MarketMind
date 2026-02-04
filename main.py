import os
import json
import logging
import traceback
import re
import time
from typing import Optional, Dict, Any, List, Tuple

import requests

from crewai import Crew
from agents import MarketResearchAgents
from tasks import MarketResearchTasks
from tools.feature_comparison import FeatureComparisonTool

# NLTK VADER for verified sentiment
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer

# Optional extractors (don’t hard fail if missing)
try:
    import trafilatura
except Exception:
    trafilatura = None

try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None


LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("MarketMind")

OUTPUTS_DIR = "outputs"


# -----------------------------
# File helpers
# -----------------------------
def _safe_json_loads(text: str) -> Optional[dict]:
    try:
        return json.loads(text)
    except Exception:
        return None


def _write_json(path: str, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def _write_text(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _normalize_price(val: Any) -> str:
    s = str(val).strip()
    if not s:
        return ""
    s = s.replace("$", "").strip()
    return f"${s}"


def _format_price_any(val: Any) -> str:
    if val is None or val == "":
        return ""
    try:
        return f"${float(val):.2f}"
    except Exception:
        return _normalize_price(val)


# -----------------------------
# Feature Comparison (table) — MUST use user features
# -----------------------------
def feature_comparison_md_from_inputs(
    product_name: str,
    industry: str,
    competitors: List[str],
    features: List[str],
    pricing_json: dict,
) -> str:
    """
    Builds a clean Feature Comparison markdown that uses EXACT user-entered features
    and uses pricing_json as the source of truth for Price (if present).
    We deliberately do NOT invent long descriptions here.
    """
    cols = [product_name] + competitors
    md = []
    md.append(f"# Feature Comparison Report for {product_name}\n")
    md.append(f"**Industry:** {industry}\n")
    md.append("## Comparison Table\n")

    # Build price lookup
    price_map = {}
    for item in pricing_json.get("prices", []):
        nm = str(item.get("name", "")).strip()
        pr = item.get("price", None)
        if nm:
            price_map[nm.lower()] = pr

    # Table header
    md.append("| Feature | " + " | ".join(cols) + " |")
    md.append("|---|" + "|".join(["---"] * len(cols)) + "|")

    for feat in features:
        row_vals = []
        feat_key = feat.strip().lower()

        for col in cols:
            if feat_key in {"price", "pricing", "price value"}:
                pr = price_map.get(col.strip().lower())
                row_vals.append(_format_price_any(pr) if pr is not None else "")
            else:
                # Keep blank values (do NOT hallucinate descriptions)
                row_vals.append("")
        md.append("| " + feat.strip() + " | " + " | ".join(row_vals) + " |")

    md.append("\n> Notes:\n")
    md.append("> - This table uses **exactly the features you entered**.\n")
    md.append("> - Non-price cells are left blank intentionally to avoid hallucinations.\n")
    md.append("> - Numerical radar scoring comes from `feature_scores.json`.\n")
    return "\n".join(md) + "\n"


# -----------------------------
# Force feature_scores completeness (fix radar showing only product)
# -----------------------------
def _ensure_complete_feature_scores(
    scores_json: dict,
    product_name: str,
    competitors: List[str],
    features: List[str],
) -> dict:
    """
    Ensures scores_json has rows for ALL (product+competitors) x features.
    If missing, fill with neutral 5 to prevent radar collapsing.
    """
    products = [product_name] + competitors
    desired = {(p, f) for p in products for f in features}

    rows = scores_json.get("scores", [])
    cleaned = []
    seen = set()

    for r in rows:
        if not isinstance(r, dict):
            continue
        p = str(r.get("product", "")).strip()
        f = str(r.get("feature", "")).strip()
        s = r.get("score", None)
        if not p or not f:
            continue
        try:
            s = float(s)
        except Exception:
            continue
        key = (p, f)
        if key in seen:
            continue
        seen.add(key)
        cleaned.append({"product": p, "feature": f, "score": max(0, min(10, s)), "note": r.get("note", "")})

    present = {(r["product"], r["feature"]) for r in cleaned}
    missing = desired - present
    for (p, f) in sorted(list(missing)):
        cleaned.append({"product": p, "feature": f, "score": 5, "note": "filled_missing"})

    return {
        "product": product_name,
        "competitors": competitors,
        "features": features,
        "scores": cleaned,
    }


# -----------------------------
# VERIFIED Sentiment (No hallucinations)
# - Pull sources via Serper
# - Scrape pages
# - Extract sentences mentioning product tokens
# - Score with VADER
# - Quotes are verbatim + URL
# -----------------------------
def _serper_search(query: str, max_results: int = 6) -> List[str]:
    api_key = os.getenv("SERPER_API_KEY", "")
    if not api_key:
        return []
    url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    payload = {"q": query}
    r = requests.post(url, headers=headers, json=payload, timeout=25)
    r.raise_for_status()
    data = r.json()
    links = []
    for item in (data.get("organic") or [])[:max_results]:
        u = item.get("link")
        if u and u.startswith("http"):
            links.append(u)
    return links


def _fetch_page_text(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
    }
    resp = requests.get(url, headers=headers, timeout=25)
    resp.raise_for_status()
    html = resp.text

    if trafilatura:
        extracted = trafilatura.extract(html, include_comments=False, include_tables=False)
        if extracted and len(extracted.strip()) > 200:
            return extracted.strip()

    if BeautifulSoup:
        soup = BeautifulSoup(html, "html.parser")
        for t in soup(["script", "style", "noscript"]):
            t.extract()
        text = soup.get_text(separator=" ")
        text = re.sub(r"\s+", " ", text).strip()
        return text[:25000]

    return (html or "")[:25000]


def _split_sentences(text: str) -> List[str]:
    text = re.sub(r"\s+", " ", (text or "")).strip()
    if not text:
        return []
    parts = re.split(r"(?<=[\.\!\?])\s+", text)
    return [p.strip() for p in parts if len(p.strip()) >= 25]


def _normalize_product_tokens(product_name: str) -> List[str]:
    base = re.sub(r"[^a-zA-Z0-9\s]", " ", product_name.lower()).split()
    joined = "".join(base)
    tokens = [t for t in base if len(t) >= 3]
    if len(joined) >= 5:
        tokens.append(joined)
    # dedupe
    out, seen = [], set()
    for t in tokens:
        if t not in seen:
            out.append(t)
            seen.add(t)
    return out


def _mentions_product(sentence: str, tokens: List[str]) -> bool:
    s = sentence.lower()
    return any(t in s for t in tokens)


def _extract_keywords(sentences: List[str], top_k: int = 6) -> List[str]:
    from collections import Counter
    STOP = {
        "the","and","a","an","to","of","in","it","is","was","for","on","with","this","that","as",
        "are","be","but","not","have","had","my","we","they","you","i","at","so","if","or",
        "from","by","their","its","them","there","when","what","which","who","will","can","just",
        "very","really","too","also","more","most","much","many","some"
    }
    words = []
    for s in sentences:
        ws = re.findall(r"[a-zA-Z]{3,}", s.lower())
        ws = [w for w in ws if w not in STOP]
        words.extend(ws)

    counts = Counter(words)
    for bad in ["product", "products", "buy", "bought", "use", "used", "using", "great", "good", "bad", "love", "like"]:
        counts.pop(bad, None)

    return [w for w, _ in counts.most_common(top_k)]


def _verified_sentiment(product_name: str) -> dict:
    """
    Returns:
    {
      product,
      sources: [{url}],
      sentiment: {positive, negative, neutral},
      top_positive_themes: [...],
      top_negative_themes: [...],
      sample_quotes: {positive:[{quote,url}], negative:[{quote,url}]},
      note: "... if insufficient evidence"
    }
    """
    try:
        nltk.download("vader_lexicon", quiet=True)
    except Exception:
        pass

    analyzer = SentimentIntensityAnalyzer()
    tokens = _normalize_product_tokens(product_name)

    query = f'"{product_name}" review OR reddit OR "rating" OR "taste" OR "buy"'
    urls = _serper_search(query=query, max_results=6)

    sources = []
    pos_sents, neg_sents, neu_sents = [], [], []
    pos_quotes, neg_quotes = [], []

    for u in urls:
        try:
            time.sleep(0.35)
            txt = _fetch_page_text(u)
            if not txt or len(txt) < 300:
                continue
            sources.append({"url": u})
            for sent in _split_sentences(txt):
                if not _mentions_product(sent, tokens):
                    continue

                score = analyzer.polarity_scores(sent)["compound"]
                if score >= 0.25:
                    pos_sents.append(sent)
                    if len(pos_quotes) < 2:
                        pos_quotes.append({"quote": sent, "url": u})
                elif score <= -0.25:
                    neg_sents.append(sent)
                    if len(neg_quotes) < 2:
                        neg_quotes.append({"quote": sent, "url": u})
                else:
                    neu_sents.append(sent)
        except Exception:
            continue

    total = len(pos_sents) + len(neg_sents) + len(neu_sents)
    if total < 8:
        return {
            "product": product_name,
            "sources": sources,
            "sentiment": {"positive": 0, "negative": 0, "neutral": 0},
            "top_positive_themes": [],
            "top_negative_themes": [],
            "sample_quotes": {"positive": [], "negative": []},
            "note": "Not enough verified product-linked text found to compute sentiment. (No hallucinated quotes.)",
        }

    pos_pct = round((len(pos_sents) / total) * 100)
    neg_pct = round((len(neg_sents) / total) * 100)
    neu_pct = 100 - pos_pct - neg_pct

    return {
        "product": product_name,
        "sources": sources,
        "sentiment": {"positive": pos_pct, "negative": neg_pct, "neutral": neu_pct},
        "top_positive_themes": _extract_keywords(pos_sents, top_k=6),
        "top_negative_themes": _extract_keywords(neg_sents, top_k=6),
        "sample_quotes": {"positive": pos_quotes, "negative": neg_quotes},
        "note": "",
    }


def _write_review_sentiment_md(outputs_dir: str, payload: dict) -> str:
    sentiment = payload.get("sentiment", {})
    pos = sentiment.get("positive", 0)
    neg = sentiment.get("negative", 0)
    neu = sentiment.get("neutral", 0)

    pos_themes = payload.get("top_positive_themes", [])
    neg_themes = payload.get("top_negative_themes", [])
    quotes = payload.get("sample_quotes", {})

    lines = []
    lines.append("# Brand Sentiment (Source-Verified)\n")
    lines.append(f"**Positive:** {pos}%  ")
    lines.append(f"**Negative:** {neg}%  ")
    lines.append(f"**Neutral:** {neu}%\n")

    note = payload.get("note", "")
    if note:
        lines.append(f"⚠️ **Note:** {note}\n")

    sources = payload.get("sources", [])
    if sources:
        lines.append("## Sources Used")
        for s in sources[:10]:
            lines.append(f"- {s.get('url','')}")
        lines.append("")

    if pos_themes:
        lines.append("## Top Positive Themes")
        for t in pos_themes[:6]:
            lines.append(f"- {t}")

    if neg_themes:
        lines.append("\n## Top Negative Themes")
        for t in neg_themes[:6]:
            lines.append(f"- {t}")

    lines.append("\n## Sample Quotes (Verbatim + URL)")
    if quotes:
        if quotes.get("positive"):
            lines.append("\n**Positive:**")
            for q in quotes["positive"][:2]:
                lines.append(f'> "{q.get("quote","")}"')
                lines.append(f"- Source: {q.get('url','')}\n")
        if quotes.get("negative"):
            lines.append("\n**Negative:**")
            for q in quotes["negative"][:2]:
                lines.append(f'> "{q.get("quote","")}"')
                lines.append(f"- Source: {q.get('url','')}\n")
    else:
        lines.append("_No quotes available._")

    path = os.path.join(outputs_dir, "review_sentiment.md")
    _write_text(path, "\n".join(lines).strip() + "\n")
    return path


# -----------------------------
# MAIN
# -----------------------------
def run_analysis(
    product_name: Optional[str] = None,
    industry: Optional[str] = None,
    geography: Optional[str] = None,
    scale: Optional[str] = None,
    competitors: Optional[List[str]] = None,
    features: Optional[List[str]] = None,
) -> Dict[str, Any]:

    product_name = product_name or "EcoWave Smart Bottle"
    industry = industry or "Consumer Goods"
    geography = geography or "US"
    scale = scale or "SME"
    competitors = competitors or []
    features = features or []

    logger.info("🚀 Running MarketMind analysis for %s (%s)", product_name, industry)

    try:
        agents = MarketResearchAgents()
        tasks = MarketResearchTasks()

        consultant = agents.strategy_consultant()
        competitor_agent = agents.competitor_analyst()
        persona_agent = agents.customer_persona_analyst()
        sentiment_agent = agents.review_analyst()
        synthesizer = agents.lead_strategy_synthesizer()

        # Core tasks (same as before)
        planning_task = tasks.research_planning_task(consultant, product_name, industry)
        persona_task = tasks.customer_persona_task(persona_agent, product_name, industry)

        pricing_task = tasks.competitor_pricing_json_task(
            competitor_agent, product_name, industry, competitors
        )

        feature_scores_task = tasks.feature_scores_json_task(
            competitor_agent, product_name, industry, competitors, features
        )

        growth_task = tasks.market_growth_json_task(
            competitor_agent, product_name, industry, geography, scale, competitors
        )

        # Keep this task, but we’ll no longer trust its quotes if it’s generic
        review_task = tasks.review_analysis_task(sentiment_agent, product_name)

        # Synthesis
        synthesis_task = tasks.synthesis_task(
            synthesizer,
            product_name,
            industry,
            [planning_task, pricing_task, feature_scores_task, growth_task, persona_task, review_task],
        )

        crew = Crew(
            agents=[consultant, competitor_agent, persona_agent, sentiment_agent, synthesizer],
            tasks=[
                planning_task,
                pricing_task,
                feature_scores_task,
                growth_task,
                persona_task,
                review_task,
                synthesis_task,
            ],
            verbose=True,
        )

        crew.kickoff()

        # OUTPUTS
        os.makedirs(OUTPUTS_DIR, exist_ok=True)
        files_written: List[str] = []

        # ---- Pricing JSON (source of truth) ----
        pricing_json = _safe_json_loads(str(getattr(pricing_task, "output", ""))) or {
            "product": product_name,
            "currency": "USD",
            "prices": [{"name": product_name, "price": 0}],
        }
        prices_path = os.path.join(OUTPUTS_DIR, "competitor_prices.json")
        _write_json(prices_path, pricing_json)
        files_written.append(prices_path)

        # ---- Feature Comparison MD (MUST use user features, no hallucinations) ----
        # We still keep your FeatureComparisonTool available, but it previously produced generic tech outputs.
        # So we generate the markdown ourselves from user inputs + pricing truth.
        feature_md = feature_comparison_md_from_inputs(
            product_name=product_name,
            industry=industry,
            competitors=competitors,
            features=features if features else ["Price"],  # safe fallback
            pricing_json=pricing_json,
        )
        feature_md_path = os.path.join(OUTPUTS_DIR, "feature_comparison.md")
        _write_text(feature_md_path, feature_md)
        files_written.append(feature_md_path)

        # ---- Feature scores JSON (force completeness for radar) ----
        scores_json = _safe_json_loads(str(getattr(feature_scores_task, "output", ""))) or {
            "product": product_name,
            "competitors": competitors,
            "features": features,
            "scores": [],
        }
        scores_json = _ensure_complete_feature_scores(scores_json, product_name, competitors, features)
        scores_path = os.path.join(OUTPUTS_DIR, "feature_scores.json")
        _write_json(scores_path, scores_json)
        files_written.append(scores_path)

        # ---- Market growth JSON ----
        growth_json = _safe_json_loads(str(getattr(growth_task, "output", ""))) or {
            "industry": industry,
            "geography": geography,
            "years": ["2023", "2024", "2025", "2026"],
            "growth_percent": [12, 18, 24, 33],
            "rationale": "Fallback growth curve.",
        }
        growth_path = os.path.join(OUTPUTS_DIR, "market_growth.json")
        _write_json(growth_path, growth_json)
        files_written.append(growth_path)

        # ---- VERIFIED Sentiment (replace generic/hallucinated output) ----
        verified_payload = _verified_sentiment(product_name)

        sentiment_metrics = verified_payload.get("sentiment", {"positive": 0, "negative": 0, "neutral": 0})
        sentiment_json_path = os.path.join(OUTPUTS_DIR, "sentiment_metrics.json")
        _write_json(sentiment_json_path, sentiment_metrics)
        files_written.append(sentiment_json_path)

        review_md_path = _write_review_sentiment_md(OUTPUTS_DIR, verified_payload)
        files_written.append(review_md_path)

        # ---- Markdown reports (make sure ALL exist like before) ----
        md_map = {
            "research_plan.md": getattr(planning_task, "output", "") or "",
            "customer_analysis.md": getattr(persona_task, "output", "") or "",
            "final_market_strategy_report.md": getattr(synthesis_task, "output", "") or "",
        }

        for name, content in md_map.items():
            path = os.path.join(OUTPUTS_DIR, name)
            if content.strip():
                _write_text(path, str(content))
            else:
                # create placeholder so UI always shows file
                _write_text(
                    path,
                    f"# {name.replace('_',' ').replace('.md','').title()}\n\n"
                    f"⚠️ This file was not generated by the agent in this run.\n"
                    f"- Product: {product_name}\n"
                    f"- Industry: {industry}\n"
                )
            files_written.append(path)

        # Also write sources.json for transparency
        sources_path = os.path.join(OUTPUTS_DIR, "sources.json")
        _write_json(sources_path, {"product": product_name, "sources": verified_payload.get("sources", [])})
        files_written.append(sources_path)

        return {"success": True, "outputs_dir": OUTPUTS_DIR, "files_written": files_written}

    except Exception as e:
        logger.error("❌ Analysis failed: %s", e)
        logger.error(traceback.format_exc())
        raise


if __name__ == "__main__":
    run_analysis()









