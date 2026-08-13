# Module 3 — Support Assistant

This is a small RAG service for Zepto customer support. I embed an 8-document policy corpus
into ChromaDB, orchestrate a classify → retrieve → answer flow with LangGraph, validate the
final output against a Pydantic schema, and expose it all through a FastAPI `/ask` endpoint.

Everything is graded through the `MOCK_LLM` offline path — I left it unset the whole time I was
building and testing, so no API key or network call is needed to run any of this.

## Architecture

The RAG pipeline has 4 stages:

1. **Ingestion** — the 8 policy files in `docs/doc_01.txt` … `doc_08.txt` are read from disk by
   `ingest()` in `ingestion.py`.
2. **Embedding** — `ingest()` turns each doc into a vector with `sentence-transformers`'
   `all-MiniLM-L6-v2` and stores it in a ChromaDB `PersistentClient` collection, still in
   `ingestion.py`.
3. **Retrieval** — `retrieve()` in `ingestion.py`, called from the `retrieve_and_answer` node in
   `graph.py`. This runs for real in both modes — it needs no API key, so `MOCK_LLM` doesn't
   touch it.
4. **Generation** — inside the `retrieve_and_answer` and `direct_answer` nodes in `graph.py`.
   This is the only stage `MOCK_LLM` branches on: in mock mode both nodes return a canned string
   built in code; with `MOCK_LLM=0` they instead format `prompt_template.py`'s template and call
   `llm.py`, which hits Groq's API and validates/retries against the `AskResponse` schema in
   `schema.py`.

## Getting it running

```
pip3 install -r requirements.txt
python3 -m uvicorn main:app --host 0.0.0.0 --port 7860
```

## How the docs turn into embeddings

The 8 policy files live in `docs/doc_01.txt` … `doc_08.txt`, one Zepto policy per file. Each
one is short enough — a single self-contained paragraph — that I didn't bother chunking it
further; splitting a ~100-word policy statement mid-sentence would've just separated a claim
from its own qualifier for no benefit.

`ingestion.py` embeds each doc with `sentence-transformers`' `all-MiniLM-L6-v2` (local, no API
key) and stores the vectors in a ChromaDB `PersistentClient` collection (`zepto_policies`,
persisted to `chroma_db/`). It only actually re-embeds when the collection is empty, so
restarting the app doesn't redo the work every time.

## The graph

`graph.py` builds a LangGraph `StateGraph` with three nodes:

- **`classify_intent`** — in mock mode this is just a keyword check (does the query mention
  "delivery", "return", "refund", "membership", "tracking", "cancel", "gift card", or "support
  hours"?) to decide `policy_question` vs `general_question`. No LLM call.
- **`retrieve_and_answer`** — retrieval always runs for real here, in either mode, since
  embedding + ChromaDB need no API key. Only the answer-generation step branches on
  `MOCK_LLM`: mock mode just returns a canned `"Based on the retrieved context: ..."` string
  built from the top chunk; the optional real-LLM path (`MOCK_LLM=0`) instead formats the
  prompt template from `prompt_template.py` and calls out to `llm.py`.
- **`direct_answer`** — for anything that isn't a policy question. No retrieval. Mock mode
  returns a fixed "I can only answer questions about Zepto policies right now." string.

The routing itself (the conditional edge out of `classify_intent`) doesn't depend on
`MOCK_LLM` at all — only the generation logic inside each node does, which is how the brief
wanted it structured.

## The prompt template

`prompt_template.py` has the role/context/task/format/length skeleton the brief asked for, plus
a negative constraint ("don't answer using info not in the context" — the standard anti-
hallucination guard for RAG) and one worked example. It's only actually used by the optional
`MOCK_LLM=0` branch, but it's there as real text either way.

## The output schema

`schema.py` defines `AskResponse` (`answer`, `sources`, `confidence` — confidence constrained
to `0–1` via Pydantic's `Field(ge=0.0, le=1.0)`). In mock mode I populate this straight from
code since there's no LLM output to validate. In the optional real-LLM path, `graph.py` asks
the LLM to return JSON matching this schema and retries up to 2 more times with a corrective
message if it doesn't validate, before giving up and returning a clearly-marked error.

## Example calls

Both run with `MOCK_LLM` left unset (the default/graded mode).

**A policy question (triggers retrieval):**

Request: `{"query": "is delivery free on small orders?"}`

```json
{"answer":"Based on the retrieved context: Zepto delivers grocery and household essentials to serviceable pin codes within 10 to 30 minutes of order confirmation, depending on the customer's delivery zone and current order volume. Standard del","sources":["doc_01","doc_05","doc_02"],"confidence":1.0}
```

**A general question (no retrieval):**

Request: `{"query": "what is the capital of France?"}`

```json
{"answer":"I can only answer questions about Zepto policies right now.","sources":[],"confidence":1.0}
```

## Docker

```
docker build -t support-assistant .
docker run -p 7860:7860 support-assistant
```

I built and ran this locally and hit it with the same two curl calls above — got identical
responses to running it straight with `uvicorn`. I didn't push it anywhere; local build/run is
all the assignment asks for.

## Optional stuff I didn't turn on

The code path for a real LLM call exists (`llm.py`, using Groq's free tier) — set `MOCK_LLM=0`
and `GROQ_API_KEY=<key>` to use it. I left it off since the graded baseline is the mock path and
I wanted that to be what actually gets tested. Same for deployment — the Dockerfile builds and
runs locally, but I didn't push it to Hugging Face Spaces or anywhere else.
