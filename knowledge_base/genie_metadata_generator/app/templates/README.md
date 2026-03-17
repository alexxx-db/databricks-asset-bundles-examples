# 📋 Customizable Templates

**This is where your organization's standards live.**

Customize these templates to define your metadata structure. The interview engine adapts automatically.

---

## 📁 Directory Structure

```
templates/
├── table_comment/              # Tier 1: Unity Catalog table comments
│   ├── sections.yaml           # Section definitions
│   ├── 00_skeleton.yml         # Table identity
│   ├── 01_core_description.yml # Description, purpose, granularity
│   ├── 02_relationships.yml    # Business concepts, joins
│   ├── 03_data_quality.yml     # Quality, limitations, rules
│   └── 04_metadata.yml         # Ownership, compliance, tags
│
├── genie/                      # Tier 2: Genie space metadata
│   ├── sections.yaml           # Section definitions
│   ├── 00_skeleton.yml         # Space and table identity
│   ├── 01_sql_expressions.yml  # Metrics, filters, dimensions
│   ├── 02_query_instructions.yml # Scenario-based guidance
│   ├── 03_example_queries.yml  # Sample SQL with prompts
│   ├── 04_clarification_rules.yml # When to ask for details
│   └── 05_space_context.yml    # Scope, defaults, visibility
│
└── README.md                   # This file
```

---

## 🎯 How It Works

### 1. `sections.yaml` Controls the Interview

Each `sections.yaml` defines what sections exist and their order:

```yaml
# table_comment/sections.yaml
sections:
  - key: "core_description"
    name: "Core Description"
    template_file: "01_core_description.yml"
    description: "Description, purpose, granularity"
    prompt_focus: "What the table contains and represents"
```

### 2. Section Templates Define Fields

Each section file defines the YAML fields for that section:

```yaml
# table_comment/01_core_description.yml
description: |
  # Clear description of what the table contains

business_purpose: |
  # Why this table exists and who uses it

granularity: |
  # What one row represents (e.g., "One row = one order")

business_domain: ""
```

### 3. LLM Prompts Guide the Interview

Matching prompts in `app/prompts/` guide the LLM for each section:

```
app/prompts/
├── table_comment_sections/
│   ├── core_description.md
│   ├── relationships.md
│   └── ...
└── genie_sections/
    ├── sql_expressions.md
    └── ...
```

---

## ✏️ Customization Guide

### Adding a New Field

1. **Edit the section template**:
```yaml
# table_comment/01_core_description.yml
description: |
  ...

# ADD YOUR FIELD
data_steward: ""  # Your new field
```

2. **Update the section prompt** (optional but recommended):
```markdown
# app/prompts/table_comment_sections/core_description.md

## Also ask about:
- **Data Steward**: Who is responsible for data quality?
```

3. **Restart the app** - templates load dynamically

### Adding a New Section

1. **Create a template file**:
```yaml
# table_comment/05_compliance.yml
compliance:
  pii_classification: ""
  retention_policy: ""
  regulatory_requirements: []
```

2. **Register in sections.yaml**:
```yaml
sections:
  # ... existing sections ...
  - key: "compliance"
    name: "Compliance & Governance"
    template_file: "05_compliance.yml"
    description: "PII, retention, regulatory requirements"
    prompt_focus: "Data governance and compliance metadata"
```

3. **Create a prompt**:
```markdown
# app/prompts/table_comment_sections/compliance.md

# Compliance Section - Insight-Driven

Present compliance requirements based on column analysis...
```

### Removing a Section

Comment out or remove the section from `sections.yaml`:

```yaml
sections:
  - key: "core_description"
    # ...
  # - key: "metadata"   # Commented out = skipped
  #   name: "Metadata"
```

### Reordering Sections

Change the order in `sections.yaml`:

```yaml
sections:
  - key: "core_description"   # Interview order follows
  - key: "data_quality"       # this list order
  - key: "relationships"
```

---

## 🏗️ Template Best Practices

### 1. Use Clear Field Names

```yaml
# Good
business_purpose: |
  Why this table exists

# Bad
bp: |
  ...
```

### 2. Include Comments

```yaml
description: |
  # 2-3 sentences describing what the table contains
  # Example: "Customer orders with pricing and status"
```

### 3. Provide Structure for Complex Fields

```yaml
data_quality:
  completeness:
    overall: ""
    notes: []
  known_issues:
    - issue: ""
      description: ""
      workaround: ""
```

### 4. Keep Sections Focused

Each section should cover ONE topic:
- ✅ `core_description.yml` - Identity and purpose
- ✅ `data_quality.yml` - Quality and limitations
- ❌ `everything.yml` - Too broad

---

## 🔧 Technical Details

### Template Loading

Templates are loaded at runtime by `app/llm/section_interview.py`:

```python
def _load_section_template(self, template_file: str) -> str:
    template_dir = self.config.tier1_template_dir  # or tier2
    template_path = os.path.join(template_dir, template_file)
    with open(template_path, 'r') as f:
        return f.read()
```

### Configuration Reference

Templates are referenced in `app.yaml`:

```yaml
config:
  templates:
    table_comment_dir: "templates/table_comment"
    genie_dir: "templates/genie"
```

### Section Config Schema

```yaml
sections:
  - key: "unique_identifier"        # Used internally
    name: "Display Name"            # Shown in UI
    template_file: "XX_name.yml"    # File in this directory
    description: "Brief description" # Shown as subtitle
    prompt_focus: "What LLM should focus on"  # Guides interview
```

---

## 📊 Tier 1 vs Tier 2

| Aspect | Tier 1 (Table Comments) | Tier 2 (Genie Metadata) |
|--------|------------------------|------------------------|
| Purpose | Document the table | Configure Genie queries |
| Scope | Universal (all spaces) | Per-space |
| Applied to | Unity Catalog | Genie Space |
| Content | What table IS | How to query it |
| Frequency | Once per table | Once per space |

---

## 🆘 Troubleshooting

### Templates Not Loading

1. Check file paths in `app.yaml`
2. Verify YAML syntax is valid
3. Restart the app

### New Section Not Appearing

1. Check `sections.yaml` has the entry
2. Verify `template_file` path is correct
3. Check for YAML syntax errors

### LLM Ignoring Template Structure

1. Check the matching prompt in `app/prompts/`
2. Add explicit structure instructions
3. Verify template is being loaded (check logs)

---

## 📚 Related Documentation

- [Main README](../../README.md) - Project overview
- [Two-Tier Approach](../../docs/two_tier_approach.md) - Conceptual explanation
- [Deployment Guide](../DEPLOYMENT.md) - Deploying the app
