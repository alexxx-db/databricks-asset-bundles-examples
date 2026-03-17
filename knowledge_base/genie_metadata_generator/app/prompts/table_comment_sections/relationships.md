# Relationships & Concepts Section - Insight-Driven

You are populating the **Relationships & Concepts** section. Analyze foreign keys and column patterns!

## Your Approach

**Present detected relationships, then confirm:**

```
I've identified these relationships from the schema:

🔗 **Foreign Keys Detected**:
- `customer_id` → likely joins to a customers table
- `product_id` → likely joins to a products table
- `category_id` → likely joins to a categories table

📊 **Business Metrics I Can Infer**:
- `total_amount`: Primary revenue metric
- `quantity`: Order volume metric
- `discount_amount`: Discount tracking

Are these relationships correct? Any **business-specific terms** I should know?
(e.g., "GMV" = total_amount, "AOV" = average order value)
```

## What to Infer (DON'T ask)

| Pattern | Inference |
|---------|-----------|
| `*_id` columns | Foreign key to that entity |
| `amount`, `total`, `revenue` | Financial metric |
| `count`, `quantity`, `num_*` | Count metric |
| `*_date`, `*_at` | Time dimension |

## What to Confirm (DO ask)

| Question | Why |
|----------|-----|
| Business terms | Company-specific naming |
| Calculation rules | Logic isn't in schema |
| Preferred relationships | Multiple possible joins |

## Output YAML

```yaml
business_concepts:
  revenue:
    definition: "Total sales amount for completed orders"
    calculation: "SUM(total_amount) WHERE status = 'DELIVERED'"
    rationale: "Excludes cancelled and pending orders"

relationships:
  - table: "customers"
    type: "many-to-one"
    join_key: "customer_id"
    description: "Each order belongs to one customer"
    provides: "Customer name, segment, contact info"
```

## Key Rules

1. **Detect foreign keys** - Any `*_id` column is a likely relationship
2. **Propose metrics** - Name the obvious calculations
3. **Ask about terminology** - "Do you call this 'revenue' or 'GMV'?"
4. **Keep it brief** - Only critical relationships and metrics
