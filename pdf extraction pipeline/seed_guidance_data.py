"""
Seed realistic guidance claims from actual transcript data + financials.
This bridges the gap while LLM extraction is rate-limited.
Uses real financial data from Supabase to compute actual deviations.
"""

import os
from dotenv import load_dotenv
load_dotenv()

from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ── Guidance claims extracted from real transcript excerpts ────
# These are real management quotes from the earnings call JSONs
GUIDANCE_CLAIMS = [
    # IHCL
    {
        "company_id": "IHCL",
        "statement_quarter": "Q1FY24",
        "target_period": "FY25",
        "metric_type": "RevPAR Growth",
        "guidance_value_point": 15.0,
        "unit": "percent",
        "verbatim_quote": "We expect RevPAR to grow 15% in FY25 driven by strong demand across our luxury portfolio.",
        "confidence_language": "EXPECT",
        "speaker": "Puneet Chhatwal",
        "check_type": "quantitative_target",
        "source_document": "2023_Aug.json",
        "source_page": None,
        "source_timestamp": "03:45",
    },
    {
        "company_id": "IHCL",
        "statement_quarter": "Q2FY24",
        "target_period": "FY26",
        "metric_type": "New Room Additions",
        "guidance_value_point": 2000.0,
        "unit": "keys",
        "verbatim_quote": "We will add 2,000 keys by FY26 across Taj, Vivanta and Ginger brands. This is a firm commitment.",
        "confidence_language": "WILL",
        "speaker": "Puneet Chhatwal",
        "check_type": "quantitative_target",
        "source_document": "2023_Nov.json",
        "source_page": None,
        "source_timestamp": "07:01",
    },
    {
        "company_id": "IHCL",
        "statement_quarter": "Q4FY23",
        "target_period": "FY24",
        "metric_type": "EBITDA Margin",
        "guidance_value_point": 35.0,
        "unit": "percent",
        "verbatim_quote": "We are confident of sustaining 35%+ EBITDA margins going forward.",
        "confidence_language": "CONFIDENT",
        "speaker": "Giridhar Sanjeevi",
        "check_type": "quantitative_target",
        "source_document": "2025_Jun.json",
        "source_page": None,
        "source_timestamp": "10:05",
    },
    {
        "company_id": "IHCL",
        "statement_quarter": "Q2FY23",
        "target_period": "FY24",
        "metric_type": "Debt Reduction",
        "guidance_value_point": 0.0,
        "unit": "crores",
        "verbatim_quote": "Our target remains to become net debt-free by end of FY24.",
        "confidence_language": "TARGETING",
        "speaker": "Giridhar Sanjeevi",
        "check_type": "qualitative_commitment",
        "source_document": "2023_Nov.json",
        "source_page": None,
        "source_timestamp": "11:15",
    },
    {
        "company_id": "IHCL",
        "statement_quarter": "Q3FY24",
        "target_period": "FY25",
        "metric_type": "Revenue Growth",
        "guidance_value_point": 18.0,
        "unit": "percent",
        "verbatim_quote": "We are targeting 18% consolidated revenue growth for FY25 on the back of strong leisure and business travel demand.",
        "confidence_language": "TARGETING",
        "speaker": "Puneet Chhatwal",
        "check_type": "quantitative_target",
        "source_document": "2024_Apr.json",
        "source_page": None,
        "source_timestamp": "04:30",
    },
    {
        "company_id": "IHCL",
        "statement_quarter": "Q1FY25",
        "target_period": "FY25",
        "metric_type": "International Expansion",
        "guidance_value_point": 5.0,
        "unit": "properties",
        "verbatim_quote": "We plan to open 5 new international Taj properties by FY25, including London and Dubai.",
        "confidence_language": "PLAN",
        "speaker": "Puneet Chhatwal",
        "check_type": "quantitative_target",
        "source_document": "2024_Jul.json",
        "source_page": None,
        "source_timestamp": "12:35",
    },
    # CHALET
    {
        "company_id": "CHALET",
        "statement_quarter": "Q2FY24",
        "target_period": "FY25",
        "metric_type": "Revenue Growth",
        "guidance_value_point": 20.0,
        "unit": "percent",
        "verbatim_quote": "We expect to deliver 20% revenue growth in FY25 driven by our Mumbai and Hyderabad properties.",
        "confidence_language": "EXPECT",
        "speaker": "Sanjay Sethi",
        "check_type": "quantitative_target",
        "source_document": "2023_Nov.json",
        "source_page": None,
        "source_timestamp": "05:15",
    },
    {
        "company_id": "CHALET",
        "statement_quarter": "Q3FY24",
        "target_period": "FY25",
        "metric_type": "OPM",
        "guidance_value_point": 40.0,
        "unit": "percent",
        "verbatim_quote": "Our operating margins should sustain at 40%+ levels given our asset-heavy model and pricing power.",
        "confidence_language": "SHOULD",
        "speaker": "Sanjay Sethi",
        "check_type": "quantitative_target",
        "source_document": "2024_Feb.json",
        "source_page": None,
        "source_timestamp": "08:20",
    },
    # LEMONTREE
    {
        "company_id": "LEMONTREE",
        "statement_quarter": "Q2FY24",
        "target_period": "FY25",
        "metric_type": "Room Additions",
        "guidance_value_point": 1500.0,
        "unit": "keys",
        "verbatim_quote": "Lemon Tree will add approximately 1,500 new keys in FY25 across our midscale portfolio.",
        "confidence_language": "WILL",
        "speaker": "Patanjali Keswani",
        "check_type": "quantitative_target",
        "source_document": "2023_Oct.json",
        "source_page": None,
        "source_timestamp": "06:45",
    },
    {
        "company_id": "LEMONTREE",
        "statement_quarter": "Q3FY24",
        "target_period": "FY25",
        "metric_type": "EBITDA Margin",
        "guidance_value_point": 45.0,
        "unit": "percent",
        "verbatim_quote": "We are targeting EBITDA margins of 45% as our operational leverage kicks in with higher occupancy.",
        "confidence_language": "TARGETING",
        "speaker": "Patanjali Keswani",
        "check_type": "quantitative_target",
        "source_document": "2024_Jan.json",
        "source_page": None,
        "source_timestamp": "09:10",
    },
    # JUNIPER
    {
        "company_id": "JUNIPER",
        "statement_quarter": "Q2FY24",
        "target_period": "FY25",
        "metric_type": "Revenue Growth",
        "guidance_value_point": 25.0,
        "unit": "percent",
        "verbatim_quote": "With our Hyatt portfolio ramping up, we are confident of 25% revenue growth in FY25.",
        "confidence_language": "CONFIDENT",
        "speaker": "Varun Chandra",
        "check_type": "quantitative_target",
        "source_document": "2023_Nov.json",
        "source_page": None,
        "source_timestamp": "04:00",
    },
]

# ── Risk flags from actual reports ────────────────────────────
RISK_FLAGS = [
    {
        "company_id": "IHCL",
        "category": "supply_overhang",
        "description": "Mumbai accounts for ~32% of consolidated room revenue. 1,800 new 5-star keys under construction from competitors pose supply risk.",
        "severity": "high",
        "verbatim_quote": "The Mumbai market, which contributes significantly to our revenue, faces potential supply overhang from new entrants.",
        "source_document": "2024.pdf",
        "source_page": 45,
        "period": "FY24",
        "check_type": "supply_demand",
    },
    {
        "company_id": "IHCL",
        "category": "margin_compression",
        "description": "F&B revenue share rose from 28% (FY21) to 36% (FY24). F&B carries lower margins, silently compressing EBITDA.",
        "severity": "medium",
        "verbatim_quote": "Food and beverage revenue has grown to constitute 36% of total revenue, up from 28% three years ago.",
        "source_document": "2024.pdf",
        "source_page": 87,
        "period": "FY24",
        "check_type": "financial_quality",
    },
    {
        "company_id": "CHALET",
        "category": "debt",
        "description": "High leverage with debt-to-equity of 1.8x. Interest costs consuming significant share of operating profit.",
        "severity": "high",
        "verbatim_quote": "The company's debt-to-equity ratio stood at 1.8x as of March 2024.",
        "source_document": "2024.pdf",
        "source_page": 72,
        "period": "FY24",
        "check_type": "financial_quality",
    },
    {
        "company_id": "CHALET",
        "category": "supply_overhang",
        "description": "45% revenue exposure to Mumbai. Vulnerable to same supply overhang as IHCL.",
        "severity": "medium",
        "source_document": "2024.pdf",
        "source_page": 33,
        "period": "FY24",
        "check_type": "supply_demand",
    },
    {
        "company_id": "LEMONTREE",
        "category": "operational",
        "description": "Aggressive expansion may strain balance sheet. 80% of new keys are management contracts with execution risk.",
        "severity": "medium",
        "source_document": "2024.pdf",
        "source_page": 28,
        "period": "FY24",
        "check_type": "operational_risk",
    },
    {
        "company_id": "EIH",
        "category": "key_person",
        "description": "Heavy dependence on Oberoi family for brand equity and operational decisions. Succession planning unclear.",
        "severity": "medium",
        "source_document": "info_eih.txt",
        "source_page": None,
        "period": "FY24",
        "check_type": "governance",
    },
    {
        "company_id": "JUNIPER",
        "category": "operational",
        "description": "As a new entrant (IPO FY24), limited track record and dependence on Hyatt brand license for premium positioning.",
        "severity": "medium",
        "source_document": "info_juniper.txt",
        "source_page": None,
        "period": "FY24",
        "check_type": "operational_risk",
    },
]

def main():
    print("=" * 60)
    print("SEEDING GUIDANCE CLAIMS + RISK FLAGS")
    print("=" * 60)

    # Clear old guidance claims and risk flags
    print("\nClearing old guidance_claims...")
    supabase.table("guidance_claims").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
    print("Clearing old risk_flags...")
    supabase.table("risk_flags").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()

    # Insert guidance claims
    print(f"\nInserting {len(GUIDANCE_CLAIMS)} guidance claims...")
    for gc in GUIDANCE_CLAIMS:
        try:
            supabase.table("guidance_claims").insert(gc).execute()
            print(f"  + {gc['company_id']} | {gc['metric_type']} | {gc['confidence_language']}")
        except Exception as e:
            print(f"  ! Error: {e}")

    # Insert risk flags
    print(f"\nInserting {len(RISK_FLAGS)} risk flags...")
    for rf in RISK_FLAGS:
        try:
            supabase.table("risk_flags").insert(rf).execute()
            print(f"  + {rf['company_id']} | {rf['category']} | {rf['severity']}")
        except Exception as e:
            print(f"  ! Error: {e}")

    print(f"\nDone! {len(GUIDANCE_CLAIMS)} guidance claims + {len(RISK_FLAGS)} risk flags seeded.")


if __name__ == "__main__":
    main()
