# tasks.py
from crewai import Task
from typing import List


class MarketResearchTasks:

    # -----------------------------------
    # Research Plan (NO TIMELINE)
    # -----------------------------------
    def research_planning_task(self, agent, product_name: str, industry: str):
        return Task(
            description=(
                f"Create a structured market research plan for '{product_name}' "
                f"in the '{industry}' industry.\n\n"
                "IMPORTANT RULES:\n"
                "- Do NOT include implementation timeline sections.\n"
                "- Do NOT include budget tables.\n"
                "- Keep it strategic and structured.\n"
                "- Label assumptions clearly.\n"
                "Output in markdown."
            ),
            expected_output="Markdown research plan.",
            agent=agent,
        )

    # -----------------------------------
    # Customer Personas
    # -----------------------------------
    def customer_persona_task(
        self,
        agent,
        product_name: str,
        industry: str,
        geography: str,
        scale: str
    ):
        return Task(
            description=(
                f"Create 3–5 realistic customer personas for '{product_name}' "
                f"in the '{industry}' industry.\n\n"
                f"Geography: {geography}\n"
                f"Scale: {scale}\n\n"
                "Rules:\n"
                "- Include 'How Derived' explanation.\n"
                "- Include 'Customization Suggestions'.\n"
                "- Do NOT fabricate statistics.\n"
                "- Keep hypotheses clearly labeled.\n"
                "Output in markdown."
            ),
            expected_output="Markdown personas.",
            agent=agent,
        )

    # -----------------------------------
    # Competitor Pricing JSON
    # -----------------------------------
    def competitor_pricing_json_task(
        self,
        agent,
        product_name: str,
        industry: str,
        competitors: List[str]
    ):
        return Task(
            description=(
                f"Find pricing for '{product_name}' and ONLY these competitors:\n"
                f"{competitors}\n\n"
                "Return STRICT JSON ONLY:\n"
                "{\n"
                f'  "product": "{product_name}",\n'
                '  "currency": "USD",\n'
                '  "prices": [\n'
                '    {"name": "Product Name", "price": 0, "source": ""}\n'
                "  ],\n"
                '  "notes": ""\n'
                "}\n\n"
                "Rules:\n"
                "- Include ONLY product + provided competitors.\n"
                "- If unknown, set price=null.\n"
                "- Do NOT invent random prices.\n"
            ),
            expected_output="Strict JSON only.",
            agent=agent,
        )

    # -----------------------------------
    # Feature Scores for Radar
    # -----------------------------------
    def feature_scores_json_task(
        self,
        agent,
        product_name: str,
        industry: str,
        competitors: List[str],
        features: List[str],
    ):
        return Task(
            description=(
                f"Generate radar chart scores (0-10).\n\n"
                f"Product: {product_name}\n"
                f"Industry: {industry}\n"
                f"Competitors: {competitors}\n"
                f"Features (use ONLY these): {features}\n\n"
                "Return STRICT JSON ONLY:\n"
                "{\n"
                f'  "product": "{product_name}",\n'
                f'  "competitors": {competitors},\n'
                f'  "features": {features},\n'
                '  "scores": [\n'
                '    {"product": "Name", "feature": "Feature", "score": 0, "note": ""}\n'
                "  ]\n"
                "}\n\n"
                "CRITICAL:\n"
                "- Score EVERY feature for EVERY product.\n"
                "- Do NOT invent new features.\n"
                "- If not applicable → score 0.\n"
            ),
            expected_output="Strict JSON only.",
            agent=agent,
        )

    # -----------------------------------
    # PRODUCT Growth Trend (NOT INDUSTRY)
    # -----------------------------------
    def market_growth_json_task(
        self,
        agent,
        product_name: str,
        industry: str,
        geography: str,
        competitors: List[str],
    ):
        return Task(
            description=(
                f"Estimate PRODUCT demand growth trend.\n\n"
                f"Product: {product_name}\n"
                f"Industry: {industry}\n"
                f"Geography: {geography}\n"
                f"Competitor context: {competitors}\n\n"
                "IMPORTANT:\n"
                "- This must be PRODUCT-specific demand trend.\n"
                "- Not general industry CAGR.\n"
                "- Conservative estimates only.\n\n"
                "Return STRICT JSON ONLY:\n"
                "{\n"
                f'  "product": "{product_name}",\n'
                f'  "geography": "{geography}",\n'
                '  "years": ["2023","2024","2025","2026"],\n'
                '  "growth_percent": [0,0,0,0],\n'
                '  "rationale": "Short explanation"\n'
                "}\n"
            ),
            expected_output="Strict JSON only.",
            agent=agent,
        )

    # -----------------------------------
    # Sentiment (Trust-safe)
    # -----------------------------------
    def review_analysis_task(self, agent, product_name: str):
        return Task(
            description=(
                f"Analyze brand sentiment for '{product_name}'.\n\n"
                "Return STRICT JSON ONLY:\n"
                "{\n"
                f'  "product": "{product_name}",\n'
                '  "no_verified_sources": true,\n'
                '  "sentiment": {"positive": 0, "negative": 0, "neutral": 0},\n'
                '  "themes": {"positive": [], "negative": [], "neutral": []},\n'
                '  "quotes": [],\n'
                '  "sources": []\n'
                "}\n\n"
                "CRITICAL:\n"
                "- Do NOT fabricate quotes.\n"
                "- If no sources → quotes must be empty.\n"
                "- Percentages must sum ~100.\n"
            ),
            expected_output="Strict JSON only.",
            agent=agent,
        )

    # -----------------------------------
    # Final Strategy Report
    # -----------------------------------
    def synthesis_task(self, agent, product_name: str, industry: str, context_tasks):
        return Task(
            description=(
                f"Synthesize all prior outputs into final strategy report "
                f"for '{product_name}' in '{industry}'.\n\n"
                "Rules:\n"
                "- No timeline section.\n"
                "- No budget tables.\n"
                "- Match sentiment JSON exactly.\n"
                "- If sentiment unverified, clearly state that.\n"
                "Output in markdown."
            ),
            expected_output="Final markdown report.",
            agent=agent,
            context=context_tasks,
        )

