# terraform/envs/dev.tfvars
# Apply with: terraform apply -var-file=envs/dev.tfvars

environment          = "dev"
aws_region           = "us-west-2"
snowflake_account    = "example.us-west-2.aws"
snowflake_admin_user = "TF_ADMIN"
databricks_host      = "https://myworkspace-dev.cloud.databricks.com"

iceberg_bucket_name  = "iceberg-lakehouse-dev"
polaris_catalog_name = "ICEBERG_LAKEHOUSE_DEV"
polaris_principal_name = "databricks_svc"

# Fill in after workspace is provisioned:
# databricks_cross_account_role_arn = "arn:aws:iam::123456789012:role/databricks-cross-account"
# databricks_workspace_id           = "123456789012345"
