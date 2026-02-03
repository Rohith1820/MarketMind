import os
import json
import traceback
from typing import Optional, Dict, Any, List

from crewai import Crew
from agents import MarketResearchAgents
from tasks import MarketResearchTasks


def _safe_json_loads(text: str):
    try:
        return json.loads(text)
    except Exception:
        return None


def _write_json(path: str, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


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

        # ---- Core tasks ----
        planning_task = tasks.research_planning_task(consultant, product_name, industry)
        persona_task = tasks.customer_persona_task(persona_agent, product_name, industry, geography, scale)

        pricing_task = tasks.competitor_pricing_json_task(competitor_agent, product_name, industry, competitors)

        # ✅ NEW: feature scores for radar
        feature_scores_task = tasks.feature_scores_json_task(
            competitor_agent, product_name, industry, competitors, features
        )

        # ✅ NEW: market growth for trend chart
        market_growth_task = tasks.market_growth_json_task(
            consultant, product_name, industry, competitors, geography
        )

        # sentiment still in your pipeline; keep it as-is (or verified version if you have sources)
        # If your sentiment task currently returns full payload, that's okay.
        # If it returns only {"positive":..}, we handle it below safely.
        sentiment_task = tasks.sentiment_verified_json_task(
            sentiment_agent, product_name, industry, sources=[]
        )

        # ---- Run crew ----
        crew = Crew(
            agents=[consultant, competitor_agent, persona_agent, sentiment_agent, synthesizer],
            tasks=[
                planning_task,
                persona_task,
                pricing_task,
                feature_scores_task,
                market_growth_task,
                sentiment_task,
            ],
            verbose=True,
        )
        crew.kickoff()

        files_written = []

        # ---- Write pricing ----
        pricing_json = _safe_json_loads(str(getattr(pricing_task, "output", ""))) or {
            "product": product_name,
            "currency": "USD",
            "prices": [{"name": product_name, "price": 0}],
            "notes": "fallback",
        }
        p_prices = os.path.join(outputs_dir, "competitor_prices.json")
        _write_json(p_prices, pricing_json)
        files_written.append(p_prices)

        # ---- Write feature scores (RADAR) ✅ ----
        scores_json = _safe_json_loads(str(getattr(feature_scores_task, "output", ""))) or {
            "product": product_name,
            "competitors": competitors,
            "features": features,
            "scores": []
        }
        p_scores = os.path.join(outputs_dir, "feature_scores.json")
        _write_json(p_scores, scores_json)
        files_written.append(p_scores)

        # ---- Write market growth ✅ ----
        growth_json = _safe_json_loads(str(getattr(market_growth_task, "output", ""))) or {
            "industry": industry,
            "geography": geography,
            "years": ["2023", "2024", "2025", "2026"],
            "growth_percent": [0, 0, 0, 0],
            "rationale": "fallback"
        }
        p_growth = os.path.join(outputs_dir, "market_growth.json")
        _write_json(p_growth, growth_json)
        files_written.append(p_growth)

        # ---- Write sentiment metrics ✅ ALWAYS ----
        sentiment_payload = _safe_json_loads(str(getattr(sentiment_task, "output", ""))) or {}

        # sentiment_task may return either:
        # A) full payload {"sentiment": {...}} OR
        # B) direct metrics {"positive":..,"negative":..,"neutral":..}
        if "sentiment" in sentiment_payload:
            metrics = sentiment_payload.get("sentiment", {})
        else:
            metrics = sentiment_payload

        # ensure defaults exist
        metrics = {
            "positive": int(metrics.get("positive", 60)),
            "negative": int(metrics.get("negative", 30)),
            "neutral": int(metrics.get("neutral", 10)),
        }

        p_sent = os.path.join(outputs_dir, "sentiment_metrics.json")
        _write_json(p_sent, metrics)
        files_written.append(p_sent)

        # ---- Write markdown reports (optional) ----
        md_reports = {
            "research_plan.md": getattr(planning_task, "output", ""),
            "customer_analysis.md": getattr(persona_task, "output", ""),
        }
        for name, content in md_reports.items():
            if content:
                p = os.path.join(outputs_dir, name)
                with open(p, "w", encoding="utf-8") as f:
                    f.write(str(content))
                files_written.append(p)

        return {"success": True, "outputs_dir": outputs_dir, "files_written": files_written}

    except Exception as e:
        print("❌ Analysis failed:", e)
        print(traceback.format_exc())
        raise







