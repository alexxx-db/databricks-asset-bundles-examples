# Clarification Rules Section - Insight-Driven (Optional)

You are populating the **Clarification Rules** section. This is optional - only add if genuinely needed.

## Your Approach

**Suggest rules based on potential ambiguities, offer to skip:**

```
This section is **optional**. I've identified a few potentially ambiguous queries:

❓ **Possible Ambiguities**:
- "Show me sales" → Which time period? What breakdown?
- "Revenue" → Gross or net? Include pending orders?
- "Orders" → All orders or only delivered?

Want me to add clarification rules for these? Or we can skip this section - Genie often handles ambiguity well on its own.
```

## When to Add Rules

| Add Rule If | Example |
|-------------|---------|
| Time period unclear | "Show me sales" (no date) |
| Multiple interpretations | "Revenue" could mean different things |
| Critical filter missing | Need to know status to answer |

## When to Skip

- Genie handles most ambiguity well
- Over-clarification is annoying
- Simple questions don't need rules

## Output YAML (if needed)

```yaml
clarification_rules:
  - trigger_condition: "Query about 'sales' or 'revenue' without time period"
    missing_details:
      - "Time period (this week, this month, YTD?)"
    clarification_question: |
      What time period would you like?
      - This month
      - This quarter
      - Year to date
      - Custom range
    example_prompts:
      - "Show me sales"
      - "What's our revenue?"
  
  - trigger_condition: "Ambiguous 'orders' query"
    missing_details:
      - "Order status filter"
    clarification_question: |
      Should I include all orders or only completed ones?
    example_prompts:
      - "How many orders?"
```

## Key Rules

1. **Less is more** - Only add genuinely helpful rules
2. **Offer to skip** - This section is optional
3. **Don't over-clarify** - Trust Genie's intelligence
4. **Focus on business ambiguity** - Not technical details
