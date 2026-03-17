# Metadata Section - Insight-Driven (Optional)

You are populating the **Metadata** section. This is optional - respect if user wants to skip.

## Your Approach

**Present what you can infer, offer to skip:**

```
For the metadata section, here's what I've identified:

🔑 **Primary Key**: `order_id` (appears unique in profile)
📅 **Last Modified**: [from table metadata if available]
🏷️ **Suggested Tags**: sales, orders, transactions, e-commerce

This section is **optional**. I can fill it with these defaults, or we can skip.

Want to add:
- **Data owner** (which team maintains this)?
- **Compliance notes** (PII, retention requirements)?
```

## What to Infer (DON'T ask)

| Field | How to Infer |
|-------|--------------|
| Primary key | Unique `*_id` column |
| Tags | From domain, table name |
| Last modified | Table metadata |

## What to Ask (IF user wants to complete)

| Question | Why |
|----------|-----|
| Data owner | Not in schema |
| Compliance | Business requirement |
| Retention | Policy not in data |

## Output YAML

```yaml
metadata:
  primary_key: "order_id"
  compliance:
    contains_pii: true
    data_classification: "confidential"
    retention_policy: "7 years"
  ownership:
    data_owner: "Sales Operations"
    technical_owner: "Data Engineering"

tags:
  - "sales"
  - "orders"
  - "transactions"
  - "revenue"
```

## Key Rules

1. **Offer to skip** - This section is optional
2. **Suggest tags** - Based on table name and domain
3. **Infer primary key** - Usually obvious from schema
4. **Keep brief** - Don't over-document
