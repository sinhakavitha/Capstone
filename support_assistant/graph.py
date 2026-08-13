import json
import os
from typing import TypedDict

from pydantic import ValidationError

from ingestion import retrieve
from llm import call_llm
from prompt_template import PROMPT_TEMPLATE
from schema import AskResponse

from langgraph.graph import StateGraph, START, END

POLICY_KEYWORDS = [
    "delivery", "return", "refund", "membership",
    "tracking", "cancel", "gift card", "support hours",
]


class GraphState(TypedDict, total=False):
    query: str
    intent: str
    answer: str
    sources: list[str]
    confidence: float


def is_mock_mode() -> bool:
    # Default (unset MOCK_LLM) is mock mode — this is the graded baseline.
    # Set MOCK_LLM=0 to opt into the real Groq call in llm.py.
    return os.environ.get("MOCK_LLM", "1") != "0"


# Node 1/3: classify_intent. Routing itself never depends on MOCK_LLM — only
# how the intent is decided (keyword heuristic vs. an LLM call) does.
def classify_intent(state: GraphState) -> GraphState:
    query = state["query"]
    if is_mock_mode():
        lowered = query.lower()
        intent = "policy_question" if any(k in lowered for k in POLICY_KEYWORDS) else "general_question"
    else:
        reply = call_llm(
            "Classify the following customer message as exactly one word: "
            "'policy_question' (about Zepto delivery, returns, membership, tracking, "
            "cancellation, gift cards, or support hours) or 'general_question' "
            f"(anything else).\n\nMessage: {query}\n\nClassification:"
        )
        intent = "policy_question" if "policy_question" in reply.lower() else "general_question"
    return {"intent": intent}


# Conditional-edge function: picks the next node by name from GraphState.
def route_by_intent(state: GraphState) -> str:
    return state["intent"]


# Node 2/3: retrieve_and_answer. Retrieval (stage 3) always runs for real;
# only the generation step below it branches on MOCK_LLM.
def retrieve_and_answer(state: GraphState) -> GraphState:
    query = state["query"]
    chunks = retrieve(query, n_results=3)
    source_ids = [c["id"] for c in chunks]

    if is_mock_mode():
        # Canned template built from the top retrieved chunk — no LLM call.
        top_snippet = chunks[0]["text"][:200] if chunks else ""
        return {
            "answer": f"Based on the retrieved context: {top_snippet}",
            "sources": source_ids,
            "confidence": 1.0,
        }

    context = "\n\n".join(c["text"] for c in chunks)
    prompt = PROMPT_TEMPLATE.format(context=context, question=query)
    answer, sources, confidence = _answer_with_retry(prompt, source_ids)
    return {"answer": answer, "sources": sources, "confidence": confidence}


# Node 3/3: direct_answer, for general_question — no retrieval involved.
def direct_answer(state: GraphState) -> GraphState:
    if is_mock_mode():
        # Fixed canned string — no LLM call.
        return {
            "answer": "I can only answer questions about Zepto policies right now.",
            "sources": [],
            "confidence": 1.0,
        }

    answer, sources, confidence = _answer_with_retry(
        f"Answer this general question briefly: {state['query']}", []
    )
    return {"answer": answer, "sources": sources, "confidence": confidence}


# Only used by the optional MOCK_LLM=0 path. Asks the LLM for JSON matching
# AskResponse and retries with a corrective message if validation fails,
# giving up after `attempts` tries rather than looping forever.
def _answer_with_retry(prompt: str, source_ids: list[str], attempts: int = 3):
    instruction = (
        f'{prompt}\n\nRespond with ONLY a JSON object of the form '
        f'{{"answer": "...", "sources": {source_ids}, "confidence": 0.0}}.'
    )
    correction = ""
    for _ in range(attempts):
        raw = call_llm(instruction + correction)
        try:
            data = json.loads(raw)
            validated = AskResponse(**data)
            return validated.answer, validated.sources, validated.confidence
        except (json.JSONDecodeError, ValidationError) as e:
            correction = (
                f"\n\nYour previous reply was invalid ({e}). "
                "Reply again with ONLY valid JSON matching the schema."
            )
    return "Error: the language model did not return a valid response after retries.", source_ids, 0.0


def build_graph():
    graph = StateGraph(GraphState)
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("retrieve_and_answer", retrieve_and_answer)
    graph.add_node("direct_answer", direct_answer)

    graph.add_edge(START, "classify_intent")
    graph.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {"policy_question": "retrieve_and_answer", "general_question": "direct_answer"},
    )
    graph.add_edge("retrieve_and_answer", END)
    graph.add_edge("direct_answer", END)

    return graph.compile()
