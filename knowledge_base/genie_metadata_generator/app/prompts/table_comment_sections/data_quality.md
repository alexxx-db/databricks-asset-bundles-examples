# Data Quality Section - Insight-Driven

You are populating the **Data Quality** section. The data profile tells you most of this!

## Your Approach

**Present what the profile reveals, then confirm:**

```
Here's what the data profile shows about quality:

📊 **Completeness**:
- Overall: 94.2% (from NULL analysis)
- `shipping_address`: 12% NULL (likely digital products?)
- `discount_code`: 78% NULL (most orders full price)
- All other columns: >99% complete

⚠️ **Potential Issues I Noticed**:
- `status` has 0.1% 'TEST' values
- Oldest records (pre-2022) have more NULLs

Are there any **known data issues** I should document?
(e.g., migration problems, historical gaps, system changes)
```

## What to Infer (DON'T ask)

| Data Point | Source |
|------------|--------|
| Completeness % | NULL counts from profile |
| Column issues | High NULL columns |
| Data patterns | Top values, distributions |
| Date coverage | Min/max dates |

## What to Confirm (DO ask)

| Question | Why |
|----------|-----|
| Known issues | Historical problems not in data |
| Workarounds | How users handle issues |
| Business rules | Filtering logic |

## Output YAML

```yaml
data_quality:
  completeness:
    overall: "94.2%"
    notes:
      - "shipping_address: 12% NULL (digital products have no shipping)"
      - "discount_code: 78% NULL (majority of orders are full price)"
  
  known_issues:
    - issue: "Legacy data gaps"
      description: "Records before 2020 missing some fields"
      workaround: "Filter to created_date >= '2020-01-01' for complete data"

limitations:
  - "Does not include returns processed outside main system"
  - "Test orders (status='TEST') should be excluded from analysis"

business_rules:
  - rule: "Valid orders filter"
    logic: "status NOT IN ('TEST', 'CANCELLED')"
    rationale: "Standard filter for reporting"
```

## Key Rules

1. **Quote the profile** - "12% NULL" not "some missing values"
2. **Explain NULLs** - Why might this column be empty?
3. **Identify test data** - Look for TEST, DUMMY, SAMPLE values
4. **Propose filters** - Suggest standard exclusion rules
