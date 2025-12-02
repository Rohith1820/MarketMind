import os
from crewai import Crew
from agents import MarketResearchAgents
from tasks import MarketResearchTasks
from tools.feature_comparison import FeatureComparisonTool


def run():
    # 1️⃣ Configuration from environment (set by app.py)
    product_name = os.getenv("PRODUCT_NAME", "EcoWave Smart Bottle")
    industry = os.getenv("INDUSTRY", "Consumer Goods")

    print(f"\n🚀 Running MarketMind Full Analysis for {product_name} ({industry})\n")

    # 2️⃣ Initialize agents and tasks manager
    agents = MarketResearchAgents()
    tasks = MarketResearchTasks()

    # --- Create agents (these must exist in agents.py)
    strategy_consultant = agents.strategy_consultant()
    competitor_analyst = agents.competitor_analyst()
    customer_analyst = agents.customer_persona_analyst()
    review_analyst = agents.review_analyst()
    synthesizer = agents.lead_strategy_synthesizer()

    # 3️⃣ Define tasks (these must exist in tasks.py)
    planning_task = tasks.research_planning_task(
        strategy_consultant, product_name, industry
    )
    competitor_task = tasks.competitor_analysis_task(
        competitor_analyst, product_name, industry
    )
    customer_task = tasks.customer_persona_task(
        customer_analyst, product_name, industry
    )
    review_task = tasks.review_analysis_task(
        review_analyst, product_name
    )
    exec_summary_task = tasks.executive_summary_task(
        synthesizer, product_name, industry
    )

    # 4️⃣ Feature comparison (separate tool, not a Crew task)
    print("🔍 Running feature comparison tool...")
    feature_tool = FeatureComparisonTool()
    feature_output_md = feature_tool._run(product_name, industry)
    print("✅ Feature comparison complete.\n")

    # 5️⃣ Final synthesis task (depends on all previous tasks)
    synthesis_task = tasks.synthesis_task(
        synthesizer,
        product_name,
        industry,
        [planning_task, competitor_task, customer_task, review_task, exec_summary_task],
    )

    # 6️⃣ Create and run the Crew (this executes all tasks)
    crew = Crew(
        agents=[
            strategy_consultant,
            competitor_analyst,
            customer_analyst,
            review_analyst,
            synthesizer,
        ],
        tasks=[
            planning_task,
            competitor_task,
            customer_task,
            review_task,
            exec_summary_task,
            synthesis_task,
        ],
        verbose=True,
    )

    print("🚀 Executing all AI agents collaboratively...\n")
    results = crew.kickoff()
    print("✅ Crew Execution Completed!\n")

    # 7️⃣ Save outputs into /outputs
    os.makedirs("outputs", exist_ok=True)
    output_files = {
        "research_plan.md": getattr(planning_task, "output", ""),
        "competitor_analysis.md": getattr(competitor_task, "output", ""),
        "customer_analysis.md": getattr(customer_task, "output", ""),
        "review_sentiment.md": getattr(review_task, "output", ""),
        "executive_summary.md": getattr(exec_summary_task, "output", ""),
        "feature_comparison.md": feature_output_md or "",
        "final_market_strategy_report.md": getattr(synthesis_task, "output", ""),
    }

    for filename, content in output_files.items():
        path = os.path.join("outputs", filename)
        if content:
            with open(path, "w", encoding="utf-8") as f:
                f.write(str(content))
        else:
            print(f"⚠️ Warning: No content for {filename}")

    print("\n🎯 All tasks completed. Reports saved to outputs/ directory!\n")
    os.system("ls -lh outputs || echo 'No outputs directory'")
    os.system("head -n 40 outputs/final_market_strategy_report.md || echo 'No final report.'")


if __name__ == "__main__":
    run()
