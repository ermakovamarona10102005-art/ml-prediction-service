terraform {
  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "= 0.117.0"
    }
  }
}

variable "pm_api_token" {
  type      = string
  sensitive = true
}
variable "ssh_public_key" { type = string }
variable "ubuntu_sha256" { type = string }

provider "proxmox" {
  endpoint  = "https://192.168.0.250:8006/"
  api_token = var.pm_api_token
  insecure  = true
}

resource "proxmox_virtual_environment_download_file" "ubuntu" {
  node_name          = "pve"
  datastore_id       = "lab6test"
  content_type       = "import"
  file_name          = "lab6-jammy-amd64.qcow2"
  url                = "https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-amd64.img"
  checksum           = var.ubuntu_sha256
  checksum_algorithm = "sha256"
  upload_timeout     = 1800
}

locals {
  machines = {
    db  = { id = 110, ip = "10.10.10.21", memory = 1024, cores = 1 }
    app = { id = 111, ip = "10.10.10.22", memory = 2048, cores = 2 }
  }
}

resource "proxmox_virtual_environment_vm" "clean" {
  for_each        = local.machines
  node_name       = "pve"
  vm_id           = each.value.id
  name            = "lab6-clean-${each.key}"
  description     = "Isolated Lab 6 clean deployment; no import of VM100 or VM101"
  tags            = [each.key, "lab6-clean"]
  started         = true
  on_boot         = false
  stop_on_destroy = true
  agent { enabled = false }
  cpu {
    cores = each.value.cores
    type  = "host"
  }
  memory { dedicated = each.value.memory }
  disk {
    datastore_id = "lab6test"
    import_from  = proxmox_virtual_environment_download_file.ubuntu.id
    interface    = "scsi0"
    file_format  = "qcow2"
    size         = 8
  }
  network_device {
    bridge = "vmbr1"
    model  = "virtio"
  }
  initialization {
    datastore_id = "lab6test"
    dns { servers = ["1.1.1.1", "8.8.8.8"] }
    ip_config {
      ipv4 {
        address = "${each.value.ip}/24"
        gateway = "10.10.10.1"
      }
    }
    user_account {
      username = "student"
      keys     = [trimspace(var.ssh_public_key)]
    }
  }
  operating_system { type = "l26" }
  serial_device {}
  lifecycle { prevent_destroy = true }
}

output "created_machines" {
  value = { for role, machine in local.machines : role => { vm_id = machine.id, ip = machine.ip } }
}
