# Terraform configuration for deploying Elsie on Microsoft Azure
# Uses Container Instances, Container Registry, and Log Analytics

terraform {
  required_version = ">= 1.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
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

variable "azure_location" {
  description = "Azure region"
  type        = string
  default     = "East US 2"
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
provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
}

# Resource Group
resource "azurerm_resource_group" "main" {
  name     = "${var.project_name}-rg"
  location = var.azure_location

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# Key Vault for secrets
resource "azurerm_key_vault" "main" {
  name                = "${var.project_name}-kv-${random_string.suffix.result}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "standard"

  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = data.azurerm_client_config.current.object_id

    secret_permissions = [
      "Get",
      "List",
      "Set",
      "Delete",
      "Recover",
      "Backup",
      "Restore"
    ]
  }

  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = azurerm_user_assigned_identity.container_identity.principal_id

    secret_permissions = [
      "Get",
      "List"
    ]
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

data "azurerm_client_config" "current" {}

# Key Vault Secrets
resource "azurerm_key_vault_secret" "discord_token" {
  name         = "discord-token"
  value        = var.discord_token
  key_vault_id = azurerm_key_vault.main.id

  depends_on = [azurerm_key_vault.main]
}

resource "azurerm_key_vault_secret" "gemma_api_key" {
  name         = "gemma-api-key"
  value        = var.gemma_api_key
  key_vault_id = azurerm_key_vault.main.id

  depends_on = [azurerm_key_vault.main]
}

resource "azurerm_key_vault_secret" "db_password" {
  name         = "db-password"
  value        = var.db_password
  key_vault_id = azurerm_key_vault.main.id

  depends_on = [azurerm_key_vault.main]
}

# Virtual Network
resource "azurerm_virtual_network" "main" {
  name                = "${var.project_name}-vnet"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# Public IP for NAT Gateway
resource "azurerm_public_ip" "nat" {
  name                = "${var.project_name}-nat-pip"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  allocation_method   = "Static"
  sku                 = "Standard"

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# NAT Gateway for outbound internet access
resource "azurerm_nat_gateway" "main" {
  name                = "${var.project_name}-nat"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku_name            = "Standard"

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "azurerm_nat_gateway_public_ip_association" "main" {
  nat_gateway_id       = azurerm_nat_gateway.main.id
  public_ip_address_id = azurerm_public_ip.nat.id
}

resource "azurerm_subnet" "containers" {
  name                 = "${var.project_name}-containers-subnet"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.1.0/24"]

  delegation {
    name = "container-delegation"
    service_delegation {
      name    = "Microsoft.ContainerInstance/containerGroups"
      actions = ["Microsoft.Network/virtualNetworks/subnets/action"]
    }
  }
}

# Associate NAT Gateway with containers subnet
resource "azurerm_subnet_nat_gateway_association" "containers" {
  subnet_id      = azurerm_subnet.containers.id
  nat_gateway_id = azurerm_nat_gateway.main.id
}

resource "azurerm_subnet" "database" {
  name                 = "${var.project_name}-database-subnet"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.2.0/24"]

  service_endpoints = ["Microsoft.Sql"]

  delegation {
    name = "database-delegation"
    service_delegation {
      name = "Microsoft.DBforPostgreSQL/flexibleServers"
      actions = [
        "Microsoft.Network/virtualNetworks/subnets/join/action",
      ]
    }
  }
}

# Network Security Groups
resource "azurerm_network_security_group" "containers" {
  name                = "${var.project_name}-containers-nsg"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  # Allow inbound from AI Agent (port 8000) for Discord Bot
  security_rule {
    name                       = "AllowAIAgentInbound"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "8000"
    source_address_prefix      = "10.0.1.0/24"
    destination_address_prefix = "10.0.1.0/24"
  }

  # Allow outbound HTTPS for Discord API and external APIs
  security_rule {
    name                       = "AllowHTTPSOutbound"
    priority                   = 100
    direction                  = "Outbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "10.0.1.0/24"
    destination_address_prefix = "Internet"
  }

  # Allow outbound to database subnet
  security_rule {
    name                       = "AllowDatabaseOutbound"
    priority                   = 110
    direction                  = "Outbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "5432"
    source_address_prefix      = "10.0.1.0/24"
    destination_address_prefix = "10.0.2.0/24"
  }

  # Deny all other inbound traffic
  security_rule {
    name                       = "DenyAllInbound"
    priority                   = 4000
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "azurerm_network_security_group" "database" {
  name                = "${var.project_name}-database-nsg"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  # Allow inbound PostgreSQL from containers subnet only
  security_rule {
    name                       = "AllowPostgreSQLFromContainers"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "5432"
    source_address_prefix      = "10.0.1.0/24"
    destination_address_prefix = "10.0.2.0/24"
  }

  # Deny all other inbound traffic
  security_rule {
    name                       = "DenyAllInbound"
    priority                   = 4000
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# Associate NSGs with subnets
resource "azurerm_subnet_network_security_group_association" "containers" {
  subnet_id                 = azurerm_subnet.containers.id
  network_security_group_id = azurerm_network_security_group.containers.id
}

resource "azurerm_subnet_network_security_group_association" "database" {
  subnet_id                 = azurerm_subnet.database.id
  network_security_group_id = azurerm_network_security_group.database.id
}

# Container Registry
resource "azurerm_container_registry" "main" {
  name                = "${var.project_name}acr${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Basic"
  admin_enabled       = true

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# User Assigned Identity for Container Instances
resource "azurerm_user_assigned_identity" "container_identity" {
  name                = "${var.project_name}-container-identity"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# Role assignments for Container Registry
resource "azurerm_role_assignment" "acr_pull" {
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.container_identity.principal_id
}

# Log Analytics Workspace
resource "azurerm_log_analytics_workspace" "main" {
  name                = "${var.project_name}-logs"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# PostgreSQL Flexible Server
resource "azurerm_postgresql_flexible_server" "main" {
  name                   = "${var.project_name}-postgres"
  resource_group_name    = azurerm_resource_group.main.name
  location               = azurerm_resource_group.main.location
  version                = "15"
  delegated_subnet_id    = azurerm_subnet.database.id
  private_dns_zone_id    = azurerm_private_dns_zone.main.id
  administrator_login    = "elsie"
  administrator_password = var.db_password
  zone                   = "1"
  storage_mb             = 32768
  sku_name               = "B_Standard_B1ms"
  backup_retention_days  = 7

  depends_on = [azurerm_private_dns_zone_virtual_network_link.main]

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "azurerm_postgresql_flexible_server_database" "elsiebrain" {
  name      = "elsiebrain"
  server_id = azurerm_postgresql_flexible_server.main.id
  collation = "en_US.utf8"
  charset   = "utf8"
}

# Private DNS Zone for PostgreSQL
resource "azurerm_private_dns_zone" "main" {
  name                = "${var.project_name}.postgres.database.azure.com"
  resource_group_name = azurerm_resource_group.main.name

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "azurerm_private_dns_zone_virtual_network_link" "main" {
  name                  = "${var.project_name}-pdz-link"
  private_dns_zone_name = azurerm_private_dns_zone.main.name
  virtual_network_id    = azurerm_virtual_network.main.id
  resource_group_name   = azurerm_resource_group.main.name

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}


# Container Group for AI Agent (Public - needs external API access)
resource "azurerm_container_group" "ai_agent" {
  name                = "${var.project_name}-ai-agent"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  ip_address_type     = "Public"
  dns_name_label      = "${var.project_name}-ai-agent-${random_string.suffix.result}"
  os_type             = "Linux"
  restart_policy      = "Always"
  exposed_port {
    port     = 8000
    protocol = "TCP"
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.container_identity.id]
  }

  image_registry_credential {
    server   = azurerm_container_registry.main.login_server
    username = azurerm_container_registry.main.admin_username
    password = azurerm_container_registry.main.admin_password
  }

  container {
    name   = "ai-agent"
    image  = "${azurerm_container_registry.main.login_server}/${var.project_name}/ai-agent:latest"
    cpu    = "1"
    memory = "1.5"

    ports {
      port     = 8000
      protocol = "TCP"
    }

    environment_variables = {
      PORT    = "8000"
      DB_HOST = azurerm_postgresql_flexible_server.main.fqdn
      DB_PORT = "5432"
      DB_NAME = "elsiebrain"
      DB_USER = "elsie"
    }

    secure_environment_variables = {
      DB_PASSWORD   = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.db_password.id})"
      GEMMA_API_KEY = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.gemma_api_key.id})"
    }
  }

  diagnostics {
    log_analytics {
      workspace_id  = azurerm_log_analytics_workspace.main.workspace_id
      workspace_key = azurerm_log_analytics_workspace.main.primary_shared_key
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }

  depends_on = [
    azurerm_role_assignment.acr_pull,
    azurerm_postgresql_flexible_server.main
  ]
}

# Container Group for Discord Bot (Private - no public IP needed)
resource "azurerm_container_group" "discord_bot" {
  name                = "${var.project_name}-discord-bot"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  ip_address_type     = "Private"
  subnet_ids          = [azurerm_subnet.containers.id]
  os_type             = "Linux"
  restart_policy      = "Always"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.container_identity.id]
  }

  image_registry_credential {
    server   = azurerm_container_registry.main.login_server
    username = azurerm_container_registry.main.admin_username
    password = azurerm_container_registry.main.admin_password
  }

  container {
    name   = "discord-bot"
    image  = "${azurerm_container_registry.main.login_server}/${var.project_name}/discord-bot:latest"
    cpu    = "0.5"
    memory = "1"

    environment_variables = {
      AI_AGENT_URL = "http://${azurerm_container_group.ai_agent.fqdn}:8000"
    }

    secure_environment_variables = {
      DISCORD_TOKEN = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.discord_token.id})"
      GEMMA_API_KEY = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.gemma_api_key.id})"
    }
  }

  diagnostics {
    log_analytics {
      workspace_id  = azurerm_log_analytics_workspace.main.workspace_id
      workspace_key = azurerm_log_analytics_workspace.main.primary_shared_key
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }

  depends_on = [
    azurerm_role_assignment.acr_pull,
    azurerm_container_group.ai_agent
  ]
}

# Container Group for DB Populator (Private - only needs outbound access)
resource "azurerm_container_group" "db_populator" {
  name                = "${var.project_name}-db-populator"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  ip_address_type     = "Private"
  subnet_ids          = [azurerm_subnet.containers.id]
  os_type             = "Linux"
  restart_policy      = "Always"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.container_identity.id]
  }

  image_registry_credential {
    server   = azurerm_container_registry.main.login_server
    username = azurerm_container_registry.main.admin_username
    password = azurerm_container_registry.main.admin_password
  }

  container {
    name   = "db-populator"
    image  = "${azurerm_container_registry.main.login_server}/${var.project_name}/db-populator:latest"
    cpu    = "0.5"
    memory = "1"

    environment_variables = {
      DB_HOST               = azurerm_postgresql_flexible_server.main.fqdn
      DB_PORT               = "5432"
      DB_NAME               = "elsiebrain"
      DB_USER               = "elsie"
      WIKI_UPDATE_INTERVAL  = "3600"
    }

    secure_environment_variables = {
      DB_PASSWORD = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.db_password.id})"
    }
  }

  diagnostics {
    log_analytics {
      workspace_id  = azurerm_log_analytics_workspace.main.workspace_id
      workspace_key = azurerm_log_analytics_workspace.main.primary_shared_key
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }

  depends_on = [
    azurerm_role_assignment.acr_pull,
    azurerm_postgresql_flexible_server.main
  ]
}

# Outputs
output "container_registry_login_server" {
  description = "Container Registry login server"
  value       = azurerm_container_registry.main.login_server
}

output "container_registry_admin_username" {
  description = "Container Registry admin username"
  value       = azurerm_container_registry.main.admin_username
  sensitive   = true
}

output "container_registry_admin_password" {
  description = "Container Registry admin password"
  value       = azurerm_container_registry.main.admin_password
  sensitive   = true
}

output "ai_agent_fqdn" {
  description = "AI Agent container group FQDN"
  value       = azurerm_container_group.ai_agent.fqdn
}

output "ai_agent_ip_address" {
  description = "AI Agent container group IP address"
  value       = azurerm_container_group.ai_agent.ip_address
}

output "database_fqdn" {
  description = "PostgreSQL server FQDN"
  value       = azurerm_postgresql_flexible_server.main.fqdn
  sensitive   = true
}

output "log_analytics_workspace_id" {
  description = "Log Analytics workspace ID"
  value       = azurerm_log_analytics_workspace.main.workspace_id
}

output "container_registry_urls" {
  description = "Container Registry URLs for pushing images"
  value = {
    ai_agent     = "${azurerm_container_registry.main.login_server}/${var.project_name}/ai-agent"
    discord_bot  = "${azurerm_container_registry.main.login_server}/${var.project_name}/discord-bot"
    db_populator = "${azurerm_container_registry.main.login_server}/${var.project_name}/db-populator"
  }
} 