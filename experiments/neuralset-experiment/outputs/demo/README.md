# outputs/demo/ — committed synthetic reference outputs

This directory contains a small, committed snapshot of the demo pipeline's
output, generated entirely from **synthetic** data (`neuralset-scaffold demo`).
It exists so the experiment's results can be reviewed in-repo without installing
or running anything. It contains **no real neural recordings**.

| File | What it is |
|------|------------|
| `metrics.json` | Validation report, event/window summary, preprocessing steps, session-aware CV metrics per fold, confusion matrix, top features, NeuralSet adapter status. |
| `trace.png` | Multichannel synthetic EEG trace (Fz/FCz/Pz/Oz). |
| `psd.png` | Welch power spectral density per channel. |
| `confusion.png` | Confusion matrix for the baseline classifier. |
| `fold_accuracy.png` | Per-fold cross-validation accuracy vs. chance. |
| `feature_importance.png` | Top bandpower features by model weight. |

**Not committed:** the raw `demo_data.csv` (~12 MB) is intentionally excluded to
keep the repository lean. Regenerate the full set — including the CSV — with:

```bash
neuralset-scaffold demo --out outputs/demo
```

These labels ("Class A / B") are arbitrary experimental conditions. Nothing here
makes any medical, diagnostic, or mental-state claim.
