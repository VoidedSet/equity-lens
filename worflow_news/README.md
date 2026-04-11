# worflow_news - Automated News Pipeline for EquityLens

This module builds a daily, fully automated Indian hospitality news pipeline aligned with PRD checks.

## What It Does
- Aggregates news from Google Alerts RSS, publisher RSS, NewsAPI, Bing News API, and optional web scraping.
- Filters for material relevance against EquityLens analytical dimensions (`check_1` ... `check_6`).
- Tags sentiment (`Positive`, `Neutral`, `Negative`, `Watch`).
- Deduplicates across sources (URL normalization + title fuzzy matching).
- Generates daily digest in JSON and Markdown with citation format: `[Source | URL | Date]`.

## Files
- `news_pipeline.py`: End-to-end pipeline script.
- `google_alerts.md`: Exact Google Alert strings to configure.
- `.env.example`: API key placeholders.
- `requirements.txt`: Python dependencies.

## Setup
1. Create and activate a virtual environment.
2. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and set API keys.
4. Open `news_pipeline.py` and update `GOOGLE_ALERT_RSS_URLS` with your RSS links from Google Alerts.

## Run
```powershell
python news_pipeline.py
```

Outputs are written to `output/`:
- `daily_digest_YYYY-MM-DD.json`
- `daily_digest_YYYY-MM-DD.md`

## Scheduler
### Linux cron (07:00 IST daily)
```bash
0 7 * * * /usr/bin/python3 /path/to/worflow_news/news_pipeline.py >> /path/to/worflow_news/pipeline.log 2>&1
```

### Windows Task Scheduler
- Program: `python`
- Arguments: `news_pipeline.py`
- Start in: `C:\Users\jaina\OneDrive\Desktop\datahack 4\worflow_news`
- Trigger: Daily, 07:00

## Notes
- Any source can fail independently; pipeline continues with remaining sources.
- If no material items are found for a section, digest explicitly marks it.
- All retained items must map to at least one of PRD checks (`check_1` to `check_6`).
