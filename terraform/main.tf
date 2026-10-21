terraform {
  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "~> 0.60"
    }
  }
}

variable "pm_api_token" {
  type      = string
  sensitive = true
}

provider "proxmox" {
  endpoint  = "https://192.168.0.250:8006/"
  api_token = var.pm_api_token
  insecure  = true
}

# Existing VMs are imported before any plan is applied.
resource "proxmox_virtual_environment_vm" "db_server" {
  node_name = "pve"
  vm_id     = 100
  name      = "vm1-db"
  tags      = ["db", "ml-project"]
  lifecycle {
    prevent_destroy = true
    # Preserve imported hardware; manage the VM identity and project tags.
    ignore_changes = [acpi, bios, boot_order, description, hotplug,
      keyboard_layout, kvm_arguments, machine, network_device, on_boot,
      pool_id, protection, scsi_hardware, started, tablet_device, template,
      agent, amd_sev, audio_device, cdrom, clone, cpu, disk, efi_disk,
      hostpci, initialization, memory, numa, operating_system, rng,
    serial_device, smbios, startup, tpm_state, usb, vga, virtiofs, watchdog]
  }
}

resource "proxmox_virtual_environment_vm" "app_server" {
  node_name = "pve"
  vm_id     = 101
  name      = "vm2-app"
  tags      = ["app", "ml-project"]
  lifecycle {
    prevent_destroy = true
    ignore_changes = [acpi, bios, boot_order, description, hotplug,
      keyboard_layout, kvm_arguments, machine, network_device, on_boot,
      pool_id, protection, scsi_hardware, started, tablet_device, template,
      agent, amd_sev, audio_device, cdrom, clone, cpu, disk, efi_disk,
      hostpci, initialization, memory, numa, operating_system, rng,
    serial_device, smbios, startup, tpm_state, usb, vga, virtiofs, watchdog]
  }
}

output "db_ip" { value = "10.10.10.11" }
output "app_ip" { value = "10.10.10.12" }
