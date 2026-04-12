"""
Promise Report & Charts
=======================
Generates visual credibility scorecard charts from promise_scorecard.json.
"""

import os
import json
import matplotlib.pyplot as plt
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
SCORECARD_JSON_PATH = os.path.join(OUTPUT_DIR, "promise_scorecard.json")

# Dark Theme Configuration
plt.style.use('dark_background')
BG_COLOR = '#0d1117'
PANEL_COLOR = '#161b22'
TEXT_COLOR = '#c9d1d9'
ACCENT_COLOR = '#58a6ff'

def generate_promise_charts(save_path=None):
    if not os.path.exists(SCORECARD_JSON_PATH):
        print("Scorecard not found. Run verify_promises.py first.")
        return None
        
    with open(SCORECARD_JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    summary = data["summary"]
    companies = list(summary["company_scores"].keys())
    
    fig = plt.figure(figsize=(15, 10), facecolor=BG_COLOR)
    if not companies:
        print("No company scores found in scorecard.")
        return None

    fig.suptitle('Management Promise Fulfillment Scorecard',
                 fontsize=18, color=TEXT_COLOR, fontweight='bold', y=0.95)
    
    # 1. Credibility Score Bar Chart
    ax1 = plt.subplot(2, 2, 1)
    ax1.set_facecolor(PANEL_COLOR)
    
    scores = [summary["company_scores"][c].get("credibility_score", 0) for c in companies]
    
    # Color based on score relative to 50
    colors = ['#2ea043' if s >= 60 else '#d29922' if s >= 50 else '#f85149' for s in scores]
    
    bars = ax1.bar(companies, scores, color=colors, alpha=0.8, edgecolor='w', linewidth=0.5)
    ax1.set_title("Management Credibility Score (0-100)", color=TEXT_COLOR, pad=15)
    ax1.set_ylim(0, 100)
    ax1.tick_params(colors=TEXT_COLOR)
    
    for spine in ax1.spines.values():
        spine.set_color('#30363d')
        
    for bar in bars:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + 2,
                 f'{height}', ha='center', va='bottom', color=TEXT_COLOR, fontweight='bold')
                 
    # 2. Overall Status Donut Chart
    ax2 = plt.subplot(2, 2, 2)
    ax2.set_facecolor(BG_COLOR)
    
    status_counts = summary["by_status"]
    labels = list(status_counts.keys())
    sizes = list(status_counts.values())
    
    status_colors = {
        "EXCEEDED": "#238636",
        "KEPT": "#2ea043",
        "PARTIAL": "#d29922",
        "BROKEN": "#f85149",
        "PENDING": "#8b949e",
    }
    
    if sum(sizes) > 0:
        ax2.pie(
            sizes, labels=labels,
            colors=[status_colors.get(l, '#ffffff') for l in labels],
            autopct='%1.1f%%', startangle=90,
            textprops=dict(color=TEXT_COLOR),
            wedgeprops=dict(width=0.4, edgecolor=BG_COLOR)
        )
    else:
        ax2.text(0.5, 0.5, "No promises found", ha="center", va="center", color=TEXT_COLOR)
    
    ax2.set_title(f"Overall Industry Outcome Tracking\nTotal Promises: {summary['total_promises']}",
                  color=TEXT_COLOR, pad=15)
                  
    # 3. Stacked Bar Chart per Company
    ax3 = plt.subplot(2, 1, 2)
    ax3.set_facecolor(PANEL_COLOR)
    
    cat_exceeded = [summary["company_scores"][c]["EXCEEDED"] for c in companies]
    cat_kept = [summary["company_scores"][c]["KEPT"] for c in companies]
    cat_partial = [summary["company_scores"][c]["PARTIAL"] for c in companies]
    cat_broken = [summary["company_scores"][c]["BROKEN"] for c in companies]
    cat_pending = [summary["company_scores"][c]["PENDING"] for c in companies]
    
    b1 = ax3.bar(companies, cat_exceeded, color=status_colors["EXCEEDED"], label="Exceeded")
    b2 = ax3.bar(companies, cat_kept, bottom=cat_exceeded, color=status_colors["KEPT"], label="Kept")
    b3 = ax3.bar(companies, cat_partial, bottom=np.add(cat_exceeded, cat_kept), color=status_colors["PARTIAL"], label="Partial")
    b4 = ax3.bar(companies, cat_broken, bottom=np.add(cat_partial, np.add(cat_exceeded, cat_kept)), color=status_colors["BROKEN"], label="Broken")
    b5 = ax3.bar(companies, cat_pending, bottom=np.add(cat_broken, np.add(cat_partial, np.add(cat_exceeded, cat_kept))), color=status_colors["PENDING"], label="Pending")
    
    ax3.set_title("Status Breakdown by Company", color=TEXT_COLOR, pad=15)
    ax3.tick_params(colors=TEXT_COLOR)
    ax3.legend(loc='upper right', facecolor=PANEL_COLOR, edgecolor='#30363d', labelcolor=TEXT_COLOR)
    
    for spine in ax3.spines.values():
        spine.set_color('#30363d')
        
    plt.tight_layout(pad=3.0)
    
    if save_path:
        save_dir = os.path.dirname(save_path)
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
        plt.savefig(save_path, facecolor=BG_COLOR, dpi=150, bbox_inches='tight')
        print(f"Chart saved to {save_path}")
    else:
        plt.show()

    return save_path

if __name__ == "__main__":
    out_file = os.path.join(PROJECT_ROOT, "credibility_scorecard.png")
    generate_promise_charts(out_file)
