# Setup Checklist — NeXus-10 + BioTrace+ (4-channel)

A practical bring-up checklist for the four-channel prototype. Work top to
bottom the first time; on later sessions, the **Session quick-check** at the end
is usually enough.

> **Ground placement is manufacturer-defined.** Wherever this document says
> "ground", use the exact site and method specified in your Mind Media
> NeXus-10 / BioTrace+ manual for your hardware revision. Do not improvise.

---

## 1. Inventory

### Hardware
- [ ] Mind Media **NeXus-10** amplifier (charged / fresh batteries)
- [ ] Bluetooth dongle or USB link as used by your unit
- [ ] EEG input cable set for **4 active channels** + reference + ground
- [ ] Ear-clip / mastoid electrodes for **linked-ear reference (A1, A2)**
- [ ] Ground electrode per manual
- [ ] Cup electrodes or cap positions for **Fz, FCz, Pz, Oz**
- [ ] Conductive paste / gel, alcohol prep pads, gauze, measuring tape
- [ ] EEG cap or individual electrode holders sized to the participant

### Software
- [ ] **BioTrace+** installed and licensed on the acquisition PC
- [ ] BioTrace+ able to see the NeXus-10 (driver / Bluetooth pairing verified)
- [ ] This repo installed: `pip install -e ".[dev]"`
- [ ] `nexus-neuromirror --version` runs
- [ ] MNE import works: `python -c "import mne; print(mne.__version__)"`

### Accessories / logistics
- [ ] Quiet room, comfortable chair, monitor for feedback/task
- [ ] Consent form / research protocol reference on hand
- [ ] Anonymized subject ID scheme (e.g. `anon-001`) — **no PII in filenames**
- [ ] Session log sheet (montage, impedances, notes, block order)

---

## 2. NeXus-10 bring-up
- [ ] Power on the amplifier; confirm battery status in BioTrace+
- [ ] Confirm the device model and firmware shown match your records
- [ ] Establish the link (Bluetooth/USB) and confirm a stable connection
- [ ] Verify the sample clock is stable (no dropouts in a 10 s idle capture)

---

## 3. BioTrace+ four-channel configuration
- [ ] Create/duplicate a **4-channel EEG** signal library / channel set
- [ ] Map inputs to **Fz, FCz, Pz, Oz** (label channels clearly; the verifier
      tolerates prefixes/suffixes such as `EEG Fz-A1A2`)
- [ ] Set the **reference** to linked ears/mastoids (A1+A2) and keep it fixed
- [ ] Confirm **ground** wired to the manufacturer-approved site
- [ ] Set the EEG **sample rate** (commonly 256 Hz) and record it in the log
- [ ] Configure a hardware/software **notch** for local mains (50 or 60 Hz)
- [ ] Run an **impedance check**: target ≤ 5 kΩ, accept ≤ 10 kΩ; re-prep any
      channel above target
- [ ] Confirm live traces look like EEG (blink artifacts on frontal channels;
      alpha rises at **Oz** when the participant closes their eyes)

---

## 4. 60-second diagnostic recording
- [ ] Participant seated, relaxed, minimal movement
- [ ] Start recording; insert an **event marker** at each transition:
  - [ ] 0–20 s: **eyes open**, fixating a cross
  - [ ] 20–40 s: **eyes closed** (expect Oz alpha to increase)
  - [ ] 40–60 s: **eyes open** again
- [ ] Stop recording at ~60 s
- [ ] Note any artifacts, movement, or electrode issues in the log

---

## 5. EDF / EDF+ export (preferred)
- [ ] Export the recording as **EDF+** (preferred) or **EDF**
  - EDF+ preserves **annotations** (your event markers) — prefer it
  - If only EDF is available, ensure markers are written to a **status/marker
    channel** instead
- [ ] Use an anonymized filename (`anon-001_block-01_diagnostic.edf`)
- [ ] Confirm the physical dimension is **µV** for EEG channels
- [ ] Save into a **git-ignored** location (e.g. `data/`) — never commit it

---

## 6. Verify the export
```bash
nexus-neuromirror verify data/anon-001_block-01_diagnostic.edf \
    --config configs/project.example.yaml \
    --out reports/anon-001_block-01
```
- [ ] Exit code is **0** (no hard failures)
- [ ] All four expected channels resolved (no `[MISS]`)
- [ ] Sample rate matches the value you configured
- [ ] Per-channel RMS is plausible (~0.5–150 µV); no near-zero (dead) leads
- [ ] `markers` count is non-zero and matches the number of transitions
- [ ] Inspect the figures in the report:
  - [ ] `trace.png` — clean multichannel EEG
  - [ ] `psd.png` — **Oz** alpha bump (~10 Hz) visible for the eyes-closed block
  - [ ] `markers.png` — events at ~20 s and ~40 s

---

## 7. Event-marker verification
- [ ] Open `diagnostic.json` and confirm `markers.n_events`
- [ ] Confirm markers came from **annotations** (EDF+) or a **marker channel**
      (`candidate_marker_channels`)
- [ ] Confirm marker onsets align with your recorded transitions (±1 s)
- [ ] If markers are missing: re-check the BioTrace+ export options and prefer
      EDF+; re-export rather than re-recording where possible

---

## 8. Data-governance checklist
- [ ] Filenames and headers contain **no PII** (name, DOB, MRN)
- [ ] Recordings stored only under git-ignored paths (`data/`)
- [ ] Generated reports stored only under git-ignored paths (`reports/`)
- [ ] Consent recorded and retained per your protocol
- [ ] A subject-ID mapping (if any) is kept **separately** and access-controlled
- [ ] Backups (if any) are encrypted and access-limited
- [ ] Retention / deletion policy agreed and documented
- [ ] Before sharing any file externally, re-confirm de-identification

---

## Session quick-check (returning sessions)
- [ ] Amplifier charged, link stable
- [ ] Same 4-channel BioTrace+ profile loaded; **same reference**
- [ ] Ground per manual; impedances ≤ target
- [ ] Markers configured; export set to **EDF+**
- [ ] Post-export `verify` returns exit 0
