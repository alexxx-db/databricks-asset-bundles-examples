# LLM Module

Simple and focused LLM integration for Genify.

## Overview

This module provides two clean, single-purpose classes:
- **`LLMClient`** - Calls Databricks LLM endpoints
- **`InterviewConductor`** - Manages the adaptive interview flow

## Files

### `client.py` (61 lines)

**Purpose**: Simple wrapper for Databricks Foundation Model API

**Key Features**:
- ✅ Minimal dependencies (only `databricks-sdk`)
- ✅ UI-agnostic (no Streamlit coupling)
- ✅ Single responsibility (just API calls)
- ✅ Clean error propagation

**Usage**:
```python
from llm.client import LLMClient

client = LLMClient(
    endpoint_name="databricks-gpt-5-2",
    max_tokens=2048,  # From config.llm_max_tokens (GPT-5.2 OTPM limit: 5,000)
    temperature=0.7
)

messages = [
    {"role": "system", "content": "You are a helpful assistant"},
    {"role": "user", "content": "Hello!"}
]

response = client.chat(messages)
```

### `interview.py` (294 lines)

**Purpose**: Conducts adaptive interview using LLM

**Key Features**:
- ✅ Loads prompt and templates dynamically
- ✅ Manages conversation history
- ✅ Formats table metadata for LLM context
- ✅ Extracts YAML from LLM responses
- ✅ Injects templates into system prompt

**Usage**:
```python
from llm.interview import InterviewConductor
from llm.client import LLMClient

# Initialize
llm = LLMClient("databricks-dbrx-instruct", 4096, 0.7)
conductor = InterviewConductor(
    llm_client=llm,
    prompt_template_path=Path("prompts/schema_generator_prompt.md"),
    tier1_template_path=Path("templates/table_comment_template.yml"),
    tier2_template_path=Path("templates/genie_space_metadata.yml")
)

# Start interview
question = conductor.start_interview(table_metadata)

# Continue interview
while not conductor.interview_complete:
    user_answer = input(question)
    question = conductor.answer_question(user_answer)

# Extract results
tier1_yaml, tier2_yaml = conductor.extract_generated_yaml(question)
```

## Design Principles

### 1. Single Responsibility
- `LLMClient` only handles API calls
- `InterviewConductor` only manages interview flow
- No mixed concerns

### 2. UI Agnostic
- No Streamlit imports in core logic
- Error handling via exceptions (UI layer handles display)
- Reusable in CLI, API, or other interfaces

### 3. Minimal Dependencies
- Only essential imports
- No unused code
- Clean and focused

### 4. Clear Separation
```
client.py       → API communication
interview.py    → Business logic
ui/interview_panel.py → User interface
```

## Recent Cleanup (Jan 2026)

### Removed
- ❌ `_generate_suggestions()` method (88 lines) - No longer needed with LLM inline suggestions
- ❌ `chat_stream()` method - Unused future feature
- ❌ `st.error()` call - Removed UI coupling
- ❌ Unused `json` import

### Updated
- ✅ Fixed file path reference in docstring
- ✅ Simplified error handling
- ✅ Improved docstrings

### Result
- **Before**: 386 lines (interview.py) + 85 lines (client.py) = 471 lines
- **After**: 294 lines (interview.py) + 61 lines (client.py) = 355 lines
- **Reduction**: 116 lines (25% smaller)

## Code Metrics

| File | Lines | Purpose | Complexity |
|------|-------|---------|------------|
| `client.py` | 61 | API calls | Low |
| `interview.py` | 294 | Interview logic | Medium |
| `__init__.py` | 1 | Package marker | Minimal |
| **Total** | **356** | | |

## Key Methods

### LLMClient

```python
def chat(messages, max_tokens=None, temperature=None) -> str
    """Send messages to LLM, get response."""
```

### InterviewConductor

```python
def start_interview(table_metadata) -> str
    """Begin interview, return first question."""

def answer_question(user_answer) -> str
    """Submit answer, get next question or final YAML."""

def extract_generated_yaml(response) -> (str, str)
    """Extract Tier 1 and Tier 2 YAML from response."""
```

## Error Handling

### Client Layer
```python
# Raises exceptions - let caller handle
response = client.chat(messages)  # May raise Exception
```

### UI Layer
```python
# Catches and displays errors
try:
    response = client.chat(messages)
except Exception as e:
    st.error(f"LLM Error: {str(e)}")
```

## Testing

### Unit Test Example
```python
def test_llm_client():
    client = LLMClient("test-endpoint", 100, 0.5)
    assert client.endpoint_name == "test-endpoint"
    assert client.max_tokens == 100
    assert client.temperature == 0.5

def test_interview_start():
    llm = MockLLMClient()
    conductor = InterviewConductor(llm, prompt_path, tier1_path, tier2_path)
    question = conductor.start_interview(mock_metadata)
    assert question is not None
    assert len(conductor.conversation_history) == 2
```

## Dependencies

```python
# client.py
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole

# interview.py
from llm.client import LLMClient
```

**No other dependencies!** ✨

## Future Enhancements

Potential improvements (not currently needed):

1. **Streaming Support**
   - Add `chat_stream()` back when needed
   - Yield chunks for real-time display

2. **Retry Logic**
   - Automatic retries on transient failures
   - Exponential backoff

3. **Caching**
   - Cache LLM responses for identical inputs
   - Reduce API calls and costs

4. **Multiple LLM Support**
   - Support different providers (OpenAI, Anthropic)
   - Unified interface

5. **Conversation Management**
   - Save/load conversation history
   - Resume interrupted interviews

## Best Practices

### ✅ Do
- Keep methods focused and single-purpose
- Raise exceptions for errors (don't catch silently)
- Use type hints in docstrings
- Write self-documenting code

### ❌ Don't
- Add UI logic to this module
- Import Streamlit or other UI frameworks
- Catch exceptions without re-raising
- Add features "just in case"

## Summary

The LLM module is now **clean, simple, and effective**:

✅ **Simple** - Only 356 lines total  
✅ **Focused** - Each class has one job  
✅ **Testable** - No UI coupling  
✅ **Maintainable** - Clear structure  
✅ **Documented** - Comprehensive docstrings  

No bloat, no unused code, no mixed concerns. Just what's needed, nothing more. 🎯
