# Jarvis Mini sur Google Cloud — guide tout simple

Ce guide est écrit **comme une liste à cocher**, pas comme un manuel de programmeur. Une étape à la fois.

> **Besoin de tout recommencer proprement dans Cloud Shell ?** Va directement voir
> [`RESET_ET_REDEMARRER.md`](RESET_ET_REDEMARRER.md) : il contient **un seul bloc** à copier-coller qui nettoie `~/jarvis_ai`, relance l’upload du ZIP, normalise les fins de ligne, et recrée les fichiers Cloud Build manquants — tout en un coup.

---

## Chemin court Cloud Shell (dans l’ordre)

À utiliser quand tu as déjà : **projet GCP + facturation**, et le code **`jarvis_ai`** sous `~/jarvis_ai` (ZIP ou `git clone`). Tout le détail (transfert ZIP, dépannage, variantes Docker) reste dans les sections **0 à H** plus bas.

### Les données d’entraînement : est-ce géré pour moi (anglais, ordi, etc.) ?

**Non, ce n’est pas automatique.** Vertex lance Megatron avec un préfixe `GCS_DATA` que **tu** remplis : il faut des données **déjà au format Megatron** (fichiers binaires + index, tokenizer par défaut `gpt2` — voir [`training/megatron/run_pretrain.sh`](../../training/megatron/run_pretrain.sh)). Le dépôt **ne télécharge pas** un corpus « anglais + informatique de base » tout prêt. Le script [`data/prepare_shards.py`](../../data/prepare_shards.py) sert à découper du texte en shards / manifest ; **ce n’est pas** équivalent au paquet binaire Megatron complet — la chaîne officielle est décrite dans [`training/megatron/README.md`](../../training/megatron/README.md).

**1 —** Aller à la racine du projet et corriger les fins de ligne des `.sh` (voir **A bis** si tu viens d’un ZIP Windows) :

```bash
cd ~/jarvis_ai
find . -name "*.sh" -type f -exec sed -i 's/\r$//' {} \;
chmod +x training/*.sh infra/gcp/*.sh 2>/dev/null || true
```

**2 —** Projet et région (exemple d’ID réel ; remplace par le tien si différent) :

```bash
export PROJECT_ID="onyx-parser-493701-c9"
export REGION="us-central1"
gcloud config set project "${PROJECT_ID}"
```

**3 —** Activer les APIs (même bloc que section **C**) :

```bash
gcloud services enable aiplatform.googleapis.com \
  artifactregistry.googleapis.com \
  storage.googleapis.com \
  cloudbuild.googleapis.com \
  --project="${PROJECT_ID}"
```

**4 —** Créer les buckets et fixer `GCS_DATA` / `GCS_CKPT` sans les taper à la main : le fichier [`infra/gcp/cloudshell_env.sh`](cloudshell_env.sh) pose des noms du type `${PROJECT_ID}-jarvis-data`. Si `gsutil mb` échoue parce que le nom est **déjà pris par un autre compte Google**, exporte `BUCKET_DATA` / `BUCKET_CKPT` **avant** le `source` (ex. `${PROJECT_ID}-jarvis-data-tonpseudo`) :

```bash
cd ~/jarvis_ai
source infra/gcp/cloudshell_env.sh
gsutil mb -p "${PROJECT_ID}" -l "${REGION}" "gs://${BUCKET_DATA}/" 2>/dev/null || true
gsutil mb -p "${PROJECT_ID}" -l "${REGION}" "gs://${BUCKET_CKPT}/" 2>/dev/null || true
echo "GCS_DATA=${GCS_DATA}"
echo "GCS_CKPT=${GCS_CKPT}"
```

**5 —** Dépôt Artifact Registry + image (sections **E** puis **F**) :

```bash
gcloud artifacts repositories create jarvis \
  --repository-format=docker \
  --location="${REGION}" \
  --project="${PROJECT_ID}" \
  --description="Jarvis training" 2>/dev/null || true

chmod +x infra/gcp/submit_train_image.sh 2>/dev/null || true
bash infra/gcp/submit_train_image.sh
```

À la fin du build, Cloud Shell affiche `IMAGE_URI=...` : garde cette valeur (ou exporte-la de nouveau si tu rouvres une session, en reprenant le tag dans [Artifact Registry](https://console.cloud.google.com/artifacts)).

**6 —** Vérifier que les **buckets** existent (le préfixe peut être vide tant que le bucket est là ; `gcloud storage ls` sur un préfixe sans objet affichait une erreur trompeuse) :

```bash
_jarvis_bucket_from_gs_uri() { local x="${1#gs://}"; echo "${x%%/*}"; }
for _label in "données" "checkpoints"; do
  if [[ "${_label}" == "données" ]]; then _u="${GCS_DATA}"; else _u="${GCS_CKPT}"; fi
  _b="$(_jarvis_bucket_from_gs_uri "${_u}")"
  if gcloud storage buckets describe "gs://${_b}" --project="${PROJECT_ID}" &>/dev/null; then
    echo "OK bucket ${_label} : gs://${_b}"
  else
    echo "ERREUR : bucket absent ou sans accès : gs://${_b} (${_label})" >&2
  fi
done
unset _label _u _b
```

**7 —** Lancer Vertex (même commande que section **H**) :

```bash
cd ~/jarvis_ai
bash training/launch_vertex.sh
```

Le script [`training/launch_vertex.sh`](../../training/launch_vertex.sh) passe les variables au conteneur via `bash -c` et des `export` (la commande `gcloud ai custom-jobs create` **n’a pas** de flag `--env-vars`).

Ensuite : [Vertex AI — Custom jobs](https://console.cloud.google.com/vertex-ai/training/custom-jobs).

---

## D’abord, qu’est-ce qu’on fait ?

Tu ne « télécharges » pas Jarvis sur ton ordi comme un jeu.

Dans l’ordre, pour toi ça donne plutôt :

0. Tu **crées un projet** Google Cloud et tu relies la **facturation** (étape 0 plus bas).  
0 bis. Tu **transfères** ton dossier / `jarvis_ai.zip` jusqu’à **Cloud Shell** (ce n’est pas automatique depuis Drive ou Claude — voir étape 0 bis).  
1. Tu prépares des **casiers** (buckets) pour tes données et les sauvegardes du modèle.  
2. Tu construis une **image Docker** (la « recette ») que Google peut lancer sur des **GPU**.  
3. Tu lances l’**entraînement**. Google allume des serveurs avec GPU pour toi.

Tout ça se passe **sur ton compte Google Cloud**. Il n’y a pas un autre site magique qui remplace Google pour cette partie : c’est bien **leur** cloud qui tourne les GPU. Par contre, tu peux tout faire **dans le navigateur** sans installer plein de trucs sur ton PC — on voit ça juste en dessous.

---

## La façon la plus simple (recommandée pour commencer)

**Idée :** tu restes sur le **site de Google Cloud** et tu utilises **Cloud Shell**.

- **Cloud Shell** = une petite fenêtre de terminal **déjà dans ton navigateur**. Tu n’as pas besoin d’installer `gcloud` sur Windows si tu ne veux pas.  
- Lien pour ouvrir la console : [https://console.cloud.google.com/](https://console.cloud.google.com/)  
- Une fois connecté, en haut à droite tu peux cliquer sur **l’icône `>_`** pour ouvrir **Cloud Shell**.

**Autre option :** installer Google Cloud CLI sur ton ordi ([page d’installation](https://cloud.google.com/sdk/docs/install)). C’est la même chose qu’Cloud Shell, mais sur ta machine. Choisis ce qui te stress le moins.

**Ce qu’on ne simplifie pas :** pour **Jarvis Mini**, il faut quand même le **code du dossier `jarvis_ai`** (par ex. téléchargé en ZIP ou cloné avec Git) au moment où tu construis l’image. Il n’existe pas un bouton « Jarvis Mini » tout fait sur un autre site : le projet est dans ce dépôt. Si un jour quelqu’un te propose « un site qui fait tout sans ce code », méfie-toi : ce ne serait pas exactement ce pipeline.

---

## Étape 0 — Créer ton **projet** Google Cloud (si tu n’en as pas encore)

Sans **projet**, tu ne peux pas lancer de machines ni de stockage : c’est le « dossier » où tout le reste vit.

### 0a — Créer le projet en cliquant (le plus simple)

1. Ouvre : **[Créer un projet](https://console.cloud.google.com/projectcreate)**  
2. Donne un **nom** (ex. « Jarvis entraînement »).  
3. Note l’**ID du projet** (souvent en minuscules avec des tirets, ex. `jarvis-entrainement-tonpseudo`) — c’est **celui** que tu mettras dans `TON_PROJECT_ID` plus bas.  
4. Clique sur **Créer**.

Tu peux aussi voir ou créer des projets ici : [Gestionnaire de ressources — projets](https://console.cloud.google.com/cloud-resource-manager).

### 0b — Lier la **facturation** (obligatoire pour GPU et beaucoup de services)

1. Ouvre : [Facturation](https://console.cloud.google.com/billing)  
2. Associe un **compte de facturation** à ton projet (carte bancaire). Sans ça, les étapes suivantes échoueront souvent.

### 0c — Créer le projet en **commandes** (optionnel, même résultat que 0a)

À coller dans [Cloud Shell](https://shell.cloud.google.com/) **après** t’être connecté (tu peux ouvrir Cloud Shell même avec un projet temporaire, puis changer de projet après).

```bash
# Remplace par un ID unique (lettres minuscules, chiffres, tirets). Ex. : jarvis-demo-marie
export PROJECT_ID="TON_NOUVEAU_PROJECT_ID"
gcloud projects create "${PROJECT_ID}" --name="Jarvis entrainement"
gcloud config set project "${PROJECT_ID}"
```

Lier la facturation (récupère d’abord l’ID du compte de facturation) :

```bash
gcloud billing accounts list
# Note la colonne ACCOUNT_ID du compte que tu utilises, puis :
export BILLING_ACCOUNT_ID="XXXXXX-XXXXXX-XXXXXX"
gcloud billing projects link "${PROJECT_ID}" --billing-account="${BILLING_ACCOUNT_ID}"
```

---

## Étape 0 bis — Mettre ton **`jarvis_ai.zip`** dans Cloud Shell (transfert du projet)

### Pourquoi ce n’est pas « automatique » avec Drive ou Claude

- **Google Drive**, **Gmail**, **Claude** (dans le navigateur), **Google Cloud** utilisent le **même compte Google** pour te connecter, mais ce sont des **endroits différents**.  
- Un ZIP déposé dans **Google Drive** ou utilisé dans **Claude Code / une conversation** **n’apparaît pas tout seul** dans Cloud Shell.  
- **Cloud Shell** = une petite machine dans le cloud : il faut **une action** pour y copier ton fichier : upload depuis ton PC, ou `gsutil` depuis un bucket, ou `git clone`.

### Méthode 1 — Tu télécharges le ZIP sur ton ordinateur, puis tu l’envoies à Cloud Shell (souvent la plus simple)

1. Si le ZIP est sur **Google Drive** : ouvre [Google Drive](https://drive.google.com/) → clic droit sur `jarvis_ai.zip` → **Télécharger** → le fichier est sur ton PC.  
2. Si le ZIP est **seulement dans une conversation** (Claude, etc.) : refais un **export / téléchargement** du projet en ZIP sur ton PC (sans fichier sur disque, Cloud Shell ne peut pas le deviner).  
3. Ouvre la [console Google Cloud](https://console.cloud.google.com/) et sélectionne **ton projet** en haut.  
4. Ouvre **Cloud Shell** (icône **`>_`** en haut à droite).  
5. Dans Cloud Shell : menu **⋮** (trois points) → **Upload** → choisis **`jarvis_ai.zip`** sur ton PC.  
6. Le fichier arrive en général dans ton dossier personnel : `~/jarvis_ai.zip`.

### Méthode 2 — Passer par un **bucket** Cloud Storage (utile si Upload est lent ou capricieux)

1. Crée un bucket (ou un dossier dans un bucket) : [Stockage — navigateur](https://console.cloud.google.com/storage/browser).  
2. Clique **Uploader** / **Upload** et envoie **`jarvis_ai.zip`** depuis ton PC.  
3. Dans Cloud Shell (avec le bon projet sélectionné) :

```bash
cd ~
gsutil cp "gs://NOM_DE_TON_BUCKET/jarvis_ai.zip" .
ls -la jarvis_ai.zip
```

*(Remplace `NOM_DE_TON_BUCKET` par le nom du bucket ; si le fichier est dans un sous-dossier, mets le chemin complet, ex. `gs://mon-bucket/uploads/jarvis_ai.zip`.)*

### Méthode 3 — **Git** (si ton code est déjà sur GitHub / GitLab / etc.)

```bash
cd ~
git clone "https://github.com/TON_COMPTE/jarvis_ai.git"
cd jarvis_ai
```

(adapte l’URL ; pas besoin de ZIP.)

### Ensuite : tu enchaînes avec la section suivante

Quand `jarvis_ai.zip` est dans ton répertoire Cloud Shell (ou que tu as cloné le dépôt), passe à **A — Dézipper** ci-dessous.

---

## Commandes pour le terminal Cloud Shell (après projet + ZIP ou clone)

Tu peux **coller les blocs dans l’ordre** dans [Cloud Shell](https://shell.cloud.google.com/) (icône `>_` en haut à droite de la [console](https://console.cloud.google.com/)).  
Ordre logique du guide : **créer le projet (étape 0)** → **transférer le ZIP (0 bis)** → **A, B, C…** ci-dessous.

**Règle d’or :** remplace les textes en **MAJUSCULES** (`TON_PROJECT_ID`, noms de buckets, etc.) par **tes** vraies valeurs avant de lancer, ou adapte ligne par ligne.

### A — Dézipper et aller dans le projet

```bash
cd ~
unzip -o jarvis_ai.zip
ls
```

- Si tu vois un dossier **`jarvis_ai`**, fais : `cd jarvis_ai`  
- Si le dossier s’appelle plutôt **`jarvis_ai-main`** (souvent quand on télécharge un ZIP depuis GitHub), fais : `cd jarvis_ai-main`  
- Si les fichiers du projet sont tout de suite là (sans sous-dossier), tu es déjà au bon endroit. Vérifie qu’il existe bien un dossier **`training`** : `ls training`

### A bis — Normaliser les fins de ligne des scripts (une seule fois, obligatoire)

Les `.sh` du ZIP proviennent de Windows et ont des fins de ligne **CRLF** que bash refuse (erreurs du type `$'\r': command not found` ou `set: pipefail`). À lancer **une seule fois** juste après `cd ~/jarvis_ai` :

```bash
cd ~/jarvis_ai
find . -name "*.sh" -type f -print -exec sed -i 's/\r$//' {} \;
chmod +x training/*.sh infra/gcp/*.sh 2>/dev/null || true
```

Si tu vois plus tard un message `$'\r': command not found` ou `set: pipefail`, c’est que tu as ré-uploadé un `.sh` depuis Windows : relance simplement ce bloc.

**Avant d’uploader le ZIP (sur ton PC) :** ouvre le dossier `jarvis_ai\infra\gcp\` dans l’explorateur Windows et vérifie que tu vois bien **`cloudbuild_jarvis_train.yaml`** (et idéalement `bootstrap_cloudbuild_assets.sh`, `submit_train_image.sh`). Si ces noms n’y sont pas, tu compresses le **mauvais dossier** ou une **vieille copie** : va à la racine du projet à jour (celui qui contient `pyproject.toml` à la racine), puis refais l’archive en incluant tout le dossier.

**Contrôle du ZIP dans Cloud Shell (optionnel) :** juste après l’upload de `jarvis_ai.zip` dans `~` :

```bash
unzip -l ~/jarvis_ai.zip | grep -E 'cloudbuild_jarvis_train|submit_train_image|bootstrap_cloudbuild' || echo "ATTENTION : ce ZIP ne contient pas les fichiers Cloud Build."
```

Si la ligne `ATTENTION` s’affiche, **ne perds pas de temps à dézipper** : refais le ZIP sur ton PC (voir ci-dessus) ou passe au **dépannage de la section F**.

**Vérification rapide (avant Cloud Build) :** depuis la racine du projet (là où tu vois `pyproject.toml` et le dossier `training`), lance :

```bash
pwd
ls training infra/gcp/cloudbuild_jarvis_train.yaml infra/gcp/bootstrap_cloudbuild_assets.sh infra/gcp/submit_train_image.sh
```

Si `ls` dit **« No such file »** pour ces fichiers, ton **ZIP est incomplet** ou tu n’es pas à la racine du dépôt. Un ZIP **seulement** déposé dans un bucket Google Cloud ne remplace pas ça : il faut la bonne archive **dézippée** dans Cloud Shell, ou le **dépannage section F**.

**Repérer la racine du projet sans te tromper :** la racine, c’est le dossier qui contient **à la fois** `pyproject.toml` et `training/`. Si tu es dans `~/jarvis_ai/infra/gcp`, tu es **trop bas** : remonte avec `cd ~/jarvis_ai` (ou `cd ..` deux fois).

### B — Choisir le projet Google et la région

*(C’est le **même** `PROJECT_ID` que celui que tu as créé à l’**étape 0**, ou celui affiché dans [Paramètres du projet](https://console.cloud.google.com/iam-admin/settings).)*

```bash
export PROJECT_ID="TON_PROJECT_ID"
export REGION="us-central1"
gcloud config set project "${PROJECT_ID}"
```

### C — Activer les APIs nécessaires

```bash
gcloud services enable aiplatform.googleapis.com \
  artifactregistry.googleapis.com \
  storage.googleapis.com \
  cloudbuild.googleapis.com \
  --project="${PROJECT_ID}"
```

### D — Créer deux buckets (noms uniques dans le monde entier)

**Le plus simple pour éviter les typos :** après `export PROJECT_ID=...` (section **B**), charge les noms par défaut puis crée les buckets :

```bash
cd ~/jarvis_ai
source infra/gcp/cloudshell_env.sh
gsutil mb -p "${PROJECT_ID}" -l "${REGION}" "gs://${BUCKET_DATA}/" 2>/dev/null || true
gsutil mb -p "${PROJECT_ID}" -l "${REGION}" "gs://${BUCKET_CKPT}/" 2>/dev/null || true
```

Tu auras alors `GCS_DATA` et `GCS_CKPT` prêts (même logique que le **chemin court**, étape 4). Si `gsutil mb` indique que le nom existe déjà **chez un autre utilisateur**, exporte `BUCKET_DATA` et `BUCKET_CKPT` **avant** `source infra/gcp/cloudshell_env.sh` (ex. suffixe `-2026` ou ton pseudo).

**Si tu préfères choisir les noms à la main :**

**Règles de nommage Google Cloud Storage (à respecter strictement) :**

- **Uniquement minuscules** : `Mon_Jarvis_Data` est **invalide** (majuscules interdites).  
- Caractères autorisés : lettres minuscules `a-z`, chiffres `0-9`, tirets `-`, underscores `_`, points `.`.  
- Pas d’espaces, pas d’accents, pas de lettres capitales.  
- Unique au monde : si le nom est déjà pris, ajoute un suffixe (ton pseudo, l’année, etc.).  
- Exemples valides : `mon-jarvis-data-2026`, `tony-jarvis-ckpt-01`.

```bash
export BUCKET_DATA="NOM_UNIQUE_BUCKET_DONNEES"   # ex. mon-jarvis-data-2026
export BUCKET_CKPT="NOM_UNIQUE_BUCKET_CHECKPOINTS" # ex. mon-jarvis-ckpt-2026

gsutil mb -p "${PROJECT_ID}" -l "${REGION}" "gs://${BUCKET_DATA}/" 2>/dev/null || true
gsutil mb -p "${PROJECT_ID}" -l "${REGION}" "gs://${BUCKET_CKPT}/" 2>/dev/null || true
export GCS_DATA="gs://${BUCKET_DATA}/jarvis/megatron_data"
export GCS_CKPT="gs://${BUCKET_CKPT}/jarvis/runs/mini-1"
```

*(Tu peux aussi créer les buckets en cliquant dans [Stockage](https://console.cloud.google.com/storage/browser) si tu préfères.)*

### E — Créer le dépôt d’images « jarvis » (Artifact Registry)

```bash
gcloud artifacts repositories create jarvis \
  --repository-format=docker \
  --location="${REGION}" \
  --project="${PROJECT_ID}" \
  --description="Jarvis training" 2>/dev/null || echo "Dépôt déjà là ou créé."
```

### F — Construire l’image d’entraînement avec Cloud Build

Ça évite d’installer Docker chez toi : Google construit l’image dans le cloud. La commande utilise le fichier [`infra/gcp/cloudbuild_jarvis_train.yaml`](cloudbuild_jarvis_train.yaml) du projet.

**Important :** tout se fait **depuis la racine du dossier `jarvis_ai`** (là où se trouvent `pyproject.toml`, `training/`, etc.), pas depuis `~` seul. Après `unzip`, fais par exemple `cd ~/jarvis_ai`.

**Si les fichiers manquent encore après `unzip` — option 1 (la plus sûre : coller dans Cloud Shell) :** ce bloc **crée lui-même** `cloudbuild_jarvis_train.yaml` et `submit_train_image.sh` dans ton dossier Cloud Shell, sans upload, sans ZIP. À coller tel quel dans le terminal :

```bash
cd ~/jarvis_ai
mkdir -p infra/gcp

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

ls infra/gcp/cloudbuild_jarvis_train.yaml infra/gcp/submit_train_image.sh
```

Important : utilise `<<'YAML'` et `<<'SH'` avec les **guillemets simples** pour empêcher Cloud Shell d’interpréter `${_IMAGE_URI}` pendant le collage. Cette méthode **évite totalement le problème CRLF**.

**Option 2 (si tu as uploadé le script et vu une erreur `$'\r'`) :** le fichier a des fins de ligne **Windows (CRLF)**. Convertis-le en LF puis relance :

```bash
cd ~/jarvis_ai
sed -i 's/\r$//' infra/gcp/bootstrap_cloudbuild_assets.sh 2>/dev/null || true
sed -i 's/\r$//' infra/gcp/submit_train_image.sh 2>/dev/null || true
# Si dos2unix est installé, c'est équivalent :
# command -v dos2unix && dos2unix infra/gcp/*.sh
chmod +x infra/gcp/bootstrap_cloudbuild_assets.sh infra/gcp/submit_train_image.sh
bash infra/gcp/bootstrap_cloudbuild_assets.sh
```

- Si tu vois **« No such file »** pour `bootstrap_cloudbuild_assets.sh`, utilise **Option 1** (collage direct) — elle n’a pas besoin du fichier.

**Méthode recommandée — construire l’image :** le script se place à la bonne racine et peut déclencher le bootstrap si besoin.

```bash
cd ~/jarvis_ai   # adapte si ton dossier s’appelle jarvis_ai-main, etc.

chmod +x infra/gcp/submit_train_image.sh 2>/dev/null || true
bash infra/gcp/submit_train_image.sh
```

*(Les variables `PROJECT_ID` et `REGION` doivent déjà être définies — section B.)*

**Méthode manuelle (équivalent) :**

```bash
cd ~/jarvis_ai   # racine : pyproject.toml + dossier training/

export IMAGE_TAG="${REGION}-docker.pkg.dev/${PROJECT_ID}/jarvis/train:jarvis-mini-$(date +%Y%m%d)"
export IMAGE_URI="${IMAGE_TAG}"

gcloud builds submit . \
  --project="${PROJECT_ID}" \
  --config=infra/gcp/cloudbuild_jarvis_train.yaml \
  --substitutions=_IMAGE_URI="${IMAGE_TAG}"
```

**Pourquoi ça arrive souvent :** le fichier `jarvis_ai.zip` que tu envoies à Cloud Shell est **une ancienne archive** ou a été créé à partir d’un dossier qui **n’était pas** la copie complète du dépôt (fichiers GCP ajoutés après, mauvais dossier source, outil qui n’a pas tout inclus). La liste `unzip` que tu colles dans le chat **ne montre jamais** `cloudbuild_jarvis_train.yaml` tant que le ZIP n’inclut pas ce chemin — ce n’est pas une erreur de `cd`, c’est le **contenu du ZIP**.

**Si tu vois « No such file » pour `cloudbuild_jarvis_train.yaml`**, applique dans l’ordre : **bootstrap** (paragraphe ci-dessus), puis **`submit_train_image.sh`**. En dernier recours : refais le **ZIP sur ton PC** à partir du dossier complet (vérifie `infra\gcp\` dans l’explorateur), ré-upload, `unzip` à nouveau. Avoir une copie du ZIP **dans un bucket** ne met pas à jour le dossier sous `~` tant que tu n’as pas retéléchargé et **re-décompressé** la bonne archive.

Attends la fin (statut **SUCCESS**). Tu peux suivre ici : [Historique Cloud Build](https://console.cloud.google.com/cloud-build/builds).

**Si l’étape échoue avec une erreur de droits sur Artifact Registry**, ouvre **IAM** et vérifie que le compte de service **Cloud Build** a le rôle **Artifact Registry Writer** sur le projet (souvent OK par défaut).

### G — Script de lancement

Après **A bis**, `training/launch_vertex.sh` est en général déjà exécutable. Sinon : `chmod +x training/launch_vertex.sh`.

### H — Lancer l’entraînement Jarvis Mini 1.0

`IMAGE_URI` doit être **exactement** le même que l’image construite à l’étape F (dans la même fenêtre Cloud Shell, `IMAGE_URI` est déjà bon si tu n’as pas fermé le terminal). Sinon, refais :

```bash
export IMAGE_TAG="${REGION}-docker.pkg.dev/${PROJECT_ID}/jarvis/train:jarvis-mini-$(date +%Y%m%d)"
export IMAGE_URI="${IMAGE_TAG}"
```

*(et remplace la date par celle du tag que tu vois dans [Artifact Registry](https://console.cloud.google.com/artifacts) si besoin).*

Si tu as suivi **D** avec `source infra/gcp/cloudshell_env.sh`, `GCS_DATA` et `GCS_CKPT` sont déjà définis. Sinon, remplace par **tes** URIs (données au format Megatron sur GCS).

**Rappel noms de buckets :** minuscules uniquement (pas de `Mon_Jarvis_Data`, écris `mon-jarvis-data`). Voir la section D.

```bash
export GCS_DATA="${GCS_DATA:-gs://NOM_UNIQUE_BUCKET_DONNEES/jarvis/megatron_data}"
export GCS_CKPT="${GCS_CKPT:-gs://NOM_UNIQUE_BUCKET_CHECKPOINTS/jarvis/runs/mini-1}"
export MODEL_CONFIG="/workspace/jarvis/configs/model_jarvis_mini_1_0.yaml"

echo "PROJECT_ID=$PROJECT_ID  REGION=$REGION  IMAGE_URI=$IMAGE_URI"
# Vérifie l’existence du *bucket* (pas la liste d’objets du préfixe, qui peut être vide)
_jarvis_bucket_from_gs_uri() { local x="${1#gs://}"; echo "${x%%/*}"; }
_b="$(_jarvis_bucket_from_gs_uri "${GCS_DATA}")"
gcloud storage buckets describe "gs://${_b}" --project="${PROJECT_ID}" &>/dev/null && echo "OK bucket données gs://${_b}" || echo "ERREUR : bucket données introuvable gs://${_b}" >&2
_b="$(_jarvis_bucket_from_gs_uri "${GCS_CKPT}")"
gcloud storage buckets describe "gs://${_b}" --project="${PROJECT_ID}" &>/dev/null && echo "OK bucket checkpoints gs://${_b}" || echo "ERREUR : bucket checkpoints introuvable gs://${_b}" >&2
unset _b

bash training/launch_vertex.sh
```

**Si tu vois `set: pipefail` ou `$'\r': command not found`** en lançant `launch_vertex.sh`, relance la normalisation CRLF de la **section A bis** :

```bash
cd ~/jarvis_ai
find . -name "*.sh" -type f -print -exec sed -i 's/\r$//' {} \;
chmod +x training/*.sh infra/gcp/*.sh 2>/dev/null || true
```

Ensuite regarde le job ici : [Vertex AI — Custom jobs](https://console.cloud.google.com/vertex-ai/training/custom-jobs).

---

### Variante : construire l’image avec Docker **dans** Cloud Shell

Si tu préfères ne pas passer par Cloud Build (plus long sur ta session Cloud Shell, gros téléchargements) :

```bash
cd ~/jarvis_ai   # même racine que pour Cloud Build

gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet
docker build -f training/Dockerfile -t "${IMAGE_TAG}" .
docker push "${IMAGE_TAG}"
```

Même `IMAGE_URI` que plus haut pour `launch_vertex.sh`.

---

## Rappels si tu as lu le guide par le bas

- **Projet + facturation** : si tu ne les as pas encore faits, remonte à l’**étape 0** et **0 bis** (création de projet, carte bancaire, transfert du ZIP).  
- **Patience** : la première fois, tout est long (APIs, quotas, gros téléchargements Docker).

---

## Étape 1 — Dire à Google : « j’autorise les bons outils »

*(Tu as peut-être **déjà** tout activé avec la **section C** (commandes) plus haut : dans ce cas, tu peux sauter cette étape ou juste vérifier que les APIs sont bien listées comme activées.)*

Tu dois **activer** quelques briques. Le plus simple : ouvre chaque lien, clique sur **Activer** / **Enable**, attends que ce soit vert.

| Quoi | Lien (tu peux coller dans ton navigateur) |
|------|-------------------------------------------|
| Vertex AI (pour l’entraînement) | [Ouvrir Vertex AI API](https://console.cloud.google.com/apis/library/aiplatform.googleapis.com) |
| Artifact Registry (pour stocker l’image Docker) | [Ouvrir Artifact Registry API](https://console.cloud.google.com/apis/library/artifactregistry.googleapis.com) |
| Stockage (pour les fichiers) | [Ouvrir Cloud Storage API](https://console.cloud.google.com/apis/library/storage.googleapis.com) |
| Cloud Build (pour construire l’image sans Docker sur ton PC, si tu choisis cette voie) | [Ouvrir Cloud Build API](https://console.cloud.google.com/apis/library/cloudbuild.googleapis.com) |

**Astuce :** si le site te demande quel projet, choisis-le en haut. Tu n’es pas obligé de modifier l’URL : le menu projet suffit.

---

## Étape 2 — Créer deux « seaux » pour tes fichiers (buckets)

Tu as besoin d’un endroit pour :

- les **données** d’entraînement (format spécial Megatron, pas juste du texte brut) ;
- les **checkpoints** (les sauvegardes du modèle).

**Le plus simple en cliquant :**

1. Ouvre : [Stockage — navigateur de buckets](https://console.cloud.google.com/storage/browser)  
2. Clique sur **Créer un bucket** / **Create bucket**.  
3. Donne un nom unique (Google te dira si le nom est pris).  
4. Répète pour le **deuxième** bucket (données d’un côté, checkpoints de l’autre).

Tu noteras les adresses du type `gs://nom-de-ton-bucket/...` — tu en auras besoin plus tard.

Pour moins les taper à la main : **Chemin court** (étape 4) + [`infra/gcp/cloudshell_env.sh`](cloudshell_env.sh). Le dossier `infra/gcp` a aussi un `README` et Terraform si tu veux aller plus loin.

---

## Étape 3 — Demander la permission d’utiliser des GPU (quota)

Sans **quota GPU**, ton entraînement peut rester bloqué ou refusé.

1. Ouvre : [Quotas](https://console.cloud.google.com/iam-admin/quotas)  
2. Cherche quelque chose comme **GPU** ou **NVIDIA** pour la région où tu veux travailler (souvent **us-central1** pour les exemples du projet).  
3. Si la limite est à **0**, tu dois **demander une augmentation** (bouton du site). Ça peut prendre un peu de temps.

Aide officielle (en anglais) : [https://cloud.google.com/compute/docs/gpus/gpu_quota](https://cloud.google.com/compute/docs/gpus/gpu_quota)

---

## Étape 4 — Préparer l’image « Jarvis Mini 1.0 »

L’entraînement utilise le fichier **Jarvis Mini 1.0** à l’intérieur du projet :  
`configs/model_jarvis_mini_1_0.yaml`.

Ici tu as **deux chemins**. Choisis le plus simple pour toi.

### Option A — Tu n’as pas Docker sur ton ordi

1. Mets le dossier `jarvis_ai` quelque part où **Cloud Shell** ou **Cloud Build** peut le lire (par ex. tu upload le ZIP dans un bucket, ou tu utilises `git clone` dans Cloud Shell).  
2. Utilise **Cloud Build** pour construire l’image (le guide technique [`jarvis_mini_vertex.md`](jarvis_mini_vertex.md) donne la commande `gcloud builds submit`).  
3. Suis la construction ici : [Historique Cloud Build](https://console.cloud.google.com/cloud-build/builds)

### Option B — Tu as Docker sur ton ordi

Tu construis l’image chez toi et tu l’envoies vers Google. Les commandes exactes sont dans [`jarvis_mini_vertex.md`](jarvis_mini_vertex.md) — c’est la partie « développeur » si tu en as besoin.

Avant, il faut un **dépôt** Artifact Registry (une « étagère » pour ton image) :

- Page pour voir tes dépôts : [Artifact Registry](https://console.cloud.google.com/artifacts)

---

## Étape 5 — Lancer l’entraînement (Jarvis Mini 1.0)

Le script du projet s’appelle `training/launch_vertex.sh`. Il utilise déjà **Jarvis Mini 1.0** par défaut dans le conteneur.

Tu dois lui donner :

- l’adresse des **données** sur ton bucket ;
- l’adresse où **sauver** les checkpoints ;
- l’**image** que tu as construite.

Les détails des commandes sont dans [`jarvis_mini_vertex.md`](jarvis_mini_vertex.md). En résumé pour toi : tu ouvres **Cloud Shell** dans le navigateur, tu vas dans le dossier du projet, tu règles les variables (nom du projet, région, liens `gs://...`), puis tu lances le script.

**Juste après avoir lancé**, ouvre cette page pour voir si ça tourne :

- [Vertex AI — Custom jobs (tes entraînements)](https://console.cloud.google.com/vertex-ai/training/custom-jobs)

---

## Étape 6 — Vérifier que ça avance

| Je veux voir… | J’ouvre… |
|---------------|----------|
| Si le job est vert, rouge, ou en cours | [Custom jobs](https://console.cloud.google.com/vertex-ai/training/custom-jobs) |
| Les fichiers sauvegardés (checkpoints) | [Stockage — buckets](https://console.cloud.google.com/storage/browser) puis tu ouvres ton bucket de checkpoints |
| Les messages d’erreur détaillés | [Logs](https://console.cloud.google.com/logs) (tu peux chercher le nom du job) |
| Combien ça coûte | [Rapports de facturation](https://console.cloud.google.com/billing/reports) |

---

## « Y a-t-il un site plus simple que tout ça ? »

- **Pour parler à Google Cloud :** le site principal, c’est [https://console.cloud.google.com/](https://console.cloud.google.com/) — tout passe par là (stockage, GPU, entraînement).  
- **Pour ne rien installer sur ton PC :** **Cloud Shell** (bouton `>_` dans la console) = terminal dans le navigateur.  
- **Pour aller plus loin sans te perdre :** le fichier [`jarvis_mini_vertex.md`](jarvis_mini_vertex.md) dans le même dossier — c’est la version **plus précise** pour quand tu es prêt.

Si quelque chose bloque (quota, erreur rouge, bucket introuvable), note **le message exact** à l’écran et la page où tu es : c’est plus facile à déboguer qu’une capture floue de « ça marche pas ».

---

## Rappel tout bête

- **Jarvis Mini 1.0** = réglages dans `configs/model_jarvis_mini_1_0.yaml` — c’est le « petit » modèle du projet (~15B), pas le géant 100B.  
- Les **données** ne sont **pas** fournies par le dépôt pour Vertex : tu dois les préparer au **format Megatron** et les mettre sous `GCS_DATA` — voir `training/megatron/README.md` et l’encadré **Les données d’entraînement** dans le **Chemin court** ci-dessus.

Bonne chance — une étape après l’autre, c’est suffisant.
