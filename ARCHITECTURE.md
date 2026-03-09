# App Review Insights Analyser — Architecture

## Overview

The **App Review Insights Analyser** is a modular, phase-driven Python pipeline that ingests raw Play Store reviews for a target application, cleans and enriches them, runs NLP analysis, and surfaces a weekly "pulse" summary via a report or dashboard.

The target app is **com.nextbillion.groww** (Groww – Stocks & Mutual Fund).

---

## High-Level Data Flow

```
Google Play Store
        │
        ▼
┌──────────────────────┐
│  Phase 1: Ingestion  │  ← google-play-scraper, date windowing
│  & Cleaning          │    PII removal, language filter, emoji strip
└──────────┬───────────┘
           │  data/reviews/YYYY-MM-DD.json
           ▼
┌──────────────────────┐
│  Phase 2: NLP        │  ← sentiment scoring (VADER / HuggingFace),
│  & Enrichment        │    topic modelling (BERTopic), keyword extraction
└──────────┬───────────┘
           │  data/enriched/YYYY-MM-DD.json
           ▼
┌──────────────────────┐
│  Phase 3: Aggregation│  ← weekly roll-ups, trend deltas,
│  & Pulse Calculation │    rating distribution, top themes
└──────────┬───────────┘
           │  data/pulse/YYYY-WW.json
           ▼
┌──────────────────────┐
│  Phase 4: Reporting  │  ← markdown / HTML weekly report,
│  & Visualisation     │    optional Streamlit dashboard
└──────────────────────┘
```

---

## Project Structure

```
Second-project/
│
├── ARCHITECTURE.md          ← this file
├── README.md
├── requirements.txt         ← top-level pinned dependencies
├── .env.example             ← environment variable template
├── .gitignore
│
├── phase1/                  ← Review Ingestion & Cleaning
│   ├── __init__.py
│   ├── scraper.py           ← Play Store API wrapper
│   ├── cleaner.py           ← text cleaning, PII, language, emoji
│   └── pipeline.py          ← orchestration entry-point
│
├── phase2/                  ← NLP & Enrichment (future)
│   ├── __init__.py
│   ├── sentiment.py
│   ├── topics.py
│   └── pipeline.py
│
├── phase3/                  ← Aggregation & Pulse (future)
│   ├── __init__.py
│   ├── aggregator.py
│   └── pipeline.py
│
├── phase4/                  ← Reporting & Visualisation (future)
│   ├── __init__.py
│   ├── report_builder.py
│   └── dashboard.py
│
├── data/
│   ├── reviews/             ← Phase 1 output (YYYY-MM-DD.json)
│   ├── enriched/            ← Phase 2 output
│   └── pulse/               ← Phase 3 output
│
└── tests/
    ├── test_phase1.py
    ├── test_phase2.py       ← (future)
    └── test_phase3.py       ← (future)
```

---

## Phase 1 — Review Ingestion & Cleaning

### Responsibilities
1. **Scraping**: Pull reviews from the Play Store using `google-play-scraper`.
2. **Date windowing**: Restrict to reviews posted within the last 8–12 weeks.
3. **Word-count filter**: Drop any review whose body has fewer than 5 words.
4. **Language filter**: Retain only English (`en`) reviews, double-verified with `langdetect`.
5. **Emoji removal**: Strip all Unicode emoji / pictographic characters.
6. **PII scrubbing**: Remove email addresses, phone numbers, URLs, and Aadhaar-style number sequences with regex.
7. **Field selection**: Persist only `{ review_id, score, date, text, thumbs_up }` — no titles.
8. **Output**: `data/reviews/YYYY-MM-DD.json` (one file per run, date = run date).

### Key Libraries
| Library | Purpose |
|---|---|
| `google-play-scraper` | Play Store review scraping |
| `langdetect` | Secondary language detection |
| `emoji` | Emoji detection and removal |
| `re` (stdlib) | PII regex patterns |
| `json` (stdlib) | Output serialisation |
| `datetime` (stdlib) | Date windowing |

### Data Schema — `data/reviews/YYYY-MM-DD.json`
```json
{
  "run_date": "2024-03-09",
  "app_id": "com.nextbillion.groww",
  "window_weeks": 12,
  "review_count": 1234,
  "reviews": [
    {
      "review_id": "gp:xxx",
      "score": 4,
      "date": "2024-03-05T10:22:00",
      "text": "Really useful app for tracking my portfolio.",
      "thumbs_up": 7
    }
  ]
}
```

---

## Phase 2 — NLP & Enrichment *(planned)*

- **Sentiment scoring**: VADER for fast rule-based scoring; optional HuggingFace transformer for nuanced results.
- **Topic modelling**: BERTopic to identify recurring pain-points and feature requests.
- **Keyword extraction**: KeyBERT to surface salient terms per review.
- **Input**: `data/reviews/YYYY-MM-DD.json`
- **Output**: `data/enriched/YYYY-MM-DD.json` — extends each review object with `{ sentiment_score, sentiment_label, topics[], keywords[] }`.

---

## Phase 3 — Aggregation & Pulse Calculation *(planned)*

- Weekly roll-up of average sentiment, rating distribution, top N topics, and review volume.
- Delta computation vs. prior week to highlight improvements or regressions.
- Produces `data/pulse/YYYY-WW.json` keyed by ISO week.

---

## Phase 4 — Reporting & Visualisation *(planned)*

- **Markdown/HTML report**: Auto-generated "Weekly Pulse" document with executive summary, charts (matplotlib/plotly), and verbatim review highlights.
- **Streamlit dashboard** (optional): Interactive explorer with date-range filter and topic drill-down.

---

## Design Principles

| Principle | Implementation |
|---|---|
| **Phase isolation** | Each phase lives in its own package (`phase1/`, `phase2/`, …) with its own `pipeline.py` entry-point. |
| **Idempotency** | Re-running Phase 1 on the same day produces the same output file (overwrite-safe). |
| **Privacy by design** | PII scrubbing is mandatory before any data is persisted. No review titles are stored. |
| **Testability** | All external I/O (scraper calls, file writes) is injectable / mockable. |
| **Observability** | Python `logging` throughout; structured log lines for easy grep / aggregation. |

---

## Configuration

Runtime behaviour is driven by environment variables (`.env` file, loaded via `python-dotenv`):

| Variable | Default | Description |
|---|---|---|
| `APP_ID` | `com.nextbillion.groww` | Target Play Store app ID |
| `WINDOW_WEEKS` | `12` | Number of weeks to look back |
| `MIN_WORD_COUNT` | `5` | Minimum words for a review to be retained |
| `REVIEWS_DIR` | `data/reviews` | Output directory for Phase 1 |
| `LOG_LEVEL` | `INFO` | Python logging level |

---

## Testing Strategy

- **Unit tests** (`tests/`): Pure-Python, no network calls. All external dependencies mocked.
- **Phase 1 tests** (`tests/test_phase1.py`): Mock `google-play-scraper`, verify filtering logic end-to-end.
- **Future integration tests**: Replay cached scraper fixtures to test multi-phase pipelines.
- **CI**: Run `pytest` on every push; coverage target ≥ 80 %.

---

## Future Considerations

- **Scheduling**: Wrap Phase 1–4 pipeline in a weekly cron job or Prefect/Airflow DAG.
- **Multi-app support**: Parameterise `APP_ID` to analyse competitor apps side-by-side.
- **Alerting**: Notify Slack/email when sentiment drops > 10 % week-over-week.
- **Storage**: Migrate from local JSON files to a lightweight SQLite or cloud object store (GCS/S3) for longer history.
