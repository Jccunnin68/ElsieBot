# Deployment Guide for Elsie

This guide will help you deploy Elsie to AWS EC2 using the free tier.

## Prerequisites

1. AWS Account
2. AWS CLI installed and configured
3. GitHub repository with the Elsie codebase
4. Discord Bot Token
5. OpenAI API Key

## Setup Steps

### 1. Create EC2 Instance

1. Navigate to AWS CloudFormation console
2. Create a new stack using the `aws/cloudformation.yml` template
3. Provide your EC2 key pair name
4. Wait for the stack creation to complete
5. Note the EC2 instance's public DNS name from the stack outputs

### 2. Configure GitHub Secrets

Add the following secrets to your GitHub repository:

- `AWS_ACCESS_KEY_ID`: Your AWS access key
- `AWS_SECRET_ACCESS_KEY`: Your AWS secret key
- `EC2_HOST`: The EC2 instance's public DNS name
- `EC2_USERNAME`: ec2-user
- `EC2_SSH_KEY`: Your EC2 private key
- `DISCORD_TOKEN`: Your Discord bot token
- `OPENAI_API_KEY`: Your OpenAI API key

### 3. Create ECR Repositories

Run the following AWS CLI commands:

```bash
aws ecr create-repository --repository-name elsie-ai-agent
aws ecr create-repository --repository-name elsie-discord-bot
```

### 4. Deploy

1. Push your code to the main branch
2. GitHub Actions will automatically:
   - Build the Docker images
   - Push them to ECR
   - Deploy to EC2

### 5. Verify Deployment

1. SSH into your EC2 instance:
   ```bash
   ssh ec2-user@<EC2_PUBLIC_DNS>
   ```

2. Check the running containers:
   ```bash
   docker ps
   ```

3. Check the logs:
   ```bash
   docker-compose logs -f
   ```

## Monitoring

- CloudWatch Logs are automatically configured
- Health checks are implemented for both services
- The AI agent exposes metrics on port 8000

## Troubleshooting

1. If containers fail to start:
   ```bash
   docker-compose logs -f
   ```

2. If ECR authentication fails:
   ```bash
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com
   ```

3. If GitHub Actions fails:
   - Check the Actions tab in your GitHub repository
   - Verify all secrets are properly configured
   - Check AWS IAM permissions 