# Isolated Lab 6 clean deployment

This configuration creates VM110 and VM111 from the official Ubuntu 22.04
cloud image. It does not import, replace or manage the original VM100/VM101.
Its Terraform state is separate from the original `terraform/` directory.

Prerequisites: Proxmox node `pve`, private bridge `vmbr1` with gateway
10.10.10.1 and outbound NAT, a separate directory datastore `lab6test`
with `images,import` content enabled, and Terraform 1.16.6 with
bpg/proxmox 0.117.0. The example checksum must match the official image at
deployment time. A changed upstream image must not be accepted without
verifying a new checksum. Keep an archived copy for exact long-term replay.

VM110: PostgreSQL, 10.10.10.21, 1 CPU, 1 GiB RAM, 8 GiB disk.
VM111: Docker application, 10.10.10.22, 2 CPUs, 2 GiB RAM, 8 GiB disk.
Both use only the private bridge and the controller's public SSH key.

From the original application/controller VM, prepare `terraform.tfvars`
locally with mode 0600. Never commit it, state, saved plans or passwords.

```sh
cd ~/ml-prediction-service/clean-lab6/terraform
terraform init
terraform validate
terraform plan -out=clean.tfplan
# Review: only VM110, VM111 and the cloud image may be created.
terraform apply clean.tfplan
terraform plan
cd ..
ansible all -i ansible/inventory.ini -m ping
read -rsp 'Database password: ' LAB6_DB_PASSWORD
export LAB6_DB_PASSWORD
export LAB6_IMAGE=ghcr.io/ermakovamarona10102005-art/ml-prediction-service:cce4e0f34678f3b151baf85d80c61091c8ec3386
ansible-playbook -i ansible/inventory.ini ansible/site.yml
ansible-playbook -i ansible/inventory.ini ansible/site.yml
python3 verify.py
unset LAB6_DB_PASSWORD LAB6_IMAGE
```

The second Ansible execution should report `changed=0`, `failed=0`.
The verification sends 13 Wine features and checks a newly inserted row in
the separately created database. New VM creation is protected with
`prevent_destroy`; no automatic cleanup or removal of VMs is performed.
The password is supplied through the environment and managed by the
PostgreSQL module. Keep the same secret for repeat executions.
