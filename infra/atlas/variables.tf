variable "atlas_org_id" {
  description = "MongoDB Atlas Organization ID"
  type        = string
}

variable "atlas_public_key" {
  description = "Atlas API public key"
  type        = string
  sensitive   = true
}

variable "atlas_private_key" {
  description = "Atlas API private key"
  type        = string
  sensitive   = true
}

variable "atlas_project_name" {
  description = "Atlas project name"
  type        = string
  default     = "careerpilot-project"
}

variable "cluster_name" {
  description = "Atlas cluster name"
  type        = string
  default     = "careerpilot-cluster"
}

variable "db_username" {
  description = "App DB username"
  type        = string
  default     = "careerpilot_app"
}

variable "db_password" {
  description = "App DB password"
  type        = string
  sensitive   = true
}

variable "app_db_name" {
  description = "Application database name"
  type        = string
  default     = "careerpilot"
}

variable "app_vm_ip" {
  description = "Public IP of Atlantic.net VM (CIDR /32)"
  type        = string
}

variable "app_collection_name" {
  description = "Application collection name"
  type        = string
  default     = "jobs"
}

variable "app_vector_dimensions" {
  description = "Application vector dimensions"
  type        = number
  default     = 1536
}

variable "mongo_uri" {
  description = "MongoDB connection string for bootstrap operations"
  type        = string
  sensitive   = true
}
