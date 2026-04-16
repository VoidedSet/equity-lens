"""
Prompts — System Prompt & Tool Schemas
=======================================
Defines the system prompt that instructs the LLM on available tools,
data structure, and how to respond.
"""

COMPANIES_INFO = """
Available Companies (Indian Hotel Sector):
1. Chalet_Hotels — K Raheja Corp group, luxury/upscale hotels (JW Marriott, Westin, etc.)
2. EIH_Limited — Oberoi Hotels group, luxury heritage hotels
3. Indian_Hotels — Tata group (IHCL), operates Taj Hotels, largest chain
4. Juniper_Hotels — Hyatt Hotels partnership, IPO in 2024 (shorter data history)
5. Lemon_Tree_Hotels — Mid-market/economy hotel chain
"""

DATA_STRUCTURE = """
Data Available Per Company:
- balance_sheet_enriched.csv: Equity, Reserves, Borrowings, Fixed Assets, CWIP, Investments, Total Assets/Liabilities + Net Worth, D/E Ratio, Equity Multiplier, Book Value per Share, YoY growths
- profit_loss_enriched.csv: Sales, Expenses, Operating Profit, OPM%, Interest, Depreciation, PBT, Net Profit, EPS + EBITDA, Margins, Interest Coverage, Cost ratios, YoY growths
- quarter_analysis_enriched.csv: Same P&L metrics at quarterly level + QoQ growth, YoY growth, Trailing 4Q sums
- cross_metrics.csv: ROE, ROA, ROCE, Asset Turnover, Fixed Asset Turnover, DuPont decomposition

Data Sources:
- "annual" → profit_loss_enriched or balance_sheet_enriched
- "quarterly" → quarter_analysis_enriched
- "cross" → cross_metrics
- "balance_sheet" → balance_sheet_enriched

Time Periods:
- Annual: Mar 2014 to Mar 2025 (Juniper from Mar 2020 only)
- Quarterly: Dec 2022 to Dec 2025
- Latest balance sheet: Sep 2025
"""

KNOWLEDGE_GRAPH_CONTEXT = """
Knowledge Graph (Neo4j):
The system has a Neo4j knowledge graph built from earnings transcripts and annual reports.
- Node Types: Company, TOPIC, LOCATION, BRAND, STRATEGY, PERSON, TIME_PERIOD
- Relationships: CO_OCCURS (entity co-occurrence in documents)
- Entity properties: name (string), count (int = mention frequency), companies (list of company codes)
- Company codes in graph: IHCL, CHALET, EIH, JUNIPER, LEMONTREE

Key entities extracted include:
- TOPICS: RevPAR, occupancy, room additions, F&B revenue, EBITDA margin, debt reduction, capex, ADR, management contracts, asset-light strategy
- LOCATIONS: Mumbai, Delhi, Bengaluru, Goa, Rajasthan, Jaipur, Udaipur, Kolkata, London, New York
- BRANDS: Taj, Vivanta, Ginger, SeleQtions (IHCL); Oberoi, Trident (EIH); Lemon Tree, Keys (LEMONTREE); JW Marriott, Westin (CHALET); Hyatt, Andaz (JUNIPER)
- STRATEGIES: asset-light expansion, management contracts, renovation capex, F&B diversification, international expansion
- PERSONS: Key management personnel from each company

This context helps answer questions about what topics management discusses, which locations are strategically important, brand portfolio comparisons, and strategic themes across companies.
"""

TOOL_SCHEMAS = [
    {
        "name": "compare_companies",
        "description": "Compare a specific financial metric across multiple companies for given time periods. Use for questions like 'Compare ROE of all companies', 'Which company has highest sales?', 'Compare debt-to-equity ratios'.",
        "parameters": {
            "metric": "The metric to compare (e.g., 'Sales +', 'ROE %', 'Net Profit Margin %', 'Debt-to-Equity Ratio', 'EBITDA Margin %'). Must match a row name in the CSV.",
            "companies": "Comma-separated company names or 'all'. Examples: 'Chalet_Hotels,Indian_Hotels' or 'all'",
            "source": "One of: 'profit_loss_enriched', 'balance_sheet_enriched', 'quarter_analysis_enriched', 'cross_metrics'. Default: auto-detect based on metric.",
            "periods": "Optional. Comma-separated periods to show. E.g., 'Mar 2023,Mar 2024,Mar 2025'. Default: last 3 available."
        }
    },
    {
        "name": "compare_quarters",
        "description": "Analyze quarterly trends for a company. Use for questions like 'Show quarterly sales trend for Chalet Hotels', 'How did Indian Hotels perform quarter by quarter?'.",
        "parameters": {
            "company": "Company name (e.g., 'Indian_Hotels', 'Chalet_Hotels')",
            "metric": "The quarterly metric to track (e.g., 'Sales +', 'Operating Profit', 'Net Profit Margin %')",
            "last_n": "Number of recent quarters to show. Default: 8"
        }
    },
    {
        "name": "financial_health",
        "description": "Generate a financial health scorecard for a company with radar chart. Use for questions like 'How healthy is Chalet Hotels financially?', 'Give me a scorecard for Lemon Tree'.",
        "parameters": {
            "company": "Company name",
            "year": "Optional. The year to evaluate (e.g., 'Mar 2025'). Default: latest available."
        }
    },
    {
        "name": "trend_analysis",
        "description": "Show multi-year trend for any metric of a company. Use for questions like 'Show me EIH revenue trend', 'How has Indian Hotels profit changed over years?'.",
        "parameters": {
            "company": "Company name",
            "metric": "The metric to track",
            "source": "One of: 'profit_loss_enriched', 'balance_sheet_enriched', 'cross_metrics', 'quarter_analysis_enriched'. Default: auto-detect."
        }
    },
    {
        "name": "ratio_deep_dive",
        "description": "Deep dive into financial ratios — DuPont decomposition, leverage analysis. Use for questions like 'Analyze Chalet Hotels DuPont', 'Break down ROE drivers for Indian Hotels'.",
        "parameters": {
            "company": "Company name",
            "year": "Optional. Year to analyze. Default: latest."
        }
    },
    {
        "name": "sector_benchmark",
        "description": "Rank all 5 companies across key financial KPIs with a heatmap. Use for questions like 'Rank all hotels', 'Which is the best hotel company?', 'Sector comparison'.",
        "parameters": {
            "year": "Optional. Year for comparison. Default: latest available.",
            "metrics": "Optional. Comma-separated metrics to rank on. Default: key KPIs (Sales, OPM, NPM, ROE, ROCE, D/E, ICR)."
        }
    },
    {
        "name": "custom_analysis",
        "description": "For queries that don't match any pre-built tool. The agent will write and execute a custom Python script. Use as a last resort.",
        "parameters": {
            "query": "The original user query",
            "analysis_plan": "A step-by-step plan of what data to load and what calculations to perform"
        }
    },
]


def get_system_prompt() -> str:
    """Build the full system prompt for the LLM."""
    tools_text = ""
    for tool in TOOL_SCHEMAS:
        tools_text += f"\n### {tool['name']}\n"
        tools_text += f"{tool['description']}\n"
        tools_text += "Parameters:\n"
        for param, desc in tool['parameters'].items():
            tools_text += f"  - {param}: {desc}\n"

    return f"""You are an expert Equity Research Analyst AI assistant. You analyze financial data for Indian hotel companies and provide insights.

{COMPANIES_INFO}

{DATA_STRUCTURE}

{KNOWLEDGE_GRAPH_CONTEXT}

## Available Tools
You have the following tools to answer financial queries:
{tools_text}

## How to Respond

You MUST respond with a JSON object in this EXACT format:
{{
    "thought": "Your reasoning about what tool to use and why",
    "tool": "tool_name",
    "args": {{
        "param1": "value1",
        "param2": "value2"
    }}
}}

IMPORTANT RULES:
1. ALWAYS respond with valid JSON. No markdown, no extra text.
2. Pick the MOST RELEVANT tool for the query.
3. For company names, use the exact folder names: Chalet_Hotels, EIH_Limited, Indian_Hotels, Juniper_Hotels, Lemon_Tree_Hotels
4. For metrics, use the exact CSV row names (e.g., "Sales +", "Net Profit +", "ROE %", "Debt-to-Equity Ratio")
5. For "source" parameter, pick based on metric:
   - Revenue/profit/expense metrics → "profit_loss_enriched"
   - Balance sheet items (debt, equity, assets) → "balance_sheet_enriched"
   - ROE, ROA, ROCE, DuPont → "cross_metrics"
   - Quarterly data → "quarter_analysis_enriched"
6. If the query is about comparing across companies → use "compare_companies" or "sector_benchmark"
7. If the query is about one company's quarterly performance → use "compare_quarters"
8. If the query is about one company over multiple years → use "trend_analysis"
9. If the query is about financial health/rating → use "financial_health"
10. If the query is about ratio analysis/DuPont → use "ratio_deep_dive"
11. Only use "custom_analysis" if NO other tool can answer the query.
12. For "all" companies, set companies to "all".
"""


def get_synthesis_prompt(query: str, tool_output: str, chart_path: str = None) -> str:
    """Prompt for the LLM to synthesize the final answer from tool output."""
    chart_note = ""
    if chart_path:
        chart_note = f"\n\nA chart has been generated and saved at: {chart_path}"

    return f"""You are an expert Equity Research Analyst. Based on the data below, provide a clear, insightful analysis answering the user's question.

USER QUESTION: {query}

DATA FROM ANALYSIS:
{tool_output}
{chart_note}

INSTRUCTIONS:
1. Provide a concise but thorough analysis (3-6 paragraphs)
2. Highlight key findings, trends, and standout performers
3. Use specific numbers from the data
4. Point out any red flags or positive signals
5. If relevant, mention which company is best positioned and why
6. Use a professional tone suitable for an equity research report
7. Format your response with clear sections using ** for bold headings
8. If a chart was generated, mention that the user can view it for visual reference

Do NOT respond with JSON. Respond with a natural language analysis.
"""
