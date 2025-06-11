# Terraform configuration for deploying Elsie on AWS
# Uses ECS Fargate, ECR, and CloudWatch

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Variables
variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "elsie"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-2"
}

variable "discord_token" {
  description = "Discord bot token"
  type        = string
  sensitive   = true
}

variable "gemma_api_key" {
  description = "Gemma API key"
  type        = string
  sensitive   = true
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

# Provider configuration
provider "aws" {
  region = var.aws_region
}

# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}

# VPC and Networking
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "${var.project_name}-vpc"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name        = "${var.project_name}-igw"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_subnet" "public" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${count.index + 1}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]

  map_public_ip_on_launch = true

  tags = {
    Name        = "${var.project_name}-public-subnet-${count.index + 1}"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${count.index + 10}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name        = "${var.project_name}-private-subnet-${count.index + 1}"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name        = "${var.project_name}-public-rt"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_route_table_association" "public" {
  count          = length(aws_subnet.public)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# Security Groups
resource "aws_security_group" "alb" {
  name_prefix = "${var.project_name}-alb"
  vpc_id      = aws_vpc.main.id

  ingress {
    description      = "HTTP from Internet"
    protocol         = "tcp"
    from_port        = 8000
    to_port          = 8000
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  egress {
    description = "To AI Agent"
    protocol    = "tcp"
    from_port   = 8000
    to_port     = 8000
    security_groups = [aws_security_group.ai_agent.id]
  }

  tags = {
    Name        = "${var.project_name}-alb-sg"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_security_group" "ai_agent" {
  name_prefix = "${var.project_name}-ai-agent"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "From ALB"
    protocol        = "tcp"
    from_port       = 8000
    to_port         = 8000
    security_groups = [aws_security_group.alb.id]
  }

  ingress {
    description     = "From Discord Bot"
    protocol        = "tcp"
    from_port       = 8000
    to_port         = 8000
    security_groups = [aws_security_group.discord_bot.id]
  }

  egress {
    description = "HTTPS to Internet"
    protocol    = "tcp"
    from_port   = 443
    to_port     = 443
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description     = "To PostgreSQL"
    protocol        = "tcp"
    from_port       = 5432
    to_port         = 5432
    security_groups = [aws_security_group.rds.id]
  }

  tags = {
    Name        = "${var.project_name}-ai-agent-sg"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_security_group" "discord_bot" {
  name_prefix = "${var.project_name}-discord-bot"
  vpc_id      = aws_vpc.main.id

  egress {
    description = "HTTPS to Internet"
    protocol    = "tcp"
    from_port   = 443
    to_port     = 443
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description     = "To AI Agent"
    protocol        = "tcp"
    from_port       = 8000
    to_port         = 8000
    security_groups = [aws_security_group.ai_agent.id]
  }

  tags = {
    Name        = "${var.project_name}-discord-bot-sg"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_security_group" "db_populator" {
  name_prefix = "${var.project_name}-db-populator"
  vpc_id      = aws_vpc.main.id

  egress {
    description = "HTTPS to Internet"
    protocol    = "tcp"
    from_port   = 443
    to_port     = 443
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description     = "To PostgreSQL"
    protocol        = "tcp"
    from_port       = 5432
    to_port         = 5432
    security_groups = [aws_security_group.rds.id]
  }

  tags = {
    Name        = "${var.project_name}-db-populator-sg"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_security_group" "rds" {
  name_prefix = "${var.project_name}-rds"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "From AI Agent"
    protocol        = "tcp"
    from_port       = 5432
    to_port         = 5432
    security_groups = [aws_security_group.ai_agent.id]
  }

  ingress {
    description     = "From DB Populator"
    protocol        = "tcp"
    from_port       = 5432
    to_port         = 5432
    security_groups = [aws_security_group.db_populator.id]
  }

  tags = {
    Name        = "${var.project_name}-rds-sg"
    Environment = var.environment
    Project     = var.project_name
  }
}

# ECR Repositories
resource "aws_ecr_repository" "ai_agent" {
  name                 = "${var.project_name}/ai-agent"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_ecr_lifecycle_policy" "ai_agent" {
  repository = aws_ecr_repository.ai_agent.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 images"
        selection = {
          tagStatus     = "untagged"
          countType     = "imageCountMoreThan"
          countNumber   = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

resource "aws_ecr_repository" "discord_bot" {
  name                 = "${var.project_name}/discord-bot"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_ecr_lifecycle_policy" "discord_bot" {
  repository = aws_ecr_repository.discord_bot.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 images"
        selection = {
          tagStatus     = "untagged"
          countType     = "imageCountMoreThan"
          countNumber   = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

resource "aws_ecr_repository" "db_populator" {
  name                 = "${var.project_name}/db-populator"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_ecr_lifecycle_policy" "db_populator" {
  repository = aws_ecr_repository.db_populator.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 images"
        selection = {
          tagStatus     = "untagged"
          countType     = "imageCountMoreThan"
          countNumber   = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# RDS Database
resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-db-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = {
    Name        = "${var.project_name}-db-subnet-group"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_db_instance" "postgres" {
  identifier     = "${var.project_name}-postgres"
  engine         = "postgres"
  engine_version = "15.4"
  instance_class = "db.t3.micro"

  allocated_storage     = 20
  max_allocated_storage = 100
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = "elsiebrain"
  username = "elsie"
  password = var.db_password

  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name

  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "Sun:04:00-Sun:05:00"

  skip_final_snapshot = true
  deletion_protection = false

  tags = {
    Name        = "${var.project_name}-postgres"
    Environment = var.environment
    Project     = var.project_name
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/${var.project_name}"
  retention_in_days = 30

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-cluster"

  configuration {
    execute_command_configuration {
      logging = "OVERRIDE"
      log_configuration {
        cloud_watch_log_group_name = aws_cloudwatch_log_group.ecs.name
      }
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# ECS Task Execution Role
resource "aws_iam_role" "ecs_task_execution_role" {
  name = "${var.project_name}-ecs-task-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_role_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# ECS Task Definitions
resource "aws_ecs_task_definition" "ai_agent" {
  family                   = "${var.project_name}-ai-agent"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn

  container_definitions = jsonencode([
    {
      name  = "ai-agent"
      image = "${aws_ecr_repository.ai_agent.repository_url}:latest"
      
      portMappings = [
        {
          containerPort = 8000
          protocol      = "tcp"
        }
      ]
      
      environment = [
        {
          name  = "PORT"
          value = "8000"
        },
        {
          name  = "DB_HOST"
          value = aws_db_instance.postgres.address
        },
        {
          name  = "DB_PORT"
          value = "5432"
        },
        {
          name  = "DB_NAME"
          value = "elsiebrain"
        },
        {
          name  = "DB_USER"
          value = "elsie"
        },
        {
          name  = "DB_PASSWORD"
          value = var.db_password
        },
        {
          name  = "GEMMA_API_KEY"
          value = var.gemma_api_key
        }
      ]
      
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ecs.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ai-agent"
        }
      }
      
      healthCheck = {
        command = ["CMD-SHELL", "curl -f http://localhost:8000/ || exit 1"]
        interval = 30
        timeout = 5
        retries = 3
        startPeriod = 60
      }
    }
  ])

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_ecs_task_definition" "discord_bot" {
  family                   = "${var.project_name}-discord-bot"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn

  container_definitions = jsonencode([
    {
      name  = "discord-bot"
      image = "${aws_ecr_repository.discord_bot.repository_url}:latest"
      
      environment = [
        {
          name  = "DISCORD_TOKEN"
          value = var.discord_token
        },
        {
          name  = "AI_AGENT_URL"
          value = "http://${aws_lb.main.dns_name}:8000"
        },
        {
          name  = "GEMMA_API_KEY"
          value = var.gemma_api_key
        }
      ]
      
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ecs.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "discord-bot"
        }
      }
    }
  ])

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# Application Load Balancer
resource "aws_lb" "main" {
  name               = "${var.project_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_lb_target_group" "ai_agent" {
  name        = "${var.project_name}-ai-agent-tg"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_lb_listener" "ai_agent" {
  load_balancer_arn = aws_lb.main.arn
  port              = "8000"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.ai_agent.arn
  }
}

# ECS Services
resource "aws_ecs_service" "ai_agent" {
  name            = "${var.project_name}-ai-agent"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.ai_agent.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    security_groups  = [aws_security_group.ai_agent.id]
    subnets          = aws_subnet.private[*].id
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.ai_agent.arn
    container_name   = "ai-agent"
    container_port   = 8000
  }

  depends_on = [aws_lb_listener.ai_agent]

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_ecs_service" "discord_bot" {
  name            = "${var.project_name}-discord-bot"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.discord_bot.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    security_groups  = [aws_security_group.discord_bot.id]
    subnets          = aws_subnet.private[*].id
    assign_public_ip = false
  }

  depends_on = [aws_ecs_service.ai_agent]

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# ECS Task Definition for DB Populator
resource "aws_ecs_task_definition" "db_populator" {
  family                   = "${var.project_name}-db-populator"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn

  container_definitions = jsonencode([
    {
      name  = "db-populator"
      image = "${aws_ecr_repository.db_populator.repository_url}:latest"
      
      environment = [
        {
          name  = "DB_HOST"
          value = aws_db_instance.postgres.address
        },
        {
          name  = "DB_PORT"
          value = "5432"
        },
        {
          name  = "DB_NAME"
          value = "elsiebrain"
        },
        {
          name  = "DB_USER"
          value = "elsie"
        },
        {
          name  = "DB_PASSWORD"
          value = var.db_password
        },
        {
          name  = "WIKI_UPDATE_INTERVAL"
          value = "3600"
        }
      ]
      
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ecs.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "db-populator"
        }
      }
    }
  ])

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# ECS Service for DB Populator
resource "aws_ecs_service" "db_populator" {
  name            = "${var.project_name}-db-populator"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.db_populator.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    security_groups  = [aws_security_group.db_populator.id]
    subnets          = aws_subnet.private[*].id
    assign_public_ip = false
  }

  depends_on = [aws_db_instance.postgres]

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# Outputs
output "ecr_ai_agent_repository_url" {
  description = "ECR repository URL for AI Agent"
  value       = aws_ecr_repository.ai_agent.repository_url
}

output "ecr_discord_bot_repository_url" {
  description = "ECR repository URL for Discord Bot"
  value       = aws_ecr_repository.discord_bot.repository_url
}

output "ecr_db_populator_repository_url" {
  description = "ECR repository URL for DB Populator"
  value       = aws_ecr_repository.db_populator.repository_url
}

output "load_balancer_dns_name" {
  description = "DNS name of the load balancer"
  value       = aws_lb.main.dns_name
}

output "database_endpoint" {
  description = "RDS instance endpoint"
  value       = aws_db_instance.postgres.endpoint
  sensitive   = true
} 