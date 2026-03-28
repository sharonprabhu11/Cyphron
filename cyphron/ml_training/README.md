## Cyphron ML Training

This folder supports two ML workflows:

1. `simulator`:
   Cyphron's lightweight internal generator for demo-only experiments.
2. `IBM AML-Data`:
   the fixed public AML benchmark used for more credible static training.

### Recommended benchmark path

1. Download the IBM HI-Small dataset:
   `bash ml_training/download_datasets.sh`
2. Convert it into Cyphron's canonical schema:
   `python ml_training/prepare_ibm_aml.py`
3. Build the graph artifact:
   `python ml_training/preprocess.py --input ml_training/data/ibm_hismall_transactions.csv --output-dir ml_training/data/ibm_hismall_processed`
4. Train GraphSAGE:
   `python ml_training/train.py --input ml_training/data/ibm_hismall_processed/processed_graph.npz --artifact-dir pipeline/ml/artifacts/ibm_hismall`

### Output artifacts

Training writes:

- `graphsage_model.pt`: GraphSAGE checkpoint
- `training_metrics.json`: evaluation metrics
- `shap_surrogate.pkl`: linear surrogate used for feature attribution
- `shap_background.npy`: background sample for SHAP

### Notes

- GraphSAGE is still the main model.
- SHAP is used for feature attribution on top of the trained model.
- The IBM dataset is static and public, but still synthetic, which is normal for AML research because real bank AML data is rarely public.
