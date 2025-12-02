# tools/feature_comparison.py
import json
import os
from crewai.tools import BaseTool


class FeatureComparisonTool(BaseTool):
    name: str = "feature_comparison"
    description: str = (
        "Compare the product's features with its top competitors to identify unique strengths, "
        "weaknesses, and opportunities for differentiation."
    )

    def _run(self, product_name: str, industry: str) -> str:
        """
        Required by CrewAI BaseTool.
        Generates a simple feature comparison and writes it to outputs/feature_comparison.md.
        Returns a JSON string with the same data.
        """

        # Mocked comparison for demo. In the future you can feed real data here.
        comparisons = [
            {
                "feature": "Design & Build Quality",
                product_name: "Premium, ergonomic design with modern aesthetics.",
                "Competitor A": "Basic design, mostly plastic materials.",
                "Competitor B": "Stylish but less durable over long-term use.",
            },
            {
                "feature": "Performance",
                product_name: "Fast, responsive performance under heavy usage.",
                "Competitor A": "Occasional lag under multitasking.",
                "Competitor B": "Optimized for specific use cases, average otherwise.",
            },
            {
                "feature": "Battery Life",
                product_name: "All-day battery with fast charging support.",
                "Competitor A": "Moderate battery life, no fast charging.",
                "Competitor B": "Good battery, but slower charging.",
            },
            {
                "feature": "Integration",
                product_name: "Seamless integration with mobile app and cloud services.",
                "Competitor A": "Limited integrations with third-party apps.",
                "Competitor B": "Good integrations, but setup is complex.",
            },
            {
                "feature": "Price",
                product_name: "$249",
                "Competitor A": "$199",
                "Competitor B": "$229",
            },
        ]

        report = {
            "title": f"Feature Comparison Report for {product_name}",
            "industry": industry,
            "analysis": (
                f"The comparison suggests that {product_name} leads on design, integration, and overall "
                "user experience, while facing price pressure from lower-cost competitors."
            ),
            "comparison_table": comparisons,
        }

        # Ensure outputs directory exists
        os.makedirs("outputs", exist_ok=True)
        md_path = os.path.join("outputs", "feature_comparison.md")

        # Write a markdown version for the Streamlit dashboard
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# Feature Comparison Report for {product_name}\n\n")
            f.write(f"**Industry:** {industry}\n\n")
            f.write("## Summary\n")
            f.write(report["analysis"] + "\n\n")
            f.write("## Feature Comparison Table\n\n")
            for row in comparisons:
                f.write(f"### {row['feature']}\n")
                for key, val in row.items():
                    if key != "feature":
                        f.write(f"- **{key}**: {val}\n")
                f.write("\n")

        return json.dumps(report, ensure_ascii=False)
