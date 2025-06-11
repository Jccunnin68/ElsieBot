# Terraform configuration for deploying Elsie on Google Cloud Platform
# Uses Cloud Run, Container Registry, and Cloud Logging

terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
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

variable "gcp_project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "gcp_region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
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
provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

# Enable required APIs
resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "sqladmin.googleapis.com",
    "secretmanager.googleapis.com",
    "logging.googleapis.com",
    "containerregistry.googleapis.com"
  ])

  project = var.gcp_project_id
  service = each.value

  disable_on_destroy = false
}

# Secret Manager secrets
resource "google_secret_manager_secret" "discord_token" {
  secret_id = "${var.project_name}-discord-token"

  labels = {
    environment = var.environment
    project     = var.project_name
  }

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "discord_token" {
  secret      = google_secret_manager_secret.discord_token.id
  secret_data = var.discord_token
}

resource "google_secret_manager_secret" "gemma_api_key" {
  secret_id = "${var.project_name}-gemma-api-key"

  labels = {
    environment = var.environment
    project     = var.project_name
  }

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "gemma_api_key" {
  secret      = google_secret_manager_secret.gemma_api_key.id
  secret_data = var.gemma_api_key
}

resource "google_secret_manager_secret" "db_password" {
  secret_id = "${var.project_name}-db-password"

  labels = {
    environment = var.environment
    project     = var.project_name
  }

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "db_password" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = var.db_password
}

# Cloud SQL Database
resource "google_sql_database_instance" "postgres" {
  name             = "${var.project_name}-postgres"
  database_version = "POSTGRES_15"
  region           = var.gcp_region

  settings {
    tier                        = "db-f1-micro"
    deletion_protection_enabled = false

    backup_configuration {
      enabled    = true
      start_time = "03:00"
      location   = var.gcp_region

      backup_retention_settings {
        retained_backups = 7
        retention_unit   = "COUNT"
      }
    }

    maintenance_window {
      day  = 7
      hour = 4
    }

    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.main.id
    }

    database_flags {
      name  = "log_statement"
      value = "all"
    }
  }

  depends_on = [
    google_project_service.apis,
    google_service_networking_connection.private_vpc_connection
  ]
}

resource "google_sql_database" "elsiebrain" {
  name     = "elsiebrain"
  instance = google_sql_database_instance.postgres.name
}

resource "google_sql_user" "elsie" {
  name     = "elsie"
  instance = google_sql_database_instance.postgres.name
  password = var.db_password
}

# VPC Network
resource "google_compute_network" "main" {
  name                    = "${var.project_name}-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "main" {
  name          = "${var.project_name}-subnet"
  ip_cidr_range = "10.0.0.0/24"
  region        = var.gcp_region
  network       = google_compute_network.main.id
}

# Dedicated subnet for VPC Connector
resource "google_compute_subnetwork" "connector" {
  name          = "${var.project_name}-connector-subnet"
  ip_cidr_range = "10.1.0.0/28"
  region        = var.gcp_region
  network       = google_compute_network.main.id
}

# VPC Connector for Cloud Run private networking
resource "google_vpc_access_connector" "main" {
  name          = "${var.project_name}-connector"
  region        = var.gcp_region
  network       = google_compute_network.main.name
  ip_cidr_range = "10.1.0.0/28"
  
  depends_on = [
    google_project_service.apis,
    google_compute_subnetwork.connector
  ]
}

# Firewall Rules
resource "google_compute_firewall" "allow_internal" {
  name    = "${var.project_name}-allow-internal"
  network = google_compute_network.main.name

  allow {
    protocol = "tcp"
    ports    = ["8000"]
  }

  source_ranges = ["10.0.0.0/16", "10.1.0.0/28"]
  target_tags   = ["${var.project_name}-internal"]
}

resource "google_compute_firewall" "allow_health_check" {
  name    = "${var.project_name}-allow-health-check"
  network = google_compute_network.main.name

  allow {
    protocol = "tcp"
    ports    = ["8000"]
  }

  source_ranges = ["130.211.0.0/22", "35.191.0.0/16"]  # Google health check ranges
  target_tags   = ["${var.project_name}-ai-agent"]
}

resource "google_compute_firewall" "deny_all_ingress" {
  name    = "${var.project_name}-deny-all-ingress"
  network = google_compute_network.main.name
  priority = 65534

  deny {
    protocol = "all"
  }

  source_ranges = ["0.0.0.0/0"]
}

# VPC Peering for Cloud SQL
resource "google_compute_global_address" "private_ip_address" {
  name          = "${var.project_name}-private-ip"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.main.id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.main.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_address.name]
}

# Service Account for Cloud Run
resource "google_service_account" "cloud_run_sa" {
  account_id   = "${var.project_name}-cloud-run"
  display_name = "Elsie Cloud Run Service Account"
}

resource "google_project_iam_member" "cloud_run_sql_client" {
  project = var.gcp_project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

resource "google_project_iam_member" "cloud_run_secret_accessor" {
  project = var.gcp_project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# Cloud Run Services
resource "google_cloud_run_v2_service" "ai_agent" {
  name     = "${var.project_name}-ai-agent"
  location = var.gcp_region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.cloud_run_sa.email

    scaling {
      min_instance_count = 0
      max_instance_count = 10
    }

    containers {
      image = "gcr.io/${var.gcp_project_id}/${var.project_name}/ai-agent:latest"

      ports {
        container_port = 8000
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
      }

      env {
        name  = "PORT"
        value = "8000"
      }

      env {
        name  = "DB_HOST"
        value = "/cloudsql/${google_sql_database_instance.postgres.connection_name}"
      }

      env {
        name  = "DB_PORT"
        value = "5432"
      }

      env {
        name  = "DB_NAME"
        value = "elsiebrain"
      }

      env {
        name  = "DB_USER"
        value = "elsie"
      }

      env {
        name = "DB_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.db_password.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "GEMMA_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.gemma_api_key.secret_id
            version = "latest"
          }
        }
      }

      volume_mounts {
        name       = "cloudsql"
        mount_path = "/cloudsql"
      }
    }

    volumes {
      name = "cloudsql"
      cloud_sql_instance {
        instances = [google_sql_database_instance.postgres.connection_name]
      }
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_cloud_run_v2_service" "discord_bot" {
  name     = "${var.project_name}-discord-bot"
  location = var.gcp_region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_ONLY"

  template {
    service_account = google_service_account.cloud_run_sa.email

    scaling {
      min_instance_count = 1
      max_instance_count = 2
    }

    vpc_access {
      connector = google_vpc_access_connector.main.name
      egress    = "PRIVATE_RANGES_ONLY"
    }

    containers {
      image = "gcr.io/${var.gcp_project_id}/${var.project_name}/discord-bot:latest"

      resources {
        limits = {
          cpu    = "0.5"
          memory = "512Mi"
        }
      }

      env {
        name = "DISCORD_TOKEN"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.discord_token.secret_id
            version = "latest"
          }
        }
      }

      env {
        name  = "AI_AGENT_URL"
        value = google_cloud_run_v2_service.ai_agent.uri
      }

      env {
        name = "GEMMA_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.gemma_api_key.secret_id
            version = "latest"
          }
        }
      }
    }
  }

  depends_on = [google_project_service.apis, google_cloud_run_v2_service.ai_agent]
}

resource "google_cloud_run_v2_service" "db_populator" {
  name     = "${var.project_name}-db-populator"
  location = var.gcp_region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_ONLY"

  template {
    service_account = google_service_account.cloud_run_sa.email

    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }

    vpc_access {
      connector = google_vpc_access_connector.main.name
      egress    = "PRIVATE_RANGES_ONLY"
    }

    containers {
      image = "gcr.io/${var.gcp_project_id}/${var.project_name}/db-populator:latest"

      resources {
        limits = {
          cpu    = "0.5"
          memory = "512Mi"
        }
      }

      env {
        name  = "DB_HOST"
        value = "/cloudsql/${google_sql_database_instance.postgres.connection_name}"
      }

      env {
        name  = "DB_PORT"
        value = "5432"
      }

      env {
        name  = "DB_NAME"
        value = "elsiebrain"
      }

      env {
        name  = "DB_USER"
        value = "elsie"
      }

      env {
        name = "DB_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.db_password.secret_id
            version = "latest"
          }
        }
      }

      env {
        name  = "WIKI_UPDATE_INTERVAL"
        value = "3600"
      }

      volume_mounts {
        name       = "cloudsql"
        mount_path = "/cloudsql"
      }
    }

    volumes {
      name = "cloudsql"
      cloud_sql_instance {
        instances = [google_sql_database_instance.postgres.connection_name]
      }
    }
  }

  depends_on = [google_project_service.apis]
}

# IAM for public access to AI Agent
resource "google_cloud_run_service_iam_member" "ai_agent_public" {
  service  = google_cloud_run_v2_service.ai_agent.name
  location = google_cloud_run_v2_service.ai_agent.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Outputs
output "ai_agent_url" {
  description = "URL of the AI Agent Cloud Run service"
  value       = google_cloud_run_v2_service.ai_agent.uri
}

output "discord_bot_url" {
  description = "URL of the Discord Bot Cloud Run service"
  value       = google_cloud_run_v2_service.discord_bot.uri
}

output "db_populator_url" {
  description = "URL of the DB Populator Cloud Run service"
  value       = google_cloud_run_v2_service.db_populator.uri
}

output "database_connection_name" {
  description = "Cloud SQL instance connection name"
  value       = google_sql_database_instance.postgres.connection_name
}

output "container_registry_urls" {
  description = "Container Registry URLs for pushing images"
  value = {
    ai_agent     = "gcr.io/${var.gcp_project_id}/${var.project_name}/ai-agent"
    discord_bot  = "gcr.io/${var.gcp_project_id}/${var.project_name}/discord-bot"
    db_populator = "gcr.io/${var.gcp_project_id}/${var.project_name}/db-populator"
  }
} 