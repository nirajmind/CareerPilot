resource "mongodbatlas_project_ip_access_list" "careerpilot_vm" {
  project_id = mongodbatlas_project.careerpilot.id
  ip_address = var.app_vm_ip
  comment    = "Atlantic.net VM for CareerPilot"
}
