terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    # This should be configured via CI/CD
    # bucket         = "my-tfstate-bucket"
    # key            = "global/s3/terraform.tfstate"
    # region         = "eu-west-2"
    # dynamodb_table = "terraform-locks"
  }
}

provider "aws" {
  region = "eu-west-2" # London
}

resource "random_string" "bucket_suffix" {
  length  = 8
  special = false
  upper   = false
}

variable "s3_bucket_prefix" {
  description = "Prefix for the S3 document storage bucket."
  type        = string
  default     = "my-app-documents-storage"
}

resource "aws_s3_bucket" "documents" {
  bucket = "${var.s3_bucket_prefix}-${random_string.bucket_suffix.result}"

  tags = {
    Name        = "Document Storage"
    Environment = "Dev"
    ManagedBy   = "Terraform"
  }
}
