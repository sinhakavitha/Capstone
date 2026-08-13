# Zepto Data & AI Platform

My capstone submission for the AI/ML certificate program: one repo, three
linked modules — a scraping-to-SQL data pipeline, a Titanic
analytics/modeling pipeline, and (still to come) a RAG-based support
assistant.

| # | Module | Status | Details |
|---|---|---|---|
| 1 | Data Pipeline | done | [`data_pipeline/README.md`](data_pipeline/README.md) |
| 2 | Analytics Pipeline | done | [`analytics/README.md`](analytics/README.md) |
| 3 | Support Assistant | done | [`support_assistant/README.md`](support_assistant/README.md) |

## Setup

I went with **one requirements.txt per stack** rather than a single
consolidated file, since Modules 1–2 and Module 3 pull in unrelated
dependency trees (pandas/scikit-learn vs. FastAPI/LangGraph/ChromaDB) that
don't need to share an environment:

- [`requirements.txt`](requirements.txt) at the repo root, for the
  Data Pipeline and Analytics notebooks (Modules 1–2):
  ```
  pip install -r requirements.txt
  ```
- [`support_assistant/requirements.txt`](support_assistant/requirements.txt),
  for the Support Assistant service (Module 3):
  ```
  pip install -r support_assistant/requirements.txt
  ```

Both are pinned to versions I actually ran against, on Python 3.9.

## Running each module

- **Data Pipeline:** run `data_pipeline/scraper.ipynb` end to end — it
  drops and recreates `books.db` from scratch every run.
- **Analytics Pipeline:** run `analytics/01_eda.ipynb` first (loads
  Titanic, saves `titanic.csv`), then `analytics/02_modeling.ipynb` (reads
  that same CSV, trains/evaluates/saves the pipeline).
- **Support Assistant:** from `support_assistant/`, run
  `python3 -m uvicorn main:app --host 0.0.0.0 --port 7860` and POST to
  `/ask`. Runs fully offline against the graded `MOCK_LLM` path by
  default — no API key needed. See
  [`support_assistant/README.md`](support_assistant/README.md) for
  example calls and the optional real-LLM/Docker paths.

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
- **Support Assistant:** retrieval (embedding + ChromaDB) always runs for
  real, since it needs no API key — only the final answer-generation step
  branches on `MOCK_LLM`, so the graded mock path still exercises the
  whole RAG pipeline end to end rather than stubbing it out. I kept the
  8 policy docs unchunked (each is a single short self-contained
  paragraph) and validated the optional real-LLM output against a
  Pydantic schema with a bounded retry loop, so a malformed reply fails
  validation instead of reaching the client.

