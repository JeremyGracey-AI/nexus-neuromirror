# outputs/ (git-ignored)

Generated experiment artifacts land here: `metrics.json` plus diagnostic plots
(`trace.png`, `psd.png`, `confusion.png`, `fold_accuracy.png`,
`feature_importance.png`) and any synthetic demo data.

These are reproducible from the source recording and the config, so they are
git-ignored by default. Regenerate rather than committing them.

**Exception — committed reference demo.** `outputs/demo/` holds a small,
committed set of *synthetic* reference artifacts (five plots + `metrics.json`)
so the experiment's results can be inspected without running anything. They are
derived entirely from synthetic data and contain no real neural recordings. The
large raw `demo_data.csv` (~12 MB) is intentionally **not** committed — it is
regenerated locally with `neuralset-scaffold demo --out outputs/demo`. See
`outputs/demo/README.md`.
