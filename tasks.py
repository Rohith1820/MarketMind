# tasks.py
from crewai import Task


class MarketResearchTasks:
    # --------------------------------------------
    # 1️⃣ Research Planning
    # --------------------------------------------
    def research_planning_task(self, agent, product_name, industry):
        return Task(
            description=(
                f"Develop a structured research plan for **{product_name}** in the **{industry}** industry. "
                "Identify data sources, key market questions, and methods for gathering insights."
            ),
            expected_output=(
                "A detailed research plan in markdown, covering objectives, data sources, "
                "target audiences, and approaches for market data collection."
            ),
            agent=agent,
        )

    # --------------------------------------------
    # 2️⃣ Competitor Analysis
    # --------------------------------------------
    def competitor_analysis_task(self, agent, product_name, industry):
        return Task(
            description=(
                f"Identify and analyze at least **5 real-world competitors** for **{product_name}** "
                f"in the **{industry}** industry.\n\n"
                "For each competitor, include:\n"
                "- Product name\n"
                "- Company name\n"
                "- Price in USD (if available)\n"
                "- Key strengths\n"
                "- Weaknesses\n\n"
                "Format the output in clean markdown with one section per competitor."
            ),
            expected_output=(
                "A markdown document listing 5+ real competitors with pricing and strengths/weaknesses."
            ),
            agent=agent,
        )

    # --------------------------------------------
    # 3️⃣ Customer Personas & Insights
    # --------------------------------------------
    def customer_persona_task(self, agent, product_name, industry):
        return Task(
            description=(
                f"Develop 3–4 detailed customer personas for **{product_name}** in the **{industry}** market. "
                "Include demographics, psychographics, goals, pain points, and buying motivations."
            ),
            expected_output=(
                "A markdown document with persona cards summarizing customer types, "
                "purchase motivations, and behavioral insights."
            ),
            agent=agent,
        )

    # --------------------------------------------
    # 4️⃣ Review Scraping & Sentiment Analysis
    # --------------------------------------------
    def review_analysis_task(self, agent, product_name):
        return Task(
            description=(
                f"Summarize customer reviews and perform sentiment analysis for **{product_name}**. "
                "If real reviews are unavailable, infer realistic review patterns based on similar products.\n\n"
                "Provide:\n"
                "- Estimated % of positive, negative, and neutral sentiment\n"
                "- Bullet list of most common praises\n"
                "- Bullet list of most common complaints\n"
                "- A short narrative summary of overall sentiment."
            ),
            expected_output=(
                "A markdown sentiment report with percentages and key themes from positive and negative feedback."
            ),
            agent=agent,
        )

    # --------------------------------------------
    # 5️⃣ Executive Summary Generation
    # --------------------------------------------
    def executive_summary_task(self, agent, product_name, industry):
        return Task(
            description=(
                f"Summarize all available research for **{product_name}** in the **{industry}** market "
                "into a short executive summary. Use insights from planning, competitors, customers, "
                "and sentiment (if available)."
            ),
            expected_output=(
                "A concise markdown executive summary (2–4 paragraphs) covering market outlook, "
                "opportunities, risks, and 3–5 top recommendations."
            ),
            agent=agent,
        )

    # --------------------------------------------
    # 6️⃣ Final Strategic Synthesis
    # --------------------------------------------
    def synthesis_task(self, agent, product_name, industry, dependencies):
        return Task(
            description=(
                f"Synthesize insights from all prior analyses — research plan, competitor study, "
                f"customer personas, sentiment analysis, and executive summary — to generate a "
                f"comprehensive market strategy report for **{product_name}** in the **{industry}** industry.\n\n"
                "Include sections: Executive Summary, Market Overview, Competitor Insights, "
                "Customer Insights, Sentiment Analysis, Feature Comparison Summary (if available), "
                "and Strategic Recommendations."
            ),
            expected_output=(
                "A comprehensive markdown report titled 'Final Market Strategy Report' with the sections described."
            ),
            agent=agent,
            context=dependencies,
        )
