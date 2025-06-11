# Deployment Workflows

This directory contains GitHub Actions workflows for deploying Elsie to multiple cloud platforms using Terraform. **All deployment workflows are currently INACTIVE by default** for safety.

## Available Workflows

- **`deploy-aws.yml`** - Deploy to Amazon Web Services (ECS Fargate)
- **`deploy-gcp.yml`** - Deploy to Google Cloud Platform (Cloud Run)  
- **`deploy-azure.yml`** - Deploy to Microsoft Azure (Container Instances)

## Activation

To activate any deployment workflow, you need to:

1. Set the corresponding environment variable in your repository:
   - AWS: `ENABLE_AWS_DEPLOYMENT=true`
   - GCP: `ENABLE_GCP_DEPLOYMENT=true`
   - Azure: `ENABLE_AZURE_DEPLOYMENT=true`

2. Configure the required secrets (see sections below)

3. Optionally set up environment protection rules for production deployments

## Required Secrets

### Common Secrets (All Platforms)
```
DISCORD_TOKEN          # Discord bot token
GEMMA_API_KEY         # Gemma API key for AI functionality  
DB_PASSWORD           # Database password
```

### AWS Specific Secrets
```
AWS_ACCESS_KEY_ID            # AWS access key
AWS_SECRET_ACCESS_KEY        # AWS secret key
AWS_TERRAFORM_BUCKET         # S3 bucket for Terraform state
```

### GCP Specific Secrets
```
GCP_SA_KEY                   # Service account JSON key
GCP_TERRAFORM_BUCKET         # GCS bucket for Terraform state
```

### Azure Specific Secrets
```
AZURE_CREDENTIALS           # Service principal credentials (JSON)
AZURE_TERRAFORM_RG          # Resource group for Terraform state
AZURE_TERRAFORM_STORAGE     # Storage account for Terraform state
```

## Usage

All workflows are triggered manually via `workflow_dispatch` with the following inputs:

- **Environment**: `staging` or `production`
- **Terraform Action**: `plan`, `apply`, or `destroy`
- **GCP Project ID** (GCP only): The Google Cloud project ID to deploy to

### Example: Running AWS Deployment

1. Go to Actions tab in GitHub
2. Select "Deploy Elsie to AWS (Terraform)"
3. Click "Run workflow"
4. Choose environment and action
5. Click "Run workflow"

## Infrastructure Details

### AWS (ECS Fargate)
- **Services**: ECS cluster with Fargate tasks
- **Database**: RDS PostgreSQL with private subnets
- **Networking**: VPC with public/private subnets, ALB
- **Security**: Minimal IAM roles, security groups
- **Monitoring**: CloudWatch Logs

### GCP (Cloud Run)
- **Services**: Cloud Run containers with auto-scaling
- **Database**: Cloud SQL PostgreSQL with private IP
- **Networking**: VPC with private Google access
- **Security**: Service accounts, firewall rules
- **Monitoring**: Cloud Logging

### Azure (Container Instances)
- **Services**: Container groups with auto-restart
- **Database**: PostgreSQL Flexible Server with private endpoint
- **Networking**: Virtual network with NSGs, NAT Gateway
- **Security**: Managed identity, Key Vault for secrets
- **Monitoring**: Log Analytics

## Environment Protection

Consider setting up environment protection rules in GitHub for production:

1. Go to Settings → Environments
2. Create environments: `aws-production`, `gcp-production`, `azure-production`
3. Add protection rules:
   - Required reviewers
   - Wait timer
   - Restrict to main branch

## Terraform State Management

Each platform requires a backend for Terraform state:

- **AWS**: S3 bucket with versioning enabled
- **GCP**: GCS bucket with versioning enabled  
- **Azure**: Storage account with blob container

Make sure these are created before running deployments.

## Safety Features

- Manual trigger only (no automatic deployments)
- Environment variable gates to prevent accidental activation
- Terraform plan step shows changes before apply
- Separate staging/production environments
- Comprehensive validation and error handling 