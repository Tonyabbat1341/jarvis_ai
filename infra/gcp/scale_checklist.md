# Checklist montée en charge ~100B paramètres

## Estimation coût / FLOPs

- [ ] Estimer les FLOPs totaux du pré-entraînement (formules Megatron/Chinchilla : tokens × 6 × params pour forward+backward approx.).
- [ ] Choisir unité de prix : GPU A100/H100 à la carte vs TPU v4/v5e — comparer $/TFLOP effective (inclure bande passante GCS).
- [ ] Fixer une cible **tokens vus** (ex. 300B–1T tokens) et en déduire durée sur le cluster choisi.

## Quotas et capacité

- [ ] Demander augmentation de quota GPU/TPU dans la région cible (`gcloud compute project-info describe --project=...`).
- [ ] Valider bande passante réseau vers GCS (répartition des chargeurs de données, checkpoint fréquent mais pas excessif).

## Checkpointing et reprise

- [ ] Checkpoints asynchrones vers GCS avec rétention versionnée (lifecycle rules pour archiver les anciens).
- [ ] Test de reprise : tuer un job et relancer depuis le dernier checkpoint valide.
- [ ] Sauvegarder `rng state`, itération, et métadonnées d’optimiseur (Megatron/DeepSpeed).

## Stabilité à grande échelle

- [ ] Loss spike detection et gradient norm logging.
- [ ] Debugger : activations/weights NaN (bf16 recommandé sur H100/A100).
- [ ] Parallélisme : tensor parallel + pipeline parallel + data parallel — tableau de configuration validé sur 7B avant 100B.

## Données

- [ ] Manifests reproductibles (hash des shards) pour le mélange anglais + informatique.
- [ ] Filtrage PII / licences conformes aux sources.

## Post-training

- [ ] Éval automatique sur sous-ensembles (perplexité, benchmarks code).
- [ ] Alignement instruction / sécurité avant exposition agent autonome.
