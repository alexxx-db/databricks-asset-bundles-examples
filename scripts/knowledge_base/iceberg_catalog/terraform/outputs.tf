output "iceberg_bucket_name" {
  description = "S3 bucket name for shared Iceberg storage"
  value       = aws_s3_bucket.iceberg.bucket
}

output "iceberg_bucket_arn" {
  description = "ARN of the S3 bucket"
  value       = aws_s3_bucket.iceberg.arn
}

output "snowflake_storage_role_arn" {
  description = "IAM role ARN to paste into the Snowflake STORAGE INTEGRATION / EXTERNAL VOLUME"
  value       = aws_iam_role.snowflake_storage.arn
}

output "databricks_storage_role_arn" {
  description = "IAM role ARN used by the Databricks storage credential"
  value       = aws_iam_role.databricks_storage.arn
}

output "databricks_external_location_name" {
  description = "UC external location name — use as the base for CREATE CATALOG ... LOCATION"
  value       = databricks_external_location.iceberg_root.name
}

output "databricks_storage_credential_name" {
  description = "UC storage credential name"
  value       = databricks_storage_credential.iceberg.name
}

# Printed after apply so the operator knows what to paste into Phase 2 Snowflake SQL
output "phase2_snowflake_sql_hint" {
  description = "Reminder: after apply, run 'DESC INTEGRATION iceberg_storage_int;' in Snowflake to get STORAGE_AWS_IAM_USER_ARN + STORAGE_AWS_EXTERNAL_ID, then update the Snowflake IAM role trust policy."
  value       = <<-EOT
    NEXT STEPS (Snowflake storage integration trust handshake):
      1. Run snowflake/01_storage_integration.sql in your Snowflake account.
      2. DESC INTEGRATION ICEBERG_STORAGE_INT;
      3. Copy STORAGE_AWS_IAM_USER_ARN and STORAGE_AWS_EXTERNAL_ID.
      4. Update aws_iam_role.snowflake_storage assume_role_policy with real values.
      5. terraform apply again to update the trust policy.
      6. Run snowflake/02_external_volume.sql and verify with DESCRIBE EXTERNAL VOLUME.
  EOT
}
