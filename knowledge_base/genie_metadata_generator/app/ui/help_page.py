"""
Help & How To Page
Comprehensive user guide for Genify application.
"""

import streamlit as st


def render_help_page():
    """Render the Help & How To page with user guide."""

    st.markdown("#### :material/help: Help & How To")
    st.caption("Complete guide to using Genify for Unity Catalog metadata generation")

    # Quick navigation
    st.markdown("---")
    st.markdown("**Quick Navigation:**")
    nav_cols = st.columns(7)
    with nav_cols[0]:
        if st.button("Overview", use_container_width=True):
            st.session_state['help_section'] = 'overview'
    with nav_cols[1]:
        if st.button("Getting Started", use_container_width=True):
            st.session_state['help_section'] = 'getting_started'
    with nav_cols[2]:
        if st.button("Document Tables", use_container_width=True):
            st.session_state['help_section'] = 'document'
    with nav_cols[3]:
        if st.button("Genie Spaces", use_container_width=True):
            st.session_state['help_section'] = 'genie'
    with nav_cols[4]:
        if st.button("Editor", use_container_width=True):
            st.session_state['help_section'] = 'editor'
    with nav_cols[5]:
        if st.button("Tips", use_container_width=True):
            st.session_state['help_section'] = 'tips'
    with nav_cols[6]:
        if st.button("Troubleshooting", use_container_width=True):
            st.session_state['help_section'] = 'troubleshooting'

    st.markdown("---")

    # Get current section
    current_section = st.session_state.get('help_section', 'overview')

    # Render selected section
    if current_section == 'overview':
        _render_overview()
    elif current_section == 'getting_started':
        _render_getting_started()
    elif current_section == 'document':
        _render_document_guide()
    elif current_section == 'genie':
        _render_genie_guide()
    elif current_section == 'editor':
        _render_editor_guide()
    elif current_section == 'tips':
        _render_tips()
    elif current_section == 'troubleshooting':
        _render_troubleshooting()


def _render_overview():
    """Render overview section."""
    st.markdown("### :material/info: Overview")

    st.markdown("""
    **Genify** is an intelligent metadata generator for Databricks Unity Catalog. It helps you create:

    - **Table Comments**: Rich, structured documentation for your data tables
    - **Genie Spaces**: AI-powered natural language query interfaces

    ### Key Features

    - 🤖 **AI-Powered**: Uses LLM to generate comprehensive metadata based on your table schema
    - 💬 **Interactive Interview**: Conversational approach to gather context and requirements
    - 📊 **Data Profiling**: Automatically analyzes your data for better documentation
    - 📝 **YAML Editor**: Full-featured editor for fine-tuning generated metadata
    - 📚 **Library Management**: Save, version, and reuse your configurations
    - 📥 **Export**: Ready-to-use YAML files for Unity Catalog

    ### How It Works

    1. **Select** tables from your Unity Catalog
    2. **Document** tables through AI-guided interview
    3. **Review** and refine generated metadata
    4. **Export** or **Save** to library for deployment

    ### Navigation

    - **Select**: Browse and select tables to document
    - **Document**: Create table comments with AI assistance
    - **Review**: View and approve generated metadata
    - **Genie**: Create Genie spaces for natural language queries
    - **Export**: Download YAML files
    - **Editor**: View and edit saved YAMLs
    - **Library**: Manage your saved configurations
    """)


def _render_getting_started():
    """Render getting started section."""
    st.markdown("### :material/rocket_launch: Getting Started")

    st.markdown("""
    ### Prerequisites

    - Access to Databricks Unity Catalog
    - Databricks workspace credentials
    - Tables with data to document

    ### First Steps

    #### 1. Browse Tables
    Navigate to the **Select** tab to see available tables in your catalog.

    #### 2. Generate Data Profiles
    - Click "Generate Data Profiles" for tables you want to document
    - Profiling analyzes your data (null rates, distinct values, patterns)
    - This helps the AI generate better, more accurate metadata

    #### 3. Start Documenting
    - Navigate to the **Document** tab
    - Select a table that has a data profile
    - Begin the AI-guided interview process

    #### 4. Review and Save
    - Check the generated YAML in the **Review** tab
    - Save to library for versioning and future edits
    - Export when ready to deploy

    ### Workflow Options

    **Option A: Single Table**
    1. Select table → Generate profile → Document → Review → Save/Export

    **Option B: Batch Processing**
    1. Select multiple tables → Generate profiles for all
    2. Document each table individually
    3. Export all at once

    **Option C: Genie Space**
    1. Document related tables first
    2. Navigate to **Genie** tab
    3. Create space with documented tables
    """)


def _render_document_guide():
    """Render document tables guide."""
    st.markdown("### :material/edit_note: Document Tables")

    st.markdown("""
    ### Table Comment Generation

    Table comments provide rich documentation for Unity Catalog tables including:
    - Core description and business purpose
    - Relationships with other tables
    - Data quality information
    - Metadata and usage notes

    ### The Interview Process

    The AI will guide you through several sections:

    #### 1. Core Description
    - **What it asks**: Table purpose, business context, key concepts
    - **Tip**: Be specific about business use cases
    - **Example**: "Tracks customer interactions with support tickets"

    #### 2. Relationships
    - **What it asks**: Related tables, join keys, relationship types
    - **Tip**: Mention foreign keys and parent/child relationships
    - **Example**: "Joins with customers table on customer_id"

    #### 3. Data Quality
    - **What it asks**: Known issues, constraints, freshness
    - **Tip**: Mention any data quality concerns
    - **Example**: "Updated nightly, may have delayed records"

    #### 4. Metadata
    - **What it asks**: Ownership, sensitivity, usage patterns
    - **Tip**: Include who maintains the data
    - **Example**: "Maintained by analytics team, contains PII"

    ### Working with Data Profiles

    Before starting the interview:
    - Generate a data profile (available in Select tab)
    - The AI uses profile data to ask better questions
    - Profile shows: null rates, distinct counts, data patterns

    ### Interview Tips

    - ✅ **Be specific**: "Customer purchase history" vs "Data"
    - ✅ **Mention use cases**: "Used for churn analysis"
    - ✅ **Include context**: "Updated daily at 2 AM UTC"
    - ✅ **Note relationships**: "References products table"
    - ❌ **Avoid vagueness**: "Some data", "Various things"

    ### Editing Generated Content

    After generation:
    - Review the YAML in the split-screen view
    - Use the Re-interview button to regenerate sections
    - Save to library, then use Editor for fine-tuning
    """)


def _render_genie_guide():
    """Render Genie spaces guide."""
    st.markdown("### :material/auto_awesome: Genie Spaces")

    st.markdown("""
    ### What is a Genie Space?

    Genie spaces enable natural language queries on your data. Users can ask questions in plain English, and Genie translates them to SQL.

    ### Creating a Genie Space

    #### 1. Prerequisites
    - Document your tables first (table comments recommended)
    - Identify related tables for the space
    - Understand common query patterns

    #### 2. Space Configuration

    The AI will help you define:

    **Space Identity**
    - Space name and purpose
    - Target audience (analysts, executives, etc.)
    - Primary use cases

    **Tables**
    - Which tables to include
    - How they relate to each other
    - Default table for queries

    **Query Instructions**
    - Time-based query patterns
    - Default filters or aggregations
    - Special business logic

    **Example Queries**
    - Sample questions users might ask
    - Expected query patterns
    - Complex query examples

    **Clarification Rules**
    - Ambiguous terms to clarify
    - Business-specific terminology
    - Default assumptions

    ### Best Practices

    ✅ **Include related tables**: Add tables that users commonly query together

    ✅ **Provide context**: Explain business terms and metrics

    ✅ **Add examples**: Show realistic query examples

    ✅ **Define clarifications**: Handle ambiguous terms upfront

    ✅ **Specify time defaults**: "Last 30 days" vs "All time"

    ### Common Use Cases

    **Sales Analytics Space**
    - Tables: sales_transactions, customers, products
    - Queries: "Total revenue last month", "Top customers"

    **Operations Dashboard Space**
    - Tables: orders, fulfillment, inventory
    - Queries: "Pending orders", "Stock levels by warehouse"

    **Customer Insights Space**
    - Tables: customers, interactions, feedback
    - Queries: "Customer satisfaction trends", "Support ticket volume"
    """)


def _render_editor_guide():
    """Render YAML editor guide."""
    st.markdown("### :material/edit_document: YAML Editor")

    st.markdown("""
    ### Using the Editor

    The YAML Editor provides a full-width interface for viewing and editing saved configurations.

    ### Features

    **File Selection**
    - Dropdown at the top shows all saved YAMLs
    - Format: `[Type] table_name (catalog.schema)`
    - Select any YAML to view/edit

    **Metadata Panel**
    - Collapsable section (click to expand)
    - Shows: Table, Catalog, Schema, Type, Updated date, Tags
    - Collapsed by default to maximize editor space

    **Validation Status**
    - Shows above the editor
    - ✓ Valid YAML / ✗ Invalid YAML with error message
    - No changes / Unsaved changes indicator

    **Editor Area**
    - Large text area with syntax highlighting
    - Monospace font for readability
    - 800px height for comfortable editing

    **Action Buttons**
    - **Download**: Get YAML file locally
    - **Delete**: Remove from library
    - **Save**: Commit changes (creates new version)

    ### Editing Workflow

    1. **Select** YAML from dropdown or navigate from Library
    2. **Expand** metadata panel if needed to see details
    3. **Edit** content in the text area
    4. **Validate** - watch for "Valid YAML" indicator
    5. **Save** - creates a new version in Lakebase

    ### Version Control

    - Every save creates a new version automatically
    - Versions are timestamped
    - Previous versions are preserved
    - Safe to experiment - history is maintained

    ### YAML Structure Tips

    **Table Comments**
    ```yaml
    table_identity:
      catalog: "..."
      schema: "..."
      name: "..."

    description: |
      Your description here

    business_purpose: |
      Business context here
    ```

    **Genie Spaces**
    ```yaml
    space_identity:
      space_name: "..."
      purpose: "..."

    tables:
      - name: "table1"
        catalog: "..."
        schema: "..."
    ```

    ### Common Edits

    - Update descriptions for clarity
    - Add more example queries
    - Refine clarification rules
    - Update data quality notes
    - Modify relationship descriptions
    """)


def _render_tips():
    """Render tips and best practices."""
    st.markdown("### :material/lightbulb: Tips & Best Practices")

    st.markdown("""
    ### General Tips

    #### 🎯 Start Small
    - Begin with 1-2 important tables
    - Learn the workflow before scaling up
    - Use successful patterns for other tables

    #### 📊 Profile First
    - Always generate data profiles before documenting
    - Profiles improve AI understanding significantly
    - Check profile results for data quality insights

    #### 💬 Interview Quality
    - Take time with the interview process
    - Provide detailed, specific answers
    - Include business context and use cases
    - Mention related tables and relationships

    #### 📝 Review Carefully
    - Always review generated YAML
    - Check for accuracy and completeness
    - Use Re-interview to regenerate poor sections
    - Edit in the Editor for fine-tuning

    ### Documentation Tips

    #### For Table Comments

    **Be Business-Focused**
    - Explain WHY the table exists, not just WHAT it contains
    - Include real use cases and users
    - Mention business metrics or KPIs

    **Describe Relationships Clearly**
    - Name related tables explicitly
    - Specify join conditions
    - Explain parent-child relationships

    **Include Data Quality Info**
    - Refresh frequency and timing
    - Known issues or limitations
    - Data completeness expectations

    #### For Genie Spaces

    **Choose Tables Wisely**
    - Include tables commonly queried together
    - Start with 3-5 core tables
    - Ensure tables have clear relationships

    **Provide Good Examples**
    - Use realistic business questions
    - Cover different query types (aggregations, filters, joins)
    - Include time-based query examples

    **Define Clarifications**
    - List ambiguous business terms
    - Specify default time ranges
    - Clarify metric calculations

    ### Library Management

    #### Naming Conventions
    - Use clear, consistent table names
    - Tag related YAMLs (e.g., "sales", "customer")
    - Include catalog/schema in context

    #### Version Control
    - Save frequently during edits
    - Each save creates a version
    - Experiment safely knowing history is preserved

    #### Organization
    - Use tags to group related YAMLs
    - Document table comments before Genie spaces
    - Keep library clean - delete unused entries

    ### Performance Tips

    #### Profiling
    - Profile smaller tables first
    - Large tables may take longer
    - Profile during off-peak hours if possible

    #### Interviews
    - Complete one section at a time
    - Use session history to reference previous work
    - Save to library after each table

    ### Workflow Tips

    #### Iterative Approach
    1. Quick first pass on all tables
    2. Review and identify gaps
    3. Re-interview to fill gaps
    4. Fine-tune in Editor

    #### Team Collaboration
    - Use consistent language across tables
    - Document naming conventions
    - Share successful examples with team
    - Use tags for team ownership
    """)


def _render_troubleshooting():
    """Render troubleshooting section."""
    st.markdown("### :material/build: Troubleshooting")

    st.markdown("""
    ### Common Issues

    #### "Lakebase connection not available"

    **Problem**: Can't access Lakebase backend

    **Solutions**:
    - Check Databricks credentials
    - Verify network connectivity
    - Confirm Lakebase is enabled in Settings
    - Contact admin if persistent

    #### "No tables available"

    **Problem**: Table browser shows no tables

    **Solutions**:
    - Verify catalog and schema access permissions
    - Check if catalogs/schemas have tables
    - Refresh the page
    - Try a different catalog

    #### "Profile generation failed"

    **Problem**: Data profiling doesn't complete

    **Solutions**:
    - Check table size (very large tables may timeout)
    - Verify read permissions on the table
    - Try again during off-peak hours
    - Check table isn't corrupted

    #### "Invalid YAML syntax"

    **Problem**: Editor shows YAML validation error

    **Solutions**:
    - Check indentation (use spaces, not tabs)
    - Verify quotes are balanced
    - Check for special characters
    - Use YAML validator to find exact issue
    - Re-generate from interview if severely broken

    #### "Save failed"

    **Problem**: Can't save YAML to library

    **Solutions**:
    - Check Lakebase connection
    - Verify YAML is valid
    - Ensure you have write permissions
    - Try refreshing and saving again

    ### Interview Issues

    #### AI gives generic responses

    **Problem**: Generated content lacks detail

    **Solutions**:
    - Provide more detailed interview answers
    - Ensure data profile was generated
    - Use Re-interview with better context
    - Edit manually in Editor for specifics

    #### Interview doesn't progress

    **Problem**: Stuck on a section

    **Solutions**:
    - Check for error messages
    - Try refreshing the page
    - Check session history for progress
    - Start new interview if needed

    ### Performance Issues

    #### Slow page loads

    **Solutions**:
    - Check network connection
    - Reduce number of open browser tabs
    - Clear browser cache
    - Try different browser

    #### Large YAML files slow to edit

    **Solutions**:
    - Use Editor page (optimized for large files)
    - Don't use preview dialog for large YAMLs
    - Close metadata panel to maximize space
    - Consider breaking into smaller sections

    ### Getting Help

    If issues persist:

    1. **Check Session History**: May show error details
    2. **Check Browser Console**: For technical errors (F12)
    3. **Document the Issue**: What you did, what happened, error messages
    4. **Contact Support**: With details above

    ### Best Practices to Avoid Issues

    ✅ Generate data profiles before documenting

    ✅ Save work frequently

    ✅ Use Re-interview for poor results instead of manual fixes

    ✅ Validate YAML before saving

    ✅ Keep library organized and clean

    ✅ Test generated YAMLs in Unity Catalog
    """)
