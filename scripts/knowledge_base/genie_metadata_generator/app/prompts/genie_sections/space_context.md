# Space Context Section - Insight-Driven (Optional)

You are populating the **Space Context** section. This is optional - quick defaults often suffice.

## Your Approach

**Propose sensible defaults, offer to customize or skip:**

```
For the space context, I can set these defaults:

🎯 **Focus Areas** (based on the tables):
- Sales/Revenue reporting
- Customer analysis
- Order tracking

⚙️ **Default Filters**:
- Exclude test orders (status ≠ 'TEST')
- Default to last 90 days for time queries

👁️ **Column Visibility**:
- Show: order_id, order_date, customer_name, total_amount
- Hide: internal_id, etl_timestamp (technical columns)

This section is **optional**. I can use these defaults, customize them, or skip entirely.

What would you prefer?
```

## What to Infer

| Setting | How to Determine |
|---------|------------------|
| Focus areas | From table purposes in Tier 1 |
| Default filters | Common status exclusions |
| Show columns | Business-relevant columns |
| Hide columns | Technical/ETL columns |

## When to Skip

- Defaults work for most spaces
- User wants minimal config
- Time constraints

## Output YAML (if customized)

```yaml
space_context:
  focus_areas:
    - "Sales and revenue reporting"
    - "Customer analysis and segmentation"
    - "Order tracking and fulfillment"
  
  excluded_from_scope:
    - "Inventory management (separate space)"
    - "Detailed logistics tracking"
  
  default_filters:
    - "Exclude test records (status ≠ 'TEST')"
    - "Default time range: last 90 days"
  
  common_user_questions:
    - "What's our revenue this month?"
    - "Who are our top customers?"
    - "How many orders yesterday?"

column_visibility:
  always_show:
    - "order_id"
    - "order_date"
    - "customer_name"
    - "total_amount"
    - "status"
  
  hide_from_space:
    - "internal_tracking_id"
    - "etl_load_timestamp"
    - reason: "Technical columns not relevant for business queries"

space_metadata:
  created_date: "2024-01-15"
  last_updated: "2024-01-15"
  space_owner: "Analytics Team"
```

## Key Rules

1. **Offer to skip** - This is truly optional
2. **Sensible defaults** - Don't ask obvious questions
3. **Quick customization** - "Want to change any of these?"
4. **Focus on value** - Only add what helps users
