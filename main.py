import os
import json
import logging
import traceback
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
    try:
        return json.loads(text)
    except Exception:
        return None


def run_analysis(
    product_name: Optional[str] = None,
    industry: Optional[str] = None,
    geography: Optional[str] = None,
    scale: Optional[str] = None,
    competitors: Optional[List[str]] = None,
    features: Optional[List[str]] = None,
) -> Dict[str, Any]:
    product_name = product_name or os.getenv("PRODUCT_NAME") or "EcoWave Smart Bottle"
    industry = industry or os.getenv("INDUSTRY") or "Consumer Goods"
    geography = geography or os.getenv("GEOGRAPHY") or "US"
    scale = scale or os.getenv("SCALE") or "SME"
    competitors = competitors or []
    features = features or []

    logger.info("🚀 Running analysis for %s (%s)", product_name, industry)
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

        # Core tasks
        planning_task = tasks.research_planning_task(consultant, product_name, industry)
        persona_task = tasks.customer_persona_task(customer_analyst, product_name, industry)

        # AI JSON tasks (key change)
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

        # Feature comparison tool (kept)
        logger.info("🔍 Running feature comparison tool...")
        feature_tool = FeatureComparisonTool()
        feature_output = feature_tool.run(product_name, industry) if hasattr(feature_tool, "run") else feature_tool._run(product_name, industry)
        logger.info("✅ Feature comparison complete.")

        # Synthesis uses markdown context tasks
        synthesis_task = tasks.synthesis_task(
            synthesizer,
            product_name,
            industry,
            [planning_task, pricing_json_task, feature_scores_task, persona_task, review_task],
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

        outputs_dir = "outputs"
        os.makedirs(outputs_dir, exist_ok=True)

        # Write markdown files
        md_files = {
            "research_plan.md": getattr(planning_task, "output", ""),
            "customer_analysis.md": getattr(persona_task, "output", ""),
            "review_sentiment.md": getattr(review_task, "output", ""),
            "feature_comparison.md": feature_output or "",
            "final_market_strategy_report.md": getattr(synthesis_task, "output", ""),
        }

        files_written = []
        for name, content in md_files.items():
            if content:
                path = os.path.join(outputs_dir, name)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(str(content))
                files_written.append(path)

        # Write JSON files (key change)
        pricing_json = _safe_json_loads(str(getattr(pricing_json_task, "output", ""))) or {"prices": []}
        with open(os.path.join(outputs_dir, "competitor_prices.json"), "w", encoding="utf-8") as f:
            json.dump(pricing_json, f, indent=2)
        files_written.append(os.path.join(outputs_dir, "competitor_prices.json"))

        scores_json = _safe_json_loads(str(getattr(feature_scores_task, "output", ""))) or {"scores": []}
        with open(os.path.join(outputs_dir, "feature_scores.json"), "w", encoding="utf-8") as f:
            json.dump(scores_json, f, indent=2)
        files_written.append(os.path.join(outputs_dir, "feature_scores.json"))

        growth_json = _safe_json_loads(str(getattr(growth_task, "output", ""))) or {"years": [], "growth_percent": []}
        with open(os.path.join(outputs_dir, "market_growth.json"), "w", encoding="utf-8") as f:
            json.dump(growth_json, f, indent=2)
        files_written.append(os.path.join(outputs_dir, "market_growth.json"))

        return {
            "success": True,
            "outputs_dir": outputs_dir,
            "files_written": files_written,
        }

    except Exception as e:
        logger.error("❌ Error: %s", str(e))
        logger.error("TRACEBACK:\n%s", traceback.format_exc())
        raise


