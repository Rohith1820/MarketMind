# MarketMind – AI Market Research Assistant

MarketMind is an AI-powered market research assistant that uses multi-agent workflows
to generate structured reports and interactive dashboards for any product.

## Features

- 📦 Product configuration (name, industry, geography, scale)
- 🧠 Multi-agent CrewAI pipeline (planning, competitors, personas, sentiment, synthesis)
- 📊 Streamlit dashboard:
  - Sentiment pie chart
  - Competitor price comparison
  - Feature comparison radar
  - Market growth trend
- 📘 Auto-generated markdown reports in `/outputs`

## Project Structure

```bash
.
├─ app.py                  # Streamlit dashboard
├─ main.py                 # Orchestrates CrewAI pipeline
├─ agents.py               # Agent role definitions
├─ tasks.py                # Task definitions for each analysis step
├─ tools/
│  ├─ __init__.py
│  └─ feature_comparison.py
├─ requirements.txt
└─ README.md

