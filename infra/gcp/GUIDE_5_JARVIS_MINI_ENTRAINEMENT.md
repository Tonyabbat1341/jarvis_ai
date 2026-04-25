# Guide 5 Jarvis Mini Entraînement

Ce guide part de **ta situation actuelle**:

- Tu as deja fait le setup GCP.
- Tes buckets repondent OK.
- L'image Docker est construite.
- Tu bloques sur `training/launch_vertex.sh` avec erreur `IMAGE_URI`.

Objectif: lancer un vrai entrainement sur GPU Vertex AI et le laisser rouler quelques heures.

---

## 0) Infos importantes enregistrees (fait)

Pour eviter de tout retaper, un fichier de session est maintenant disponible:

- `infra/gcp/jarvis_session_env.sh`

Dans une nouvelle session Cloud Shell:

```bash
cd ~/jarvis_ai
source infra/gcp/jarvis_session_env.sh
echo "$PROJECT_ID | $REGION"
echo "$GCS_DATA"
echo "$GCS_CKPT"
echo "$IMAGE_URI"
```

Ensuite, lancement direct:

```bash
bash training/launch_vertex.sh
```

---

## 1) Repartir proprement dans la session Cloud Shell

Dans un nouveau terminal (ou si tu as perdu les variables), colle ceci:

```bash
cd ~/jarvis_ai

export PROJECT_ID="onyx-parser-493701-c9"
export REGION="us-central1"
gcloud config set project "${PROJECT_ID}"

source infra/gcp/cloudshell_env.sh

export IMAGE_URI="us-central1-docker.pkg.dev/onyx-parser-493701-c9/jarvis/train:jarvis-mini-20260425"

echo "PROJECT_ID=${PROJECT_ID}"
echo "REGION=${REGION}"
echo "GCS_DATA=${GCS_DATA}"
echo "GCS_CKPT=${GCS_CKPT}"
echo "IMAGE_URI=${IMAGE_URI}"
```

Pourquoi ton erreur arrivait: `launch_vertex.sh` exige `IMAGE_URI` (ligne 8), donc si la variable n'est pas exportee dans la session, le job ne part pas.

---

## 2) Verification rapide avant lancement

Tu as deja valide les buckets, mais voici le mini check final:

```bash
_jarvis_bucket_from_gs_uri() { local x="${1#gs://}"; echo "${x%%/*}"; }
for _label in "data" "ckpt"; do
  if [[ "${_label}" == "data" ]]; then _u="${GCS_DATA}"; else _u="${GCS_CKPT}"; fi
  _b="$(_jarvis_bucket_from_gs_uri "${_u}")"
  gcloud storage buckets describe "gs://${_b}" --project="${PROJECT_ID}" >/dev/null && echo "OK ${_label}: gs://${_b}" || echo "ERREUR ${_label}: gs://${_b}"
done
unset _label _u _b
```

---

## 3) Lancer l'entrainement GPU (version simple)

Commande minimale:

```bash
cd ~/jarvis_ai
bash training/launch_vertex.sh
```

Si tout est bon, la commande retourne un `CustomJob` Vertex AI cree.

---

## 4) Le faire rouler "une couple d'heures"

Tu as 2 approches:

- **Approche simple (recommandee maintenant):** tu lances le job et tu le laisses tourner 2 a 3 heures, puis tu l'arretes manuellement.
- **Approche avancee:** limiter le nombre d'iterations directement dans la commande de training (necessite adaptation des scripts).

Pour ton cas, prends l'approche simple.

### Suivre le job

- Console: [Vertex AI Custom Jobs](https://console.cloud.google.com/vertex-ai/training/custom-jobs?project=onyx-parser-493701-c9)
- Clique ton job `jarvis-mini-training` pour voir logs et statut.

### Arreter apres 2-3 heures

Option console: bouton **Cancel** dans le job.

Option CLI:

```bash
gcloud ai custom-jobs list \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --sort-by="~createTime" \
  --limit=5
```

Recupere le `CUSTOM_JOB_ID`, puis:

```bash
gcloud ai custom-jobs cancel CUSTOM_JOB_ID \
  --project="${PROJECT_ID}" \
  --region="${REGION}"
```

Les checkpoints deja ecrits dans `GCS_CKPT` restent disponibles.

---

## 5) GPU quota a 2: quoi mettre comme config

Tu as augmente ton quota GPU a 2, donc c'est bon.

Important:

- Le script actuel est configure par defaut pour **1 GPU** (`a2-highgpu-1g`, `ACCELERATOR_COUNT=1`).
- Tu peux deja entrainer maintenant avec 1 GPU.
- Passer a 2 GPU demande d'ajuster la machine/parallelisme pour rester coherent.

Pour un premier run stable de quelques heures: reste en 1 GPU.

---

## 6) Recette "copier-coller" complete (depuis ton etat actuel)

Si tu veux un bloc unique:

```bash
cd ~/jarvis_ai
export PROJECT_ID="onyx-parser-493701-c9"
export REGION="us-central1"
gcloud config set project "${PROJECT_ID}"
source infra/gcp/cloudshell_env.sh
export IMAGE_URI="us-central1-docker.pkg.dev/onyx-parser-493701-c9/jarvis/train:jarvis-mini-20260425"
bash training/launch_vertex.sh
```

Ensuite, ouvre Vertex AI et laisse tourner environ 2 heures, puis cancel.

---

## 7) Si ca re-bloque, verifier en premier

1. `echo "${IMAGE_URI}"` n'est pas vide.
2. `echo "${GCS_DATA}"` et `echo "${GCS_CKPT}"` pointent vers les bons buckets.
3. Tu es bien dans le bon projet: `gcloud config get-value project`.
4. Le job apparait dans Vertex AI Custom Jobs.

Si tu veux, prochainement je peux te faire un **Guide 6** pour:

- lancer automatiquement avec nom/date de run;
- monitorer les logs en direct;
- faire un resume propre depuis les checkpoints.
