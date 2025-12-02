# agents.py
from crewai import Agent


class MarketResearchAgents:
    def __init__(self):
        # No external tools wired in here to keep deployment simple.
        # CrewAI + the LLM will handle most of the reasoning.
        pass

    def strategy_consultant(self):
        return Agent(
            role="Market Strategy Consultant",
            goal="Design a structured research plan for understanding the market, customers, and competition.",
            backstory=(
                "You are a senior market strategist who has worked with global brands to "
                "structure research initiatives, define key questions, and align objectives."
            ),
            verbose=True,
        )

    def competitor_analyst(self):
        return Agent(
            role="Competitor Analyst",
            goal=(
                "Identify and benchmark REAL competitors for the given product, "
                "including pricing, positioning, and key strengths/weaknesses."
            ),
            backstory=(
                "You specialize in competitive intelligence and benchmarking across consumer "
                "and enterprise markets. You always focus on real products and brands."
            ),
            verbose=True,
        )

    def customer_persona_analyst(self):
        return Agent(
            role="Customer Persona Analyst",
            goal=(
                "Develop detailed customer personas describing who buys the product, why, and how "
                "they make decisions."
            ),
            backstory=(
                "You are a behavioral marketing expert who transforms raw data into vivid personas "
                "with goals, pain points, and buying motivations."
            ),
            verbose=True,
        )

    def review_analyst(self):
        return Agent(
            role="Review & Sentiment Analyst",
            goal=(
                "Summarize customer sentiment and identify recurring themes from real or hypothetical reviews."
            ),
            backstory=(
                "You specialize in text analysis, extracting sentiment trends and key pain points "
                "from customer feedback, app store reviews, and social media."
            ),
            verbose=True,
        )

    def lead_strategy_synthesizer(self):
        return Agent(
            role="Lead Strategy Synthesizer",
            goal=(
                "Integrate all research outputs into a clear, structured market strategy report "
                "for executives and product leaders."
            ),
            backstory=(
                "You are a seasoned strategy leader who can read long research artifacts and synthesize "
                "them into concise, compelling narratives with actionable recommendations."
            ),
            verbose=True,
        )
