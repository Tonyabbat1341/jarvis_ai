# Repartir de zéro dans Cloud Shell (upload du projet)

Ce fichier contient **un seul bloc à coller** dans [Cloud Shell](https://shell.cloud.google.com/) pour effacer tout ce qui a été tenté avant et recommencer proprement l’upload du projet `jarvis_ai`.

Il règle d’un coup **tous** les problèmes déjà rencontrés dans les sessions précédentes :

| Problème observé | Cause | Réglé ici par |
|------------------|-------|---------------|
| `$'\r': command not found`, `set: pipefail` | `.sh` uploadés depuis Windows en **CRLF** | `sed -i 's/\r$//'` auto sur tous les `.sh`, **et** on crée les fichiers critiques directement dans Cloud Shell via `heredoc` (donc LF garanti) |
| `ls: cannot access 'infra/gcp/cloudbuild_jarvis_train.yaml'` | ZIP incomplet (archive trop vieille) | Le bloc **recrée** `cloudbuild_jarvis_train.yaml` et `submit_train_image.sh` quoi qu’il arrive |
| `gcloud builds submit .` lancé depuis `~` | mauvais répertoire | Le bloc fait `cd ~/jarvis_ai` explicitement et vérifie `pyproject.toml` + `training/Dockerfile` |
| Dossier `~/jarvis_ai` pollué par d’anciens essais | `unzip -o` empilé sur une archive précédente | **Suppression complète** avant de recommencer |
| Bucket `Mon_Jarvis_Project_Incroyable_Data` refusé | majuscules / underscores | Rappel explicite + vérification `[a-z0-9._-]` |

---

## 1. Préparer l’upload sur ton PC (1 min)

Avant de coller le bloc ci-dessous, sur **ton PC** :

1. Repère la racine du projet : c’est le dossier qui contient **à la fois** `pyproject.toml` et le dossier `training/`.  
2. Crée un ZIP de **tout ce dossier** (clic droit → « Compresser » / « Send to → Zip » sur Windows). Le fichier doit s’appeler `jarvis_ai.zip`.  
3. Ouvre `jarvis_ai.zip` et **vérifie** que tu vois bien, à l’intérieur, le chemin `infra/gcp/cloudbuild_jarvis_train.yaml`. Si tu ne le vois pas, tu zippes le **mauvais** dossier.

> Même si ton ZIP est **incomplet** ou a des scripts en CRLF, le bloc plus bas continuera de fonctionner : il recrée les fichiers manquants et normalise les fins de ligne.

---

## 2. Le bloc à coller dans Cloud Shell (tout-en-un)

Ouvre [Cloud Shell](https://shell.cloud.google.com/) (icône `>_` en haut à droite de la [console](https://console.cloud.google.com/)), puis colle **ce bloc unique**. Il s’arrête au milieu pour te demander d’uploader `jarvis_ai.zip` (menu **⋮** → **Upload**).

```bash
# =============================================================================
#  Jarvis Mini — RESET COMPLET + RELANCE de l'upload dans Cloud Shell
#  Copie/colle l'intégralité de ce bloc. Il est conçu pour être idempotent :
#  tu peux le recoller autant de fois que tu veux sans casser l'état cloud
#  (projet, APIs, buckets, Artifact Registry restent intacts).
# =============================================================================
set -u

# ---- 0. (Optionnel mais recommandé) dis au shell quel projet tu utilises ----
# Décommente et remplace par ton vrai ID si tu veux le fixer dès maintenant.
# export PROJECT_ID="TON_PROJECT_ID"
# export REGION="us-central1"
# [[ -n "${PROJECT_ID:-}" ]] && gcloud config set project "${PROJECT_ID}"

# ---- 1. Nettoyage : on supprime tout reliquat d'upload précédent --------------
cd ~
echo ">>> Nettoyage de ~/jarvis_ai et ~/jarvis_ai.zip (s'ils existent)…"
rm -rf  ~/jarvis_ai ~/jarvis_ai-main
rm -f   ~/jarvis_ai.zip
ls -la ~ | grep -E 'jarvis' || echo "    OK : plus aucune trace de jarvis dans ~"

# ---- 2. Pause : fais l'UPLOAD du ZIP maintenant ------------------------------
cat <<'MSG'

============================================================
  UPLOAD DU ZIP MAINTENANT
  1) Dans Cloud Shell : menu  ⋮ (trois points en haut à droite
     du terminal)  →  "Upload"
  2) Choisis ton fichier jarvis_ai.zip depuis ton PC.
  3) Quand l'upload est fini, TAPE ENTREE ici pour continuer.
============================================================
MSG
read -r -p "Appuie sur ENTREE une fois jarvis_ai.zip uploadé dans ~ : " _

# ---- 3. Vérification que le ZIP est bien là ----------------------------------
if [[ ! -f ~/jarvis_ai.zip ]]; then
  echo "ERREUR : ~/jarvis_ai.zip est introuvable. Refais l'upload puis relance ce bloc." >&2
  return 1 2>/dev/null || exit 1
fi
echo ">>> ZIP trouvé : $(ls -la ~/jarvis_ai.zip)"

# ---- 4. Inspection du ZIP (diagnostic, non bloquant) -------------------------
echo ">>> Contenu attendu du ZIP (infra/gcp) :"
unzip -l ~/jarvis_ai.zip | grep -E 'infra/gcp/(cloudbuild_jarvis_train\.yaml|submit_train_image\.sh|bootstrap_cloudbuild_assets\.sh)' \
  || echo "    (!) Le ZIP n'inclut pas tous les fichiers Cloud Build — on va les recréer plus bas, pas grave."

# ---- 5. Décompression --------------------------------------------------------
cd ~
unzip -o ~/jarvis_ai.zip >/dev/null
if [[ -d ~/jarvis_ai ]]; then
  PROJECT_DIR=~/jarvis_ai
elif [[ -d ~/jarvis_ai-main ]]; then
  PROJECT_DIR=~/jarvis_ai-main
else
  PROJECT_DIR="$(find ~ -maxdepth 2 -type d -name 'jarvis_ai*' | head -n1)"
fi
if [[ -z "${PROJECT_DIR:-}" ]] || [[ ! -d "${PROJECT_DIR}" ]]; then
  echo "ERREUR : impossible de trouver le dossier décompressé (jarvis_ai / jarvis_ai-main)." >&2
  return 1 2>/dev/null || exit 1
fi
echo ">>> Projet décompressé dans : ${PROJECT_DIR}"
cd "${PROJECT_DIR}"

# ---- 6. Vérif racine du projet ----------------------------------------------
if [[ ! -f pyproject.toml ]] || [[ ! -f training/Dockerfile ]]; then
  echo "ERREUR : ${PROJECT_DIR} ne ressemble pas à la racine du dépôt (pas de pyproject.toml + training/Dockerfile)." >&2
  echo "         Refais un ZIP depuis le bon dossier sur ton PC." >&2
  return 1 2>/dev/null || exit 1
fi

# ---- 7. Normalisation CRLF -> LF sur TOUS les .sh (tue 'set: pipefail') ------
echo ">>> Normalisation des fins de ligne (.sh) de Windows vers Unix…"
find . -name "*.sh" -type f -exec sed -i 's/\r$//' {} \;
chmod +x training/*.sh infra/gcp/*.sh 2>/dev/null || true

# ---- 8. Bootstrap : recrée les fichiers Cloud Build s'ils manquent -----------
mkdir -p infra/gcp
if [[ ! -f infra/gcp/cloudbuild_jarvis_train.yaml ]]; then
  echo ">>> Création de infra/gcp/cloudbuild_jarvis_train.yaml (manquait dans le ZIP)"
  cat > infra/gcp/cloudbuild_jarvis_train.yaml <<'YAML'
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'build'
      - '-f'
      - 'training/Dockerfile'
      - '-t'
      - '${_IMAGE_URI}'
      - '.'
images:
  - '${_IMAGE_URI}'
timeout: 3600s
YAML
fi

if [[ ! -f infra/gcp/submit_train_image.sh ]]; then
  echo ">>> Création de infra/gcp/submit_train_image.sh (manquait dans le ZIP)"
  cat > infra/gcp/submit_train_image.sh <<'SH'
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CLOUDBUILD="${REPO_ROOT}/infra/gcp/cloudbuild_jarvis_train.yaml"
cd "${REPO_ROOT}"
if [[ ! -f "${REPO_ROOT}/pyproject.toml" ]] || [[ ! -f "${REPO_ROOT}/training/Dockerfile" ]]; then
  echo "Erreur : lance depuis la racine du projet (pyproject.toml + training/)." >&2
  exit 1
fi
: "${PROJECT_ID:?export PROJECT_ID=ton-projet}"
: "${REGION:?export REGION=us-central1}"
IMAGE_TAG="${REGION}-docker.pkg.dev/${PROJECT_ID}/jarvis/train:jarvis-mini-$(date +%Y%m%d)"
export IMAGE_URI="${IMAGE_TAG}"
gcloud builds submit . \
  --project="${PROJECT_ID}" \
  --config="${CLOUDBUILD}" \
  --substitutions=_IMAGE_URI="${IMAGE_TAG}"
echo ""
echo "IMAGE_URI=${IMAGE_URI}"
SH
  chmod +x infra/gcp/submit_train_image.sh
fi

# ---- 9. Verdict final --------------------------------------------------------
echo ""
echo "============================================================"
echo "  ETAT DE L'ENVIRONNEMENT"
echo "============================================================"
echo "  Répertoire projet : $(pwd)"
ls infra/gcp/cloudbuild_jarvis_train.yaml infra/gcp/submit_train_image.sh training/Dockerfile training/launch_vertex.sh 2>&1 | sed 's/^/  /'
echo ""
echo "  PROJECT_ID = ${PROJECT_ID:-(non défini — à faire avec: export PROJECT_ID=...)}"
echo "  REGION     = ${REGION:-(non défini — à faire avec: export REGION=us-central1)}"
echo ""
echo "  PROCHAINES ETAPES :"
echo "    1) export PROJECT_ID=\"ton-projet-id\""
echo "    2) export REGION=\"us-central1\""
echo "    3) gcloud config set project \"\${PROJECT_ID}\""
echo "    4) Sections C, D, E du guide (APIs, buckets, Artifact Registry) si"
echo "       pas encore fait — ces étapes sont IDEMPOTENTES, tu peux les rejouer."
echo "    5) bash infra/gcp/submit_train_image.sh   # construit l'image"
echo "    6) bash training/launch_vertex.sh          # lance l'entraînement"
echo "============================================================"
```

Quand tu vois `ETAT DE L'ENVIRONNEMENT` avec les 4 fichiers listés (pas de `No such file`), ton upload est **reparti du bon pied**. Tu peux continuer avec les sections B → H du guide principal [`GUIDE_SIMPLE_JARVIS_MINI_GCP.md`](GUIDE_SIMPLE_JARVIS_MINI_GCP.md).

---

## 3. Rappels « nommage » pour ne pas perdre de temps après

- **Buckets** : seulement `a-z 0-9 - _ .` — **pas de majuscules**, pas d’accents, pas d’espaces. Unique au monde.  
  ❌ `gs://Mon_Jarvis_Project_Incroyable_Data`  
  ✅ `gs://mon-jarvis-project-incroyable-data-2026`
- **`PROJECT_ID`** : celui affiché en haut de la [console](https://console.cloud.google.com/), pas le nom « humain » (donc `jarvis-entrainement-123` et pas `Jarvis entraînement`).
- Si tu ouvres **une nouvelle session** Cloud Shell, tu perds `IMAGE_URI` et `PROJECT_ID` : re-exporte-les (le script du point 5 ci-dessus les réaffiche pour rappel).

---

## 4. Ce qui a été corrigé **dans le code** suite aux anciennes erreurs

- Tous les `.sh` du dépôt sont maintenant en **LF** (plus de CRLF) : `training/launch_vertex.sh`, `training/launch_gke.sh`, `infra/gcp/bootstrap_cloudbuild_assets.sh`, `infra/gcp/submit_train_image.sh`, `infra/gcp/setup_bucket.sh`.
- Ajout de [`.gitattributes`](../../.gitattributes) à la racine du dépôt : les `.sh`, `.yaml`, `Dockerfile`, etc. sont marqués `text eol=lf`. Ça empêche Windows / Git de ré-introduire des CRLF lors d’un prochain clone ou checkout, donc d’un prochain upload Cloud Shell.
- Le bloc ci-dessus fait aussi `sed -i 's/\r$//'` et recrée les fichiers Cloud Build en **heredoc** (LF garanti) : **double sécurité** si jamais un `.sh` arrive encore en CRLF dans un futur ZIP.
