# terraform/envs/prod.tfvars
# Apply with: terraform apply -var-file=envs/prod.tfvars

environment          = "prod"
aws_region           = "us-west-2"
snowflake_account    = "example.us-west-2.aws"
snowflake_admin_user = "TF_ADMIN"
databricks_host      = "https://myworkspace.cloud.databricks.com"

iceberg_bucket_name    = "iceberg-lakehouse"
polaris_catalog_name   = "ICEBERG_LAKEHOUSE"
polaris_principal_name = "databricks_svc"

# databricks_cross_account_role_arn = "arn:aws:iam::123456789012:role/databricks-cross-account"
# databricks_workspace_id           = "123456789012345"
