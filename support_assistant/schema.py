from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    query: str


class AskResponse(BaseModel):
    answer: str
    sources: list[str]
    # Bounded so a malformed real-LLM reply (e.g. confidence=5) fails
    # validation in graph.py's retry loop instead of reaching the client.
    confidence: float = Field(ge=0.0, le=1.0)
