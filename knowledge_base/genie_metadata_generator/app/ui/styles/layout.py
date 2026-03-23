"""
Layout CSS for full-height views and scroll management.
Prevents double scrollbars by containing scroll within panes.

Note: Top padding is handled by streamlit-navigation-bar (6rem default).
"""

LAYOUT_CSS = """
/* ============================================
   LAYOUT - Full Height & Scroll Management
   ============================================ */

/* Main content area - navbar handles top padding */
.main .block-container {
    padding-bottom: var(--spacing-md, 16px);
    max-width: 100%;
}

/* ===== Ultra-Compact Material Design Sidebar ===== */
/* Using 4dp/6dp/8dp grid for maximum compactness while maintaining Material Design */

/* Reduce sidebar container padding to minimum */
section[data-testid="stSidebar"] .block-container {
    padding-top: 0.5rem !important;       /* 8dp */
    padding-bottom: 0.5rem !important;    /* 8dp */
    padding-left: 0.75rem !important;     /* 12dp */
    padding-right: 0.75rem !important;    /* 12dp */
}

/* Ultra-compact alerts/info/success/warning boxes */
section[data-testid="stSidebar"] [data-testid="stAlert"],
section[data-testid="stSidebar"] [data-testid="stNotification"],
section[data-testid="stSidebar"] .stAlert {
    padding: 0.375rem 0.625rem !important;  /* 6dp vert, 10dp horiz */
    margin-bottom: 0.375rem !important;      /* 6dp */
    margin-top: 0 !important;
    line-height: 1.3 !important;
}

/* Remove padding from alert inner divs */
section[data-testid="stSidebar"] [data-testid="stAlert"] > div,
section[data-testid="stSidebar"] [data-testid="stAlert"] p {
    padding: 0 !important;
    margin: 0 !important;
}

/* Compact buttons */
section[data-testid="stSidebar"] .stButton {
    margin-top: 0 !important;
    margin-bottom: 0.375rem !important;      /* 6dp */
}

section[data-testid="stSidebar"] .stButton > button {
    padding: 0.375rem 0.625rem !important;   /* 6dp vert, 10dp horiz */
    min-height: 32px !important;             /* Smaller than 36px */
    line-height: 1.2 !important;
}

/* Force smaller gaps on all container elements */
section[data-testid="stSidebar"] [data-testid="stVerticalBlock"],
section[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"],
section[data-testid="stSidebar"] .element-container {
    gap: 0.25rem !important;                 /* 4dp - very tight */
    margin-bottom: 0.25rem !important;       /* 4dp */
}

/* Reduce all element container margins */
section[data-testid="stSidebar"] .element-container > * {
    margin-top: 0 !important;
    margin-bottom: 0.25rem !important;       /* 4dp */
}

/* Compact markdown containers */
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
    margin-bottom: 0.25rem !important;       /* 4dp */
    margin-top: 0 !important;
}

/* Material Design typography spacing - moved to theme.py but kept for specificity */
section[data-testid="stSidebar"] .stMarkdown h3,
section[data-testid="stSidebar"] .stMarkdown h4 {
    margin-top: 0.375rem !important;         /* 6dp */
    margin-bottom: 0.25rem !important;       /* 4dp */
}

section[data-testid="stSidebar"] .stMarkdown p {
    margin-top: 0 !important;
    margin-bottom: 0.25rem !important;       /* 4dp */
}

/* Tighter expanders */
section[data-testid="stSidebar"] [data-testid="stExpander"] {
    margin-bottom: 0.375rem !important;      /* 6dp */
}

section[data-testid="stSidebar"] [data-testid="stExpander"] summary {
    padding: 0.5rem !important;              /* 8dp */
    margin-bottom: 0 !important;
    line-height: 1.2 !important;
}

section[data-testid="stSidebar"] [data-testid="stExpander"] > div > div {
    padding: 0.5rem !important;              /* 8dp all sides */
}

/* Minimal dividers */
section[data-testid="stSidebar"] hr {
    margin: 0.375rem 0 !important;           /* 6dp top/bottom */
    opacity: 0.12;
}

/* Compact form elements */
section[data-testid="stSidebar"] [data-testid="stCheckbox"],
section[data-testid="stSidebar"] [data-testid="stRadio"] {
    margin-bottom: 0.375rem !important;      /* 6dp */
    padding: 0.25rem 0 !important;           /* 4dp */
}

/* Compact metrics */
section[data-testid="stSidebar"] [data-testid="stMetric"] {
    padding: 0.375rem 0 !important;          /* 6dp vertical */
}

/* Compact captions */
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
    margin-bottom: 0.25rem !important;       /* 4dp */
    margin-top: 0 !important;
}

/* Reduce padding on ALL sidebar text elements */
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span {
    line-height: 1.3 !important;
}

/* Interview layout - two column with internal scroll */
/* Adjusted for navbar height (6rem = ~96px) */
.interview-layout {
    display: flex;
    gap: var(--spacing-lg, 24px);
    height: calc(100vh - 200px);
    min-height: 500px;
}

.interview-pane {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
    overflow: hidden;
}

.interview-pane-content {
    flex: 1;
    overflow-y: auto;
    padding-right: var(--spacing-sm, 8px);
}

/* YAML pane specific */
.yaml-pane {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
    overflow: hidden;
}

.yaml-pane-content {
    flex: 1;
    overflow-y: auto;
}

/* Scrollable containers - consistent styling */
.scrollable-container {
    overflow-y: auto;
    scrollbar-width: thin;
    scrollbar-color: var(--color-border) transparent;
}

.scrollable-container::-webkit-scrollbar {
    width: 6px;
}

.scrollable-container::-webkit-scrollbar-track {
    background: transparent;
}

.scrollable-container::-webkit-scrollbar-thumb {
    background-color: var(--color-border);
    border-radius: 3px;
}

.scrollable-container::-webkit-scrollbar-thumb:hover {
    background-color: var(--color-text-muted);
}

/* Chat container styling */
.stChatMessage {
    margin-bottom: var(--spacing-sm, 8px);
}

/* Expander content - prevent expanding page height */
[data-testid="stExpander"] details[open] > div {
    max-height: 400px;
    overflow-y: auto;
}

/* Code blocks in scrollable areas */
.stCodeBlock {
    max-height: 500px;
    overflow-y: auto;
}

/* ----- Responsive Design ----- */

/* Main content container - responsive width */
.main .block-container {
    max-width: 1400px;
    padding-left: var(--md-spacing-md, 16px);
    padding-right: var(--md-spacing-md, 16px);
}

/* Tablet layout adjustments */
@media (max-width: 1024px) {
    .main .block-container {
        max-width: 100%;
        padding-left: var(--md-spacing-sm, 8px);
        padding-right: var(--md-spacing-sm, 8px);
    }

    .interview-layout {
        height: calc(100vh - 180px);
        gap: var(--spacing-md, 16px);
    }
}

/* Mobile layout adjustments */
@media (max-width: 768px) {
    .main .block-container {
        padding-left: var(--md-spacing-xs, 4px);
        padding-right: var(--md-spacing-xs, 4px);
    }

    /* Stack interview layout vertically on mobile */
    .interview-layout {
        flex-direction: column;
        height: auto;
        min-height: auto;
    }

    .interview-pane {
        min-height: 400px;
    }
}

/* Small mobile devices */
@media (max-width: 480px) {
    .main .block-container {
        padding-bottom: var(--md-spacing-sm, 8px);
    }

    /* Reduce expander max-height on mobile */
    [data-testid="stExpander"] details[open] > div {
        max-height: 300px;
    }
}

/* ===== YAML Editor Page Layout ===== */
/* Single-column layout with maximum space for editor */

/* YAML text area styling - monospace font */
.stTextArea textarea {
    font-family: 'Monaco', 'Menlo', 'Consolas', 'Courier New', monospace !important;
    font-size: 13px !important;
    line-height: 1.5 !important;
}

/* Compact metadata expander */
[data-testid="stExpander"] details summary {
    padding: 8px 12px !important;
    font-size: 14px !important;
}

/* Reduce spacing in metadata expander */
[data-testid="stExpander"] [data-testid="column"] {
    padding: 4px 8px !important;
}

/* Compact status messages above editor */
[data-testid="stNotification"] {
    padding: 8px 12px !important;
    margin: 4px 0 !important;
}

/* Action buttons row - compact */
[data-testid="column"] button {
    margin: 4px 0 !important;
}
"""
