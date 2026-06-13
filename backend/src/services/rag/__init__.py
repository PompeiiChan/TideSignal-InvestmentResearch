"""Local knowledge-base RAG services."""

from .models import RagHit, RagRetrievalResult
from .service import RagNotReadyError, RagService

__all__ = [
    "RagHit",
    "RagNotReadyError",
    "RagRetrievalResult",
    "RagService",
]
