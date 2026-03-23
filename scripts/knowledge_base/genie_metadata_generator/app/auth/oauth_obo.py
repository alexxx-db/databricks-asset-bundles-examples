"""
OAuth On-Behalf-Of (OBO) authentication for Databricks.
This is a placeholder for future implementation.

When ready to switch:
1. Implement OAuth flow using databricks-sdk
2. Update this function to use user token
3. Change app.yaml: config.auth.mode = "oauth_obo"
4. No other code changes needed - same interface as service_principal.py
"""


def get_connection():
    """
    Future: Implement OAuth on-behalf-of authentication.

    This will allow the app to query data as the logged-in user,
    respecting their Unity Catalog permissions.

    Migration path:
    1. Implement OAuth flow using databricks-sdk
    2. Use user's access token for authentication
    3. Update app.yaml to enable OBO mode
    4. Test with user-specific permissions

    Returns:
        Connection object (not yet implemented)

    Raises:
        NotImplementedError: OBO auth not yet available
    """
    raise NotImplementedError(
        "OAuth on-behalf-of (OBO) authentication not yet implemented.\n"
        "Please use service_principal authentication mode in app.yaml."
    )
