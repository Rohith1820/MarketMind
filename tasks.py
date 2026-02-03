from crewai import Task
from typing import List


class MarketResearchTasks:
    def research_planning_task(self, agent, product_name, industry):
        return Task(
            description=(
                f"Create a structured market research plan for '{product_name}' "
                f"in the '{industry}' industry. Output in markdown."
            ),
            expected_output="Markdown research plan.",
            agent=agent,
        )

    def customer_persona_task(self, agent, product_name, industry, geography, scale):
        return Task(
            description=(
                f"Create 3-5 customer personas for '{product_name}' in '{industry}'.\n"
                f"Geography: {geography}\n"
                f"Scale: {scale}\n\n"
                "IMPORTANT:\n"
                "- Personas must include a short 'How derived' explanation.\n"
                "- Include a 'Customization suggestions' section explaining how user could adjust personas.\n"
                "- Do NOT invent hard facts. Keep plausible and labeled as hypotheses.\n"
                "Output in markdown."
            ),
            expected_output="Markdown personas with derivation + customization suggestions.",
            agent=agent,
        )

    def competitor_pricing_json_task(self, agent, product_name, industry, competitors: List[str]):
        comps = ", ".join(competitors) if competitors else ""
        return Task(
            description=(
                f"Estimate realistic US pricing for '{product_name}' and ONLY the competitors listed.\n"
                f"Industry: {industry}\n"
                f"Competitors: {comps}\n\n"
                "Return STRICT JSON ONLY:\n"
                "{\n"
                f'  "product": "{product_name}",\n'
                '  "currency": "USD",\n'
                '  "prices": [\n'
                f'    {{"name": "{product_name}", "price": 0}},\n'
                '    {"name": "Competitor Name", "price": 0}\n'
                "  ],\n"
                '  "notes": "short reasoning, include if prices are approximate"\n'
                "}\n\n"
                "Rules:\n"
                "- price must be a number (float/int), not a string.\n"
                "- ONLY include given competitors.\n"
            ),
            expected_output="Strict JSON only.",
            agent=agent,
        )

    def feature_comparison_json_task(
        self,
        agent,
        product_name,
        industry,
        competitors: List[str],
        features: List[str],
        pricing_json: dict
    ):
        """
        Generates a comparison table that MUST use user-entered features.
        If a feature is irrelevant to the product category, output 'N/A'.
        Uses pricing_json for the price row if feature includes 'Price'.
        """
        comps = ", ".join(competitors) if competitors else ""
        feats = ", ".join(features) if features else ""

        return Task(
            description=(
                f"Build a feature comparison for '{product_name}' in '{industry}'.\n"
                f"Competitors: {comps}\n"
                f"Features: {feats}\n\n"
                "CRITICAL RULES:\n"
                "- Use ONLY the provided features. Do NOT add or substitute features.\n"
                "- If a feature doesn't apply to this product category, output 'N/A' for that cell.\n"
                "- Keep language consistent with the industry/product (e.g., food should not mention battery).\n"
                "- For any feature that looks like Price / Pricing, use the provided pricing_json values.\n"
                "- Do NOT invent brand facts.\n\n"
                f"pricing_json:\n{pricing_json}\n\n"
                "Return STRICT JSON ONLY:\n"
                "{\n"
                f'  "title": "Feature Comparison Report for {product_name}",\n'
                f'  "industry": "{industry}",\n'
                '  "summary": "1-2 lines, cautious tone",\n'
                '  "comparison_table": [\n'
                '    {\n'
                '      "feature": "Feature name",\n'
                f'      "{product_name}": "value or N/A",\n'
                '      "Competitor 1": "value or N/A",\n'
                '      "Competitor 2": "value or N/A"\n'
                '    }\n'
                '  ]\n'
                "}\n"
            ),
            expected_output="Strict JSON only.",
            agent=agent,
        )

    def sentiment_verified_json_task(self, agent, product_name, industry, sources: List[dict]):
        """
        Sentiment must be grounded in sources.
        If no usable sources, DO NOT include quotes and mark no_verified_sources=true.
        """
        return Task(
            description=(
                f"Analyze brand sentiment for '{product_name}' in '{industry}'.\n\n"
                "You are given sources containing extracted text + URL.\n"
                "You MUST NOT create quotes unless they are present in sources.\n\n"
                f"SOURCES (list of dicts with url,title,text):\n{sources}\n\n"
                "Return STRICT JSON ONLY:\n"
                "{\n"
                f'  "product": "{product_name}",\n'
                '  "no_verified_sources": false,\n'
                '  "sentiment": {"positive": 0, "negative": 0, "neutral": 0},\n'
                '  "themes": {\n'
                '    "positive": ["..."],\n'
                '    "negative": ["..."],\n'
                '    "neutral": ["..."]\n'
                "  },\n"
                '  "quotes": [\n'
                '    {\n'
                '      "polarity": "positive|negative|neutral",\n'
                '      "quote": "verbatim snippet from source",\n'
                '      "url": "source url"\n'
                '    }\n'
                "  ]\n"
                "}\n\n"
                "Rules:\n"
                "- Percentages must sum to ~100.\n"
                "- If sources are empty or insufficient: set no_verified_sources=true and quotes=[]\n"
                "- Quotes must be verbatim and tied to url.\n"
            ),
            expected_output="Strict JSON only.",
            agent=agent,
        )

    def synthesis_task(self, agent, product_name, industry, context_tasks):
        return Task(
            description=(
                f"Synthesize prior outputs into a final strategy report for '{product_name}' in '{industry}'.\n\n"
                "Rules:\n"
                "- Do not include an implementation timeline unless user explicitly requested it.\n"
                "- Do not include budgets unless user explicitly provided a budget range.\n"
                "- Any claims about sentiment must match the verified sentiment JSON.\n"
                "- If no_verified_sources=true, explicitly state sentiment is not source-verified.\n"
                "Output in markdown."
            ),
            expected_output="Final markdown strategy report.",
            agent=agent,
            context=context_tasks,
        )
