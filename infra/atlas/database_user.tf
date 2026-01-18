resource "mongodbatlas_database_user" "careerpilot_app" {
  project_id = mongodbatlas_project.careerpilot.id
  username   = var.db_username
  password   = var.db_password
  auth_database_name = "admin"

  roles {
    role_name     = "readWrite"
    database_name = var.app_db_name
  }
}
