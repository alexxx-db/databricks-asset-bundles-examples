"""
LLM client for Databricks Foundation Models and Serving Endpoints.
Reference: https://docs.databricks.com/en/machine-learning/foundation-models/index.html
"""

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole
import streamlit as st
import logging
import time

# Configure logger for LLM calls
logger = logging.getLogger(__name__)


# Custom exceptions for LLM errors
class LLMRateLimitError(Exception):
    """Raised when LLM rate limit is exceeded."""
    pass


class LLMTimeoutError(Exception):
    """Raised when LLM call times out."""
    pass


@st.cache_resource
def get_cached_llm_client(endpoint_name: str, max_tokens: int, temperature: float) -> 'LLMClient':
    """
    Get or create a cached LLM client instance.
    
    Uses st.cache_resource to avoid recreating the client on every page rerun.
    The client is cached based on its configuration parameters.
    
    Args:
        endpoint_name: Name of serving endpoint
        max_tokens: Maximum tokens in response
        temperature: Sampling temperature
    
    Returns:
        Cached LLMClient instance
    """
    logger.info(f"Creating cached LLM client: {endpoint_name}")
    return LLMClient(endpoint_name, max_tokens, temperature)


def get_main_llm_client() -> 'LLMClient':
    """
    Get cached LLM client for main interview endpoint (GPT-5.2).
    
    Convenience function that reads config and creates cached client
    for the main interview LLM endpoint.
    
    Returns:
        Cached LLMClient configured for interviews
    """
    from config import config
    return get_cached_llm_client(
        config.llm_endpoint_name,
        config.llm_max_tokens,
        config.llm_temperature
    )


def get_summarizer_llm_client() -> 'LLMClient':
    """
    Get cached LLM client for summarizer endpoint (Gemini Flash).
    
    Convenience function that reads config and creates cached client
    for the context summarizer LLM endpoint.
    
    Returns:
        Cached LLMClient configured for context summarization
    """
    from config import config
    return get_cached_llm_client(
        config.summarizer_endpoint_name,
        config.summarizer_max_tokens,
        config.summarizer_temperature
    )


class LLMClient:
    """Simple client for calling Databricks LLM endpoints with comprehensive logging."""
    
    def __init__(self, endpoint_name, max_tokens, temperature):
        """
        Initialize LLM client.
        
        Args:
            endpoint_name: Name of serving endpoint (e.g., "databricks-dbrx-instruct")
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0.0-1.0)
        """
        self.endpoint_name = endpoint_name
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.client = WorkspaceClient()
        self.call_count = 0
        
        logger.info(f"LLMClient initialized: endpoint={endpoint_name}, max_tokens={max_tokens}, temp={temperature}")
    
    def chat(self, messages, max_tokens=None, temperature=None):
        """
        Send chat request to LLM endpoint with comprehensive logging.
        
        Args:
            messages: List of {"role": "user/assistant/system", "content": "text"}
            max_tokens: Override default max tokens
            temperature: Override default temperature
        
        Returns:
            String response from LLM
        
        Raises:
            Exception: If LLM call fails
        """
        self.call_count += 1
        call_id = self.call_count
        
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature or self.temperature
        
        # Calculate input statistics
        total_input_chars = sum(len(m["content"]) for m in messages)
        message_count = len(messages)
        
        # Log request details
        logger.info(f"[Call #{call_id}] LLM Request Started")
        logger.info(f"[Call #{call_id}] Endpoint: {self.endpoint_name}")
        logger.info(f"[Call #{call_id}] Messages: {message_count} (System: {sum(1 for m in messages if m['role'] == 'system')}, "
                   f"User: {sum(1 for m in messages if m['role'] == 'user')}, "
                   f"Assistant: {sum(1 for m in messages if m['role'] == 'assistant')})")
        logger.info(f"[Call #{call_id}] Input size: {total_input_chars:,} chars (~{total_input_chars // 4:,} tokens)")
        logger.info(f"[Call #{call_id}] Parameters: max_tokens={max_tokens}, temperature={temperature}")
        
        # Log message breakdown (first 100 chars of each)
        for i, msg in enumerate(messages):
            preview = msg["content"][:100].replace("\n", " ")
            if len(msg["content"]) > 100:
                preview += "..."
            logger.debug(f"[Call #{call_id}] Message {i+1} ({msg['role']}): {preview}")
        
        # Make the API call with timing
        start_time = time.time()
        
        try:
            # Convert to SDK format
            sdk_messages = [
                ChatMessage(
                    role=ChatMessageRole(m["role"]),
                    content=m["content"]
                )
                for m in messages
            ]
            
            response = self.client.serving_endpoints.query(
                name=self.endpoint_name,
                messages=sdk_messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            elapsed_time = time.time() - start_time
            response_content = response.choices[0].message.content
            
            # Validate we got actual content
            if not response_content:
                logger.warning(f"[Call #{call_id}] ⚠️ LLM returned empty response")
                response_content = ""
            
            response_length = len(response_content)
            
            # Log response details
            logger.info(f"[Call #{call_id}] LLM Response Received")
            logger.info(f"[Call #{call_id}] Response time: {elapsed_time:.2f}s")
            logger.info(f"[Call #{call_id}] Response size: {response_length:,} chars (~{response_length // 4:,} tokens)")
            
            if response_content:
                logger.info(f"[Call #{call_id}] Response preview: {response_content[:150].replace(chr(10), ' ')}...")
            else:
                logger.info(f"[Call #{call_id}] Response preview: (empty)")
            
            logger.info(f"[Call #{call_id}] ✅ Success")
            
            return response_content
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            error_msg = str(e).lower()
            
            # Classify error types
            if "rate limit" in error_msg or "429" in error_msg:
                logger.error(f"[Call #{call_id}] ❌ Rate Limit Error after {elapsed_time:.2f}s")
                raise LLMRateLimitError(f"Rate limit exceeded: {e}")
            elif "timeout" in error_msg or "timed out" in error_msg:
                logger.error(f"[Call #{call_id}] ❌ Timeout Error after {elapsed_time:.2f}s")
                raise LLMTimeoutError(f"Request timed out: {e}")
            else:
                logger.error(f"[Call #{call_id}] ❌ Error after {elapsed_time:.2f}s: {str(e)}")
                logger.error(f"[Call #{call_id}] Error type: {type(e).__name__}")
                raise
    
    def chat_with_retry(self, messages, max_retries=3, max_tokens=None, temperature=None):
        """
        Chat with LLM with exponential backoff retry logic.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            max_retries: Maximum number of retry attempts (default: 3)
            max_tokens: Optional max tokens override
            temperature: Optional temperature override
        
        Returns:
            str: LLM response content
        
        Raises:
            LLMRateLimitError: If rate limit exceeded after retries
            LLMTimeoutError: If timeout after retries
            Exception: For other errors
        """
        for attempt in range(max_retries):
            try:
                return self.chat(messages, max_tokens, temperature)
            except LLMRateLimitError as e:
                if attempt == max_retries - 1:
                    raise
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                logger.warning(f"Rate limited, waiting {wait_time}s before retry {attempt + 1}/{max_retries}...")
                time.sleep(wait_time)
            except LLMTimeoutError as e:
                if attempt == max_retries - 1:
                    raise
                wait_time = 2 ** attempt
                logger.warning(f"Timeout, waiting {wait_time}s before retry {attempt + 1}/{max_retries}...")
                time.sleep(wait_time)
            except Exception as e:
                # Don't retry for other errors
                raise
