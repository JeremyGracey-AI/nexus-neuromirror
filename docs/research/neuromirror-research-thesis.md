# NeXus NeuroMirror: A Research Thesis and Experimental Roadmap for Multimodal-Supervised Cognitive State Modeling and Closed-Loop Actionability Testing

**Status:** Draft research thesis (standalone) · **Platform:** NeXus-10 / BioTrace+, four-channel EEG (Fz, FCz, Pz, Oz) · **Prepared:** July 2026

---

## Abstract

Consumer- and prosumer-grade EEG systems are increasingly proposed as substrates for "AI-supervised" cognitive-state models and neurofeedback products, yet the scientific literature offers no settled methodology for validating what such systems actually measure, learn, or change. This thesis specifies a rigorous, falsifiable research program for the NeXus NeuroMirror platform — a four-channel (Fz/FCz/Pz/Oz) EEG system built on the legacy Mind Media NeXus-10/BioTrace+ amplifier, instrumented to align raw EEG with behavioral event markers, structured subjective reports, and AI-derived embeddings of experimental stimuli. We formalize a central, two-part hypothesis: (H1, *supervision*) multimodal, temporally aligned signals — EEG, behavior, subjective report, and stimulus embeddings — can be used to fit models that predict operationally defined cognitive-state labels above chance and above unimodal baselines; and (H2, *actionability*) closed-loop neurofeedback interventions driven by these learned states can produce measurable, specific, dose-dependent change in the target state or downstream behavior, distinguishable from placebo, sham-feedback, and regression-to-the-mean controls. We explicitly do not claim to "decode thoughts" or to identify neural correlates of consciousness; both are out of scope and are operationally fenced off from the platform's claims. We define operational constructs (arousal, engagement/attention, valence, error-related processing) in terms of observable EEG features, behavioral markers, and self-report scales; specify a staged experimental roadmap from signal-quality validation through supervised-model benchmarking to sham-controlled closed-loop trials; and enumerate the controls, metrics, pre-registration commitments, and stopping rules needed for each stage. We treat the four-channel, linked-ears-referenced montage as a hard constraint that bounds claims to broad, midline-topography phenomena and precludes source localization or fine-grained spatial inference, following established evidence that sub-32-channel arrays cannot resolve cortical sources with useful precision. We adopt NeuralSet-style structure-data decoupling — events, extractors, and temporally aligned tensors — as the data-engineering backbone that makes the EEG–behavior–report–embedding alignment auditable and reproducible ([Meta FAIR, NeuralSet](https://github.com/facebookresearch/neuroai/)). We close with data governance and ethics commitments appropriate to a non-clinical research prototype, and success/failure criteria that allow the program to be abandoned or redirected on principled, pre-specified grounds.

---

## 1. Motivation and Scope

### 1.1 Why this thesis is needed now

Two independent trends motivate — and complicate — the NeuroMirror program. First, "Neuro-AI" tooling has matured to the point where naturalistic, multimodal experiments (EEG/MEG/fMRI aligned with pretrained text/audio/image/video embeddings) are becoming standard infrastructure, exemplified by frameworks like NeuralSet that unify neural recordings and AI stimulus embeddings into a single temporally aligned, PyTorch-ready pipeline ([King et al., NeuralSet](https://github.com/facebookresearch/neuroai/)). This makes it technically straightforward to *fit* models relating brain signals to stimulus content and behavior. Second, the neurofeedback literature shows that fitting a model that correlates with a state is not the same as demonstrating that feeding a model's output back to a person as neurofeedback produces a specific, causal, learnable change in that state — a large fraction of sham-controlled neurofeedback trials fail to show learning specificity or fail to separate active feedback from placebo ([Pigott et al., 2018](https://pmc.ncbi.nlm.nih.gov/articles/PMC7783691/); [Sorger et al., 2019, "Control Freaks"](https://pmc.ncbi.nlm.nih.gov/articles/PMC6338498/); [Syrjänen et al., 2026](http://biorxiv.org/lookup/doi/10.64898/2026.01.07.698228)). NeuroMirror sits precisely at the seam between these two trends: it is built to *generate* the aligned multimodal dataset NeuralSet-style tooling expects, and it is intended to eventually *close the loop* — but closing the loop is a distinct, harder, and separately falsifiable scientific claim from fitting a supervised model. This thesis treats that seam as the central object of study rather than glossing over it.

### 1.2 Platform under study

- **Hardware:** Mind Media NeXus-10 amplifier with BioTrace+ acquisition software (legacy platform, no public real-time SDK confirmed).
- **Montage:** four EEG channels — Fz (midline frontal), FCz (fronto-central), Pz (midline parietal), Oz (midline occipital) — referenced to linked ears/mastoids (A1+A2), manufacturer-approved ground.
- **Data model:** aligned EEG + discrete behavioral event markers (stimulus onsets, responses, task states) + structured subjective reports (e.g., post-block Likert/VAS ratings) + AI-derived embeddings of experimental stimuli (text/image/audio) as auxiliary regressors/covariates.
- **Workflow:** currently **offline-first, blockwise**: record a block, export EDF/EDF+, analyze/verify, adapt parameters, record next block. Real-time closed-loop neurofeedback is an explicit future stage, not a current capability.
- **Existing tooling referenced (not modified by this thesis):** the `nexus-neuromirror` repository's verifier, montage config, and diagnostic reporting pipeline, which already implement channel/sample-rate validation, RMS/peak-to-peak diagnostics, marker detection, and reproducible JSON+figure reporting. This thesis defines the *science*, not the *software*, and does not propose edits to that codebase.

### 1.3 What this thesis is *not* claiming

To keep the program falsifiable and to prevent scope creep into unfalsifiable or overclaimed territory, we explicitly exclude two classes of claims:

1. **Not decoding in the strong sense.** We do not claim to reconstruct the content of thought, imagery, inner speech, or specific stimulus identity from EEG at the fidelity implied by "mind reading." Four-channel scalp EEG lacks the spatial and signal-to-noise properties required for that; even high-density (128–256 channel) EEG source imaging is limited to roughly 1–2 cm resolution under ideal conditions, well below what fine-grained content decoding requires ([Neurosity, EEG source localization](https://neurosity.co/guides/source-localization-eeg-how-it-works); [Farahibozorg et al., EEG spatial sampling review](https://pmc.ncbi.nlm.nih.gov/articles/PMC6458265/)). Any classifier output in this program is a coarse, probabilistic label over a small, pre-defined set of operationally defined states — not a reconstruction of mental content.
2. **Not a consciousness study.** We do not claim to identify neural correlates of consciousness (NCC) or to adjudicate between theories of consciousness (global workspace, integrated information, higher-order theories, etc.). The NCC literature itself has not converged on consensus scalp-EEG or MEG markers, and explicitly flags that scalp-level signals conflate deep and superficial sources (the "inverse problem"), which undermines strong NCC claims from four-channel EEG in particular ([Neural correlates of perceptual consciousness from within, eLife 2026](https://elifesciences.org/reviewed-preprints/109604); [Koch et al., 2016, NCC: progress and problems](https://puredhamma.net/wp-content/uploads/Neural-correlates-of-consciousness-Koch-et-al-2016.pdf)). NeuroMirror's constructs (arousal, engagement, valence, error-processing) are functional/behavioral, not phenomenological, and are defined without reference to subjective experience as ground truth beyond self-report as one *input signal* among several.

---

## 2. Central Hypothesis, Framed Scientifically

### 2.1 The two-part hypothesis

> **H1 (Supervision Hypothesis).** Temporally aligned multimodal signals — four-channel EEG features, discrete behavioral event markers, structured subjective reports, and AI-derived embeddings of experimental stimuli — jointly and non-trivially supervise machine-learned models of a small set of *operationally defined* cognitive/affective states, such that model predictions exceed the accuracy of (a) chance, (b) unimodal EEG-only baselines, and (c) demographic/prior-only baselines, on held-out sessions and held-out participants.

> **H2 (Actionability Hypothesis).** A closed-loop neurofeedback intervention that presents a participant with real-time (or blockwise-adapted) feedback derived from the H1 model's state estimate produces a *specific, dose-related* change in the targeted state or in a pre-registered downstream behavioral/cognitive outcome, relative to (a) a no-feedback control, (b) a sham/randomized-feedback control matched for task demands and attention, and (c) an active alternative-target control.

These are deliberately framed as **two separate, sequentially dependent hypotheses**. H2 can only be meaningfully tested once H1 has cleared pre-specified validity thresholds (Section 6), because a closed loop built on an invalid or unreliable state estimate cannot yield an interpretable test of actionability — a null H2 result would be uninformative if H1 has not first been shown to hold. This sequencing itself is a scientific commitment, motivated directly by the neurofeedback literature's well-documented "specificity problem," where studies proceed to intervention before establishing that the trained signal is learnable or valid, producing uninterpretable null or positive results ([Sorger et al., 2019](https://pmc.ncbi.nlm.nih.gov/articles/PMC6338498/); [Pigott et al., 2018](https://pmc.ncbi.nlm.nih.gov/articles/PMC7783691/)).

### 2.2 Why this framing, and not "decoding" or "consciousness"

- **Decoding** implies recovering *content* (what stimulus, what thought) from neural signals with a fidelity claim about representational specificity. NeuroMirror instead performs **state classification/regression** over a small, closed set of coarse labels defined jointly by task structure and self-report — closer to affective/cognitive-state monitoring than to content decoding. This distinction matters because the evidentiary bar, spatial resolution requirements, and failure modes differ sharply between the two ([EEG decoding of conscious vs. unconscious processing, 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC12325685/) illustrates a genuine *decoding* study, contrastable with the *state-classification* framing used here).
- **Consciousness research** requires (a) a theory-neutral or theory-explicit operationalization of conscious access/report, (b) controls for confounds like task difficulty, attention, and motor response, and (c) typically no-report paradigms or high-spatial-resolution recordings to disentangle perceptual content from access/report machinery. NeuroMirror's four-channel, report-dependent design cannot support these controls and therefore cannot license NCC claims.
- **State classification supervised by multimodal alignment + closed-loop actionability testing** is falsifiable, matches the actual evidentiary capacity of a four-channel EEG system, and directly inherits methodological lessons from the fMRI/EEG neurofeedback literature on specificity and placebo control ([Robineau et al., 2017](http://journal.frontiersin.org/article/10.3389/fnhum.2017.00131/full); [Enz et al., 2021 — causal Beta/inhibitory-control result](http://biorxiv.org/lookup/doi/10.1101/2021.10.07.463487)).

---

## 3. Research Questions

**RQ1 (Signal quality / feasibility).** Under NeXus-10/BioTrace+ acquisition with the Fz/FCz/Pz/Oz montage, what is the achievable signal-to-noise ratio, artifact burden, and marker-alignment precision across realistic recording conditions, and are these sufficient to support any downstream modeling claim?

**RQ2 (Unimodal baseline).** How well do four-channel EEG spectral/temporal features alone predict each operationally defined cognitive/affective state label, using only within-participant and only cross-participant validation?

**RQ3 (Multimodal supervision).** Does adding behavioral event markers, structured subjective reports, and AI stimulus embeddings as auxiliary inputs/regularizers improve state-model performance over the EEG-only baseline (RQ2), and by how much, with what calibration?

**RQ4 (Generalization boundary).** Do multimodal-supervised state models generalize across sessions (same participant, different day) and across participants, or are they participant/session-specific — and how does this generalization boundary depend on the specific state construct?

**RQ5 (Actionability).** When a validated (per RQ1–RQ4) state estimate is fed back to the participant as blockwise or real-time neurofeedback, does the participant's targeted state change in the intended direction, with what effect size, timecourse, and durability, relative to sham and active-control conditions?

**RQ6 (Specificity of the loop).** Is any observed neurofeedback effect specific to the trained EEG feature/state (versus a general arousal, attention, motivation, or expectancy effect that would also appear under sham feedback)?

**RQ7 (Boundary conditions of four-channel EEG).** Which cognitive/affective constructs, if any, are *in principle* unreachable by a four-channel midline montage, and can the program pre-specify this boundary rather than discover it post hoc via null results?

---

## 4. Operational Definitions

Rigor requires that every construct used above cash out in measurable, pre-registrable terms. We define four candidate primary constructs; additional constructs may be added later under the same template, but the initial roadmap is restricted to these to keep multiple-comparisons risk bounded.

| Construct | EEG operationalization (four-channel) | Behavioral operationalization | Subjective-report operationalization | Explicit non-claims |
|---|---|---|---|---|
| **Arousal / alertness** | Oz/Pz alpha (8–12 Hz) power, alpha suppression on eyes-open vs. eyes-closed; Fz/FCz beta (13–30 Hz) power | Reaction-time variability, lapse rate on a sustained-attention task (e.g., psychomotor vigilance task, PVT) | Karolinska Sleepiness Scale (KSS) or a single-item VAS ("How alert do you feel right now?") | Not a claim about wakefulness/consciousness level; not a clinical vigilance/DOC measure |
| **Task engagement / attentional allocation** | Fz/FCz frontal midline theta (4–8 Hz) power during task vs. rest; Pz P300-like ERP amplitude time-locked to markers | Accuracy and RT on the concurrent task; response-marker-to-stimulus-marker latency | Single-item VAS ("How engaged/focused did you feel during that block?") | Not a claim about "attention" as a unitary cognitive faculty; construct is task-bound |
| **Affective valence (self-reported)** | Frontal alpha asymmetry proxy (Fz-referenced, acknowledging this is normally computed from bilateral F3/F4 and is only weakly approximable at a single midline site — flagged as a *known montage limitation*, not silently assumed) | Approach/avoidance choice behavior where task design allows | Self-Assessment Manikin (SAM) valence/arousal scale, or PANAS short form | Not a claim of decoding emotional *content*; valence label is self-report-anchored, EEG is a correlate/predictor, not ground truth |
| **Error-related / cognitive-control processing** | FCz error-related negativity (ERN)-like deflection time-locked to response-marker-defined errors | Post-error slowing, error-correction latency | Post-block confidence rating | Not a claim about a general "executive function" construct; scoped to the specific task's error events |

**General operational rules adopted throughout:**

- Every state label used for supervision must be **derivable from at least one non-EEG channel** (behavior or report) so that EEG is never used to define its own ground truth (avoiding circularity).
- Every EEG feature used as a predictor must be **pre-specified** (frequency band, channel, time window relative to a marker) before looking at outcome data for that experiment, to prevent post hoc feature mining.
- AI stimulus embeddings (text/image/audio, e.g., via HuggingFace-style pretrained encoders as used in NeuralSet's extractor abstraction) are used strictly as **auxiliary conditioning inputs** describing *what the participant was shown*, temporally aligned to the same event timeline as EEG and behavior — they are not treated as neural data and never substitute for a brain-derived signal ([NeuralSet, Extractors](https://github.com/facebookresearch/neuroai/)).

---

## 5. Staged Experimental Roadmap

The roadmap is deliberately gated: each stage has an explicit go/no-go criterion, and no stage begins data collection for the next scientific claim until the prior stage's criterion is met. This mirrors the recommended practice in the neurofeedback-validation literature of establishing learning/signal validity before testing clinical or behavioral efficacy ([Sorger et al., 2019](https://pmc.ncbi.nlm.nih.gov/articles/PMC6338498/)).

### Stage 0 — Instrumentation and Signal-Quality Validation (feasibility gate)

**Goal:** Establish that the NeXus-10/BioTrace+/four-channel pipeline produces usable, aligned, reproducible data at all, before any modeling claim is attempted.

- Bench validation: known-signal injection (function generator or phantom) to confirm amplifier linearity, sampling-rate accuracy, and channel crosstalk.
- Human bring-up sessions (n ≥ 6 pilot participants, single session each): 60-second eyes-open/eyes-closed alpha blocking, standardized as a canonical "sanity check" because Oz alpha suppression on eye opening is one of the most robust, well-replicated EEG phenomena and functions as a built-in positive control.
- Marker-alignment audit: quantify jitter (ms) between BioTrace+ event markers and true stimulus/response onset (measured via an external photodiode/audio loopback if available); this bounds the temporal precision assumed by every later ERP-locked analysis (e.g., FCz ERN, Pz P300-like feature).
- Artifact characterization: eye-blink, jaw-clench, and movement artifact templates per channel, using standard MNE-based preprocessing (consistent with the ecosystem NeuralSet is designed to orchestrate, not replace: MNE-Python remains the validated signal-processing layer underneath any higher-level tooling ([NeuralSet Discussion, "Orchestration, not reinvention"](https://github.com/facebookresearch/neuroai/))).

**Go/no-go:** Proceed to Stage 1 only if (a) eyes-closed Oz alpha power exceeds eyes-open by a pre-specified effect size (e.g., Cohen's d ≥ 0.8, within-participant) in ≥ 80% of pilot participants, and (b) marker jitter is below a pre-specified threshold (e.g., < 20 ms SD) sufficient for the shortest planned ERP window.

### Stage 1 — Unimodal EEG Baseline Modeling (RQ2)

**Goal:** Establish the ceiling and floor of what four-channel EEG alone can predict, before adding other modalities — this baseline is the yardstick every later "multimodal improves things" claim must beat.

- Tasks: sustained-attention (PVT-style) and a simple oddball/P300 paradigm, each with dense behavioral markers.
- Models: interpretable baselines first (band-power logistic/linear regression per channel), then a modest deep model (e.g., shallow CNN/EEGNet-style architecture) — model complexity is capped deliberately given n=4 channels, to avoid overfitting artifacts of complexity to a low-dimensional input.
- Validation: nested cross-validation, reported separately for within-session, within-participant/cross-session, and cross-participant splits (these routinely diverge sharply in EEG decoding and must not be conflated).
- Preregistration: primary metric, band definitions, and channel selections fixed before data collection.

**Go/no-go:** Proceed to Stage 2 only for constructs where the EEG-only model exceeds a chance-corrected performance floor (e.g., balanced accuracy significantly > 50% at a pre-registered alpha, or equivalent regression R² > a pre-specified minimum) in cross-session validation. Constructs that fail this floor are **provisionally shelved**, not silently dropped — see Section 9 (RQ7 boundary-mapping).

### Stage 2 — Multimodal Supervision (RQ3, RQ4; tests H1)

**Goal:** Directly test H1 by adding behavioral markers, subjective reports, and AI stimulus embeddings as auxiliary inputs to the Stage 1 architecture, using a NeuralSet-style aligned-events data model (Events → Extractors → Segments → tensors) so that every training example is provably drawn from a consistent temporal alignment of EEG, marker, report, and embedding streams ([NeuralSet Framework](https://github.com/facebookresearch/neuroai/)).

- **Ablation design (mandatory):** train and report every combination of {EEG, EEG+behavior, EEG+report, EEG+stimulus-embedding, EEG+all} so that any performance gain is attributed to a specific modality rather than to "more features" in general.
- **Stimulus embeddings:** static or dynamic embeddings (e.g., text/image encoders) time-aligned to stimulus-onset events, exactly analogous to NeuralSet's static-vs-dynamic extractor abstraction — this lets the design cleanly separate "the brain's response to a category of stimulus" from "the brain's intrinsic state," which is essential to prevent stimulus-content leakage from masquerading as state prediction.
- **Confound controls:** include stimulus embedding as a *predictor of the label* in a separate control model; if stimulus embedding alone (without EEG) predicts the label as well as EEG+embedding, the "supervision" claim is confounded by stimulus-driven behavior/report rather than reflecting brain-state information — this is a mandatory falsification check built into the design, not an afterthought.
- **Generalization tests (RQ4):** report leave-one-session-out and leave-one-participant-out performance explicitly; pre-register the minimum participant/session count needed for adequately powered cross-participant generalization estimates.

**Go/no-go — this is the H1 validity gate for Stage 3:** H1 is considered *provisionally supported* for a given construct only if (a) the full multimodal model significantly outperforms the EEG-only baseline (Stage 1) at a pre-registered effect-size threshold, (b) the ablation shows the gain is not attributable to stimulus-embedding-only or report-only leakage, and (c) cross-session generalization is significantly above chance. Only constructs clearing all three move to Stage 3.

### Stage 3 — Blockwise Closed-Loop Pilot (bridge to real-time; partial test of H2)

**Goal:** Test whether a *blockwise* (not yet real-time) feedback loop — consistent with the platform's current offline-first, blockwise-adaptation architecture — produces any directional change, before investing in true real-time infrastructure.

- Design: within-participant, multiple-block sessions; after each block, compute the Stage-2 model's state estimate from that block's aligned data, and adjust the *next* block's task/feedback parameters (e.g., difficulty, stimulus pacing, explicit feedback display) accordingly.
- Control arms (see Section 7): no-feedback control blocks, sham-feedback blocks (randomized or previous-participant-yoked feedback values, matched for timing/salience), and active-alternative-target blocks (feedback on a different, non-targeted EEG feature).
- Outcome: change in the targeted state's operational measures (Section 4) across blocks, and any transfer to the pre-registered downstream behavioral outcome.

**Go/no-go:** Proceed to real-time Stage 4 investment only if the blockwise pilot shows a specific effect (targeted arm > both sham and active-alternative arms) at a pre-registered effect size, since real-time engineering investment is expensive and should not precede evidence that the underlying loop can work at all, even at coarse (blockwise) temporal resolution.

### Stage 4 — Real-Time Closed-Loop Neurofeedback Trial (full test of H2)

**Goal:** The full actionability test, only attempted if Stage 3 clears its gate and real-time infrastructure has been engineered and separately validated for latency and reliability (explicitly out of this thesis's scope to design, per the instruction not to edit the NeuroMirror codebase; this thesis specifies the *scientific* requirements the engineering must satisfy).

- Pre-registered, sham-controlled, ideally double-blind (participant and, where feasible, experimenter-blind to arm) randomized design, following best-practice control taxonomies for neurofeedback trials (no-feedback, sham, bidirectional-regulation control, or active-alternative-target control; ([Sorger et al., 2019](https://pmc.ncbi.nlm.nih.gov/articles/PMC6338498/))), and ideally a counterbalanced active-sham design within participant where feasible to increase power at modest sample sizes ([Mayer et al., 2024, counterbalanced active-sham validation](https://pmc.ncbi.nlm.nih.gov/articles/PMC11060147/)).
- Primary outcome: pre-registered, specific, dose-related change in the targeted operational construct.
- Secondary outcomes: durability (post-training retention without feedback, following the multi-month follow-up logic used in fMRI-neurofeedback retention studies ([Robineau et al., 2017](http://journal.frontiersin.org/article/10.3389/fnhum.2017.00131/full))), and transfer to the downstream behavioral outcome.
- Mandatory learning-curve reporting at the individual level (not just group-average), since a substantial fraction of participants in typical neurofeedback studies are "non-learners," and group averages can mask this heterogeneity ([Syrjänen et al., 2026](http://biorxiv.org/lookup/doi/10.64898/2026.01.07.698228)).

---

## 6. Controls (Consolidated)

Because control adequacy is the single most common failure point in the neurofeedback literature, controls are specified once here and referenced by stage above, rather than left implicit.

1. **Signal-level controls (Stage 0):** phantom/bench calibration; eyes-open/eyes-closed alpha-blocking positive control; marker-jitter audit.
2. **Modeling controls (Stages 1–2):** chance-level and shuffled-label permutation baselines; demographic/prior-only baseline; full modality ablation grid; stimulus-embedding-only leakage check; separate within-session vs. cross-session vs. cross-participant reporting.
3. **Neurofeedback controls (Stages 3–4):**
   - **No-feedback control** — same task, no feedback signal at all (baseline drift/regression-to-mean control).
   - **Sham/randomized feedback control** — feedback matched in timing, modality, and salience but statistically decoupled from the participant's actual EEG state (placebo/expectancy control).
   - **Active-alternative-target control** — feedback that is real and contingent, but trained on a different EEG feature than the one hypothesized to matter (specificity control; this is the design that let [Enz et al. (2021)](http://biorxiv.org/lookup/doi/10.1101/2021.10.07.463487) demonstrate that Beta-rhythm feedback, and not Alpha-rhythm feedback, specifically predicted inhibitory-control change).
   - **Counterbalanced within-participant active-sham**, where feasible, to increase statistical power under small samples typical of single-lab EEG studies ([Mayer et al., 2024](https://pmc.ncbi.nlm.nih.gov/articles/PMC11060147/)).
4. **Statistical controls:** pre-registration of primary endpoints and analysis code before unblinding; correction for multiple comparisons across the four candidate constructs; individual-level learning-curve analysis in addition to group means.

---

## 7. Evaluation Metrics

| Stage | Primary metric(s) | Secondary metric(s) |
|---|---|---|
| Stage 0 (signal quality) | Eyes-closed/eyes-open Oz alpha power ratio (dB); marker-jitter SD (ms) | Per-channel RMS/peak-to-peak in plausible physiological range (µV); artifact rate per minute |
| Stage 1 (unimodal) | Balanced accuracy or R² vs. chance, cross-session split | AUROC; calibration (Brier score); within- vs. cross-participant gap |
| Stage 2 (multimodal, H1) | Δ balanced accuracy / Δ R² (multimodal − EEG-only), with 95% CI | Ablation-attributed variance per modality; leave-one-participant-out generalization gap; leakage-check pass/fail |
| Stage 3 (blockwise loop) | Block-over-block change in targeted construct, targeted vs. sham/active-alternative arms | Behavioral transfer effect size; number of "non-learner" participants |
| Stage 4 (real-time loop, H2) | Pre-registered primary specific effect size (targeted vs. sham) | Durability at follow-up; dose–response slope (feedback exposure vs. effect); individual learning-curve typology |

All effect sizes are reported with confidence intervals, not p-values alone, and all stages report negative/null results with the same rigor as positive ones — a pre-registered commitment intended to counteract publication-bias-style selective reporting that has historically undermined confidence in the neurofeedback literature ([Pigott et al., 2018](https://pmc.ncbi.nlm.nih.gov/articles/PMC7783691/) vs. counter-critiques in the same debate).

---

## 8. Data Governance and Ethics

- **Scope and consent.** All data collection occurs under an appropriate research/IRB-equivalent protocol (or self-experimentation with documented informed consent where applicable), consistent with the platform's own stated posture as a research/educational prototype, not a medical device, making no diagnostic or clinical claims.
- **Data minimization and de-identification.** Recordings and derived reports must contain no personally identifying information; this is already a stated design goal of the platform's diagnostic reporting and is adopted unchanged as a governance requirement for this research program.
- **Sensitive-data handling.** EEG and subjective-report data are treated as sensitive personal (potentially health-adjacent) data throughout the pipeline — storage, transfer, and analysis should follow the principle of least exposure (local-first analysis, encrypted-at-rest storage, access logging), independent of and in addition to whatever software-level protections exist in the current codebase.
- **AI stimulus embeddings and third-party models.** Where pretrained embedding models (text/image/audio encoders) are used to featurize stimuli, their licenses and provenance must be documented, and no participant-identifying raw stimulus (e.g., a participant's own photo, if ever used as a stimulus) should be sent to a third-party embedding API without explicit consent and a data-processing agreement.
- **Withdrawal and downstream use.** Participants must be able to withdraw and have their data excluded from any subsequent model training; models trained on withdrawn data must be flagged for retraining or documented as a limitation.
- **No clinical or diagnostic inference.** Consistent with the platform's disclaimer, no output of any stage of this research program — including closed-loop feedback — may be presented to participants or third parties as diagnostic, therapeutic, or predictive of any medical or psychiatric condition. Any observed "improvement" in a task-relevant state is a research finding about a specific operational construct under specific task conditions, not a clinical claim.
- **Safety monitoring.** Given documented risks of fatigue, headache, or discomfort during neurofeedback, all closed-loop stages (3–4) require a stop-if-adverse-effect rule and a maximum session-length cap, mirroring the platform's own existing safety disclaimer.
- **Publication commitment.** Null and negative results at any gate are pre-committed for reporting (e.g., as part of the roadmap's public documentation or a registered report), to avoid the file-drawer problem that has particularly afflicted small-sample EEG neurofeedback research.

---

## 9. Limitations of Four-Channel EEG (Explicit Boundary Conditions)

This section operationalizes RQ7 by pre-specifying, rather than discovering post hoc, what the montage cannot support — turning a limitation into a testable boundary rather than an excuse for unfalsifiable claims.

1. **No source localization.** EEG source imaging with fewer than ~32 channels produces severe blurring and mislocalization; four channels support *no* meaningful source localization — only broad, electrode-anchored regional inference (e.g., "occipital-region alpha," not "V1 activity") ([Farahibozorg et al., EEG source imaging review](https://pmc.ncbi.nlm.nih.gov/articles/PMC6458265/); [Neurosity, channel-count vs. source localization capability table](https://neurosity.co/guides/source-localization-eeg-how-it-works)). All claims in this thesis are therefore stated at the level of scalp-topography features (e.g., "Oz-site alpha power"), never as claims about a specific cortical generator.
2. **Underdetermined inverse problem, worse at n=4.** The EEG inverse problem is underdetermined even with 64–256 channels; with 4 channels the system can constrain at most one or two very coarse dipoles, if any — recent work quantifies a √(electrode-reduction-ratio) scaling law for localization-accuracy loss as channel count drops ([How Reducing EEG Electrodes Affects Source Localization, 2025](https://arxiv.org/html/2510.10770v1)).
3. **No access to deep/subcortical structures.** Structures implicated in arousal and affect (thalamus, amygdala, brainstem nuclei) are, for practical purposes, invisible to scalp EEG at any channel count, and especially so at four channels; any "arousal" or "valence" construct here is a scalp-level, midline-topography correlate, not a claim about subcortical circuitry.
4. **No lateralized/asymmetry measures.** Classic constructs like frontal alpha asymmetry (F3 vs. F4) are not measurable with a single midline frontal site (Fz); this thesis flags valence operationalization (Section 4) as *weakened* by this constraint rather than silently substituting a midline proxy without comment.
5. **Coarse spatial sampling degrades connectivity estimates faster than power estimates.** Evidence from systematic channel-subsampling studies shows spectral power estimates degrade more gracefully with fewer channels than connectivity estimates, which drop off sharply below ~64 channels ([Comprehensive evaluation of EEG spatial sampling, 2026](https://academic.oup.com/braincomms/article/8/1/fcag022/8441705)). Consequently, this program restricts itself to power/ERP-style features and explicitly excludes any connectivity-based construct as out of scope for the current montage.
6. **Volume conduction and cross-talk.** With only four scalp sites and a linked-ears reference, individual channels are not spatially independent; apparent "co-activation" across Fz/FCz/Pz/Oz may partly reflect shared volume-conducted signal rather than distinct generators, and must be interpreted with that caveat in every multichannel analysis.
7. **Consequence for H1/H2 scope.** These limitations do not invalidate H1/H2 — they bound the *grain* at which H1/H2 can be tested. The hypotheses are scoped to broad, task-relevant, midline-topography state constructs, which is exactly the level of claim four-channel EEG can support, consistent with the "regional inference only" capability tier for 1–4 channel systems identified in the literature.

---

## 10. Success and Failure Criteria

Defined at the program level, not just per-stage, to make the overall thesis falsifiable rather than open-ended.

**Success criteria (any one of the following constitutes a scientifically meaningful positive outcome, independent of whether every stage is completed):**
- S1: At least one operational construct clears the Stage 2 (H1) multimodal-supervision gate with pre-registered ablation evidence ruling out stimulus-embedding leakage, demonstrating that multimodal alignment adds real information beyond EEG alone.
- S2: At least one construct that clears S1 also clears the Stage 3 blockwise-loop specificity gate (targeted arm > sham and > active-alternative-target arm), demonstrating actionability at coarse temporal grain.
- S3: A full real-time closed-loop trial (Stage 4) shows a pre-registered, sham-controlled specific effect with a documented dose–response relationship and partial durability at follow-up.
- S4 (negative-result success): The program rigorously establishes that a specific construct (e.g., valence) is *not* supportable by this montage/design (fails Stage 1 or Stage 2 at pre-registered thresholds across adequately powered attempts), thereby correctly mapping the boundary predicted in Section 9 rather than leaving it speculative.

**Failure criteria (any one of the following should trigger a stop, redesign, or reframing of the program):**
- F1: No construct clears the Stage 1 EEG-only floor after adequately powered attempts — indicating a Stage 0 signal-quality problem, not a modeling problem, and requiring a return to instrumentation validation.
- F2: Constructs clear Stage 1 but no construct shows a non-leaking multimodal gain at Stage 2 — indicating H1 is not supported for this platform in its current form, and the program should not proceed to closed-loop testing.
- F3: A construct clears Stage 2 but fails the Stage 3 specificity check (sham/active-alternative arms perform equivalently to the targeted arm) — indicating any observed change is a generic attention/expectancy/motivation effect, not a validated actionable brain-state loop; H2 is disconfirmed for that construct.
- F4: Individual-level learning-curve analysis shows the large majority of participants are "non-learners" even where group averages appear positive — this is treated as a failure of practical actionability even if a statistically significant group effect exists, following the documented "non-learner" phenomenon in the wider neurofeedback literature.

---

## 11. Relationship to Existing Tooling (Non-modifying reference)

This thesis is designed to be executed using — but does not require modifying — the existing `nexus-neuromirror` repository's verifier/diagnostic pipeline for Stage 0, and is compatible with a NeuralSet-style Events/Extractors/Segments data model for Stages 1–2, where EEG, behavioral markers, subjective reports, and stimulus embeddings would each be represented as events on a shared timeline and combined via extractors into aligned tensors for model training ([NeuralSet](https://github.com/facebookresearch/neuroai/)). Adopting this structure-data decoupling pattern is a methodological recommendation for reproducibility and auditability, not a mandate to alter any specific existing file, and no changes to `/home/user/workspace/nexus-neuromirror` are proposed or required by this thesis.

---

## 12. Summary Table: Hypotheses, Stages, Gates

| Hypothesis | Tested in stage | Primary gate | If gate fails |
|---|---|---|---|
| Feasibility (signal quality) | Stage 0 | Eyes-closed/open alpha effect ≥ d=0.8; marker jitter < threshold | Fix instrumentation before any modeling |
| H1 (multimodal supervision) | Stages 1–2 | Multimodal > EEG-only, no leakage, cross-session generalization | Construct shelved as "not supportable by this design" (S4/F2) |
| H2 (actionability, coarse) | Stage 3 | Targeted arm > sham and > active-alternative-target arm | Construct disconfirmed for closed-loop use (F3); do not proceed to Stage 4 |
| H2 (actionability, real-time) | Stage 4 | Pre-registered specific effect + dose–response + partial durability | Report null result; reassess real-time infrastructure investment |

---

## References (selected, inline-linked above)

- King, J.-R., et al. *NeuralSet: A High-Performing Python Package for Neuro-AI.* Meta FAIR. Code: https://github.com/facebookresearch/neuroai/
- Pigott, H.E., Trullinger, M., Cannon, R.L. (2018). *The Fallacy of Sham-Controlled Neurofeedback Trials.* https://pmc.ncbi.nlm.nih.gov/articles/PMC7783691/
- Sorger, B., Linden, D., Scharnowski, F., Young, K.D., Hampson, M. (2019). *Control Freaks: Towards optimal selection of control conditions for fMRI neurofeedback studies.* https://pmc.ncbi.nlm.nih.gov/articles/PMC6338498/
- Syrjänen, E., Silva, J., Åstrand, E. (2026). *Successful single-session neural self-regulation through neurofeedback varies between features.* http://biorxiv.org/lookup/doi/10.64898/2026.01.07.698228
- Enz, N., et al. (2021). *Self-regulation of the brain's Beta rhythm using a brain-computer interface improves inhibitory control.* http://biorxiv.org/lookup/doi/10.1101/2021.10.07.463487
- Robineau, F., et al. (2017). *Maintenance of Voluntary Self-regulation Learned through Real-Time fMRI Neurofeedback.* http://journal.frontiersin.org/article/10.3389/fnhum.2017.00131/full
- Mayer, A.R., et al. (2024). *Validation of real-time fMRI neurofeedback procedure using counterbalanced active-sham study design.* https://pmc.ncbi.nlm.nih.gov/articles/PMC11060147/
- Farahibozorg, S.-R., et al. *EEG Source Imaging: A Practical Review of the Analysis Steps.* https://pmc.ncbi.nlm.nih.gov/articles/PMC6458265/
- *How Reducing EEG Electrodes Affects Source Localization* (2025). https://arxiv.org/html/2510.10770v1
- Neurosity. *Source Localization in EEG: How It Works.* https://neurosity.co/guides/source-localization-eeg-how-it-works
- *Comprehensive evaluation of EEG spatial sampling, head modelling* (2026). https://academic.oup.com/braincomms/article/8/1/fcag022/8441705
- *Neural correlates of perceptual consciousness from within* (2026, eLife reviewed preprint). https://elifesciences.org/reviewed-preprints/109604
- Koch, C., et al. (2016). *Neural correlates of consciousness: progress and problems.* https://puredhamma.net/wp-content/uploads/Neural-correlates-of-consciousness-Koch-et-al-2016.pdf
- *EEG Decoding of Conscious versus Unconscious Processing* (2025). https://pmc.ncbi.nlm.nih.gov/articles/PMC12325685/

*(Additional supporting sources retrieved during research are cited inline throughout the document above at point of use.)*
