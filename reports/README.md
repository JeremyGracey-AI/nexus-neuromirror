# reports/ — generated diagnostics (git-ignored)

The `nexus-neuromirror verify` command writes its output here: a
`diagnostic.json` plus `trace`, `psd`, and `markers` figures in PNG and SVG.

**Nothing in this directory except this README is committed to git.** Reports
are **derived from neural recordings** and can leak the same sensitive
information (signal shapes, timing, session structure). Treat them with the same
care as the raw data.

## Rules

- Do not commit generated reports.
- Reports are **reproducible**: regenerate them from the source recording rather
  than storing them long-term in shared locations.
- If you must share a report, confirm it contains **no PII** and is consistent
  with your consent/protocol.

## Typical contents

```
reports/anon-001_block-01/
  diagnostic.json     # machine-readable summary + validation result
  trace.png / .svg    # short multichannel EEG trace
  psd.png  / .svg     # per-channel power spectral density
  markers.png / .svg  # event/marker timeline (when markers are present)
```
