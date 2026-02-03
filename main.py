import os
import re
import json
import time
import math
import traceback
from typing import List, Dict, Any, Optional

import requests

# NLTK VADER (source-based sentiment)
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer

# Optional extractors (best effort)
try:
    import trafilatura  # great extractor if available
except Exception:
    trafilatura = None

try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None


OUTPUT_DIR = "outputs"


def _write_json(path: str, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def _write_text(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _safe_int(x, default=0):
    try:
        return int(x)
    except Exception:
        return default


def _normalize_product_tokens(product_name: str) -> List[str]:
    base = re.sub(r"[^a-zA-Z0-9\s]", " ", product_name.lower()).split()
    joined = "".join(base)
    tokens = [t for t in base if len(t) >= 3]
    if len(joined) >= 5:
        tokens.append(joined)
    # dedupe
    out = []
    seen = set()
    for t in tokens:
        if t not in seen:
            out.append(t)
            seen.add(t)
    return out


def _split_sentences(text: str) -> List[str]:
    text = re.sub(r"\s+", " ", (text or "")).strip()
    if not text:
        return []
    parts = re.split(r"(?<=[\.\!\?])\s+", text)
    return [p.strip() for p in parts if len(p.strip()) >= 25]


def _mentions_product(sentence: str, tokens: List[str]) -> bool:
    s = sentence.lower()
    return any(t in s for t in tokens)


STOPWORDS = {
    "the","and","a","an","to","of","in","it","is","was","for","on","with","this","that","as",
    "are","be","but","not","have","had","my","we","they","you","i","at","so","if","or",
    "from","by","their","its","them","there","when","what","which","who","will","can","just",
    "very","really","too","also","more","most","much","many","some"
}


def _extract_keywords(sentences: List[str], top_k: int = 6) -> List[str]:
    from collections import Counter
    words = []
    for s in sentences:
        ws = re.findall(r"[a-zA-Z]{3,}", s.lower())
        ws = [w for w in ws if w not in STOPWORDS]
        words.extend(ws)

    counts = Counter(words)
    # remove generic review filler words
    for bad in ["product","products","buy","bought","use","used","using","great","good","bad","love","like"]:
        counts.pop(bad, None)

    return [w for w, _ in counts.most_common(top_k)]


def _serper_search(query: str, max_results: int = 6) -> List[str]:
    """
    Uses SERPER_API_KEY (https://google.serper.dev/).
    Returns a list of URLs.
    """
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
    """
    Best-effort page text extraction:
    - trafilatura if available
    - bs4 fallback
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
    }
    resp = requests.get(url, headers=headers, timeout=25)
    resp.raise_for_status()
    html = resp.text

    if trafilatura:
        downloaded = trafilatura.extract(html, include_comments=False, include_tables=False)
        if downloaded and len(downloaded.strip()) > 200:
            return downloaded.strip()

    if BeautifulSoup:
        soup = BeautifulSoup(html, "html.parser")
        # remove script/style
        for t in soup(["script", "style", "noscript"]):
            t.extract()
        text = soup.get_text(separator=" ")
        text = re.sub(r"\s+", " ", text).strip()
        return text[:20000]  # cap
    return (html or "")[:20000]


def collect_sources(product_name: str, max_urls: int = 6) -> List[Dict[str, Any]]:
    """
    Collect review-like sources. Returns [{"url","text"}].
    """
    # tuned query for "trust" — try to find actual discussions/reviews
    query = f'"{product_name}" review OR reddit OR "rating" OR "taste"'
    urls = _serper_search(query=query, max_results=max_urls)

    sources = []
    for u in urls:
        try:
            time.sleep(0.4)
            txt = _fetch_page_text(u)
            if txt and len(txt) > 300:
                sources.append({"url": u, "text": txt})
        except Exception:
            continue
    return sources


def analyze_sources_sentiment(product_name: str, sources: List[Dict[str, Any]], max_quotes_per_bucket: int = 2) -> Dict[str, Any]:
    """
    Verified sentiment:
    - quotes are verbatim sentences from sources
    - every quote has a source URL
    - if not enough product-linked evidence => unverified
    """
    try:
        nltk.download("vader_lexicon", quiet=True)
    except Exception:
        pass

    analyzer = SentimentIntensityAnalyzer()
    tokens = _normalize_product_tokens(product_name)

    pos_sents, neg_sents, neu_sents = [], [], []
    quote_pool = {"positive": [], "negative": [], "neutral": []}

    for src in sources:
        url = src.get("url", "")
        text = src.get("text", "") or ""
        for sent in _split_sentences(text):
            if not _mentions_product(sent, tokens):
                continue

            compound = analyzer.polarity_scores(sent)["compound"]
            if compound >= 0.25:
                pos_sents.append(sent)
                quote_pool["positive"].append({"quote": sent, "url": url})
            elif compound <= -0.25:
                neg_sents.append(sent)
                quote_pool["negative"].append({"quote": sent, "url": url})
            else:
                neu_sents.append(sent)
                quote_pool["neutral"].append({"quote": sent, "url": url})

    total = len(pos_sents) + len(neg_sents) + len(neu_sents)

    # Trust gate: if we don't have enough evidence, we refuse to pretend
    if total < 8:
        return {
            "product": product_name,
            "no_verified_sources": True,
            "sentiment": {"positive": 0, "negative": 0, "neutral": 0},
            "themes": {"positive": [], "negative": [], "neutral": []},
            "quotes": [],
            "note": "Not enough product-linked text found in sources to compute verified sentiment."
        }

    pos_pct = round((len(pos_sents) / total) * 100)
    neg_pct = round((len(neg_sents) / total) * 100)
    neu_pct = 100 - pos_pct - neg_pct

    themes = {
        "positive": _extract_keywords(pos_sents, top_k=6),
        "negative": _extract_keywords(neg_sents, top_k=6),
        "neutral": _extract_keywords(neu_sents, top_k=6),
    }

    def pick_quotes(bucket: str):
        seen = set()
        out = []
        for q in quote_pool[bucket]:
            key = q["quote"].lower()
            if key in seen:
                continue
            seen.add(key)
            out.append({"polarity": bucket, "quote": q["quote"], "url": q["url"]})
            if len(out) >= max_quotes_per_bucket:
                break
        return out

    quotes = pick_quotes("positive") + pick_quotes("negative")

    return {
        "product": product_name,
        "no_verified_sources": False,
        "sentiment": {"positive": pos_pct, "negative": neg_pct, "neutral": neu_pct},
        "themes": themes,
        "quotes": quotes
    }


def _call_openai_json(prompt: str) -> Optional[dict]:
    """
    Best-effort LLM JSON helper.
    If OpenAI SDK isn't configured, returns None.
    """
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": "Return ONLY valid JSON. No markdown. No commentary."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        text = resp.choices[0].message.content.strip()
        return json.loads(text)
    except Exception:
        return None


def run_analysis(
    product_name: str,
    industry: str,
    geography: str,
    scale: str,
    competitors: List[str],
    features: List[str],
) -> Dict[str, Any]:
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    files_written = []

    # -------------------------
    # 1) SOURCES + VERIFIED SENTIMENT
    # -------------------------
    sources = collect_sources(product_name, max_urls=6)

    sources_meta = {
        "product": product_name,
        "sources_count": len(sources),
        "sources": [{"url": s["url"]} for s in sources],
    }
    p_sources = os.path.join(OUTPUT_DIR, "sources.json")
    _write_json(p_sources, sources_meta)
    files_written.append(p_sources)

    sentiment_payload = analyze_sources_sentiment(product_name=product_name, sources=sources)

    # metrics for pie chart (always written)
    p_sent_metrics = os.path.join(OUTPUT_DIR, "sentiment_metrics.json")
    _write_json(p_sent_metrics, sentiment_payload.get("sentiment", {"positive": 0, "negative": 0, "neutral": 0}))
    files_written.append(p_sent_metrics)

    # markdown report with sourced quotes
    sent = sentiment_payload.get("sentiment", {})
    themes = sentiment_payload.get("themes", {})
    quotes = sentiment_payload.get("quotes", [])

    md_lines = []
    md_lines.append("# Brand Sentiment (Source-Verified)\n")
    md_lines.append(f"**Product:** {product_name}")
    md_lines.append(f"**Industry:** {industry}")
    md_lines.append(f"**Sources Used:** {sources_meta.get('sources_count', 0)}\n")

    if sentiment_payload.get("no_verified_sources"):
        md_lines.append("⚠️ **UNVERIFIED:** Not enough product-linked evidence found in scraped sources.")
        md_lines.append(sentiment_payload.get("note", ""))
        md_lines.append("\n## What you can do")
        md_lines.append("- Try a more specific product name (include brand + exact name).")
        md_lines.append("- Increase sources / enable additional review sources.")
        md_lines.append("- Avoid JS-only pages (harder to scrape).")
    else:
        md_lines.append(f"**Positive Sentiment:** {_safe_int(sent.get('positive'), 0)}%")
        md_lines.append(f"**Negative Sentiment:** {_safe_int(sent.get('negative'), 0)}%")
        md_lines.append(f"**Neutral Sentiment:** {_safe_int(sent.get('neutral'), 0)}%\n")

        md_lines.append("## Themes\n")
        md_lines.append("**Top Positive Themes**")
        for t in (themes.get("positive") or [])[:6]:
            md_lines.append(f"- {t}")
        md_lines.append("\n**Top Negative Themes**")
        for t in (themes.get("negative") or [])[:6]:
            md_lines.append(f"- {t}")

        md_lines.append("\n## Sample Quotes (Verbatim + Sources)\n")
        if not quotes:
            md_lines.append("No quotable product-linked sentences found.")
        else:
            for q in quotes:
                md_lines.append(f'> "{q["quote"]}"')
                md_lines.append(f"- Source: {q['url']}\n")

    p_review_md = os.path.join(OUTPUT_DIR, "review_sentiment.md")
    _write_text(p_review_md, "\n".join(md_lines).strip() + "\n")
    files_written.append(p_review_md)

    # -------------------------
    # 2) FEATURE SCORES (for radar) - strict JSON using user features
    # -------------------------
    # Always write a file so UI doesn't go blank
    feature_scores = {
        "product": product_name,
        "competitors": competitors,
        "features": features,
        "scores": []
    }

    if competitors and features and os.getenv("OPENAI_API_KEY"):
        prompt = f"""
Generate numeric feature scores (0-10) for a radar chart.

Product: {product_name}
Industry: {industry}
Competitors: {competitors}
Features: {features}

Rules:
- Use ONLY the competitor names exactly as given.
- Use ONLY the features exactly as given.
- Output JSON ONLY in this exact format:

{{
  "product": "{product_name}",
  "competitors": {json.dumps(competitors)},
  "features": {json.dumps(features)},
  "scores": [
    {{"product": "NAME", "feature": "FEATURE", "score": 0, "note": ""}}
  ]
}}
"""
        resp = _call_openai_json(prompt)
        if isinstance(resp, dict) and isinstance(resp.get("scores"), list):
            feature_scores = resp

    p_scores = os.path.join(OUTPUT_DIR, "feature_scores.json")
    _write_json(p_scores, feature_scores)
    files_written.append(p_scores)

    # -------------------------
    # 3) MARKET GROWTH (for trend chart) - cautious JSON
    # -------------------------
    market_growth = {
        "industry": industry,
        "geography": geography,
        "years": ["2023", "2024", "2025", "2026"],
        "growth_percent": [0, 0, 0, 0],
        "rationale": "Not generated (missing OPENAI_API_KEY or insufficient context)."
    }

    if os.getenv("OPENAI_API_KEY"):
        prompt = f"""
Estimate market growth trend for:
Industry: {industry}
Geography: {geography}
Competitors context: {competitors}

Return JSON ONLY:
{{
  "industry": "{industry}",
  "geography": "{geography}",
  "years": ["2023","2024","2025","2026"],
  "growth_percent": [0,0,0,0],
  "rationale": "1-2 lines, cautious, no fake citations"
}}
"""
        resp = _call_openai_json(prompt)
        if isinstance(resp, dict) and isinstance(resp.get("years"), list) and isinstance(resp.get("growth_percent"), list):
            market_growth = resp

    p_growth = os.path.join(OUTPUT_DIR, "market_growth.json")
    _write_json(p_growth, market_growth)
    files_written.append(p_growth)

    # -------------------------
    # 4) (OPTIONAL) competitor_prices.json
    # -------------------------
    competitor_prices = {
        "product": product_name,
        "currency": "USD",
        "prices": [],
        "note": "Not generated (missing OPENAI_API_KEY)."
    }

    if competitors and os.getenv("OPENAI_API_KEY"):
        prompt = f"""
Estimate competitor prices for the following product category.

Product: {product_name}
Industry: {industry}
Competitors: {competitors}

Return JSON ONLY:
{{
  "product": "{product_name}",
  "currency": "USD",
  "prices": [
    {{"name": "Competitor Name", "price": 0}}
  ],
  "note": "Short note (no fake citations)"
}}
"""
        resp = _call_openai_json(prompt)
        if isinstance(resp, dict) and isinstance(resp.get("prices"), list):
            competitor_prices = resp

    p_prices = os.path.join(OUTPUT_DIR, "competitor_prices.json")
    _write_json(p_prices, competitor_prices)
    files_written.append(p_prices)

    return {"outputs_dir": OUTPUT_DIR, "files_written": files_written}







