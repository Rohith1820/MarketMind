import os
import json
import logging
import traceback
from typing import Optional, Dict, Any, List, Callable

from crewai import Crew
from agents import MarketResearchAgents
from tasks import MarketResearchTasks

# If you still use this tool, keep it. If not, you can remove it safely.
try:
    from tools.feature_comparison import FeatureComparisonTool
except Exception:
    FeatureComparisonTool = None


LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("MarketMind")

OUTPUT_DIR = "outputs"


# ----------------------------
# Helpers
# ----------------------------
def _safe_json_loads(text: str) -> Optional[dict]:
    try:
        if text is None:
            return None
        return json.loads(text)
    except Exception:
        return None


def _write_json(path: str, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def _normalize_price(val: Any) -> str:
    s = str(val).strip()
    if not s:
        return ""
    s = s.replace("$", "").strip()
    try:
        return f"${float(s):.2f}"
    except Exception:
        return f"${s}"


def _write_text(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(str(content or "").strip() + "\n")


def _write_review_sentiment_md(outputs_dir: str, payload: dict) -> str:
    """
    Writes a clean review_sentiment.md from the SAME JSON used by the app chart.
    """
    sentiment = payload.get("sentiment", {})
    pos = int(sentiment.get("positive", 60))
    neg = int(sentiment.get("negative", 30))
    neu = int(sentiment.get("neutral", 10))

    themes = payload.get("themes", {})
    pos_themes = themes.get("positive", []) or payload.get("top_positive_themes", []) or []
    neg_themes = themes.get("negative", []) or payload.get("top_negative_themes", []) or []
    quotes = payload.get("quotes", []) or payload.get("sample_quotes", {})

    lines: List[str] = []
    lines.append("# Review Sentiment Summary\n")
    lines.append(f"**Positive:** {pos}%  ")
    lines.append(f"**Negative:** {neg}%  ")
    lines.append(f"**Neutral:** {neu}%\n")

    # Themes are optional — you can remove if you want (kept concise)
    if pos_themes:
        lines.append("## Top Positive Themes")
        for t in pos_themes[:5]:
            lines.append(f"- {t}")
        lines.append("")

    if neg_themes:
        lines.append("## Top Negative Themes")
        for t in neg_themes[:5]:
            lines.append(f"- {t}")
        lines.append("")

    # Quotes must be source-tied if you enforce that in tasks
    # We support both formats:
    # 1) quotes: [{polarity, quote, url}]
    # 2) sample_quotes: {positive:[...], negative:[...]}
    lines.append("## Sample Quotes")
    if isinstance(quotes, list) and quotes:
        for q in quotes[:6]:
            polarity = (q.get("polarity") or "").strip().lower()
            quote = (q.get("quote") or "").strip()
            url = (q.get("url") or "").strip()
            if quote:
                tag = polarity.capitalize() if polarity else "Quote"
                if url:
                    lines.append(f"- **{tag}:** “{quote}”  \n  Source: {url}")
                else:
                    lines.append(f"- **{tag}:** “{quote}”")
    else:
        # fallback: dict style
        if isinstance(quotes, dict):
            posq = quotes.get("positive", []) or []
            negq = quotes.get("negative", []) or []
            if posq:
                lines.append("\n**Positive:**")
                for q in posq[:3]:
                    lines.append(f"> {q}")
            if negq:
                lines.append("\n**Negative:**")
                for q in negq[:3]:
                    lines.append(f"> {q}")

    path = os.path.join(outputs_dir, "review_sentiment.md")
    _write_text(path, "\n".join(lines))
    return path


def feature_comparison_json_to_md(payload: dict) -> str:
    title = payload.get("title", "Feature Comparison Report")
    industry = payload.get("industry", "")
    summary = payload.get("summary", "")
    table = payload.get("comparison_table", [])

    md: List[str] = []
    md.append(f"# {title}\n")
    if industry:
        md.append(f"**Industry:** {industry}\n")
    if summary:
        md.append(f"**Summary:** {summary}\n")

    md.append("## Comparison Table\n")
    if not table:
        md.append("_No comparison table generated._\n")
        return "\n".join(md)

    cols = [k for k in table[0].keys() if k != "feature"]
    md.append("| Feature | " + " | ".join(cols) + " |")
    md.append("|---|" + "|".join(["---"] * len(cols)) + "|")

    for row in table:
        feat = str(row.get("feature", "")).strip()
        values = []
        for c in cols:
            v = row.get(c, "")
            if feat.lower() in {"price", "pricing"}:
                v = _normalize_price(v)
            values.append(str(v).strip())
        md.append("| " + feat + " | " + " | ".join(values) + " |")

    return "\n".join(md) + "\n"


def patch_price_row_from_competitor_prices(
    fc_payload: dict,
    pricing_json: dict,
    product_name: str,
    competitors: List[str],
) -> dict:
    """
    Overwrites Price row using competitor_prices.json.
    Supports real column names AND generic Competitor A/B/C.
    """
    if not fc_payload or "comparison_table" not in fc_payload:
        return fc_payload

    price_map: Dict[str, Any] = {}
    for item in pricing_json.get("prices", []):
        nm = str(item.get("name", "")).strip()
        pr = item.get("price", None)
        if nm:
            price_map[nm.lower()] = pr

    def fmt(p: Any) -> str:
        if p is None or p == "":
            return ""
        try:
            return f"{float(p):.2f}"
        except Exception:
            return str(p).replace("$", "").strip()

    generic_map: Dict[str, str] = {}
    for i, comp in enumerate(competitors):
        generic_map[f"competitor {chr(ord('a') + i)}"] = comp.lower()

    for row in fc_payload["comparison_table"]:
        feat = str(row.get("feature", "")).strip().lower()
        if feat in {"price", "pricing"}:
            for col in list(row.keys()):
                if col == "feature":
                    continue
                col_key = str(col).strip().lower()

                if col_key in price_map:
                    row[col] = fmt(price_map[col_key])
                    continue

                if col_key in generic_map:
                    real_key = generic_map[col_key]
                    if real_key in price_map:
                        row[col] = fmt(price_map[real_key])

            prod_key = product_name.strip().lower()
            if prod_key in price_map:
                for col in list(row.keys()):
                    if col == "feature":
                        continue
                    if col.strip().lower() == prod_key:
                        row[col] = fmt(price_map[prod_key])
                        break
            break

    return fc_payload


def _call_task_with_fallbacks(fn: Callable, *attempts):
    """
    Tries multiple argument tuples until one matches the task signature.
    This is what prevents your 'missing positional argument' crash.
    """
    last_err = None
    for args in attempts:
        try:
            return fn(*args)
        except TypeError as e:
            last_err = e
            continue
    raise last_err


# ----------------------------
# Main entry
# ----------------------------
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

        # --- Core tasks ---
        planning_task = tasks.research_planning_task(consultant, product_name, industry)

        # persona task signature differs in your versions; keep it safe:
        persona_task = _call_task_with_fallbacks(
            tasks.customer_persona_task,
            (persona_agent, product_name, industry, geography, scale),  # newer
            (persona_agent, product_name, industry),                    # older
        )

        pricing_task = tasks.competitor_pricing_json_task(
            competitor_agent, product_name, industry, competitors
        )

        feature_scores_task = tasks.feature_scores_json_task(
            competitor_agent, product_name, industry, competitors, features
        )

        # ✅ FIX: market_growth_json_task has changed across your versions.
        # We try common signatures:
        growth_task = _call_task_with_fallbacks(
            tasks.market_growth_json_task,
            (competitor_agent, product_name, industry, competitors, geography),             # (agent, product, industry, competitors, geography)
            (competitor_agent, product_name, industry, geography, scale, competitors),     # (agent, product, industry, geography, scale, competitors)
            (competitor_agent, product_name, industry, geography, competitors),            # (agent, product, industry, geography, competitors)
        )

        review_task = tasks.review_analysis_task(sentiment_agent, product_name)

        # Feature comparison tool (optional)
        raw_feature_output = None
        if FeatureComparisonTool is not None:
            feature_tool = FeatureComparisonTool()
            raw_feature_output = (
                feature_tool.run(product_name, industry)
                if hasattr(feature_tool, "run")
                else feature_tool._run(product_name, industry)
            )

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

        # ----------------------------
        # Write outputs
        # ----------------------------
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        files_written: List[str] = []

        # ---- Pricing JSON ----
        pricing_json = _safe_json_loads(str(getattr(pricing_task, "output", ""))) or {
            "product": product_name,
            "currency": "USD",
            "prices": [{"name": product_name, "price": 0}],
            "notes": "Fallback pricing JSON (task output missing/invalid).",
        }
        prices_path = os.path.join(OUTPUT_DIR, "competitor_prices.json")
        _write_json(prices_path, pricing_json)
        files_written.append(prices_path)

        # ---- Feature comparison markdown (patch price row if possible) ----
        feature_md = ""
        fc_payload = _safe_json_loads(str(raw_feature_output)) if raw_feature_output else None
        if fc_payload and isinstance(fc_payload, dict):
            fc_payload = patch_price_row_from_competitor_prices(
                fc_payload, pricing_json, product_name=product_name, competitors=competitors
            )
            feature_md = feature_comparison_json_to_md(fc_payload)
        else:
            # If tool isn't available or isn't JSON, still write something
            feature_md = str(raw_feature_output or "Feature comparison tool not available or returned no data.")

        feature_md_path = os.path.join(OUTPUT_DIR, "feature_comparison.md")
        _write_text(feature_md_path, feature_md)
        files_written.append(feature_md_path)

        # ---- Feature scores JSON ----
        scores_json = _safe_json_loads(str(getattr(feature_scores_task, "output", ""))) or {
            "product": product_name,
            "competitors": competitors,
            "features": features,
            "scores": [],
        }
        scores_path = os.path.join(OUTPUT_DIR, "feature_scores.json")
        _write_json(scores_path, scores_json)
        files_written.append(scores_path)

        # ---- Market growth JSON ----
        growth_json = _safe_json_loads(str(getattr(growth_task, "output", ""))) or {
            "industry": industry,
            "geography": geography,
            "years": ["2023", "2024", "2025", "2026"],
            "growth_percent": [12, 18, 24, 33],
            "rationale": "Fallback growth curve (task output missing/invalid).",
        }
        growth_path = os.path.join(OUTPUT_DIR, "market_growth.json")
        _write_json(growth_path, growth_json)
        files_written.append(growth_path)

        # ---- Sentiment JSON + review_sentiment.md (single source of truth) ----
        sentiment_payload = _safe_json_loads(str(getattr(review_task, "output", ""))) or {
            "product": product_name,
            "sentiment": {"positive": 60, "negative": 30, "neutral": 10},
            "themes": {"positive": [], "negative": [], "neutral": []},
            "quotes": [],
            "no_verified_sources": True,
        }

        sentiment_metrics = sentiment_payload.get("sentiment", {"positive": 60, "negative": 30, "neutral": 10})
        sentiment_json_path = os.path.join(OUTPUT_DIR, "sentiment_metrics.json")
        _write_json(sentiment_json_path, sentiment_metrics)
        files_written.append(sentiment_json_path)

        review_md_path = _write_review_sentiment_md(OUTPUT_DIR, sentiment_payload)
        files_written.append(review_md_path)

        # ---- Markdown reports (ALL) ----
        md_map = {
            "research_plan.md": getattr(planning_task, "output", ""),
            "customer_analysis.md": getattr(persona_task, "output", ""),
            "final_market_strategy_report.md": getattr(synthesis_task, "output", ""),
        }
        for name, content in md_map.items():
            if content:
                path = os.path.join(OUTPUT_DIR, name)
                _write_text(path, str(content))
                files_written.append(path)

        logger.info("✅ Analysis complete. Files written: %s", len(files_written))
        return {"success": True, "outputs_dir": OUTPUT_DIR, "files_written": files_written}

    except Exception as e:
        logger.error("❌ Analysis failed: %s", e)
        logger.error(traceback.format_exc())
        raise


if __name__ == "__main__":
    run_analysis()











