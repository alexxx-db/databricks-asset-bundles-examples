# AI-Assisted Schema Generation Prompts

This directory contains prompts for using Large Language Models (LLMs) to generate table schemas through an adaptive interview process.

## Files

### [`schema_generator_prompt.md`](schema_generator_prompt.md)
The main LLM prompt that enables AI-assisted schema generation. This file contains:
- Complete embedded schema template
- Interview strategy and adaptive questions
- Quality guidelines
- Output formatting instructions

**Usage**: Copy the entire contents of this file and paste it into your LLM interface (Claude, ChatGPT, etc.)

### [`example_input.md`](example_input.md)
Template for gathering the information you'll need before starting the interview. Includes sections for:
- Table schema (DDL, column list)
- Data profiling statistics
- Common queries and use cases
- Business context
- Related tables
- Known issues

**Usage**: Fill out this template with your table information before starting the LLM interview

## Quick Start

1. **Prepare your information** using [`example_input.md`](example_input.md)
2. **Copy the prompt** from [`schema_generator_prompt.md`](schema_generator_prompt.md)
3. **Open your LLM** (https://claude.ai or https://chat.openai.com)
4. **Paste the prompt** and provide your table information
5. **Answer questions** from the adaptive interview
6. **Receive your schema** as a complete YAML file

## Detailed Instructions

See [docs/using_llm_generator.md](../docs/using_llm_generator.md) for:
- Step-by-step walkthrough
- Tips for best results
- Troubleshooting common issues
- Quality checklist
- Example sessions

## Benefits

- **Fast**: Generate a schema in 10-15 minutes vs 30-60 minutes manually
- **Adaptive**: Questions adjust based on your table structure
- **High quality**: 80-90% production-ready without manual editing
- **Consistent**: Follows best practices automatically
- **Educational**: Learn what makes a good schema through the questions

## Recommended LLMs

- **Claude 3.5 Sonnet** - Best choice (https://claude.ai)
- **GPT-4** or **GPT-4 Turbo** - Also excellent (https://chat.openai.com)
- **Claude 3 Opus** - High quality

## Need Help?

- Full guide: [docs/using_llm_generator.md](../docs/using_llm_generator.md)
- Examples: [examples/](../examples/)
- Best practices: [docs/best_practices.md](../docs/best_practices.md)
- Main README: [README.md](../README.md)
