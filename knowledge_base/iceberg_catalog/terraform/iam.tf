# ── Snowflake storage IAM role ────────────────────────────────────────────────
# Phase 1: create the role with a placeholder self-trust so Terraform can get
# its ARN.  After applying, run the Snowflake external volume SQL (which
# populates STORAGE_AWS_IAM_USER_ARN + STORAGE_AWS_EXTERNAL_ID), then come
# back and apply again — the aws_iam_role_policy_attachment updates
# automatically via the snowflake_storage_integration data source below.

resource "aws_iam_role" "snowflake_storage" {
  name = local.snowflake_iam_role_name

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "SnowflakeTrustPlaceholder"
      Effect = "Allow"
      Principal = {
        # Placeholder — replaced in Phase 2 with Snowflake's actual IAM user ARN.
        # Snowflake docs: https://docs.snowflake.com/en/user-guide/data-load-s3-config-storage-integration
        AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
      }
      Action = "sts:AssumeRole"
      Condition = {
        StringEquals = {
          "sts:ExternalId" = "ICEBERG_PLACEHOLDER"
        }
      }
    }]
  })

  description = "Assumed by Snowflake Open Catalog storage integration to access the shared Iceberg S3 bucket"
}

resource "aws_iam_role_policy" "snowflake_storage_s3" {
  name = "iceberg-s3-access"
  role = aws_iam_role.snowflake_storage.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "s3:GetObject", "s3:GetObjectVersion",
        "s3:PutObject", "s3:DeleteObject", "s3:DeleteObjectVersion",
        "s3:GetBucketLocation", "s3:ListBucket",
        "s3:GetBucketVersioning",
      ]
      Resource = [
        aws_s3_bucket.iceberg.arn,
        "${aws_s3_bucket.iceberg.arn}/*",
      ]
    }]
  })
}

# ── Databricks storage credential IAM role ────────────────────────────────────
# Unity Catalog uses an IAM role as its "storage credential" for external
# locations.  The trust policy allows Databricks' cross-account role to assume
# it (standard UC storage credential pattern).

data "aws_caller_identity" "current" {}

# Databricks cross-account role ARN — find in workspace Settings → Cloud resources
variable "databricks_cross_account_role_arn" {
  description = "Databricks cross-account IAM role ARN (from workspace cloud resources settings)"
  type        = string
}

resource "aws_iam_role" "databricks_storage" {
  name = local.databricks_iam_role_name

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "DatabricksUCStorageCredential"
      Effect = "Allow"
      Principal = {
        AWS = var.databricks_cross_account_role_arn
      }
      Action = "sts:AssumeRole"
      Condition = {
        StringEquals = {
          # UC uses the workspace ID as external ID — find in workspace Settings
          "sts:ExternalId" = var.databricks_workspace_id
        }
      }
    }]
  })

  description = "Assumed by Databricks Unity Catalog to access the shared Iceberg S3 bucket"
}

variable "databricks_workspace_id" {
  description = "Databricks workspace ID (numeric, used as ExternalId in storage credential trust)"
  type        = string
}

resource "aws_iam_role_policy" "databricks_storage_s3" {
  name = "iceberg-s3-access"
  role = aws_iam_role.databricks_storage.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject", "s3:GetObjectVersion",
          "s3:PutObject", "s3:DeleteObject", "s3:DeleteObjectVersion",
          "s3:GetBucketLocation", "s3:ListBucket",
          "s3:GetBucketVersioning", "s3:ListBucketVersions",
          "s3:ListBucketMultipartUploads", "s3:AbortMultipartUpload",
        ]
        Resource = [
          aws_s3_bucket.iceberg.arn,
          "${aws_s3_bucket.iceberg.arn}/*",
        ]
      },
      # UC also needs sts:GetCallerIdentity to validate the credential
      {
        Effect   = "Allow"
        Action   = ["sts:GetCallerIdentity"]
        Resource = "*"
      },
    ]
  })
}

# ── Databricks Unity Catalog resources ────────────────────────────────────────

resource "databricks_storage_credential" "iceberg" {
  name = "iceberg-${var.environment}"

  aws_iam_role {
    role_arn = aws_iam_role.databricks_storage.arn
  }

  comment = "Storage credential for Shared Iceberg S3 bucket (${var.environment})"

  depends_on = [aws_iam_role_policy.databricks_storage_s3]
}

resource "databricks_external_location" "iceberg_root" {
  name            = "iceberg-root-${var.environment}"
  url             = "s3://${aws_s3_bucket.iceberg.bucket}/${var.iceberg_bucket_prefix}"
  credential_name = databricks_storage_credential.iceberg.name
  comment         = "Root external location for Shared Iceberg tables"
}
