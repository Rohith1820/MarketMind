from crewai import Task
from typing import List


class MarketResearchTasks:

    def research_planning_task(self, agent, product_name, industry):
        return Task(
            description=(
                f"Create a structured market research plan for {product_name} "
                f"in the {industry} industry."
            ),
            expected_output="A clear research plan in markdown.",
            agent=agent,
        )

    def customer_persona_task(self, agent, product_name, industry):
        return Task(
            description=(
                f"Define customer personas for {product_name} "
                f"in the {industry} industry."
            ),
            expected_output="Customer personas in markdown.",
            agent=agent,
        )

    def competitor_pricing_json_task(
        self,
        agent,
        product_name,
        industry,
        competitors: List[str],
    ):
        return Task(
            description=(
                f"Estimate pricing for {product_name} and its competitors "
                f"in the {industry} industry.\n\n"
                "Return STRICT JSON ONLY in the following format:\n"
                "{\n"
                '  "product": "<product_name>",\n'
                '  "currency": "USD",\n'
                '  "prices": [\n'
                '    {"name": "Competitor A", "price": 29.99},\n'
                '    {"name": "Competitor B", "price": 24.99}\n'
                "  ]\n"
                "}\n\n"
                f"Competitors to include: {competitors}"
            ),
            expected_output="Strict JSON only.",
            agent=agent,
        )

    def feature_scores_json_task(
        self,
        agent,
        product_name,
        industry,
        competitors: List[str],
        features: List[str],
    ):
        return Task(
            description=(
                f"Score {product_name} and competitors on selected features "
                f"in the {industry} industry.\n\n"
                "Return STRICT JSON ONLY:\n"
                "{\n"
                '  "product": "<product_name>",\n'
                '  "scores": [\n'
                '    {\n'
                '      "feature": "Design",\n'
                '      "scores": {\n'
                '        "<product_name>": 8,\n'
                '        "Competitor A": 7\n'
                "      }\n"
                "    }\n"
                "  ]\n"
                "}\n\n"
                f"Features: {features}\n"
                f"Competitors: {competitors}"
            ),
            expected_output="Strict JSON only.",
            agent=agent,
        )

    def market_growth_json_task(
        self,
        agent,
        product_name,
        industry,
        geography,
        scale,
        competitors: List[str],
    ):
        return Task(
            description=(
                f"Estimate market growth for {product_name} "
                f"in the {industry} industry.\n\n"
                "Return STRICT JSON ONLY:\n"
                "{\n"
                '  "industry": "<industry>",\n'
                '  "geography": "<geography>",\n'
                '  "years": ["2023","2024","2025","2026"],\n'
                '  "growth_percent": [12,18,24,33],\n'
                '  "rationale": "Short explanation."\n'
                "}\n\n"
                f"Geography: {geography}\n"
                f"Scale: {scale}\n"
                f"Competitors: {competitors}"
            ),
            expected_output="Strict JSON only.",
            agent=agent,
        )

    def review_analysis_task(self, agent, product_name):
        return Task(
            description=(
                f"Analyze customer reviews for {product_name}.\n\n"
                "Return STRICT JSON ONLY:\n"
                "{\n"
                '  "product": "<product_name>",\n'
                '  "sentiment": {"positive": 62, "negative": 23, "neutral": 15},\n'
                '  "top_positive_themes": ["...","..."],\n'
                '  "top_negative_themes": ["...","..."],\n'
                '  "sample_quotes": {\n'
                '    "positive": ["...","..."],\n'
                '    "negative": ["...","..."]\n'
                "  }\n"
                "}\n"
            ),
            expected_output="Strict JSON only.",
            agent=agent,
        )

    def synthesis_task(self, agent, product_name, industry, context_tasks):
        return Task(
            description=(
                f"Synthesize all prior analysis into a final executive "
                f"market strategy report for {product_name} "
                f"in the {industry} industry.\n\n"
                "Use sentiment metrics exactly as provided. "
                "Do NOT invent new percentages."
            ),
            expected_output="Final executive market strategy report in markdown.",
            agent=agent,
            context=context_tasks,
        )

