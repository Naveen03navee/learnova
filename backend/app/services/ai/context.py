from typing import List, Tuple, Dict
import logging
from app.core.config import settings
from app.schemas.rag import RetrievalResult

logger = logging.getLogger(__name__)

def estimate_tokens(text: str) -> int:
    """
    Conservatively estimates the number of tokens in a string.
    Using a safe heuristic of ~3.5 characters per token.
    """
    if not text:
        return 0
    return len(text) // 3

def build_bounded_context(chunks: List[RetrievalResult]) -> Tuple[str, Dict[str, dict]]:
    """
    Takes raw RAG chunks and builds a consolidated context string,
    strictly bounded by GENERATION_MAX_CONTEXT_TOKENS.
    Also ensures we do not exceed GENERATION_MAX_RETRIEVAL_CHUNKS and GENERATION_MAX_CHUNKS_PER_RESOURCE
    (even though SQL should handle this, it's enforced here as a safety measure).
    Returns (context_string, provenance_map) where provenance_map maps "Source X" to chunk info.
    """
    # 1. Enforce max chunks globally
    chunks = chunks[:settings.GENERATION_MAX_RETRIEVAL_CHUNKS]

    # 2. Enforce max chunks per resource
    resource_counts = {}
    filtered_chunks = []
    for chunk in chunks:
        count = resource_counts.get(chunk.resource_id, 0)
        if count < settings.GENERATION_MAX_CHUNKS_PER_RESOURCE:
            filtered_chunks.append(chunk)
            resource_counts[chunk.resource_id] = count + 1
    
    # 3. Build context string while enforcing token limit
    current_tokens = 0
    max_tokens = settings.GENERATION_MAX_CONTEXT_TOKENS
    context_parts = []
    provenance_map = {}

    for idx, chunk in enumerate(filtered_chunks):
        source_label = f"Source {idx+1}"
        # Format the chunk
        page_info = f" (Page {chunk.page_number})" if chunk.page_number else ""
        chunk_header = f"--- {source_label}: {chunk.resource_name}{page_info} ---"
        
        # Estimate header tokens
        header_tokens = estimate_tokens(chunk_header)
        
        # Check if we even have room for the header
        if current_tokens + header_tokens >= max_tokens:
            logger.warning("Context builder hit token limit before adding all chunks.")
            break
            
        context_parts.append(chunk_header)
        current_tokens += header_tokens
        
        # Calculate remaining tokens for the actual content
        remaining_tokens = max_tokens - current_tokens
        
        content_tokens = estimate_tokens(chunk.content)
        
        if content_tokens <= remaining_tokens:
            # We can fit the whole chunk
            context_parts.append(chunk.content)
            current_tokens += content_tokens
        else:
            # We must truncate the chunk
            # Calculate allowed characters (approx tokens * 3)
            allowed_chars = remaining_tokens * 3
            truncated_content = chunk.content[:allowed_chars] + "... [TRUNCATED DUE TO CONTEXT LIMITS]"
            context_parts.append(truncated_content)
            current_tokens += estimate_tokens(truncated_content)
            logger.warning("Context builder truncated a chunk to fit within limits.")
            # Map provenance even if truncated
            provenance_map[source_label] = {
                "chunk_id": chunk.chunk_id,
                "resource_id": chunk.resource_id
            }
            break # We filled the budget

        provenance_map[source_label] = {
            "chunk_id": chunk.chunk_id,
            "resource_id": chunk.resource_id
        }

        context_parts.append("\n")
        current_tokens += estimate_tokens("\n")

    return "\n".join(context_parts), provenance_map
