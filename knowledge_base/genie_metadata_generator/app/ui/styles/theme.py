"""
Material Design Theme CSS for Genify.
Implements Material Design principles with Roboto typography and Material color palette.
"""

THEME_CSS = """
/* ============================================
   MATERIAL DESIGN THEME
   ============================================ */

/* Import Roboto font */
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');

:root {
    /* Material Design Primary Colors */
    --md-primary: #1976D2;
    --md-primary-light: #BBDEFB;
    --md-primary-dark: #0D47A1;
    --md-on-primary: #FFFFFF;
    
    /* Material Secondary/Surface Colors */
    --md-secondary: #424242;
    --md-surface: #FFFFFF;
    --md-background: #FAFAFA;
    --md-on-surface: rgba(0, 0, 0, 0.87);
    
    /* Material Status Colors */
    --md-error: #D32F2F;
    --md-success: #388E3C;
    --md-warning: #F57C00;
    --md-info: #1976D2;
    
    /* Material Chip/Tag Colors */
    --md-chip-bg: rgba(25, 118, 210, 0.1);
    --md-chip-text: #1976D2;
    
    /* Material Text Colors */
    --md-text-primary: rgba(0, 0, 0, 0.87);
    --md-text-secondary: rgba(0, 0, 0, 0.60);
    --md-text-disabled: rgba(0, 0, 0, 0.38);
    --md-text-hint: rgba(0, 0, 0, 0.38);
    
    /* Material Dividers & Borders */
    --md-divider: rgba(0, 0, 0, 0.12);
    --md-border: rgba(0, 0, 0, 0.12);
    
    /* Typography - Roboto */
    --md-font-family: 'Roboto', -apple-system, BlinkMacSystemFont, sans-serif;
    
    /* Material Spacing (8px grid) */
    --md-spacing-xs: 4px;
    --md-spacing-sm: 8px;
    --md-spacing-md: 16px;
    --md-spacing-lg: 24px;
    --md-spacing-xl: 32px;
    
    /* Material Border Radius */
    --md-radius-sm: 4px;
    --md-radius-md: 8px;
    --md-radius-lg: 12px;
    
    /* Material Icon Sizes */
    --md-icon-size-sm: 18px;
    --md-icon-size-md: 22px;
    --md-icon-size-lg: 28px;
    
    /* Material Elevation Shadows */
    --md-shadow-1: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);
    --md-shadow-2: 0 3px 6px rgba(0,0,0,0.16), 0 3px 6px rgba(0,0,0,0.23);
    --md-shadow-3: 0 10px 20px rgba(0,0,0,0.19), 0 6px 6px rgba(0,0,0,0.23);
    
    /* Hover/Interaction Colors */
    --md-hover-overlay: rgba(25, 118, 210, 0.08);
    
    /* Transitions */
    --md-transition-fast: 0.15s cubic-bezier(0.4, 0, 0.2, 1);
    --md-transition-normal: 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    
    /* Legacy variable mapping for compatibility */
    --color-primary: var(--md-primary);
    --color-primary-light: var(--md-primary-light);
    --color-primary-dark: var(--md-primary-dark);
    --color-text-muted: var(--md-text-secondary);
    --color-border: var(--md-border);
    --color-bg-subtle: var(--md-background);
    --spacing-xs: var(--md-spacing-xs);
    --spacing-sm: var(--md-spacing-sm);
    --spacing-md: var(--md-spacing-md);
    --spacing-lg: var(--md-spacing-lg);
    --radius-sm: var(--md-radius-sm);
    --radius-md: var(--md-radius-md);
    --transition-fast: var(--md-transition-fast);
}

/* Apply Roboto font to main content areas only */
html, body {
    font-family: var(--md-font-family);
}

/* Target specific Streamlit components for font */
.stMarkdown, .stText, .stCaption, .stButton button {
    font-family: var(--md-font-family);
}

/* Material Typography Scale - Improved hierarchy */
.stMarkdown h1 {
    font-size: 28px;
    font-weight: 500;
    letter-spacing: 0;
    line-height: 1.3;
}

.stMarkdown h2 {
    font-size: 22px;
    font-weight: 500;
    letter-spacing: 0.15px;
    line-height: 1.4;
}

.stMarkdown h3 {
    font-size: 18px;
    font-weight: 500;
    letter-spacing: 0.15px;
    line-height: 1.5;
}

/* Material body text - Only in markdown */
.stMarkdown p {
    font-size: 14px;
    font-weight: 400;
    letter-spacing: 0.25px;
    line-height: 1.5;
}

/* ===== Compact Typography for Sidebar ===== */
/* Ultra-tight line heights for maximum space efficiency */

section[data-testid="stSidebar"] .stMarkdown h3 {
    line-height: 1.3 !important;
    margin-top: 0.375rem !important;     /* 6dp */
    margin-bottom: 0.25rem !important;   /* 4dp */
}

section[data-testid="stSidebar"] .stMarkdown p {
    line-height: 1.3 !important;         /* Tighter than 1.5 */
    margin-top: 0 !important;
    margin-bottom: 0.25rem !important;   /* 4dp */
}

section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] div {
    line-height: 1.3 !important;
}

/* ============================================
   DARK MODE SUPPORT
   ============================================
   Dark mode is supported via two methods:
   1. System preference (@media prefers-color-scheme: dark)
   2. Streamlit theme attribute ([data-theme="dark"])
   
   Both methods update CSS variables to ensure consistent
   theming across all components. Colors are adjusted for
   better contrast and readability in dark environments.
   ============================================ */

/* Dark mode - System preference */
@media (prefers-color-scheme: dark) {
    :root {
        --md-primary: #90CAF9;
        --md-primary-light: #BBDEFB;
        --md-primary-dark: #42A5F5;
        --md-on-primary: #000000;
        
        --md-secondary: #B0BEC5;
        --md-surface: #1E1E1E;
        --md-background: #121212;
        --md-on-surface: rgba(255, 255, 255, 0.87);
        
        /* Status colors - slightly adjusted for dark mode */
        --md-error: #EF5350;
        --md-success: #66BB6A;
        --md-warning: #FFA726;
        --md-info: #90CAF9;
        
        --md-text-primary: rgba(255, 255, 255, 0.87);
        --md-text-secondary: rgba(255, 255, 255, 0.60);
        --md-text-disabled: rgba(255, 255, 255, 0.38);
        
        --md-divider: rgba(255, 255, 255, 0.12);
        --md-border: rgba(255, 255, 255, 0.12);
        
        /* Dark mode chip colors */
        --md-chip-bg: rgba(144, 202, 249, 0.16);
        --md-chip-text: #90CAF9;
        
        /* Dark mode hover overlay */
        --md-hover-overlay: rgba(144, 202, 249, 0.12);
        
        /* Dark mode shadows - lighter for better visibility */
        --md-shadow-1: 0 1px 3px rgba(0,0,0,0.3), 0 1px 2px rgba(0,0,0,0.4);
        --md-shadow-2: 0 3px 6px rgba(0,0,0,0.4), 0 3px 6px rgba(0,0,0,0.5);
        --md-shadow-3: 0 10px 20px rgba(0,0,0,0.5), 0 6px 6px rgba(0,0,0,0.6);
        
        --color-text-muted: var(--md-text-secondary);
        --color-border: var(--md-border);
        --color-bg-subtle: var(--md-surface);
    }
}

/* Dark mode - Streamlit theme attribute */
[data-testid="stAppViewContainer"][data-theme="dark"] {
    --md-primary: #90CAF9;
    --md-primary-light: #BBDEFB;
    --md-primary-dark: #42A5F5;
    --md-on-primary: #000000;
    
    --md-secondary: #B0BEC5;
    --md-surface: #1E1E1E;
    --md-background: #121212;
    --md-on-surface: rgba(255, 255, 255, 0.87);
    
    /* Status colors - slightly adjusted for dark mode */
    --md-error: #EF5350;
    --md-success: #66BB6A;
    --md-warning: #FFA726;
    --md-info: #90CAF9;
    
    --md-text-primary: rgba(255, 255, 255, 0.87);
    --md-text-secondary: rgba(255, 255, 255, 0.60);
    --md-text-disabled: rgba(255, 255, 255, 0.38);
    
    --md-divider: rgba(255, 255, 255, 0.12);
    --md-border: rgba(255, 255, 255, 0.12);
    
    /* Dark mode chip colors */
    --md-chip-bg: rgba(144, 202, 249, 0.16);
    --md-chip-text: #90CAF9;
    
    /* Dark mode hover overlay */
    --md-hover-overlay: rgba(144, 202, 249, 0.12);
    
    /* Dark mode shadows - lighter for better visibility */
    --md-shadow-1: 0 1px 3px rgba(0,0,0,0.3), 0 1px 2px rgba(0,0,0,0.4);
    --md-shadow-2: 0 3px 6px rgba(0,0,0,0.4), 0 3px 6px rgba(0,0,0,0.5);
    --md-shadow-3: 0 10px 20px rgba(0,0,0,0.5), 0 6px 6px rgba(0,0,0,0.6);
    
    --color-text-muted: var(--md-text-secondary);
    --color-border: var(--md-border);
    --color-bg-subtle: var(--md-surface);
}
"""
