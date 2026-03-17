variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  description = "Deployment environment: dev | test | prod"
  type        = string
  validation {
    condition     = contains(["dev", "test", "prod"], var.environment)
    error_message = "environment must be dev, test, or prod"
  }
}

variable "snowflake_account" {
  description = "Snowflake account identifier (e.g. example.us-west-2.aws)"
  type        = string
}

variable "snowflake_admin_user" {
  description = "Snowflake admin user for Terraform operations"
  type        = string
  default     = "TF_ADMIN"
}

variable "databricks_host" {
  description = "Databricks workspace URL (e.g. https://myworkspace.cloud.databricks.com)"
  type        = string
}

variable "databricks_metastore_admin_group" {
  description = "Databricks group that will administer the UC metastore connection"
  type        = string
  default     = "metastore-admins"
}

variable "iceberg_bucket_name" {
  description = "S3 bucket name for shared Iceberg storage (must be globally unique)"
  type        = string
  default     = "iceberg-lakehouse"
}

variable "iceberg_bucket_prefix" {
  description = "S3 key prefix under which all Iceberg table data is written"
  type        = string
  default     = "iceberg"
}

variable "polaris_catalog_name" {
  description = "Name of the Snowflake Open Catalog (Polaris) catalog"
  type        = string
  default     = "ICEBERG_LAKEHOUSE"
}

variable "polaris_principal_name" {
  description = "Polaris service principal used by Databricks to authenticate"
  type        = string
  default     = "databricks_svc"
}

# Derived
locals {
  name_prefix = "iceberg-${var.environment}"

  # Snowflake needs STORAGE_AWS_ROLE_ARN before it can generate the
  # STORAGE_AWS_IAM_USER_ARN + STORAGE_AWS_EXTERNAL_ID trust policy values.
  # We use a two-phase approach: create the role with a placeholder trust,
  # then update it after Snowflake returns the actual values.
  snowflake_iam_role_name = "${local.name_prefix}-snowflake-storage"
  databricks_iam_role_name = "${local.name_prefix}-databricks-storage"
}
