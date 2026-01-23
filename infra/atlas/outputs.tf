output "connection_string_template" {
  description = "MongoDB connection string template"
  value       = "mongodb+srv://${var.db_username}:${var.db_password}@${mongodbatlas_cluster.careerpilot.connection_strings[0].standard_srv}/?retryWrites=true&w=majority&tls=true"
  sensitive   = true
}
