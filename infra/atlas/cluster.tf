resource "mongodbatlas_cluster" "careerpilot" {
  depends_on = [
    mongodbatlas_project_ip_access_list.careerpilot_vm
  ]

  project_id   = mongodbatlas_project.careerpilot.id
  name         = var.cluster_name
  cluster_type = "REPLICASET"

  provider_name               = "TENANT"
  backing_provider_name       = "AWS"
  provider_region_name        = "EU_WEST_1"
  provider_instance_size_name = "M0"

  mongo_db_major_version = "7.0"
}
