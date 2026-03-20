"""Embeddings + ChromaDB vector store for semantic search and RAG.

Uses ChromaDB's built-in sentence-transformers (all-MiniLM-L6-v2) for embeddings.
Completely free — no API key needed. Falls back gracefully if unavailable.
"""
from typing import List, Dict, Optional
from backend.config import CHROMA_PERSIST_DIR

_collection = None
_chroma = None

try:
    import chromadb
    _chroma = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    # ChromaDB uses sentence-transformers/all-MiniLM-L6-v2 by default
    _collection = _chroma.get_or_create_collection(
        name="support_tickets",
        metadata={"hnsw:space": "cosine"}
    )
except Exception as e:
    print(f"ChromaDB init error: {e}")


def is_available() -> bool:
    return _collection is not None


def store_ticket(ticket_id: str, message: str, metadata: Dict, **kwargs):
    """Store a ticket in ChromaDB. Embeddings are generated automatically."""
    if not _collection:
        return
    try:
        clean_meta = {k: str(v) if v is not None else "" for k, v in metadata.items()}
        _collection.upsert(
            ids=[ticket_id],
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
        where_filter = None
        if category:
            where_filter = {"ai_category": category}

        results = _collection.query(
            query_texts=[message],
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
                    "similarity": round(1 - dist, 3),
                })
        return similar
    except Exception as e:
        print(f"ChromaDB search error: {e}")
        return []


def reset():
    """Clear the vector store."""
    global _collection
    if _collection and _chroma:
        try:
            _chroma.delete_collection("support_tickets")
            _collection = _chroma.get_or_create_collection(
                name="support_tickets",
                metadata={"hnsw:space": "cosine"}
            )
        except Exception as e:
            print(f"ChromaDB reset error: {e}")
