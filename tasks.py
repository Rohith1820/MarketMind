# tasks.py
from crewai import Task
from typing import List, Dict


class MarketResearchTasks:

    # ---------------------------
    # Markdown Tasks
    # ---------------------------
    def research_planning_task(self, agent, product_name: str, industry: str):
        return Task(
            description=(
                f"Create a structured market research plan for '{product_name}' in the '{industry}' industry.\n"
                "Output in markdown.\n\n"
                "Rules:\n"
                "- Do NOT invent numbers or citations.\n"
                "- If you make assumptions, label them as assumptions.\n"
            ),
            expected_output="Markdown research plan.",
            agent=agent,
        )

    def customer_persona_task(self, agent, product_name: str, industry: str, geography: str = "US", scale: str = "SME"):
        return Task(
            description=(
                f"Create 3-5 customer personas for '{product_name}' in '{industry}'.\n"
                f"Geography: {geography}\n"
                f"Scale: {scale}\n\n"
                "IMPORTANT:\n"
                "- Personas must include a short 'How derived' explanation.\n"
                "- Include a 'Customization suggestions' section for how users can adjust personas.\n"
                "- Do NOT invent hard facts. Keep plausible and label hypotheses.\n"
                "Output in markdown."
            ),
            expected_output="Markdown personas with derivation + customization suggestions.",
            agent=agent,
        )

    # ---------------------------
    # JSON Tasks for Dashboard
    # ---------------------------
    def competitor_pricing_json_task(self, agent, product_name: str, industry: str, competitors: List[str]):
        comps = competitors or []
        return Task(
            description=(
                f"Find pricing for '{product_name}' and ONLY these competitors: {comps}\n"
                f"Industry: {industry}\n\n"
                "Return STRICT JSON ONLY (no markdown):\n"
                "{\n"
                f'  \"product\": \"{product_name}\",\n'
                '  \"currency\": \"USD\",\n'
                '  \"prices\": [\n'
                '    {\"name\": \"<name>\", \"price\": <number|null>, \"source\": \"<url|empty>\"}\n'
                '  ],\n'
                '  \"notes\": \"short notes if approximate or unverified\"\n'
                "}\n\n"
                "Rules:\n"
                "- ONLY include the product + given competitors.\n"
                "- If you cannot verify price, set price=null and source=\"\".\n"
                "- Do NOT output placeholder random values.\n"
            ),
            expected_output="Strict JSON only.",
            agent=agent,
        )

    def feature_scores_json_task(self, agent, product_name: str, industry: str, competitors: List[str], features: List[str]):
        comps = competitors or []
        feats = features or []
        return Task(
            description=(
                f"Generate numeric feature scores (0-10) for a radar chart.\n"
                f"Product: {product_name}\n"
                f"Industry: {industry}\n"
                f"Competitors: {comps}\n"
                f"Features (use ONLY these): {feats}\n\n"
                "Return STRICT JSON ONLY:\n"
                "{\n"
                f'  \"product\": \"{product_name}\",\n'
                f'  \"competitors\": {comps},\n'
                f'  \"features\": {feats},\n'
                '  \"scores\": [\n'
                '    {\"product\": \"<name>\", \"feature\": \"<feature>\", \"score\": 0, \"note\": \"\"}\n'
                "  ]\n"
                "}\n\n"
                "CRITICAL RULES:\n"
                "- You MUST output rows for product_name AND EACH competitor.\n"
                "- You MUST score EVERY feature for EVERY product.\n"
                "- Do NOT invent new features. Do NOT substitute generic tech features.\n"
                "- If not applicable, score 0 and write note='Not applicable'.\n"
            ),
            expected_output="Strict JSON only.",
            agent=agent,
        )

    def market_growth_json_task(self, agent, product_name: str, industry: str, geography: str, scale: str, competitors: List[str]):
        comps = competitors or []
        return Task(
            description=(
                f"Estimate market growth trend for '{industry}'.\n"
                f"Geography: {geography}\n"
                f"Scale: {scale}\n"
                f"Competitor context: {comps}\n\n"
                "Return STRICT JSON ONLY:\n"
                "{\n"
                f'  \"industry\": \"{industry}\",\n'
                f'  \"geography\": \"{geography}\",\n'
                '  \"years\": [\"2023\",\"2024\",\"2025\",\"2026\"],\n'
                '  \"growth_percent\": [0,0,0,0],\n'
                '  \"rationale\": \"1-2 cautious lines\"\n'
                "}\n\n"
                "Rules:\n"
                "- growth_percent values must be numbers.\n"
                "- Do not invent citations.\n"
            ),
            expected_output="Strict JSON only.",
            agent=agent,
        )

    def review_analysis_task(self, agent, product_name: str):
        """
        Trust-safe sentiment JSON. Quotes must be tied to URLs.
        If you do not have sources, quotes must be [] and no_verified_sources=true.
        """
        return Task(
            description=(
                f"Analyze brand sentiment for '{product_name}'.\n\n"
                "Return STRICT JSON ONLY:\n"
                "{\n"
                f'  \"product\": \"{product_name}\",\n'
                '  \"no_verified_sources\": true,\n'
                '  \"sentiment\": {\"positive\": 0, \"negative\": 0, \"neutral\": 0},\n'
                '  \"themes\": {\n'
                '     \"positive\": [],\n'
                '     \"negative\": [],\n'
                '     \"neutral\": []\n'
                "  },\n"
                '  \"quotes\": [\n'
                '     {\"polarity\":\"positive|negative|neutral\",\"quote\":\"verbatim\",\"url\":\"source url\"}\n'
                "  ],\n"
                '  \"sources\": [\"url1\",\"url2\"]\n'
                "}\n\n"
                "CRITICAL TRUST RULES:\n"
                "- Do NOT create quotes unless you have verified sources.\n"
                "- If you do not have sources: no_verified_sources=true, quotes=[], sources=[]\n"
                "- Percentages should sum to ~100.\n"
                "- Themes must match the product category (no battery themes for food).\n"
            ),
            expected_output="Strict JSON only.",
            agent=agent,
        )

    # ---------------------------
    # Final Synthesis (Markdown)
    # ---------------------------
    def synthesis_task(self, agent, product_name: str, industry: str, context_tasks: List[Task]):
        return Task(
            description=(
                f"Synthesize prior outputs into a final strategy report for '{product_name}' in '{industry}'.\n\n"
                "Rules:\n"
                "- Do NOT include an implementation timeline unless user explicitly requested it.\n"
                "- Do NOT include budgets unless user explicitly provided a budget range.\n"
                "- Any claims about sentiment must match the sentiment JSON.\n"
                "- If no_verified_sources=true, explicitly state sentiment is not source-verified.\n"
                "Output in markdown."
            ),
            expected_output="Final markdown strategy report.",
            agent=agent,
            context=context_tasks,
        )

