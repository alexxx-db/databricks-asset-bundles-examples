"""
Description Agent - Simplified UI with Genify Backend
AI-powered description generator for Databricks Unity Catalog tables and columns.
"""

import streamlit as st
import logging
from typing import Optional, Tuple
from config import config
from llm.client import get_main_llm_client
from auth.service_principal import get_sql_connection
from data.information_schema import get_columns_for_table
from state.services.profile_service import get_profile_service, ProfileService
from state import get_state_manager
from data.profile_formatter import format_profile_for_llm
from utils.sql_identifiers import (
    InvalidIdentifierError,
    validate_identifier,
    validate_qualified_table_name,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Description Agent",
    page_icon="✨",
    layout="wide"
)

# Custom CSS for blue color scheme
st.markdown("""
<style>
    /* Blue color scheme */
    :root {
        --primary-blue: #0066FF;
        --dark-navy: #001529;
        --medium-blue: #003D7A;
        --light-blue: #E6F0FF;
        --success-green: #28C76F;
    }
    
    /* Main app background */
    .stApp {
        background-color: #f5f7fa;
    }
    
    /* Headers */
    h1 {
        color: var(--dark-navy) !important;
        font-weight: 700;
    }
    
    h2 {
        color: var(--medium-blue) !important;
        font-weight: 600;
    }
    
    /* Buttons */
    .stButton > button {
        background-color: var(--primary-blue);
        color: white;
        border: none;
        border-radius: 6px;
        padding: 0.6rem 1.5rem;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    
    .stButton > button:hover {
        background-color: var(--medium-blue);
        box-shadow: 0 4px 8px rgba(0, 102, 255, 0.3);
    }
    
    /* Primary buttons */
    .stButton > button[kind="primary"] {
        background-color: var(--success-green);
    }
    
    .stButton > button[kind="primary"]:hover {
        background-color: #24B263;
    }
    
    /* Input fields */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        border: 2px solid #d1d5db;
        border-radius: 6px;
    }
    
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: var(--primary-blue);
        box-shadow: 0 0 0 3px rgba(0, 102, 255, 0.1);
    }
    
    /* Radio buttons */
    .stRadio > div {
        background-color: white;
        padding: 1rem;
        border-radius: 8px;
        border: 2px solid var(--primary-blue);
    }
    
    /* Code blocks */
    .stCodeBlock {
        background-color: var(--dark-navy) !important;
        border-radius: 6px;
    }
    
    /* Success messages */
    .stSuccess {
        background-color: rgba(40, 199, 111, 0.1);
        border-left: 4px solid var(--success-green);
    }
    
    /* Info messages */
    .stInfo {
        background-color: var(--light-blue);
        border-left: 4px solid var(--primary-blue);
    }
</style>
""", unsafe_allow_html=True)


def escape_sql_string(text: str) -> str:
    """Escape single quotes for SQL."""
    return text.replace("'", "''")


def generate_comment_sql(table_name: str, column_name: Optional[str], description: str) -> str:
    """
    Generate COMMENT ON TABLE/COLUMN SQL statement.
    
    Validates table_name and column_name to prevent identifier/SQL injection.
    
    Args:
        table_name: Fully qualified table name (catalog.schema.table)
        column_name: Column name (None for table comments)
        description: Description text
    
    Returns:
        SQL statement as string
    
    Raises:
        InvalidIdentifierError: If table_name or column_name fail validation.
    """
    parts = validate_qualified_table_name(table_name)
    table_ref = ".".join(parts)
    escaped_desc = escape_sql_string(description)

    if column_name:
        col = validate_identifier(column_name, "column")
        return f"COMMENT ON COLUMN {table_ref}.{col} IS '{escaped_desc}';"
    return f"COMMENT ON TABLE {table_ref} IS '{escaped_desc}';"


def execute_comment_sql(sql: str) -> Tuple[bool, Optional[str]]:
    """
    Execute COMMENT ON SQL statement.
    
    Args:
        sql: SQL statement to execute
    
    Returns:
        (success: bool, error: Optional[str])
    """
    try:
        connection = get_sql_connection()
        cursor = connection.cursor()
        cursor.execute(sql)
        connection.commit()
        cursor.close()
        return (True, None)
    except Exception as e:
        error_msg = f"Failed to execute COMMENT ON statement: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return (False, error_msg)


def generate_description_with_llm(
    table_name: str,
    information: str,
    column_name: Optional[str] = None,
    profile_data: Optional[str] = None
) -> Tuple[Optional[str], Optional[str]]:
    """
    Generate description using Genify's LLM client.
    
    Args:
        table_name: Table name
        information: User-provided information about the table/column
        column_name: Optional column name
        profile_data: Optional formatted profile data
    
    Returns:
        (result: Optional[str], error: Optional[str])
    """
    try:
        # Build the prompt
        prompt_parts = [f"Help me generate description for table: {table_name}"]
        
        if column_name:
            prompt_parts.append(f"Column: {column_name}")
        
        prompt_parts.append(f"\nUser information: {information}")
        
        # Add profile data if available
        if profile_data:
            prompt_parts.append(f"\n\nData Profile:\n{profile_data}")
        
        prompt_parts.append("\n\nPlease provide a clear, concise description that captures the purpose and key characteristics of this data asset. Format your response as:\n\nSample Improved Description:\n[Your description here]")
        
        prompt = "\n".join(prompt_parts)
        
        # Call LLM
        llm_client = get_main_llm_client()
        messages = [
            {"role": "system", "content": "You are an expert data catalog documentation assistant. Your task is to generate clear, comprehensive descriptions for database tables and columns based on the provided information and data profiles."},
            {"role": "user", "content": prompt}
        ]
        
        response = llm_client.chat(messages)
        
        return (response, None)
        
    except Exception as e:
        error_msg = f"LLM error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return (None, error_msg)


def review_description_with_llm(
    table_name: str,
    existing_description: str,
    column_name: Optional[str] = None,
    profile_data: Optional[str] = None
) -> Tuple[Optional[str], Optional[str]]:
    """
    Review existing description using Genify's LLM client.
    
    Args:
        table_name: Table name
        existing_description: Current description text
        column_name: Optional column name
        profile_data: Optional formatted profile data
    
    Returns:
        (result: Optional[str], error: Optional[str])
    """
    try:
        # Build the prompt
        prompt_parts = [f"Review my description for table: {table_name}"]
        
        if column_name:
            prompt_parts.append(f"Column: {column_name}")
        
        prompt_parts.append(f"\nExisting description: {existing_description}")
        
        # Add profile data if available
        if profile_data:
            prompt_parts.append(f"\n\nData Profile:\n{profile_data}")
        
        prompt_parts.append("\n\nPlease identify any weaknesses, missing details, or areas for improvement. Then provide a revised, improved description. Format your response as:\n\nIssues and Suggestions:\n[Your analysis here]\n\nSample Improved Description:\n[Your improved description here]")
        
        prompt = "\n".join(prompt_parts)
        
        # Call LLM
        llm_client = get_main_llm_client()
        messages = [
            {"role": "system", "content": "You are an expert data catalog documentation reviewer. Your task is to critically review existing descriptions and suggest concrete improvements to make them more clear, complete, and useful."},
            {"role": "user", "content": prompt}
        ]
        
        response = llm_client.chat(messages)
        
        return (response, None)
        
    except Exception as e:
        error_msg = f"LLM error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return (None, error_msg)


def get_profile_for_table(
    catalog: str,
    schema: str,
    table: str,
    profile_service: ProfileService
) -> Optional[str]:
    """
    Get or generate profile data for a table.
    
    Args:
        catalog: Catalog name
        schema: Schema name
        table: Table name
        profile_service: ProfileService instance
    
    Returns:
        Formatted profile string or None
    """
    try:
        # Check if profile exists
        existing_profile = profile_service.get_profile(catalog, schema, table)
        if existing_profile and 'summary' in existing_profile:
            return existing_profile['summary']
        
        # Generate new profile
        connection = get_sql_connection()
        columns = get_columns_for_table(connection, catalog, schema, table)
        
        success, profile_data, error = profile_service.generate_profile(
            connection, catalog, schema, table, columns
        )
        
        if success and profile_data and 'summary' in profile_data:
            return profile_data['summary']
        else:
            logger.warning(f"Failed to generate profile: {error}")
            return None
            
    except Exception as e:
        logger.error(f"Error getting profile: {e}", exc_info=True)
        return None


def main():
    """Main app logic."""
    
    # Initialize state
    state_manager = get_state_manager()
    profile_service = get_profile_service(state_manager)
    
    # Header
    st.title("✨ Description Agent")
    st.caption("AI-powered description generator for Unity Catalog tables and columns")
    
    st.divider()
    
    # Mode selector
    mode = st.radio(
        "Select Mode:",
        options=["Get me started", "Check my work"],
        horizontal=True,
        help="Choose 'Get me started' to draft initial descriptions, or 'Check my work' to review existing ones"
    )
    
    st.divider()
    
    # Get me started mode
    if mode == "Get me started":
        st.header("🚀 Get me started")
        st.caption("Generate initial descriptions from conceptual information")
        
        # Input fields
        table_name = st.text_input(
            "Table Name *",
            placeholder="catalog.schema.table_name",
            help="Enter the fully qualified table name (e.g., es_demo.test.orders)"
        )
        
        column_name = st.text_input(
            "Column Name (optional)",
            placeholder="column_name",
            help="Leave blank to generate a table-level description"
        )
        
        information = st.text_area(
            "Information about the table or column *",
            height=150,
            placeholder="Paste notes, examples, business logic, or any context about this data asset...",
            help="Provide conceptual or business context to help generate a meaningful description"
        )
        
        # Profile data checkbox
        use_profile = st.checkbox(
            "📊 Profile my data",
            value=False,
            help="Include automated data profiling statistics to enhance the description"
        )
        
        # Generate button
        if st.button("Generate Description", type="primary", use_container_width=True):
            # Validation
            if not table_name:
                st.error("❌ Table name is required")
            elif not information:
                st.error("❌ Information about the table or column is required")
            else:
                # Parse table name
                parts = table_name.split(".")
                if len(parts) != 3:
                    st.error("❌ Table name must be in format: catalog.schema.table")
                else:
                    catalog, schema, table = parts
                    
                    # Get profile data if requested
                    profile_data = None
                    if use_profile:
                        with st.spinner("📊 Profiling data..."):
                            profile_data = get_profile_for_table(catalog, schema, table, profile_service)
                            if profile_data:
                                st.success("✅ Data profile generated")
                            else:
                                st.warning("⚠️ Could not generate data profile, proceeding without it")
                    
                    # Generate description
                    with st.spinner("🤖 Generating description..."):
                        result, error = generate_description_with_llm(
                            table_name, information, column_name, profile_data
                        )
                    
                    if error:
                        st.error(f"❌ Error: {error}")
                    elif result:
                        # Escape $ signs for display
                        escaped_result = result.replace('$', r'\$')
                        
                        # Store in session state
                        st.session_state.generated_result = escaped_result
                        st.session_state.table_name = table_name
                        st.session_state.column_name = column_name
                        
                        # Extract description after "Sample Improved Description:"
                        extracted_desc = escaped_result
                        if "Sample Improved Description:" in escaped_result:
                            parts = escaped_result.split("Sample Improved Description:", 1)
                            if len(parts) > 1:
                                extracted_desc = parts[1].strip()
                        
                        st.session_state.extracted_description = extracted_desc
                        
                        st.success("✅ Description generated successfully!")
        
        # Display results if available
        if 'generated_result' in st.session_state:
            st.divider()
            st.subheader("📝 Generated Description")
            
            # Show full AI response
            with st.expander("View full AI response", expanded=False):
                st.markdown(st.session_state.generated_result)
            
            # Editable description
            edited_description = st.text_area(
                "Refined description:",
                value=st.session_state.get('extracted_description', ''),
                height=200,
                key="editable_description_start",
                help="This is auto-populated with the improved description. You can freely edit this text before applying it to your data asset"
            )
            
            # Apply to database
            st.divider()
            st.subheader("💾 Apply description to data asset")
            
            stored_table_name = st.session_state.get('table_name', '')
            stored_column_name = st.session_state.get('column_name', '')
            
            if stored_table_name:
                # Un-escape $ signs before applying to database
                description_for_db = edited_description.replace(r'\$', '$')
                
                # Extract only text after "Sample Improved Description:" if present
                description_to_apply = description_for_db
                if "Sample Improved Description:" in description_for_db:
                    parts = description_for_db.split("Sample Improved Description:", 1)
                    if len(parts) > 1:
                        description_to_apply = parts[1].strip()
                
                # Generate SQL
                comment_sql = generate_comment_sql(
                    stored_table_name,
                    stored_column_name if stored_column_name else None,
                    description_to_apply
                )
                
                # Show SQL
                st.code(comment_sql, language="sql")
                
                # Execute button
                if st.button("Apply description", type="primary"):
                    with st.spinner("Applying description..."):
                        success, error = execute_comment_sql(comment_sql)
                    
                    if success:
                        st.success("✅ Description applied successfully!")
                    else:
                        st.error(f"❌ Error executing SQL: {error}")
    
    # Check my work mode
    else:
        st.header("🔍 Check my work")
        st.caption("Review existing descriptions for quality and completeness")
        
        # Input fields
        table_name = st.text_input(
            "Table Name *",
            placeholder="catalog.schema.table_name",
            help="Enter the fully qualified table name",
            key="check_table_name"
        )
        
        column_name = st.text_input(
            "Column Name (optional)",
            placeholder="column_name",
            help="Leave blank to review a table-level description",
            key="check_column_name"
        )
        
        existing_description = st.text_area(
            "Existing Description *",
            height=150,
            placeholder="Paste the current description you want to review...",
            help="The description you want the AI to review and improve",
            key="check_existing_desc"
        )
        
        # Profile data checkbox
        use_profile = st.checkbox(
            "📊 Profile my data",
            value=False,
            help="Include automated data profiling statistics to enhance the review",
            key="check_use_profile"
        )
        
        # Review button
        if st.button("Review Description", type="primary", use_container_width=True, key="review_btn"):
            # Validation
            if not table_name:
                st.error("❌ Table name is required")
            elif not existing_description:
                st.error("❌ Existing description is required")
            else:
                # Parse table name
                parts = table_name.split(".")
                if len(parts) != 3:
                    st.error("❌ Table name must be in format: catalog.schema.table")
                else:
                    catalog, schema, table = parts
                    
                    # Get profile data if requested
                    profile_data = None
                    if use_profile:
                        with st.spinner("📊 Profiling data..."):
                            profile_data = get_profile_for_table(catalog, schema, table, profile_service)
                            if profile_data:
                                st.success("✅ Data profile generated")
                            else:
                                st.warning("⚠️ Could not generate data profile, proceeding without it")
                    
                    # Review description
                    with st.spinner("🤖 Reviewing description..."):
                        result, error = review_description_with_llm(
                            table_name, existing_description, column_name, profile_data
                        )
                    
                    if error:
                        st.error(f"❌ Error: {error}")
                    elif result:
                        # Escape $ signs for display
                        escaped_result = result.replace('$', r'\$')
                        
                        # Store in session state
                        st.session_state.review_result = escaped_result
                        st.session_state.check_table_name_stored = table_name
                        st.session_state.check_column_name_stored = column_name
                        
                        # Extract improved description
                        extracted_desc = escaped_result
                        if "Sample Improved Description:" in escaped_result:
                            parts = escaped_result.split("Sample Improved Description:", 1)
                            if len(parts) > 1:
                                extracted_desc = parts[1].strip()
                        
                        st.session_state.extracted_description_check = extracted_desc
                        
                        st.success("✅ Review completed!")
        
        # Display results if available
        if 'review_result' in st.session_state:
            st.divider()
            st.subheader("📋 Review Results")
            
            # Show full AI response
            with st.expander("View full AI review", expanded=True):
                st.markdown(st.session_state.review_result)
            
            # Editable revised description
            revised_description = st.text_area(
                "Refined description:",
                value=st.session_state.get('extracted_description_check', ''),
                height=200,
                key="editable_description_check",
                help="This is auto-populated with the improved description. You can freely edit this text before applying it to your data asset"
            )
            
            # Apply to database
            st.divider()
            st.subheader("💾 Apply description to data asset")
            
            stored_table_name = st.session_state.get('check_table_name_stored', '')
            stored_column_name = st.session_state.get('check_column_name_stored', '')
            
            if stored_table_name:
                # Un-escape $ signs before applying to database
                description_for_db = revised_description.replace(r'\$', '$')
                
                # Extract only text after "Sample Improved Description:" if present
                description_to_apply = description_for_db
                if "Sample Improved Description:" in description_for_db:
                    parts = description_for_db.split("Sample Improved Description:", 1)
                    if len(parts) > 1:
                        description_to_apply = parts[1].strip()
                
                # Generate SQL
                comment_sql = generate_comment_sql(
                    stored_table_name,
                    stored_column_name if stored_column_name else None,
                    description_to_apply
                )
                
                # Show SQL
                st.code(comment_sql, language="sql")
                
                # Execute button
                if st.button("Apply description", type="primary", key="apply_check_btn"):
                    with st.spinner("Applying description..."):
                        success, error = execute_comment_sql(comment_sql)
                    
                    if success:
                        st.success("✅ Description applied successfully!")
                    else:
                        st.error(f"❌ Error executing SQL: {error}")


if __name__ == "__main__":
    main()

