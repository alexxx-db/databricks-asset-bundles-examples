"""
Centralized help content for consistency across UI.

Single source of truth for common help text used in multiple components.
"""

GETTING_STARTED_GUIDE = """
### Quick Start Guide

**Step 1: Select Tables**
- Choose a **Catalog** and **Schema** from dropdowns below
- Select one or more tables (use search to find tables quickly)

**Step 2: Add to Queue**
- Click "Add to Queue" to batch process multiple tables
- View your queue in the expandable section

**Step 3: Profile (Recommended)**
- Click "Profile" in the queue to analyze data
- Profiles help AI pre-fill 50-70% of metadata fields
- Takes 2-5 seconds per table

**Step 4: Start Documenting**
- Click "Start Documenting" to begin AI interviews
- Your progress auto-saves every few questions
- You can resume anytime if interrupted

**Pro Tips:**
- Profile tables before documenting for faster interviews
- Add similar tables together for batch processing
- Start with your most important tables first
"""

INTERVIEW_TIPS = """
**How Interviews Work:**
- AI asks questions section by section (Core → Relationships → Quality → Metadata)
- ~50-70% of fields pre-filled from data profiling
- Only asks what truly needs human input

**Your Part:**
- Answer in your own words (formatting handled by AI)
- Use suggested answers if correct
- Skip sections you don't know about

**Helpful Features:**
- ✓ Progress auto-saves every 3 questions
- ✓ Resume if browser refreshes
- ✓ Live YAML preview on right side
- ✓ Edit final YAML after interview
"""

WHATS_NEXT_REVIEW = """
### You've documented your tables! Now you have 3 options:

**Option 1: Configure Genie Space** (Recommended)
- Click "Configure Genie" to optimize for natural language queries
- Adds SQL expressions, query instructions, examples
- Takes 3-5 minutes for all tables together

**Option 2: Export Comments Only**
- Click "Export Comments Only" to download table documentation
- Apply to Unity Catalog with SQL COMMENT statements
- Skip Genie configuration for now

**Option 3: Add More Tables**
- Click "Add More Tables" to document additional tables
- All progress is saved automatically

**Need to Edit?** Click "Edit" on any table to modify its documentation.
"""
