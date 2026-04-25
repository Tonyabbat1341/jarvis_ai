# GCP — buckets, IAM, jobs test

## Terraform

```bash
cd infra/gcp
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with project and unique bucket names
terraform init
terraform apply
```

Crée deux buckets GCS, un compte de service `jarvis-training`, et IAM `storage.objectAdmin` sur les buckets + `roles/aiplatform.user` pour Vertex.

## Sans Terraform

```bash
export PROJECT_ID=your-project
export DATA_BUCKET=your-unique-data-bucket
export CKPT_BUCKET=your-unique-ckpt-bucket
bash setup_bucket.sh
```

## Job test

Utiliser [`../../training/launch_vertex.sh`](../../training/launch_vertex.sh) après construction d’une image dans Artifact Registry et configuration de `IMAGE_URI`, `GCS_DATA`, `GCS_CKPT`.

## Jarvis Mini 1.0 (~15B) sur Vertex

Guide détaillé (buckets, image Docker, variables d’environnement, dépannage) : [`jarvis_mini_vertex.md`](jarvis_mini_vertex.md).
