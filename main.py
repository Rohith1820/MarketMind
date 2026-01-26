import os
import json
import logging
import traceback
import re
from typing import Optional, Dict, Any, List

from crewai import Crew
from agents import MarketResearchAgents
from tasks import MarketResearchTasks
from tools.feature_comparison import FeatureComparisonTool

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("MarketMind")


def _safe_json_loads(text: str) -> Optional[dict]:
    """Parse a JSON string safely. Returns None if invalid."""
    try:
        return json.loads(text)
    except Exception:
        return None


def _extract_sentiment_from_text(text: str) -> Dict[str, int]:
    """
    Extract Positive/Negative/Neutral percentages from text.
    Falls back to default values if not found.
    """
    t = (text or "").lower()

    def _grab(label: str, default: int) -> int:
        m = re.search(rf"{label}[^0-9]*([0-9]{{1,3}})\s*%", t)
        if not m:
            return default
        try:
            val = int(m.group(1))
            return max(0, min(100, val))
        except Exception:
            return default

    pos = _grab("positive", 60)
    neg = _grab("negative", 30)
    neu = _grab("neutral", 10)

    # Optional: normalize if totals go weird (keep simple & safe)
    total = pos + neg + neu
    if total == 0:
        return {"positive": 60, "negative": 30, "neutral": 10}
    if total != 100:
        # scale to 100 (simple proportional normalization)
        pos = round(pos * 100 / total)
        neg = round(neg * 100 / total)
        neu = 100 - pos - neg

    return {"positive": pos, "negative": neg, "neutral": neu}


def run_analysis(
    product_name: Optional[str] = None,
    industry: Optional[str] = None,
    geography: Optional[str] = None,
    scale: Optional[str] = None,
    competitors: Optional[List[str]] = None,
    features: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Runs MarketMind analysis and writes outputs to ./outputs
    including JSON artifacts for charts.
    """
    product_name = product_name or os.getenv("PRODUCT_NAME") or "EcoWave Smart Bottle"
    industry = industry or os.getenv("INDUSTRY") or "Consumer Goods"
    geography = geography or os.getenv("GEOGRAPHY") or "US"
    scale = scale or os.getenv("SCALE") or "SME"
    competitors = competitors or []
    features = features or []

    logger.info("🚀 Running analysis for %s (%s)", product_name, industry)
    logger.info("Geography=%s | Scale=%s", geography, scale)
    logger.info("Competitors=%s", competitors)
    logger.info("Features=%s", features)

    try:
        agents = MarketResearchAgents()
        tasks = MarketResearchTasks()

        consultant = agents.strategy_consultant()
        competitor_agent = agents.competitor_analyst()
        customer_analyst = agents.customer_persona_analyst()
        sentiment_analyst = agents.review_analyst()
        synthesizer = agents.lead_strategy_synthesizer()

        # --- Tasks ---
        planning_task = tasks.research_planning_task(consultant, product_name, industry)
        persona_task = tasks.customer_persona_task(customer_analyst, product_name, industry)

        pricing_json_task = tasks.competitor_pricing_json_task(
            competitor_agent, product_name, industry, competitors
        )
        feature_scores_task = tasks.feature_scores_json_task(
            competitor_agent, product_name, industry, competitors, features
        )
        growth_task = tasks.market_growth_json_task(
            competitor_agent, product_name, industry, geography, scale, competitors
        )

        review_task = tasks.review_analysis_task(sentiment_analyst, product_name)

        # External tool (kept)
        logger.info("🔍 Running feature comparison tool...")
        feature_tool = FeatureComparisonTool()
        feature_output = feature_tool.run(product_name, industry) if hasattr(feature_tool, "run") else feature_tool._run(product_name, industry)
        logger.info("✅ Feature comparison tool done.")

        synthesis_task = tasks.synthesis_task(
            synthesizer,
            product_name,
            industry,
            [planning_task, pricing_json_task, feature_scores_task, growth_task, persona_task, review_task],
        )

        crew = Crew(
            agents=[consultant, competitor_agent, customer_analyst, sentiment_analyst, synthesizer],
            tasks=[
                planning_task,
                pricing_json_task,
                feature_scores_task,
                growth_task,
                persona_task,
                review_task,
                synthesis_task,
            ],
            verbose=True,
        )

        _ = crew.kickoff()
        logger.info("✅ Crew finished.")

        # --- Write outputs ---
        outputs_dir = "outputs"
        os.makedirs(outputs_dir, exist_ok=True)
        files_written: List[str] = []

        # Markdown reports (keep these)
        md_files = {
            "research_plan.md": getattr(planning_task, "output", ""),
            "customer_analysis.md": getattr(persona_task, "output", ""),
            "review_sentiment.md": getattr(review_task, "output", ""),
            "feature_comparison.md": feature_output or "",
            "final_market_strategy_report.md": getattr(synthesis_task, "output", ""),
        }

        for name, content in md_files.items():
            if content:
                path = os.path.join(outputs_dir, name)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(str(content))
                files_written.append(path)

        # JSON: competitor prices
        pricing_json = _safe_json_loads(str(getattr(pricing_json_task, "output", ""))) or {
            "product": product_name,
            "currency": "USD",
            "prices": []
        }
        prices_path = os.path.join(outputs_dir, "competitor_prices.json")
        with open(prices_path, "w", encoding="utf-8") as f:
            json.dump(pricing_json, f, indent=2)
        files_written.append(prices_path)

        # JSON: feature scores
        scores_json = _safe_json_loads(str(getattr(feature_scores_task, "output", ""))) or {
            "product": product_name,
            "scores": []
        }
        scores_path = os.path.join(outputs_dir, "feature_scores.json")
        with open(scores_path, "w", encoding="utf-8") as f:
            json.dump(scores_json, f, indent=2)
        files_written.append(scores_path)

        # JSON: market growth
        growth_json = _safe_json_loads(str(getattr(growth_task, "output", ""))) or {
            "industry": industry,
            "geography": geography,
            "years": ["2023", "2024", "2025", "2026"],
            "growth_percent": [12, 18, 24, 33],
            "rationale": "Fallback trend used because AI JSON was unavailable."
        }
        growth_path = os.path.join(outputs_dir, "market_growth.json")
        with open(growth_path, "w", encoding="utf-8") as f:
            json.dump(growth_json, f, indent=2)
        files_written.append(growth_path)

        # ✅ JSON: sentiment metrics (NEW)
        review_text = str(getattr(review_task, "output", "") or "")
        sentiment_metrics = _extract_sentiment_from_text(review_text)

        sentiment_path = os.path.join(outputs_dir, "sentiment_metrics.json")
        with open(sentiment_path, "w", encoding="utf-8") as f:
            json.dump(sentiment_metrics, f, indent=2)
        files_written.append(sentiment_path)

        logger.info("✅ Outputs written to %s", outputs_dir)

        return {
            "success": True,
            "outputs_dir": outputs_dir,
            "files_written": files_written,
        }

    except Exception as e:
        logger.error("❌ Error: %s", str(e))
        logger.error("TRACEBACK:\n%s", traceback.format_exc())
        raise


# Optional CLI entrypoint
if __name__ == "__main__":
    run_analysis()
