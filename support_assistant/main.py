from fastapi import FastAPI

from graph import build_graph
from schema import AskRequest, AskResponse

app = FastAPI()
_graph = build_graph()


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    # Runs classify_intent -> (retrieve_and_answer | direct_answer) end to end.
    result = _graph.invoke({"query": request.query})
    # response_model=AskResponse means FastAPI validates this shape either way.
    return AskResponse(
        answer=result["answer"],
        sources=result["sources"],
        confidence=result["confidence"],
    )
