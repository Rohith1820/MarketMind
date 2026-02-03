import os
import json
import logging
import traceback
from typing import Optional, Dict, Any, List

from crewai import Crew
from agents import MarketResearchAgents
from tasks import MarketResearchTasks

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))
logger = logging.getLogger("MarketMind")


def _safe_json_loads(text: str):
    try:
        return json.loads(text)
    except Exception:
        return None


def _write_json(path: str, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def feature_comparison_json_to_md(payload: dict) -> str:
    title = payload.get("title", "Feature Comparison Report")
    industry = payload.get("industry", "")
    summary = payload.get("summary", "")
    table = payload.get("comparison_table", [])

    md = []
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
        values = [str(row.get(c, "")).strip() for c in cols]
        md.append("| " + feat + " | " + " | ".join(values) + " |")

    return "\n".join(md) + "\n"


def _write_sentiment_md(outputs_dir: str, payload: dict):
    sent = payload.get("sentiment", {})
    pos = sent.get("positive", 0)
    neg = sent.get("negative", 0)
    neu = sent.get("neutral", 0)

    md = []
    md.append("# Review Sentiment Summary\n")
    if payload.get("no_verified_sources"):
        md.append("⚠️ **Note:** Sentiment could not be verified from scraped sources. Quotes are omitted.\n")

    md.append(f"**Positive:** {pos}%  ")
    md.append(f"**Negative:** {neg}%  ")
    md.append(f"**Neutral:** {neu}%\n")

    themes = payload.get("themes", {})
    if themes.get("positive"):
        md.append("\n## Top Positive Themes")
        for t in themes["positive"][:6]:
            md.append(f"- {t}")
    if themes.get("negative"):
        md.append("\n## Top Negative Themes")
        for t in themes["negative"][:6]:
            md.append(f"- {t}")
    if themes.get("neutral"):
        md.append("\n## Top Neutral Themes")
        for t in themes["neutral"][:6]:
            md.append(f"- {t}")

    quotes = payload.get("quotes", [])
    if quotes:
        md.append("\n## Verified Quotes (with Sources)")
        for q in quotes[:6]:
            md.append(f'> "{q.get("quote","")}"')
            md.append(f"- Source: {q.get('url','')}\n")

    path = os.path.join(outputs_dir, "review_sentiment.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(md).strip() + "\n")
    return path


def collect_sources_stub(product_name: str) -> List[dict]:
    """
    If you have web scraping enabled, replace this stub with:
    - SERPER query -> URLs
    - scrape_pipeline extract -> text
    Then return: [{"url":..., "title":..., "text":...}, ...]
    For now: returns empty list => sentiment will be marked as unverified (no quotes).
    """
    return []


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

    outputs_dir = "outputs"
    os.makedirs(outputs_dir, exist_ok=True)

    try:
        agents = MarketResearchAgents()
        tasks = MarketResearchTasks()

        consultant = agents.strategy_consultant()
        competitor_agent = agents.competitor_analyst()
        persona_agent = agents.customer_persona_analyst()
        sentiment_agent = agents.review_analyst()
        synthesizer = agents.lead_strategy_synthesizer()

        planning_task = tasks.research_planning_task(consultant, product_name, industry)

        persona_task = tasks.customer_persona_task(
            persona_agent, product_name, industry, geography, scale
        )

        pricing_task = tasks.competitor_pricing_json_task(
            competitor_agent, product_name, industry, competitors
        )

        # Collect sources (replace stub with real scraping later)
        sources = collect_sources_stub(product_name)
        sources_path = os.path.join(outputs_dir, "sources.json")
        _write_json(sources_path, {"product": product_name, "sources": sources})

        sentiment_task = tasks.sentiment_verified_json_task(
            sentiment_agent, product_name, industry, sources
        )

        # Feature comparison MUST use user-entered features + pricing_json
        # We'll run pricing first, then use its output in feature comparison task
        crew_stage_1 = Crew(
            agents=[consultant, competitor_agent, persona_agent, sentiment_agent],
            tasks=[planning_task, persona_task, pricing_task, sentiment_task],
            verbose=True,
        )
        crew_stage_1.kickoff()

        pricing_json = _safe_json_loads(str(getattr(pricing_task, "output", ""))) or {
            "product": product_name,
            "currency": "USD",
            "prices": [{"name": product_name, "price": 0}],
            "notes": "fallback",
        }

        feature_compare_task = tasks.feature_comparison_json_task(
            competitor_agent,
            product_name,
            industry,
            competitors,
            features,
            pricing_json
        )

        synthesis_task = tasks.synthesis_task(
            synthesizer,
            product_name,
            industry,
            [planning_task, persona_task, pricing_task, sentiment_task, feature_compare_task],
        )

        crew_stage_2 = Crew(
            agents=[competitor_agent, synthesizer],
            tasks=[feature_compare_task, synthesis_task],
            verbose=True,
        )
        crew_stage_2.kickoff()

        files_written = []

        # Write pricing json
        competitor_prices_path = os.path.join(outputs_dir, "competitor_prices.json")
        _write_json(competitor_prices_path, pricing_json)
        files_written.append(competitor_prices_path)

        # Write feature comparison md from strict json
        fc_json = _safe_json_loads(str(getattr(feature_compare_task, "output", ""))) or {}
        fc_md = feature_comparison_json_to_md(fc_json)
        feature_md_path = os.path.join(outputs_dir, "feature_comparison.md")
        with open(feature_md_path, "w", encoding="utf-8") as f:
            f.write(fc_md)
        files_written.append(feature_md_path)

        # Write sentiment json + md
        sentiment_payload = _safe_json_loads(str(getattr(sentiment_task, "output", ""))) or {
            "product": product_name,
            "no_verified_sources": True,
            "sentiment": {"positive": 0, "negative": 0, "neutral": 0},
            "themes": {"positive": [], "negative": [], "neutral": []},
            "quotes": [],
        }

        sentiment_metrics = sentiment_payload.get("sentiment", {"positive": 0, "negative": 0, "neutral": 0})
        sentiment_json_path = os.path.join(outputs_dir, "sentiment_metrics.json")
        _write_json(sentiment_json_path, sentiment_metrics)
        files_written.append(sentiment_json_path)

        review_md_path = _write_sentiment_md(outputs_dir, sentiment_payload)
        files_written.append(review_md_path)

        # Write markdown reports
        md_reports = {
            "research_plan.md": getattr(planning_task, "output", ""),
            "customer_analysis.md": getattr(persona_task, "output", ""),
            "final_market_strategy_report.md": getattr(synthesis_task, "output", ""),
        }

        for name, content in md_reports.items():
            if content:
                p = os.path.join(outputs_dir, name)
                with open(p, "w", encoding="utf-8") as f:
                    f.write(str(content))
                files_written.append(p)

        return {"success": True, "outputs_dir": outputs_dir, "files_written": files_written}

    except Exception as e:
        logger.error("Analysis failed: %s", e)
        logger.error(traceback.format_exc())
        raise


if __name__ == "__main__":
    run_analysis()






