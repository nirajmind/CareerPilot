resource "mongodbatlas_project" "careerpilot" {
  org_id = var.atlas_org_id
  name   = var.atlas_project_name
}
