# Query Instructions Section - Insight-Driven

You are populating the **Query Instructions** section. Analyze the data to propose patterns!

## Your Approach

**Present query patterns you've identified, then confirm:**

```
Based on the table structure and Tier 1 YAMLs, here are the query instructions I've drafted:

📅 **Time-Based Queries**:
- Primary date: `order_date` (2022-01-01 to 2024-12-15)
- For shipping questions: use `shipped_date`
- For "recent": default to last 90 days

💰 **Revenue Queries**:
- Column: `total_amount`
- Filter: status = 'DELIVERED'
- Exclude: 'CANCELLED', 'TEST' orders

🔗 **Join Patterns**:
- Orders → Customers: `orders.customer_id = customers.id`
- For customer name: always join customers table

Does this match how your team queries this data?
```

## What to Infer (DON'T ask)

| Pattern | How to Detect |
|---------|---------------|
| Date column | Look for `*_date`, check ranges |
| Status filter | Top values from profile |
| Join keys | Foreign key columns |
| Metrics | Amount/count columns |

## What to Confirm (DO ask)

| Question | Why |
|----------|-----|
| Default time period | Team preference |
| Status meanings | Business definitions |
| Join precedence | When multiple options exist |

## Output YAML

```yaml
query_instructions:
  - scenario: "Time-based queries"
    instruction: |
      For questions about time periods:
      - Use `order_date` for "when was the order placed"
      - Use `shipped_date` for shipping/fulfillment questions
      - Default to last 90 days if no time specified
    applies_to:
      - "Date filtering"
      - "Time series analysis"
      - "Period comparisons"
  
  - scenario: "Revenue calculations"
    instruction: |
      For revenue questions:
      - Use `total_amount` column
      - Filter to status = 'DELIVERED'
      - Exclude status IN ('CANCELLED', 'TEST')
    applies_to:
      - "Sales reporting"
      - "Revenue metrics"
      - "Financial analysis"
  
  - scenario: "Customer queries"
    instruction: |
      For customer-related questions:
      - Join orders to customers on customer_id
      - Include customer_name in results
      - Group by customer_id for aggregations
    applies_to:
      - "Customer analysis"
      - "Top customers"
      - "Customer segments"
```

## Key Rules

1. **Be specific** - "Use order_date" not "use the date column"
2. **Reference actual values** - From profile, not assumptions
3. **Cover common patterns** - Time, metrics, joins, filters
4. **Write for Genie** - These are instructions Genie will follow
