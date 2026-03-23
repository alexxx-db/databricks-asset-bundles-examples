"""
Material Design Component CSS.
Cards, elevation, and reusable UI elements following Material Design principles.
"""

COMPONENT_CSS = """
/* ============================================
   MATERIAL DESIGN COMPONENTS
   ============================================ */

/* ----- Material Cards ----- */
.material-card {
    background: var(--md-surface, #FFFFFF);
    border-radius: var(--md-radius-md, 8px);
    box-shadow: var(--md-shadow-1);
    padding: var(--md-spacing-md, 16px);
    margin-bottom: var(--md-spacing-md, 16px);
    transition: box-shadow var(--md-transition-fast);
}

.material-card:hover {
    box-shadow: var(--md-shadow-2);
}

.material-card-elevated {
    background: var(--md-surface, #FFFFFF);
    border-radius: var(--md-radius-md, 8px);
    box-shadow: var(--md-shadow-2);
    padding: var(--md-spacing-md, 16px);
    margin-bottom: var(--md-spacing-md, 16px);
}

/* ----- Material Surface (outlined variant) ----- */
.material-surface {
    background: var(--md-surface, #FFFFFF);
    border: 1px solid var(--md-border, rgba(0,0,0,0.12));
    border-radius: var(--md-radius-md, 8px);
    padding: var(--md-spacing-md, 16px);
    margin-bottom: var(--md-spacing-md, 16px);
}

/* ----- Info Cards (Material style) ----- */
.info-card {
    background: var(--md-surface, #FFFFFF);
    border: 1px solid var(--md-border, rgba(0,0,0,0.12));
    border-radius: var(--md-radius-md, 8px);
    padding: var(--md-spacing-md, 16px);
    margin-bottom: var(--md-spacing-md, 16px);
}

.info-card-header {
    font-size: 14px;
    font-weight: 500;
    color: var(--md-text-primary);
    margin-bottom: var(--md-spacing-sm, 8px);
}

/* ----- Section Headers ----- */
.section-header {
    display: flex;
    align-items: center;
    gap: var(--md-spacing-sm, 8px);
    margin-bottom: var(--md-spacing-md, 16px);
    color: var(--md-text-primary);
}

.section-title {
    font-size: 16px;
    font-weight: 500;
    letter-spacing: 0.15px;
}

/* ----- Material List Items ----- */
.material-list-item {
    display: flex;
    align-items: center;
    padding: var(--md-spacing-sm, 8px) var(--md-spacing-md, 16px);
    border-radius: var(--md-radius-sm, 4px);
    transition: background-color var(--md-transition-fast);
}

.material-list-item:hover {
    background: rgba(0, 0, 0, 0.04);
}

/* Dark mode list hover */
@media (prefers-color-scheme: dark) {
    .material-list-item:hover {
        background: var(--md-hover-overlay, rgba(255, 255, 255, 0.08));
    }
}

/* Dark mode - Streamlit theme attribute for list hover */
[data-testid="stAppViewContainer"][data-theme="dark"] .material-list-item:hover {
    background: var(--md-hover-overlay, rgba(255, 255, 255, 0.08));
}

/* ----- Session Cards (Material style) ----- */
.session-card {
    background: var(--md-surface, #FFFFFF);
    border: 1px solid var(--md-border, rgba(0,0,0,0.12));
    border-radius: var(--md-radius-md, 8px);
    padding: var(--md-spacing-sm, 8px) var(--md-spacing-md, 16px);
    margin-bottom: var(--md-spacing-sm, 8px);
    transition: border-color var(--md-transition-fast), box-shadow var(--md-transition-fast);
}

.session-card:hover {
    border-color: var(--md-primary);
    box-shadow: var(--md-shadow-1);
}

/* ----- Material Chips ----- */
.material-chip {
    display: inline-flex;
    align-items: center;
    padding: var(--md-spacing-xs, 4px) var(--md-spacing-sm, 8px);
    border-radius: 16px;
    font-size: 12px;
    font-weight: 500;
    background: var(--md-chip-bg, var(--md-primary-light));
    color: var(--md-chip-text, var(--md-primary-dark));
}

/* Tag chips for inline HTML (used in yaml_library_panel) */
.tag-chip {
    background: var(--md-chip-bg, rgba(25, 118, 210, 0.1));
    color: var(--md-chip-text, #1976D2);
    padding: 4px 8px;
    border-radius: 12px;
    font-size: 12px;
}

/* ----- Material Divider ----- */
.material-divider {
    height: 1px;
    background: var(--md-divider, rgba(0,0,0,0.12));
    margin: var(--md-spacing-md, 16px) 0;
}

/* ----- Material Badge ----- */
.material-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 20px;
    height: 20px;
    padding: 0 6px;
    border-radius: 10px;
    font-size: 12px;
    font-weight: 500;
    background: var(--md-primary);
    color: var(--md-on-primary);
}

/* ----- Streamlit Component Overrides for Material ----- */

/* Make expanders look more Material - Reduced specificity */
[data-testid="stExpander"] {
    border: 1px solid var(--md-border, rgba(0,0,0,0.12));
    border-radius: var(--md-radius-md, 8px);
}

/* Style metrics for Material look */
[data-testid="stMetric"] {
    background: var(--md-surface);
    padding: var(--md-spacing-md, 16px);
    border-radius: var(--md-radius-md, 8px);
    border: 1px solid var(--md-border, rgba(0,0,0,0.12));
}

/* Code blocks with Material styling */
[data-testid="stCode"] {
    border-radius: var(--md-radius-sm, 4px);
}

/* Button refinements - More gentle approach */
.stButton > button {
    font-family: var(--md-font-family);
    font-weight: 500;
    letter-spacing: 0.5px;
    border-radius: var(--md-radius-sm, 4px);
    transition: all var(--md-transition-fast);
}

/* Tabs Material styling - Reduced specificity */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    gap: 0;
}

[data-testid="stTabs"] [data-baseweb="tab"] {
    font-family: var(--md-font-family);
    font-weight: 500;
    font-size: 14px;
    letter-spacing: 0.5px;
}

/* ----- Pills Navigation ----- */
.pills-nav-container {
    background: var(--md-surface);
    padding: var(--md-spacing-md, 16px) var(--md-spacing-lg, 24px);
    border-radius: var(--md-radius-md, 8px);
    margin-bottom: var(--md-spacing-md, 16px);
    box-shadow: var(--md-shadow-1);
}

/* Spacing after navigation */
.nav-spacer {
    height: var(--md-spacing-md, 16px);
}

/* Pills navigation buttons - Override default button styling */
.pills-nav-container .stButton > button {
    border-radius: 24px;
    padding: 10px 20px;
    font-size: 14px;
    font-weight: 500;
    letter-spacing: 0.5px;
    border: 2px solid transparent;
    transition: all var(--md-transition-fast);
}

/* Primary (active) pill button */
.pills-nav-container .stButton > button[kind="primary"] {
    background: var(--md-primary);
    color: var(--md-on-primary);
    border-color: var(--md-primary);
}

/* Secondary (inactive) pill button */
.pills-nav-container .stButton > button[kind="secondary"] {
    background: transparent;
    color: var(--md-text-primary);
    border-color: var(--md-border);
}

.pills-nav-container .stButton > button[kind="secondary"]:hover {
    background: var(--md-hover-overlay, rgba(25, 118, 210, 0.08));
    border-color: var(--md-primary);
}

/* Disabled (active) button - keep highlighted */
.pills-nav-container .stButton > button:disabled {
    opacity: 1;
    background: var(--md-primary);
    color: var(--md-on-primary);
    cursor: default;
}

/* Responsive pills navigation */
@media (max-width: 768px) {
    .pills-nav-container {
        padding: var(--md-spacing-sm, 8px);
    }

    .pills-nav-container .stButton > button {
        font-size: 12px;
        padding: 8px 12px;
    }
}

/* ===== Material Icon Sizing - Make Icons Bigger and More Prominent ===== */
/* Genify logo styling - vibrant colors for light mode */
.genify-logo {
    color: #1976D2 !important; /* Vibrant blue for light mode */
    opacity: 1 !important;
}

.genify-tagline {
    color: rgba(0, 0, 0, 0.87) !important; /* Strong dark gray for light mode */
    opacity: 1 !important;
}

/* Dark mode logo colors */
@media (prefers-color-scheme: dark) {
    .genify-logo {
        color: #90CAF9 !important; /* Light blue for dark mode */
    }

    .genify-tagline {
        color: rgba(255, 255, 255, 0.87) !important; /* Light text for dark mode */
    }
}

[data-testid="stAppViewContainer"][data-theme="dark"] .genify-logo {
    color: #90CAF9 !important; /* Light blue for dark mode */
}

[data-testid="stAppViewContainer"][data-theme="dark"] .genify-tagline {
    color: rgba(255, 255, 255, 0.87) !important; /* Light text for dark mode */
}

/* Legacy sidebar logo styling - keep for compatibility */
section[data-testid="stSidebar"] > div > div:first-child .stMarkdown:first-of-type h1,
section[data-testid="stSidebar"] > div > div:first-child .stMarkdown:first-of-type p:first-of-type {
    font-size: 28px;
    font-weight: 500;
    color: var(--md-primary);
    margin: 0;
    padding: 0;
}

/* Navigation pills icons - larger and more visible */
.pills-nav-container .stButton > button span[data-testid="stMarkdownContainer"] {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-size: var(--md-icon-size-md, 22px);
}

/* General Material icon sizing - increase default size for prominence */
.stButton > button,
[data-testid="stExpander"] summary,
.stMarkdown {
    font-size: inherit;
}

/* Streamlit renders Material icons with specific styling - target them */
.stButton > button > div,
[data-testid="stExpander"] > summary > div {
    display: inline-flex;
    align-items: center;
    gap: 6px;
}

/* Sidebar button icons - prominent but not overwhelming */
section[data-testid="stSidebar"] .stButton > button {
    font-size: 14px !important;
}

/* ===== Sidebar-Specific Component Overrides ===== */
/* Override main component spacing for ultra-compact sidebar */

section[data-testid="stSidebar"] .material-card,
section[data-testid="stSidebar"] .material-surface,
section[data-testid="stSidebar"] .info-card {
    padding: var(--md-spacing-sm, 8px) !important;       /* 8dp instead of 16dp */
    margin-bottom: var(--md-spacing-xs, 4px) !important; /* 4dp instead of 16dp */
}

section[data-testid="stSidebar"] .material-divider {
    margin: var(--md-spacing-xs, 4px) 0 !important;      /* 4dp instead of 16dp */
}

section[data-testid="stSidebar"] .section-header {
    margin-bottom: var(--md-spacing-sm, 8px) !important; /* 8dp instead of 16dp */
    gap: var(--md-spacing-xs, 4px) !important;           /* 4dp instead of 8dp */
}

section[data-testid="stSidebar"] .session-card {
    padding: var(--md-spacing-xs, 4px) var(--md-spacing-sm, 8px) !important;
    margin-bottom: var(--md-spacing-xs, 4px) !important;
}

/* Compact Streamlit component overrides for sidebar */
section[data-testid="stSidebar"] [data-testid="stExpander"] {
    border-width: 1px;
    margin-bottom: 0.375rem !important;    /* 6dp */
}

section[data-testid="stSidebar"] [data-testid="stMetric"] {
    padding: var(--md-spacing-sm, 8px) !important;       /* 8dp instead of 16dp */
}

/* ===== Split Screen Interview - Section Indicators ===== */
/* Horizontal section indicators at top of YAML panel */
.section-indicator-row {
    display: flex;
    gap: 8px;
    margin-bottom: 12px;
    flex-wrap: wrap;
}

.section-indicator {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 16px;
    font-size: 13px;
    background: var(--md-surface);
    border: 1px solid var(--md-border);
    transition: all var(--md-transition-fast);
}

.section-indicator.current {
    background: var(--md-primary);
    color: var(--md-on-primary);
    font-weight: 500;
    border-color: var(--md-primary);
}

.section-indicator.completed {
    background: var(--md-success);
    color: white;
    border-color: var(--md-success);
}

.section-indicator.skipped {
    background: var(--md-surface);
    color: var(--md-text-disabled);
    border-color: var(--md-border);
    opacity: 0.6;
}

/* Compact interview plan */
.interview-plan-compact {
    font-size: 14px;
    color: var(--md-text-secondary);
    padding: 4px 0 8px 0;
    margin: 0;
}
"""
