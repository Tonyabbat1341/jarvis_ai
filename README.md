# Jarvis 1.0

Pipeline données → entraînement sur GCP (objectif scale ~100B) → mémoire hiérarchique → agent autonome par tâche.

## Installation

Python **3.11+** est requis. Sous Windows, si `python` est en 3.7, utilisez par exemple `py -3.11 -m pip install -e ".[dev]"`.

```bash
pip install -e ".[dev,training]"
```

## Layout

| Path | Role |
|------|------|
| `configs/` | Hyperparamètres et profils modèle (`model_jarvis_mini_1_0.yaml` ≈15B, `model_7b.yaml`, `model_1b.yaml`) |
| `data/` | Préparation shards et manifests |
| `training/` | Entraînement (Megatron/DeepSpeed + entrée locale de validation) |
| `infra/gcp/` | Terraform et scripts `gcloud` |
| `src/jarvis/memory/` | `MemoryStore` (travail, RAG, épisodes) |
| `src/jarvis/agent/` | Boucle tâche, outils, sandbox |
| `eval/` | Scripts d’évaluation |

## Usage rapide

- Mémoire + agent (bac à sable mock) : voir `tests/test_agent.py` et `python -m jarvis.agent.cli`.
- Données : `python -m data.prepare_shards --help`
- Infra GCP : `infra/gcp/README.md`
- Montée en charge 100B : `infra/gcp/scale_checklist.md`
