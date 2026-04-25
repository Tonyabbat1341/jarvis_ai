# Jarvis Mini 1.0 (~15B) — déploiement d’entraînement sur Google Cloud (Vertex AI)

Ce guide enchaîne les étapes pour préparer le stockage, construire l’image Docker (Jarvis + branche Megatron-LM pinnée), et soumettre un **Custom Job** Vertex AI qui exécute [`training/megatron/run_pretrain.sh`](../../training/megatron/run_pretrain.sh).

## Prérequis

- Projet GCP avec facturation active.
- Outils locaux : `gcloud` (authentifié), Docker (pour builder l’image), éventuellement Terraform si vous utilisez [`infra/gcp/`](.).
- APIs activées : **Vertex AI API**, **Artifact Registry API**, **Cloud Storage API**, **Cloud Build API** (si build distant).

## 1. Choisir région et quotas

- Région courante pour GPU : `us-central1` (variable `REGION`).
- Pour un modèle ~15B, prévoir plusieurs **A100 80G** ou **H100** ; demandez une augmentation de quota GPU si besoin (voir [`scale_checklist.md`](scale_checklist.md)).

## 2. Buckets GCS (données + checkpoints)

**Option A — Terraform** (recommandé si le dépôt le fournit) :

```bash
cd infra/gcp
cp terraform.tfvars.example terraform.tfvars
# Éditer terraform.tfvars : project_id, noms de buckets uniques
terraform init
terraform apply
```

**Option B — script** : suivre [`README.md`](README.md) (`setup_bucket.sh`).

Vous devez obtenir deux URI du type :

- `gs://VOTRE_BUCKET_DATA/jarvis/...` → utilisé comme `GCS_DATA` (préfixe passé à Megatron comme `--data-path`).
- `gs://VOTRE_BUCKET_CKPT/jarvis/...` → utilisé comme `GCS_CKPT` (checkpoints `--save` / `--load`).

Les données doivent être au **format Megatron** (binaires + index, pas seulement du texte brut). Voir [`training/megatron/README.md`](../../training/megatron/README.md).

## 3. Compte de service et IAM

Créez ou réutilisez un compte de service (ex. `jarvis-training@...`) avec au minimum :

- Lecture/écriture sur les deux buckets (ex. `roles/storage.objectAdmin` sur les buckets ou préfixes concernés).
- `roles/aiplatform.user` pour lancer des jobs Vertex.

## 4. Registre d’images (Artifact Registry)

Créez un dépôt Docker (ex. `jarvis` en `REGION`) :

```bash
export PROJECT_ID=your-project
export REGION=us-central1
gcloud services enable artifactregistry.googleapis.com --project="${PROJECT_ID}"
gcloud artifacts repositories create jarvis \
  --repository-format=docker \
  --location="${REGION}" \
  --project="${PROJECT_ID}" \
  --description="Jarvis training" || true
```

## 5. Construire et pousser l’image

Depuis la racine du dépôt `jarvis_ai` :

```bash
export REGION=us-central1
export PROJECT_ID=your-project
export IMAGE_TAG="${REGION}-docker.pkg.dev/${PROJECT_ID}/jarvis/train:jarvis-mini-$(date +%Y%m%d)"
```

Build local puis push :

```bash
docker build -f training/Dockerfile -t "${IMAGE_TAG}" .
docker push "${IMAGE_TAG}"
```

Ou **Cloud Build** (sans Docker local), avec le fichier de config du dépôt :

```bash
gcloud builds submit . \
  --project="${PROJECT_ID}" \
  --config=infra/gcp/cloudbuild_jarvis_train.yaml \
  --substitutions=_IMAGE_URI="${IMAGE_TAG}"
```

(`gcloud builds submit --tag` attend un `Dockerfile` à la racine ; le Dockerfile du projet est sous `training/`, d’où ce fichier YAML.)

Définissez `IMAGE_URI="${IMAGE_TAG}"` pour l’étape suivante.

**Build-arg utile** : `MEGATRON_REF` (défaut `core_r0.12.0` dans le Dockerfile). Ne changez la branche/tag Megatron qu’en vérifiant la compatibilité PyTorch/CUDA.

## 6. Configuration locale (référence projet)

Copiez [`configs/gcs.example.yaml`](../../configs/gcs.example.yaml) vers `configs/gcs.yaml` (fichier ignoré par git) et renseignez `project_id`, `region`, URIs de buckets, email du compte de service.

## 7. Lancer le Custom Job Vertex

Variables **obligatoires** :

- `PROJECT_ID`, `IMAGE_URI`, `GCS_DATA`, `GCS_CKPT`

Variables **optionnelles** (voir [`training/launch_vertex.sh`](../../training/launch_vertex.sh)) :

- `REGION` (défaut `us-central1`)
- `MODEL_CONFIG` : chemin **dans le conteneur** vers le YAML Jarvis (défaut `/workspace/jarvis/configs/model_jarvis_mini_1_0.yaml`)
- `DISPLAY_NAME`, `MACHINE_TYPE`, `ACCELERATOR_TYPE`, `ACCELERATOR_COUNT`, `REPLICA_COUNT`
- `TENSOR_MODEL_PARALLEL_SIZE`, `PIPELINE_MODEL_PARALLEL_SIZE`, `NPROC_PER_NODE`
- `DATA_SPLIT`, `TOKENIZER_TYPE`, `TOKENIZER_MODEL`

Exemple minimal :

```bash
export PROJECT_ID=your-project
export REGION=us-central1
export IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/jarvis/train:jarvis-mini-20260417"
export GCS_DATA="gs://VOTRE_BUCKET_DATA/jarvis/megatron_data"
export GCS_CKPT="gs://VOTRE_BUCKET_CKPT/jarvis/runs/mini-1"
export MODEL_CONFIG="/workspace/jarvis/configs/model_jarvis_mini_1_0.yaml"

bash training/launch_vertex.sh
```

Le script exécute dans le conteneur une commande du type `bash -c 'export DATA_PATH=…; …; cd /workspace/Megatron-LM && bash ../jarvis/training/megatron/run_pretrain.sh'`. Les variables (`DATA_PATH`, `CHECKPOINT_DIR`, `MODEL_CONFIG`, parallélisme, etc.) sont passées ainsi, car **`gcloud ai custom-jobs create` n’a pas de flag `--env-vars`** (contrairement à d’autres produits Google Cloud).

Pour un équivalent déclaratif en YAML (`CustomJobSpec`, donc racine `workerPoolSpecs`), voir [`training/vertex/custom_job.yaml`](../../training/vertex/custom_job.yaml) — à soumettre avec `--display-name=...` en plus de `--config=...`.

## 8. Suivi et coûts

- Suivi des jobs : console GCP → Vertex AI → Training → Custom jobs.
- Surveillez la consommation GPU et la fréquence de checkpoint vers `GCS_CKPT` (règles de lifecycle sur le bucket pour limiter la rétention).

## 9. DeepSpeed (optionnel)

Pour ZeRO-2 avec profil adapté au Mini, voir [`training/deepspeed/ds_config_jarvis_mini_zero2.json`](../../training/deepspeed/ds_config_jarvis_mini_zero2.json). L’entrée actuelle `run_pretrain.sh` lance **torchrun + Megatron** ; intégrer DeepSpeed/Megatron en profondeur demande le launcher DeepSpeed et les flags attendus par votre branche Megatron.

## Dépannage rapide

- **Job démarre mais erreur Megatron** : vérifiez que `DATA_PATH` pointe vers des données **déjà préparées** au format Megatron, et que `MODEL_CONFIG` est lisible dans l’image.
- **OOM GPU** : baissez `micro_batch_size` dans [`configs/model_jarvis_mini_1_0.yaml`](../../configs/model_jarvis_mini_1_0.yaml), augmentez le parallélisme tenseur (`TENSOR_MODEL_PARALLEL_SIZE`), ou utilisez des GPU avec plus de mémoire.
- **Incompatibilité de versions** : ajustez l’image PyTorch de base ou `MEGATRON_REF` dans le build Docker.
