# SQL Expressions Section - Insight-Driven

You are populating the **SQL Expressions** section. Generate SQL from the data, don't ask for it!

## Your Approach

**Generate expressions from the data profile, then confirm:**

```
I've generated these SQL expressions based on your data:

💰 **Metrics**:
```sql
-- Revenue (using total_amount, excluding cancelled)
SUM(CASE WHEN status = 'DELIVERED' THEN total_amount ELSE 0 END)

-- Order Count  
COUNT(DISTINCT order_id)

-- Average Order Value
AVG(total_amount)
```

🔍 **Filters**:
```sql
-- Valid orders (from status values in profile)
status NOT IN ('CANCELLED', 'TEST', 'PENDING')

-- Recent orders (last 90 days)
order_date >= CURRENT_DATE - INTERVAL 90 DAY
```

📅 **Time Expressions**:
```sql
-- This month
DATE_TRUNC('month', order_date) = DATE_TRUNC('month', CURRENT_DATE)
```

These are based on:
- Amount column: `total_amount`
- Status values: DELIVERED, SHIPPED, CANCELLED, TEST (from profile)
- Date column: `order_date`

Any adjustments needed?
```

## What to Infer (DON'T ask)

| Expression | How to Build |
|------------|--------------|
| Revenue | Find amount/total columns |
| Counts | Use primary key for DISTINCT |
| Filters | Use status values from profile |
| Time | Use primary date column |

## What to Confirm (DO ask)

| Question | Why |
|----------|-----|
| Which statuses count? | Business rules |
| Revenue definition | Gross vs net |
| Default time period | User preference |

## Output YAML

```yaml
sql_expressions:
  # Metrics
  - name: "revenue"
    sql: "SUM(CASE WHEN status = 'DELIVERED' THEN total_amount ELSE 0 END)"
    description: "Total delivered revenue"
    category: "metric"
    
  - name: "order_count"
    sql: "COUNT(DISTINCT order_id)"
    description: "Number of unique orders"
    category: "metric"

  # Filters  
  - name: "valid_orders"
    sql: "status NOT IN ('CANCELLED', 'TEST')"
    description: "Exclude cancelled and test orders"
    category: "filter"
    
  - name: "recent"
    sql: "order_date >= CURRENT_DATE - INTERVAL 90 DAY"
    description: "Last 90 days"
    category: "filter"

  # Time
  - name: "this_month"
    sql: "DATE_TRUNC('month', order_date) = DATE_TRUNC('month', CURRENT_DATE)"
    description: "Current month to date"
    category: "filter"
```

## Key Rules

1. **Use actual column names** - From the schema, not guesses
2. **Use actual status values** - From the data profile
3. **Propose complete SQL** - Ready to use
4. **Ask for adjustments** - Not "what should I write?"
