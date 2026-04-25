# Megatron-LM (NVIDIA) — intégration recommandée pour 7B–100B

1. Cloner en dehors du dépôt (ou sous-module git) :

```bash
git clone https://github.com/NVIDIA/Megatron-LM.git
```

2. Installer les dépendances listées par Megatron (PyTorch CUDA, Apex optionnel, Transformer Engine selon GPU).

3. Préparer les données au format Megatron (tokenisation `gpt2` ou SentencePiece, binaires `.bin` + index).

4. **Profils Jarvis** : [`configs/model_7b.yaml`](../configs/model_7b.yaml), [`configs/model_jarvis_mini_1_0.yaml`](../configs/model_jarvis_mini_1_0.yaml) (~15B), etc. Les hyperparamètres sont traduits vers Megatron par [`jarvis_yaml_to_args.py`](jarvis_yaml_to_args.py).

5. **Script d’entrée** : [`run_pretrain.sh`](run_pretrain.sh) lit `MODEL_CONFIG` (défaut Mini 1.0), `DATA_PATH`, `CHECKPOINT_DIR`, et lance `torchrun pretrain_gpt.py`. Variables utiles : `TENSOR_MODEL_PARALLEL_SIZE`, `PIPELINE_MODEL_PARALLEL_SIZE`, `TOKENIZER_TYPE` / `TOKENIZER_MODEL`.

6. DeepSpeed : [`training/deepspeed/ds_config_zero2.json`](../deepspeed/ds_config_zero2.json) (générique) ou [`ds_config_jarvis_mini_zero2.json`](../deepspeed/ds_config_jarvis_mini_zero2.json) (micro-batch explicite pour ~15B) ; ajuster selon la VRAM.

Les scripts [`launch_vertex.sh`](../launch_vertex.sh) et [`launch_gke.sh`](../launch_gke.sh) passent `DATA_PATH` / `CHECKPOINT_DIR` / `MODEL_CONFIG` au conteneur. Guide pas-à-pas GCP : [`infra/gcp/jarvis_mini_vertex.md`](../../infra/gcp/jarvis_mini_vertex.md).
