# Example Queries Section - Insight-Driven

You are populating the **Example Queries** section. Generate realistic examples from the data!

## Your Approach

**Present examples you've created, then ask for more:**

```
Based on the tables and common patterns, here are example queries:

**📊 Simple Metrics:**
```sql
-- "What's our total revenue this month?"
SELECT SUM(total_amount) as revenue
FROM catalog.schema.orders
WHERE status = 'DELIVERED'
  AND DATE_TRUNC('month', order_date) = DATE_TRUNC('month', CURRENT_DATE)
```

**👥 Customer Analysis:**
```sql
-- "Who are our top 10 customers?"
SELECT c.customer_name, SUM(o.total_amount) as revenue
FROM catalog.schema.orders o
JOIN catalog.schema.customers c ON o.customer_id = c.id
WHERE o.status = 'DELIVERED'
GROUP BY c.customer_name
ORDER BY revenue DESC
LIMIT 10
```

**📈 Time Series:**
```sql
-- "Show me daily orders for the last week"
SELECT DATE(order_date), COUNT(*) as orders
FROM catalog.schema.orders
WHERE order_date >= CURRENT_DATE - INTERVAL 7 DAY
GROUP BY DATE(order_date)
ORDER BY 1
```

These cover: revenue, customer analysis, time series.

What other questions do your users commonly ask?
```

## What to Generate (DON'T ask first)

| Category | Example Pattern |
|----------|-----------------|
| Simple count | "How many orders this month?" |
| Aggregation | "What's total revenue?" |
| Top N | "Top 10 customers/products" |
| Time series | "Daily/weekly trend" |
| Filtered | "Orders by status X" |

## What to Ask (AFTER presenting)

- "What other questions do users frequently ask?"
- "Any business-specific queries I should add?"
- "Are these SQL patterns correct for your setup?"

## Output YAML

```yaml
example_queries:
  - prompt: "What is our total revenue this month?"
    description: "Monthly revenue calculation"
    sql: |
      SELECT SUM(total_amount) as revenue
      FROM catalog.schema.orders
      WHERE status = 'DELIVERED'
        AND DATE_TRUNC('month', order_date) = DATE_TRUNC('month', CURRENT_DATE)
    category: "revenue"
  
  - prompt: "Who are our top 10 customers by revenue?"
    description: "Customer ranking"
    sql: |
      SELECT 
        c.customer_name,
        SUM(o.total_amount) as total_revenue
      FROM catalog.schema.orders o
      JOIN catalog.schema.customers c ON o.customer_id = c.id
      WHERE o.status = 'DELIVERED'
      GROUP BY c.customer_name
      ORDER BY total_revenue DESC
      LIMIT 10
    category: "customer_analysis"
  
  - prompt: "Show me daily order counts for the last week"
    description: "Recent order trend"
    sql: |
      SELECT 
        DATE(order_date) as date,
        COUNT(*) as order_count
      FROM catalog.schema.orders
      WHERE order_date >= CURRENT_DATE - INTERVAL 7 DAY
      GROUP BY DATE(order_date)
      ORDER BY date
    category: "time_series"
```

## Key Rules

1. **Use real table names** - From the actual catalog.schema.table
2. **Use real column names** - From the schema
3. **Apply correct filters** - Based on query instructions
4. **Variety is key** - Cover different query types
5. **SQL must be valid** - These should actually work
