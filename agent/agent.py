"""
Financial Agent -- Main Orchestrator CLI
=========================================
Interactive CLI that takes natural language financial queries,
routes them through the LLM to pick the right tool, executes it,
and synthesizes insights with visualizations.

Usage: python agent/agent.py
"""

import sys
import os
import json
import time

# Enable ANSI colors on Windows and fix encoding
if sys.platform == "win32":
    os.system("")  # enables ANSI escape codes in Windows terminal
    # Force UTF-8 output encoding to handle LLM responses with unicode
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from agent.llm_client import chat_completion, parse_json_response
from agent.prompts import get_system_prompt, get_synthesis_prompt
from agent.tool_registry import execute_tool


# --- ANSI Colors for terminal output ---

class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    END = "\033[0m"


def print_banner():
    """Print the startup banner."""
    print(f"""
{Colors.CYAN}{Colors.BOLD}
============================================================
                                                            
   Financial Agentic Analyst                                
   ------------------------------------------              
   Indian Hotel Sector Analysis System                      
                                                            
   Companies: Chalet Hotels | EIH (Oberoi) | Indian Hotels  
              Juniper Hotels | Lemon Tree Hotels             
                                                            
   Commands: 'exit' to quit | 'help' for examples           
                                                            
============================================================
{Colors.END}""")


def print_help():
    """Print example queries."""
    print(f"""
{Colors.YELLOW}{Colors.BOLD}Example Queries:{Colors.END}
{Colors.DIM}
  > "Compare ROE of all companies for Mar 2025"
  > "Show quarterly sales trend for Chalet Hotels"
  > "Which hotel company is the best overall?"
  > "Give me a financial health scorecard for Indian Hotels"
  > "How has Lemon Tree's debt-to-equity ratio changed over the years?"
  > "Break down ROE drivers for EIH Limited using DuPont analysis"
  > "Compare EBITDA margins: Chalet vs Indian Hotels vs EIH"
  > "Rank all companies on profitability and leverage"
  > "Which company has the highest interest coverage ratio?"
  > "Show net profit margin trend for Juniper Hotels"
{Colors.END}""")


def process_query(query: str, conversation_history: list) -> str:
    """
    Process a user query through the full agent pipeline:
    1. Send to LLM for tool selection
    2. Execute the selected tool
    3. Send results back to LLM for synthesis
    4. Return the final analysis
    """

    # Step 1: Get tool selection from LLM
    print(f"\n{Colors.DIM}  [1/4] Analyzing query...{Colors.END}")

    system_prompt = get_system_prompt()
    messages = [
        {"role": "system", "content": system_prompt},
    ]

    # Add conversation history for context (last 4 turns)
    for entry in conversation_history[-4:]:
        messages.append(entry)

    messages.append({"role": "user", "content": query})

    tool_response = chat_completion(messages, temperature=0.2, json_mode=True)

    if tool_response.startswith("[LLM Error]"):
        return f"{Colors.RED}LLM Error: {tool_response}{Colors.END}"

    # Step 2: Parse tool call
    tool_call = parse_json_response(tool_response)

    if "error" in tool_call:
        # LLM didn't return valid JSON, try to use it as a direct answer
        return f"{Colors.YELLOW}Could not parse tool selection. LLM response:\n{tool_response[:500]}{Colors.END}"

    tool_name = tool_call.get("tool", "custom_analysis")
    tool_args = tool_call.get("args", {})
    thought = tool_call.get("thought", "")

    print(f"{Colors.DIM}  [2/4] Thought: {thought[:120]}...{Colors.END}")
    print(f"{Colors.BLUE}  Tool selected: {tool_name}{Colors.END}")
    print(f"{Colors.DIM}  Args: {json.dumps(tool_args, indent=2)[:200]}{Colors.END}")

    # Step 3: Execute the tool
    print(f"{Colors.DIM}  [3/4] Executing tool...{Colors.END}")
    start_time = time.time()

    tool_result = execute_tool(tool_name, tool_args)
    elapsed = time.time() - start_time

    print(f"{Colors.DIM}  Done in {elapsed:.1f}s{Colors.END}")

    # Check for charts
    chart_path = tool_result.get("chart_path")
    chart_path_latest = tool_result.get("chart_path_latest")
    chart_path_trend = tool_result.get("chart_path_trend")
    chart_path_overall = tool_result.get("chart_path_overall")
    chart_path_leverage = tool_result.get("chart_path_leverage")
    chart_path_bar = tool_result.get("chart_path_bar")

    all_charts = [p for p in [chart_path, chart_path_latest, chart_path_trend,
                               chart_path_overall, chart_path_leverage, chart_path_bar] if p]

    if all_charts:
        print(f"{Colors.GREEN}  Charts generated:{Colors.END}")
        for cp in all_charts:
            print(f"{Colors.DIM}     -> {cp}{Colors.END}")

    # Step 4: Synthesize final answer with LLM
    print(f"{Colors.DIM}  [4/4] Generating analysis...{Colors.END}")

    tool_output_str = tool_result.get("output", json.dumps(tool_result, default=str)[:3000])
    synthesis_prompt = get_synthesis_prompt(query, tool_output_str, chart_path)

    synthesis_messages = [
        {"role": "system", "content": "You are an expert Equity Research Analyst providing financial insights."},
        {"role": "user", "content": synthesis_prompt},
    ]

    final_analysis = chat_completion(synthesis_messages, temperature=0.4, max_tokens=2048)

    if final_analysis.startswith("[LLM Error]"):
        # Fallback: show raw data if LLM fails
        return f"{Colors.YELLOW}LLM synthesis failed. Here's the raw data:\n\n{tool_output_str}{Colors.END}"

    return final_analysis


def main():
    """Main interactive loop."""
    print_banner()

    # Check if enriched data exists
    enriched_check = os.path.join(
        PROJECT_ROOT, "Raw Data Extraction", "Indian_Hotels", "balance_sheet_enriched.csv"
    )
    if not os.path.exists(enriched_check):
        print(f"{Colors.YELLOW}{Colors.BOLD}")
        print(f"  Enriched data not found!")
        print(f"  Please run feature engineering first:")
        print(f"  python feature_engineering.py")
        print(f"{Colors.END}")
        return

    conversation_history = []

    while True:
        try:
            print(f"\n{Colors.BOLD}{Colors.GREEN}You > {Colors.END}", end="")
            query = input().strip()

            if not query:
                continue

            if query.lower() in ("exit", "quit", "q"):
                print(f"\n{Colors.CYAN}Goodbye! Happy analyzing!{Colors.END}\n")
                break

            if query.lower() == "help":
                print_help()
                continue

            # Process the query
            result = process_query(query, conversation_history)

            # Display result
            print(f"\n{Colors.CYAN}{Colors.BOLD}--- Analysis ---{Colors.END}")
            print(f"\n{result}")
            print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.END}")

            # Add to conversation history
            conversation_history.append({"role": "user", "content": query})
            conversation_history.append({"role": "assistant", "content": result[:500]})

        except KeyboardInterrupt:
            print(f"\n\n{Colors.CYAN}Interrupted. Goodbye!{Colors.END}\n")
            break
        except Exception as e:
            print(f"\n{Colors.RED}Error: {e}{Colors.END}")
            import traceback
            traceback.print_exc()
            continue


if __name__ == "__main__":
    main()
