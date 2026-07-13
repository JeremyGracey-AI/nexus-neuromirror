# data/ — recordings (git-ignored)

Put EEG recordings here (EDF/EDF+ from BioTrace+, or intermediate `.fif`).

**Nothing in this directory except this README is committed to git.** The
repository `.gitignore` excludes recordings and common EEG formats. This is
deliberate:

- Neural recordings can be **sensitive personal data**. Even without a name,
  raw EEG plus session metadata may be re-identifiable.
- Recordings are large and binary; they do not belong in version control.

## Rules

- **No PII** in filenames or file headers. Use an anonymized ID scheme, e.g.
  `anon-001_block-01_diagnostic.edf`.
- Keep any subject-ID → identity mapping **outside this repo**, access-controlled.
- Prefer **EDF+** so event markers travel with the data as annotations.
- Follow your consent/protocol and retention policy for storage and deletion.

## Suggested layout

```
data/
  anon-001/
    anon-001_block-01_diagnostic.edf
    anon-001_block-02_task.edf
```

To verify a file:

```bash
nexus-neuromirror verify data/anon-001/anon-001_block-01_diagnostic.edf \
    --config configs/project.example.yaml \
    --out reports/anon-001_block-01
```
