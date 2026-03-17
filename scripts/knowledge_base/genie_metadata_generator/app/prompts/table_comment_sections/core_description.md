# Core Description Section - Insight-Driven

You are populating the **Core Description** section. You have data - use it!

## Your Approach

**Present your analysis, then confirm:**

```
Based on the data profile, here's what I've identified:

📋 **Description**: This is a [entity] table containing [what]
📊 **Granularity**: One row = [what makes a row unique]
🏢 **Domain**: [sales/finance/marketing/operations]
📅 **Date Range**: [start] to [end]
📈 **Volume**: [count] rows, [completeness]%

Does this capture it? What's the **business purpose** - who uses this and why?
```

## What to Infer (DON'T ask)

| Field | How to Infer |
|-------|--------------|
| Description | Table name + column types |
| Granularity | Look for `_id` columns, unique keys |
| Domain | Column names (amount=sales, user=marketing) |
| Date range | Min/max from date columns in profile |
| Completeness | NULL percentages from profile |

## What to Confirm (DO ask)

| Field | Why You Need User Input |
|-------|------------------------|
| Business purpose | Intent isn't in the data |
| Who uses it | Users/teams aren't in schema |
| Special rules | Business context not visible |

## Output YAML

```yaml
description: |
  [2-3 sentences about what this table contains]

business_purpose: |
  [Who uses it and why - from user input]

granularity: |
  One row represents [specific entity from your analysis]

business_domain: "[domain]"

data_scope:
  date_range:
    start_date: "[actual date from profile]"
    current: "[actual date from profile]"
  completeness: "[% from profile]"
  refresh_frequency: "[daily/hourly/etc]"
```

## Key Rules

1. **Use specific values** - "2022-01-01" not "historical"
2. **Reference columns** - "order_id is the unique key"
3. **1-2 questions max** - You have most of the info already
4. **Be confident** - You analyzed the data, present findings
