from crewai import Task
import json


class MarketResearchTasks:

    def research_planning_task(self, agent, product_name, industry):
        return Task(
            description=(
                f"Develop a structured research plan for {product_name} in the {industry} industry."
            ),
            expected_output="A detailed research plan in markdown.",
            agent=agent,
        )

    def customer_persona_task(self, agent, product_name, industry):
        return Task(
            description=(
                f"Develop 3–4 detailed customer personas for {product_name} in the {industry} market. "
                "Include demographics, goals, pain points, and buying motivations."
            ),
            expected_output="Markdown personas.",
            agent=agent,
        )

    def review_analysis_task(self, agent, product_name):
        return Task(
            description=(
                f"Collect and analyze customer reviews for {product_name}. "
                "Perform sentiment analysis and clearly include: "
                "'Positive: X%, Negative: Y%, Neutral: Z%'."
            ),
            expected_output="Markdown sentiment report.",
            agent=agent,
        )

    # -----------------------------
    # NEW: AI Pricing JSON task
    # -----------------------------
    def competitor_pricing_json_task(self, agent, product_name, industry, competitors):
        competitors_text = ", ".join(competitors) if competitors else "(none provided)"
        return Task(
            description=(
                f"Fetch REAL current prices in USD for these competitors of {product_name} "
                f"in the {industry} industry.\n\n"
                f"Competitors list (use ONLY these names): {competitors_text}\n\n"
                "Rules:\n"
                "- Use web search/sources when possible.\n"
                "- If a price cannot be found, set price to null.\n"
                "- Return STRICT JSON only. No markdown.\n\n"
                "JSON schema:\n"
                '{\n'
                '  "product": "<product_name>",\n'
                '  "currency": "USD",\n'
                '  "prices": [\n'
                '    {"name": "<competitor>", "price": 79.99, "source": "<source_name_or_url>"},\n'
                '    ...\n'
                '  ]\n'
                '}\n'
            ),
            expected_output="Strict JSON only.",
            agent=agent,
        )

    # -----------------------------
    # NEW: AI Feature scores JSON
    # -----------------------------
    def feature_scores_json_task(self, agent, product_name, industry, competitors, features):
        competitors_text = ", ".join(competitors) if competitors else "(none provided)"
        features_text = ", ".join(features) if features else "(none provided)"
        return Task(
            description=(
                f"Generate feature scores (0–10) for {product_name} vs the competitors below "
                f"in the {industry} industry.\n\n"
                f"Competitors (use ONLY these): {competitors_text}\n"
                f"Features (use ONLY these): {features_text}\n\n"
                "Rules:\n"
                "- Score 0–10 for each product-feature pair.\n"
                "- Be consistent and realistic.\n"
                "- Return STRICT JSON only.\n\n"
                "JSON schema:\n"
                '{\n'
                '  "product": "<product_name>",\n'
                '  "scores": [\n'
                '    {"product": "<name>", "feature": "<feature>", "score": 7, "rationale": "<short reason>"},\n'
                '    ...\n'
                '  ]\n'
                '}\n'
            ),
            expected_output="Strict JSON only.",
            agent=agent,
        )

    # -----------------------------
    # NEW: Market Growth JSON task
    # -----------------------------
    def market_growth_json_task(self, agent, product_name, industry, geography, scale, competitors):
        competitors_text = ", ".join(competitors) if competitors else "(none provided)"
        return Task(
            description=(
                f"Estimate market growth trend (2023–2026) for {industry} in {geography} "
                f"given the competitive landscape:\n{competitors_text}\n\n"
                f"Business scale: {scale}\n\n"
                "Return STRICT JSON only.\n"
                "Schema:\n"
                '{\n'
                '  "industry": "<industry>",\n'
                '  "geography": "<geography>",\n'
                '  "years": ["2023","2024","2025","2026"],\n'
                '  "growth_percent": [12, 18, 24, 33],\n'
                '  "rationale": "<short explanation of why competitors affect the curve>"\n'
                '}\n'
            ),
            expected_output="Strict JSON only.",
            agent=agent,
        )

    def synthesis_task(self, agent, product_name, industry, dependencies):
        return Task(
            description=(
                f"Create a final market strategy report for {product_name} in {industry} using the provided context."
            ),
            expected_output=(
                "A comprehensive markdown report with sections: "
                "Executive Summary, Market Overview, Competitors, Customers, Sentiment, Recommendations."
            ),
            agent=agent,
            context=dependencies,
        )

