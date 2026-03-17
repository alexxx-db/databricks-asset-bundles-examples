terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.40"
    }
    snowflake = {
      source  = "Snowflake-Labs/snowflake"
      version = "~> 0.89"
    }
    databricks = {
      source  = "databricks/databricks"
      version = "~> 1.40"
    }
  }

  # S3 backend for Terraform state — adjust bucket/key/region per env
  backend "s3" {
    bucket         = "iceberg-terraform-state"
    key            = "iceberg-catalog/terraform.tfstate"
    region         = "us-west-2"
    encrypt        = true
    dynamodb_table = "iceberg-terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "iceberg-catalog"
      Environment = var.environment
      ManagedBy   = "terraform"
      Team        = "platform"
    }
  }
}

provider "snowflake" {
  account  = var.snowflake_account
  username = var.snowflake_admin_user
  # Password/key via SNOWFLAKE_PASSWORD env var or ~/.snowflake/config.toml
  role = "ACCOUNTADMIN"
}

provider "databricks" {
  host = var.databricks_host
  # Auth via DATABRICKS_TOKEN env var or ~/.databrickscfg
}
