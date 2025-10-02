module "compute" {
  source = "../../../utils/modules/compute"

  environment = var.environment
  group_name  = var.group_name
}