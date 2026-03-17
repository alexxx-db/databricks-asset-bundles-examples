# ── S3 bucket ─────────────────────────────────────────────────────────────────
# This is the *shared* Iceberg storage layer.  Both Snowflake (via its IAM role)
# and Databricks (via its instance profile / Unity Catalog storage credential)
# land Parquet data files + Iceberg metadata.json / manifest files here.
# Polaris (Snowflake Open Catalog) also reads/writes catalog metadata here.

resource "aws_s3_bucket" "iceberg" {
  bucket = var.iceberg_bucket_name
}

resource "aws_s3_bucket_versioning" "iceberg" {
  bucket = aws_s3_bucket.iceberg.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "iceberg" {
  bucket = aws_s3_bucket.iceberg.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "iceberg" {
  bucket                  = aws_s3_bucket.iceberg.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle: Iceberg manifests and metadata accumulate; clean up old snapshots.
# Polaris itself handles expiry of snapshot entries, but the S3 objects need
# separate lifecycle rules to prevent unbounded storage growth.
resource "aws_s3_bucket_lifecycle_configuration" "iceberg" {
  bucket = aws_s3_bucket.iceberg.id

  rule {
    id     = "expire-old-iceberg-metadata"
    status = "Enabled"
    filter {
      prefix = "${var.iceberg_bucket_prefix}/metadata/"
    }
    # After 90 days, old metadata.json versions can be removed.
    # Polaris expire_snapshots must run before this to avoid orphaned refs.
    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }

  rule {
    id     = "abort-incomplete-multipart"
    status = "Enabled"
    filter { prefix = "" }
    abort_incomplete_multipart_upload { days_after_initiation = 7 }
  }
}

# ── Bucket policy ──────────────────────────────────────────────────────────────
# Grants both the Snowflake IAM role and the Databricks IAM role access.
# The Snowflake trust handshake uses an ExternalId to prevent confused-deputy.
resource "aws_s3_bucket_policy" "iceberg" {
  bucket = aws_s3_bucket.iceberg.id
  policy = data.aws_iam_policy_document.iceberg_bucket.json
}

data "aws_iam_policy_document" "iceberg_bucket" {
  # Snowflake storage role
  statement {
    sid    = "SnowflakeStorageIntegration"
    effect = "Allow"
    principals {
      type        = "AWS"
      identifiers = [aws_iam_role.snowflake_storage.arn]
    }
    actions = [
      "s3:GetObject", "s3:GetObjectVersion",
      "s3:PutObject", "s3:DeleteObject", "s3:DeleteObjectVersion",
      "s3:GetBucketLocation", "s3:ListBucket",
      "s3:GetBucketVersioning",
    ]
    resources = [
      aws_s3_bucket.iceberg.arn,
      "${aws_s3_bucket.iceberg.arn}/*",
    ]
  }

  # Databricks storage credential role
  statement {
    sid    = "DatabricksStorageCredential"
    effect = "Allow"
    principals {
      type        = "AWS"
      identifiers = [aws_iam_role.databricks_storage.arn]
    }
    actions = [
      "s3:GetObject", "s3:GetObjectVersion",
      "s3:PutObject", "s3:DeleteObject", "s3:DeleteObjectVersion",
      "s3:GetBucketLocation", "s3:ListBucket",
      "s3:GetBucketVersioning", "s3:ListBucketVersions",
      "s3:ListBucketMultipartUploads", "s3:AbortMultipartUpload",
    ]
    resources = [
      aws_s3_bucket.iceberg.arn,
      "${aws_s3_bucket.iceberg.arn}/*",
    ]
  }

  # Deny any non-TLS access
  statement {
    sid    = "DenyNonTLS"
    effect = "Deny"
    principals { type = "*"; identifiers = ["*"] }
    actions   = ["s3:*"]
    resources = [aws_s3_bucket.iceberg.arn, "${aws_s3_bucket.iceberg.arn}/*"]
    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}
