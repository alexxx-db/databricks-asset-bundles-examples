"""
Context Summarizer Service
Handles conditional LLM-based summarization of large contexts.
"""
import logging

from llm.client import LLMClient

logger = logging.getLogger(__name__)


class ContextSummarizerService:
    """
    Service for managing and summarizing large context for LLM prompts.
    Uses conditional summarization - only pays when needed.
    """

    def __init__(self, llm_client: LLMClient):
        """
        Initialize context summarizer service.

        Args:
            llm_client: LLM client instance for summarization
        """
        self.llm = llm_client
        logger.info("ContextSummarizerService initialized")

    def summarize_if_needed(self, context: str, max_chars: int = 8000) -> str:
        """
        Conditionally summarize context if it exceeds token budget.

        Args:
            context: Full context string
            max_chars: Maximum chars before summarization (~2K tokens)

        Returns:
            Original context if under budget, summarized if over
        """
        if not context:
            return context

        # Fast path: context is small enough
        if len(context) <= max_chars:
            logger.info(f"Context size {len(context)} chars - using as-is (under {max_chars} budget)")
            return context

        # Slow path: context exceeds budget, summarize
        logger.warning(f"Context size {len(context)} chars exceeds {max_chars} - summarizing to fit")

        try:
            summarized = self._summarize_context(context)
            logger.info(f"✓ Summarized context from {len(context)} to {len(summarized)} chars")
            return summarized
        except Exception as e:
            # Catches: empty responses (ValueError), rate limits, timeouts, other errors
            logger.error(f"Failed to summarize context after retries: {e}")
            logger.warning(f"Falling back to truncation at {max_chars} chars")
            # Fallback to simple truncation - preserves data instead of losing it
            return self._truncate_context(context, max_chars)

    def _summarize_context(self, context: str) -> str:
        """
        Use LLM to intelligently summarize context preserving key information.
        Uses retry logic with exponential backoff for reliability.

        Args:
            context: Full context string

        Returns:
            Summarized context (~2000 chars)

        Raises:
            ValueError: If LLM returns empty or too-short summary after retries
        """
        summarization_messages = [
            {
                "role": "system",
                "content": """You are a data context summarizer. Your job is to compress table/data context while preserving ALL key information for interview planning.

**Preserve:**
- Table names, schemas, catalogs
- Column names and types (all of them, comma-separated if needed)
- Key statistics (row counts, date ranges, distinct values)
- Business context from YAMLs (descriptions, purposes, relationships)
- Data quality insights (null percentages, top values)

**Remove:**
- Verbose formatting
- Redundant explanations
- Empty sections
- Excessive whitespace

**Output:** Concise markdown summary under 2000 characters that preserves all semantic information."""
            },
            {
                "role": "user",
                "content": f"Summarize this context to under 2000 characters:\n\n{context}"
            }
        ]

        # FIX: Use chat_with_retry instead of chat for reliability
        # Exponential backoff: 1s, 2s, 4s if LLM is busy or fails
        summarized = self.llm.chat_with_retry(
            summarization_messages,
            max_tokens=800,
            temperature=0.3,
            max_retries=3
        )

        # FIX: Validate response is substantial
        # Empty or too-short responses indicate LLM failure
        if not summarized or len(summarized) < 100:
            logger.warning(
                f"LLM returned insufficient summary ({len(summarized) if summarized else 0} chars), "
                f"raising error to trigger fallback"
            )
            raise ValueError(f"Empty or too-short summary from LLM ({len(summarized) if summarized else 0} chars)")

        return summarized

    def _truncate_context(self, context: str, max_chars: int) -> str:
        """
        Fallback: simple truncation when summarization fails.

        Args:
            context: Full context string
            max_chars: Maximum characters to keep

        Returns:
            Truncated context with note
        """
        if len(context) <= max_chars:
            return context

        original_len = len(context)
        truncated = context[:max_chars]
        preserved_pct = int((max_chars / original_len) * 100)

        logger.info(f"Using truncated context: {max_chars} chars (preserved {preserved_pct}% of {original_len} chars)")

        return truncated + f"\n\n...(truncated to {max_chars} chars - LLM summarization failed, preserved {preserved_pct}% of original)"


def get_context_summarizer_service(llm_client: LLMClient) -> ContextSummarizerService:
    """
    Get cached context summarizer service instance.
    Follows InterviewService pattern - session-state cached.

    Args:
        llm_client: LLM client for summarization

    Returns:
        Cached ContextSummarizerService instance
    """
    import streamlit as st

    # Cache per session (like InterviewService)
    if '_context_summarizer_service' not in st.session_state:
        st.session_state._context_summarizer_service = ContextSummarizerService(llm_client)

    return st.session_state._context_summarizer_service
