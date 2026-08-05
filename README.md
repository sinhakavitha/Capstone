# Zepto Data & AI Platform

My capstone submission for the AI/ML certificate program: one repo, three
linked modules — a scraping-to-SQL data pipeline, a Titanic
analytics/modeling pipeline, and (still to come) a RAG-based support
assistant.

| # | Module | Status | Details |
|---|---|---|---|
| 1 | Data Pipeline | done | [`data_pipeline/README.md`](data_pipeline/README.md) |
| 2 | Analytics Pipeline | done | [`analytics/README.md`](analytics/README.md) |
| 3 | Support Assistant | not started | — |

## Setup

I've got one consolidated [`requirements.txt`](requirements.txt) at the
repo root, pinned to the versions I actually ran the notebooks with:

```
pip install -r requirements.txt
```

## Running each module

- **Data Pipeline:** run `data_pipeline/scraper.ipynb` end to end — it
  drops and recreates `books.db` from scratch every run.
- **Analytics Pipeline:** run `analytics/01_eda.ipynb` first (loads
  Titanic, saves `titanic.csv`), then `analytics/02_modeling.ipynb` (reads
  that same CSV, trains/evaluates/saves the pipeline).

## Design decisions

- **Data Pipeline:** I used the fixed baseline rate 1 GBP = 105.50 INR,
  no live FX lookup. Tables get dropped and recreated each run so
  re-running never double-inserts rows. Bad numeric fields fall back to
  the median; rows I couldn't parse get dropped.
- **Analytics Pipeline:** I drove missing-value handling off a %-missing
  threshold (drop rows <5%, impute 5–30%, drop the column above that —
  `deck` at 77%). I did the stratified split before any preprocessing and
  fit all imputing/encoding/scaling on train only. I'd deploy the tuned
  Random Forest (best AUC/precision), though its recall trails the
  untuned forest/decision tree.

