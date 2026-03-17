"""
UI Constants for consistent button labels, icons, and messages.

Centralizes all UI text for consistency and easier maintenance.
"""

# ============================================================================
# Button Labels
# ============================================================================

# Navigation
BUTTON_BACK_TO_SELECT = "Back to Select"
BUTTON_BACK_TO_REVIEW = "Back to Review"
BUTTON_BACK_TO_EXPORT = "Back to Export"
BUTTON_BACK_TO_BROWSER = "Back to Browser"  # Deprecated, use BACK_TO_SELECT
BUTTON_GO_BACK = "Go Back"
BUTTON_CONTINUE = "Continue"

# Actions
BUTTON_ADD_TABLES = "Add Tables"
BUTTON_ADD_MORE_TABLES = "Add More Tables"
BUTTON_START_DOCUMENTING = "Start Documenting"
BUTTON_START_INTERVIEW = "Start Interview"
BUTTON_START_OVER = "Start Over"
BUTTON_START_FRESH = "Start Fresh"

# Save/Edit/Delete
BUTTON_SAVE = "Save"
BUTTON_SAVE_PROGRESS = "Save Progress"
BUTTON_EDIT = "Edit"
BUTTON_DELETE = "Delete"
BUTTON_REMOVE = "Remove"
BUTTON_CLEAR_QUEUE = "Clear Queue"

# Generation
BUTTON_GENERATE_PROFILE = "Generate Profile"
BUTTON_GENERATE_YAML = "Generate YAML"

# Export
BUTTON_DOWNLOAD = "Download"
BUTTON_DOWNLOAD_YAML = "Download YAML"
BUTTON_DOWNLOAD_ZIP = "Download All as ZIP"
BUTTON_EXPORT = "Export"

# Interview
BUTTON_SKIP_SECTION = "Skip Section"
BUTTON_COMPLETE_SECTION = "Complete Section"
BUTTON_CONTINUE_INTERVIEW = "Continue Interview"

# ============================================================================
# Material Icons (Consistent across UI)
# ============================================================================

# Navigation icons
ICON_BACK = ":material/arrow_back:"
ICON_FORWARD = ":material/arrow_forward:"
ICON_HOME = ":material/home:"

# Action icons
ICON_ADD = ":material/add:"
ICON_REMOVE = ":material/remove:"
ICON_DELETE = ":material/delete:"
ICON_CLOSE = ":material/close:"

# Edit icons
ICON_EDIT = ":material/edit:"
ICON_SAVE = ":material/save:"
ICON_REFRESH = ":material/refresh:"
ICON_UNDO = ":material/undo:"

# File icons
ICON_DOWNLOAD = ":material/download:"
ICON_UPLOAD = ":material/upload:"
ICON_FOLDER = ":material/folder:"
ICON_FOLDER_ZIP = ":material/folder_zip:"
ICON_FILE = ":material/description:"

# Status icons
ICON_CHECK = ":material/check:"
ICON_CHECK_CIRCLE = ":material/check_circle:"
ICON_WARNING = ":material/warning:"
ICON_ERROR = ":material/error:"
ICON_INFO = ":material/info:"

# Feature icons
ICON_SEARCH = ":material/search:"
ICON_FILTER = ":material/filter_alt:"
ICON_SETTINGS = ":material/settings:"
ICON_HELP = ":material/help:"
ICON_LIGHTBULB = ":material/lightbulb:"

# Data icons
ICON_TABLE = ":material/table_chart:"
ICON_ANALYTICS = ":material/analytics:"
ICON_BAR_CHART = ":material/bar_chart:"
ICON_DATABASE = ":material/storage:"

# Interview icons
ICON_INTERVIEW = ":material/edit_note:"
ICON_REVIEW = ":material/rate_review:"
ICON_GENIE = ":material/auto_awesome:"

# Library icons
ICON_LIBRARY = ":material/library_books:"
ICON_HISTORY = ":material/history:"
ICON_VISIBILITY = ":material/visibility:"

# ============================================================================
# Status Messages
# ============================================================================

# Success messages
MSG_SUCCESS_SAVED = "✓ Saved successfully!"
MSG_SUCCESS_DELETED = "✓ Deleted successfully"
MSG_SUCCESS_GENERATED = "✓ Profile generated"
MSG_SUCCESS_EXPORTED = "✓ Exported successfully"

# Error messages
MSG_ERROR_SAVE_FAILED = "❌ Failed to save"
MSG_ERROR_DELETE_FAILED = "❌ Failed to delete"
MSG_ERROR_GENERATION_FAILED = "❌ Generation failed"
MSG_ERROR_NO_CONNECTION = "❌ Database connection unavailable"

# Warning messages
MSG_WARNING_NO_PROFILE = "⚠️ No data profile generated"
MSG_WARNING_UNSAVED_CHANGES = "⚠️ You have unsaved changes"
MSG_WARNING_CANNOT_UNDO = "⚠️ This action cannot be undone"

# Info messages
MSG_INFO_EMPTY_QUEUE = "No tables in queue"
MSG_INFO_NO_TABLES = "No tables documented yet"
MSG_INFO_LAKEBASE_REQUIRED = "Lakebase connection required"

# ============================================================================
# Helper Text
# ============================================================================

HELP_PROFILE_BENEFIT = "Reduces interview questions by 50-70%"
HELP_PROFILE_TIME = "Takes 2-5 seconds for typical tables"
HELP_AUTOSAVE = "Progress auto-saves every 3 questions"
HELP_RESUME = "You can resume anytime if interrupted"

# ============================================================================
# Workflow Labels
# ============================================================================

WORKFLOW_LABELS = {
    'browse': 'Selecting tables',
    'table_interview': 'Documenting tables',
    'review': 'Reviewing',
    'genie_interview': 'Configuring Genie',
    'export': 'Ready to export',
    'library': 'Library',
    'help': 'Help'
}

# ============================================================================
# Page Titles
# ============================================================================

PAGE_TITLE_SELECT = "Browse Tables"
PAGE_TITLE_DOCUMENT = "Document Tables"
PAGE_TITLE_REVIEW = "Review Table Comments"
PAGE_TITLE_GENIE = "Genie Space Configuration"
PAGE_TITLE_EXPORT = "Export Metadata"
PAGE_TITLE_EDITOR = "YAML Editor"
PAGE_TITLE_LIBRARY = "YAML Library"
PAGE_TITLE_HELP = "Help & How To"
