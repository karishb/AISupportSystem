"""OpenAI embeddings + ChromaDB vector store for semantic search and RAG.

Generates embeddings using text-embedding-3-small and stores them in ChromaDB
for retrieving similar resolved tickets (used as context for response generation).
"""
from typing import List, Dict, Optional
from backend.config import OPENAI_API_KEY, EMBEDDING_MODEL, CHROMA_PERSIST_DIR

_embed_client = None
_collection = None

try:
    from openai import OpenAI
    if OPENAI_API_KEY:
        # Test the key with a tiny request before enabling
        test_client = OpenAI(api_key=OPENAI_API_KEY)
        test_client.embeddings.create(model=EMBEDDING_MODEL, input="test")
        _embed_client = test_client
except Exception:
    _embed_client = None  # Key invalid or quota exhausted — disable embeddings silently

try:
    import chromadb
    _chroma = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    _collection = _chroma.get_or_create_collection(
        name="support_tickets",
        metadata={"hnsw:space": "cosine"}
    )
except Exception as e:
    print(f"ChromaDB init error: {e}")


def is_available() -> bool:
    return _embed_client is not None and _collection is not None


def get_embedding(text: str) -> Optional[List[float]]:
    """Generate embedding for a single text using OpenAI."""
    if not _embed_client:
        return None
    try:
        resp = _embed_client.embeddings.create(model=EMBEDDING_MODEL, input=text)
        return resp.data[0].embedding
    except Exception as e:
        print(f"Embedding error: {e}")
        return None


def get_embeddings_batch(texts: List[str]) -> List[Optional[List[float]]]:
    """Generate embeddings for a batch of texts."""
    if not _embed_client:
        return [None] * len(texts)
    try:
        resp = _embed_client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
        return [item.embedding for item in resp.data]
    except Exception as e:
        print(f"Batch embedding error: {e}")
        return [None] * len(texts)


def store_ticket(ticket_id: str, message: str, metadata: Dict, embedding: Optional[List[float]] = None):
    """Store a ticket embedding in ChromaDB."""
    if not _collection:
        return
    try:
        if embedding is None:
            embedding = get_embedding(message)
        if embedding is None:
            return
        # ChromaDB metadata values must be str, int, float, or bool
        clean_meta = {k: str(v) if v is not None else "" for k, v in metadata.items()}
        _collection.upsert(
            ids=[ticket_id],
            embeddings=[embedding],
            documents=[message],
            metadatas=[clean_meta],
        )
    except Exception as e:
        print(f"ChromaDB store error: {e}")


def find_similar(message: str, top_k: int = 3, category: Optional[str] = None) -> List[Dict]:
    """Find similar tickets using vector search."""
    if not _collection or _collection.count() == 0:
        return []
    try:
        embedding = get_embedding(message)
        if embedding is None:
            return []

        where_filter = None
        if category:
            where_filter = {"ai_category": category}

        results = _collection.query(
            query_embeddings=[embedding],
            n_results=min(top_k, _collection.count()),
            where=where_filter if where_filter and _collection.count() > 0 else None,
        )

        similar = []
        if results and results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                dist = results["distances"][0][i] if results["distances"] else 1.0
                similar.append({
                    "message": doc[:200],
                    "category": meta.get("ai_category", ""),
                    "resolution": meta.get("agent_reply", "")[:200],
                    "similarity": round(1 - dist, 3),  # cosine distance to similarity
                })
        return similar
    except Exception as e:
        print(f"ChromaDB search error: {e}")
        return []


def reset():
    """Clear the vector store."""
    global _collection
    if _collection:
        try:
            _chroma.delete_collection("support_tickets")
            _collection = _chroma.get_or_create_collection(
                name="support_tickets",
                metadata={"hnsw:space": "cosine"}
            )
        except Exception as e:
            print(f"ChromaDB reset error: {e}")
