import os
import glob
import chromadb
from sentence_transformers import SentenceTransformer

DOCS_DIR = os.path.join(os.path.dirname(__file__), "docs")
CHROMA_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")
COLLECTION_NAME = "zepto_policies"

_embedder = None


def get_embedder():
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder


def get_collection():
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = client.get_or_create_collection(COLLECTION_NAME)
    # Only embed once — PersistentClient survives restarts, so an empty
    # collection means this is the first run against this chroma_db/ dir.
    if collection.count() == 0:
        ingest(collection)
    return collection


# Stage 1 (ingestion) + Stage 2 (embedding) of the RAG pipeline.
def ingest(collection):
    paths = sorted(glob.glob(os.path.join(DOCS_DIR, "doc_*.txt")))
    ids = []
    documents = []
    for path in paths:
        doc_id = os.path.splitext(os.path.basename(path))[0]
        with open(path) as f:
            text = f.read().strip()
        ids.append(doc_id)
        documents.append(text)

    embeddings = get_embedder().encode(documents).tolist()
    collection.add(ids=ids, documents=documents, embeddings=embeddings)


# Stage 3 (retrieval). Runs for real in both MOCK_LLM modes — embedding a
# query and querying ChromaDB needs no API key, so there's nothing to mock.
def retrieve(query, n_results=3):
    collection = get_collection()
    query_embedding = get_embedder().encode([query]).tolist()
    results = collection.query(query_embeddings=query_embedding, n_results=n_results)
    return [
        {"id": doc_id, "text": text}
        for doc_id, text in zip(results["ids"][0], results["documents"][0])
    ]
