# TSUAN Review — Findings & Action Items

This document captures code review findings, issues discovered while implementing and testing TSUAN, and recommended next actions grouped by the TODO list items.

Status summary
- Tests: 19 unit tests added; all pass locally in the workspace venv.
- Package: editable install tested (`pip install -e ".[dev]"`).
- Standalone repo: scaffold pushed to https://github.com/matthew-lottly/TSUAN

Files changed during scaffold & fixes
- `pyproject.toml` — build-backend adjusted for editable install
- `.vscode/settings.json` — Pylance extraPaths for `projects/tsuan/src`
- `src/tsuan/*` — full package scaffold (encoder, attention, uncertainty, decoder, model, losses, data, train, inference, tests)
- `tests/test_tsuan.py` — 19 tests, including mismatched-config alignment test

Per-module review

1) Encoder (`src/tsuan/encoder.py`)
- Findings: clean, simple CNN encoder with consistent time flatten/reshape logic. Produces `(B,T,D,H',W')` as expected.
- Potential issues: `CNNEncoder` channel progression uses `min(embed_dim, 2**i * max(32, in_channels))`. This may produce unexpected intermediate channel sizes when `embed_dim` is small; acceptable but documentable.
- Action: add brief docstring note and an assert in `CNNEncoder.__init__` if you prefer stricter invariants. (low effort)

2) Attention (`src/tsuan/attention.py`)
- Findings: Implements the research spec: uncertainty encoder, dynamic temperature, intra-modal and cross-modal attention, aggregation with residual and FFN.
- Strengths: explicit handling of spatial tokens (B*S, T, D), multi-head implementation, physical penalty hook in `CrossModalAttention`.
- Concerns / suggestions:
  - Memory: current design reshapes to (B*S, T, D) which can be large for big H,W. Consider optional patching/strided attention or token reduction for production.
  - `pviol_net` uses `nn.Linear` over embedding dim; consider adding a small conv or 1×1 conv with spatial awareness if physical violations are spatially structured.
  - Numeric stability: `DynamicTemperature` returns Softplus outputs — good. Consider clamping λ to a max to avoid overly large penalties.
- Actions: add comments about expected max spatial token sizes and an optional argument to enable token reduction. (medium effort)

3) Model composition (`src/tsuan/model.py`)
- Findings: TSUAN composes encoder → attention → decoder → uncertainty heads. We fixed channel mismatches by making downstream modules use `attention.embed_dim`.
- Improvements made: decoder / uncertainty / cloud head now use `cfg.attention.embed_dim`. Added `TSUANConfig.__post_init__` to align dims.
- Actions: consider raising an error (instead of silently aligning) if user sets inconsistent embed dims in production. Add unit test already exists. (low effort)

4) Losses (`src/tsuan/losses.py`)
- Findings: Implements L_recon (masked L1), NLL uncertainty calibration, physical NDVI/EVI consistency, temporal smoothness, and auxiliary BCE for cloud segmentation.
- Concerns: `PhysicalConsistencyLoss` hardcodes band indices defaults (red_idx=3, nir_idx=7, blue_idx=1) — document clearly and allow band-name config mapping for custom datasets.
- Actions: expose a helper to map common band orderings and add unit tests for physical loss with synthetic data. (low effort)

5) Data & Decoder (`src/tsuan/data.py`, `src/tsuan/decoder.py`)
- Findings (data): Dataset expects `.npy` stacks and split files. `__getitem__` now returns `patch_id` and types were relaxed for Pylance compatibility. Augmentations and temporal sampling implemented.
- Findings (decoder): Symmetric ConvTranspose decoder; channel progression attempts to halve channels across upsampling blocks.
- Concerns / suggestions:
  - Data: Add metadata checks (shape, channel count), robust missing-file handling, and optional lazy loading to handle large datasets.
  - Decoder: ConvTranspose block channel choices assume close parity with encoder; keep decoder flexible by accepting `in_channels` param or build from `att_dim` (we already aligned to `att_dim`).
- Actions: Add simple data validation in `SatelliteTimeSeriesDataset.__init__` and optional `verify_dataset()` util. (medium effort)

6) Train & Inference (`src/tsuan/train.py`, `src/tsuan/inference.py`)
- Findings: Training loop includes mixed precision, warmup + cosine LR scheduler, EMA, checkpointing, and logging. Inference supports TTA and ONNX export.
- Concerns / suggestions:
  - Checkpoint saving currently stores `config` object directly; consider serializing `cfg.__dict__` or a lightweight dict to avoid pickling issues across envs.
  - EMA: we update shadow during training and apply at end; add ability to save/load EMA shadow state.
  - ONNX export: verify dynamic axes and ensure the model is traceable (some ops like adaptive pooling or permute are OK, but test export on target PyTorch/GPU combos).
- Actions: add `save_ema_state()` and `load_ema_state()` helper; modify checkpoint format to include a serializable config dict. Add CI job to attempt ONNX export. (medium effort)

Cross-cutting issues and quick wins
- Add GitHub Actions to run tests on push (small YAML file). (low effort)
- Add a minimal example dataset generator (`scripts/make_dummy_data.py`) and a quick-start notebook demonstrating `Trainer` and `predict_with_tta`. (medium effort)
- Document expected input shapes and band ordering in `README.md` and top-level module docstrings. (low effort)

Actionable checklist (prioritized)
1. CI: add GitHub Actions to run unit tests on PRs and push. (priority: high, est: 1–2h)
2. Add `save_ema_state()` / `load_ema_state()` and include EMA in checkpoints. (priority: medium, est: 1h)
3. Add dataset verification utility and document data format. (priority: medium, est: 1–2h)
4. Add small example dataset generator and notebook demo. (priority: medium, est: 2–4h)
5. Improve attention memory handling / token reduction options for large images. (priority: low, est: 4–8h)
6. Harden config validation (option to error on mismatch). (priority: low, est: 30m)

Next step
- I can implement item (1) CI workflow now (quick). Do you want that, or prefer a runnable example dataset + notebook first? Reply with your preference and I'll do it next and update this REVIEW.md.

Additional findings — train.py & inference.py
- **Invalid torch.load usage (train.py):** `load_checkpoint` currently calls `torch.load(..., weights_only=False)` which is not a valid argument for `torch.load`. This will raise a TypeError on some environments. Fix: remove the `weights_only` kwarg and load normally.
- **Checkpoint serialization (train.py):** Checkpoints save `config` as the dataclass object. While this pickles in many cases, it's safer to store a serializable dict (e.g., `dataclasses.asdict(cfg)`) to improve cross-environment compatibility and avoid pickling issues.
- **EMA persistence (train.py):** EMA shadow weights are updated during training but not saved separately. Add `save_ema_state()` / `load_ema_state()` helpers and include EMA shadow parameters in the checkpoint to allow exact EMA restoration for evaluation or resuming training.
- **TTA inverse-transform bug (inference.py):** In `predict_with_tta` you inverse-transform `x_hat` but do not inverse-transform `sigma_pixel` (uncertainty) before aggregating. This misaligns spatial uncertainty with the de-augmented prediction. Fix: apply `inv_fn` to `out['sigma_pixel']` (and any other spatial outputs) before appending to `uncertainties`.
- **Fragile shape handling in TTA aggregation (inference.py):** The code uses slicing like `pred_var[..., : sigma_model.shape[-2], : sigma_model.shape[-1]]` to crop variance to `sigma_model` size. Prefer explicit `F.interpolate` or center-cropping to match shapes robustly and avoid subtle off-by-one issues for odd/even dims.
- **ONNX export dynamic axes (inference.py):** `export_onnx` lists `output_names` including `sigma_pixel`, `sigma_patch`, etc., but `dynamic_axes` only maps `x_hat`. Add dynamic axes entries for all spatial/time outputs. Also ensure the exported model returns a tuple (or script a wrapper) so `output_names` map deterministically to ONNX outputs.
- **Recommended tests:** Add unit tests that exercise `predict_with_tta` (verify inverse transforms and uncertainty aggregation) and a smoke test for `export_onnx` (export to a temp file and ensure file exists and loads with onnx runtime if desired).

Action items (train/inference) — recommended
- **Fix torch.load arg & serialize config:** remove invalid kwarg and save `dataclasses.asdict(cfg)` in checkpoints. (priority: high, est: 15–30m)
- **Persist EMA:** add `save_ema_state()` / `load_ema_state()` and include EMA in checkpoints. (priority: medium, est: 45–60m)
- **Fix TTA uncertainty inverse-transform and shape-matching:** inverse-transform `sigma_pixel` with `inv_fn` and use `interpolate`/explicit crop to match sizes. Add TTA unit tests. (priority: high, est: 30–60m)
- **Harden ONNX export:** include dynamic axes for all outputs and export via a small wrapper returning a fixed tuple, add smoke test in CI. (priority: medium, est: 45–90m)

I can implement any of the above automatically — which of these should I do next? CI + TTA fixes would be my recommended pair (CI first, then TTA/ONNX tests).

---

Research-grade deep dive — Negative Knowledge, rebuttals, and publication requirements

## The Most Important Finding: The Closest Prior Work

The single most dangerous paper you must know about is **UnCRtainTS (Ebel et al., CVPR EarthVision 2023)**.  Reading the full paper reveals this direct quote from Figure 1's caption: *"Note how higher uncertainties (in red) are associated with **persistent occlusion**."*  They already show that under total, persistent cloud coverage with no clear observations in the time series, their model outputs high uncertainty, and they explicitly use this to **filter out unreliable reconstructions** — Figure 3 shows discarding the top 50% of uncertain samples **halves prediction error**.  This is the most direct threat to the novelty claim and must be understood precisely. [arxiv](https://arxiv.org/pdf/2304.05464.pdf)

## Exhaustive Rebuttal Mapping for Negative Knowledge Learning

### Rebuttal 1 (MOST DANGEROUS): UnCRtainTS already does this

**The claim it attacks:** TSUAN-NK's structural abstention on persistent voids is new.

**The evidence:** UnCRtainTS explicitly: (1) predicts uncertainty that is highest at persistent occlusion, (2) shows that filtering by this uncertainty dramatically reduces reconstruction error, and (3) links high uncertainty to "restorations based on too little evidence."  The SEN12MS-CR-TS benchmark they use even contains scenes with 100% cloud coverage across all time steps. [patricktum.github](https://patricktum.github.io/cloud_removal/)

**How to rebut it — and how strong that rebuttal is:**

The critical distinction survives, but narrowly:
- UnCRtainTS' abstention is **post-hoc** and **confidence-threshold-based** — it ranks completed reconstructions by their variance and discards the worst ones at inference time.  It does not predict *before* running the reconstruction whether a pixel is structurally unknowable. [arxiv](https://arxiv.org/pdf/2304.05464.pdf)
- TSUAN-NK's mechanism is fundamentally different: it jointly trains a **Structural Observational Void Detector (SOVD)** that predicts *a priori* (from the input observation archive structure) whether a pixel is even worth attempting to reconstruct — before the reconstruction head runs, not after it.
- UnCRtainTS will produce a reconstruction output AND an uncertainty for every pixel; TSUAN-NK's detector would **suppress the reconstruction branch** for voided pixels and output a binary "I cannot know" instead of a high-variance estimate.

**This distinction is real but extremely narrow.** A reviewer will say: "High-uncertainty filtering in UnCRtainTS is functionally equivalent to your abstention — you're just thresholding the same signal at a different point in the pipeline." You need a very clear empirical demonstration that SOVD fires on cases where UnCRtainTS is incorrectly *low* uncertainty (i.e., confidently wrong), to separate them.

### Rebuttal 2: Barnes & Barnes "NotWrong Loss" — already in Earth science

**The claim it attacks:** Training-integrated abstention during learning in Earth observation is new.

**The evidence:** Barnes & Barnes (2021) published the "NotWrong loss" specifically for Earth system prediction, applied during training (not post-hoc), with a PID controller to enforce a user-specified abstention fraction.  It was published in the *Journal of Advances in Modeling Earth Systems* — directly in the geoscience ML domain.  It even uses a dedicated abstention class in the output layer, identical in spirit to what TSUAN-NK proposes. [arxiv](https://arxiv.org/abs/2104.08281)

**How to rebut it:**
- Barnes & Barnes apply this to **temporal prediction** (climate forecasting, classification problems). Their abstention trigger is *model confidence* in classifying the current system state.
- TSUAN-NK's trigger is fundamentally different: it is triggered by **structural absence in the spatial-temporal observation archive**, not by **model confidence** in what it has seen. A Barnes-style model trained on full-coverage data would never abstain on a fully-cloudy pixel because it hasn't seen the observational void — it's not in its input representation.
- However, a reviewer will still note significant conceptual overlap in the training objective design.

**Survivability: Moderate.** The domain specificity (spatiotemporal reconstruction vs. temporal classification) and trigger mechanism (structural void vs. model confidence) are genuine differences, but the paper must explicitly address this comparison.

### Rebuttal 3: The Confidence Gate Theorem — structural uncertainty abstention is already formalized

**The claim it attacks:** The distinction between structural and confidence-based abstention is a new conceptual contribution.

**The evidence:** A paper published March 2026 — *"The Confidence Gate Theorem: When Should Ranked Decision Systems Abstain?"* — formally defines and empirically validates the **exact distinction** between structural uncertainty (missing data, cold-start) and contextual uncertainty (temporal drift), showing that structural uncertainty produces near-monotonic abstention gains while contextual uncertainty does not.  This paper is 19 days old and directly formalizes the theoretical backbone of TSUAN-NK's novelty claim. [arxiv](https://arxiv.org/html/2603.09947v1)

**How to rebut it:**
- The Confidence Gate Theorem is applied to **ranked decision systems** (recommenders, clinical triage queues) — not spatial reconstruction.
- It formalizes the distinction mathematically and empirically, which actually *helps* TSUAN-NK: you can **cite this as theoretical grounding** for why structural abstention is distinct and beneficial, then claim the first application in geospatial image reconstruction.
- However, the theoretical novelty of the concept is now weaker since it has been formalized elsewhere.

**Survivability: Moderate-to-Strong.** The formalization exists but in a different domain. You inherit the theoretical grounding, which is better than having to prove it from scratch, and claim domain novelty.

### Rebuttal 4: "Learning to Abstain From Uninformative Data" (2023)

**The claim it attacks:** Jointly training a predictor and selector that distinguishes informative from uninformative data is new.

**The evidence:** Zhang et al. (2023) do exactly this — jointly optimize a predictor and a selector based on selective learning theory, with theoretical guarantees, in domains with high noise-to-signal ratio.  Their framework distinguishes "informative data" from "uninformative data" during **both training and inference** — structurally identical to the TSUAN-NK framing. [arxiv](https://arxiv.org/abs/2309.14240)

**How to rebut it:**
- Zhang et al. define uninformative data by **label noise** (noisy ground truth signal), not by **structural spatial-temporal absence of ground truth**.
- In TSUAN-NK, the uninformative case is not a noisy label — it is the **nonexistence of any label** for a persistent void, which is a physically different situation.
- Noisy labels can still provide a training signal; structural voids cannot. The distinction is between *"unreliable signal"* and *"no signal"*.

**Survivability: Moderate.** Genuine distinction exists, but requires careful framing.

### Rebuttal 5: SelectSeg — uncertainty-based selective prediction for segmentation already exists in remote sensing

**The claim it attacks:** Selective prediction with abstention for geospatial tasks is new.

**The evidence:** SelectSeg (2025) introduces uncertainty-based selective training and prediction for **segmentation**, specifically including the scenario where high foreground uncertainty should trigger abstention.  This is in the same domain (geospatial analysis) and uses a similar selective training loss. [sciencedirect](https://www.sciencedirect.com/science/article/abs/pii/S0951832025001127)

**How to rebut it:**
- SelectSeg addresses classification/segmentation uncertainty — it abstains when class boundaries are ambiguous.
- TSUAN-NK addresses **reconstruction** under structural observational absence — a completely different task where the question is not "which class?" but "does any ground truth observation exist for this pixel in the archive?"

**Survivability: Strong.** Different task, different trigger, different output.

### Rebuttal 6: RESTORE-DiT — already claims "reliable" satellite reconstruction

**The claim it attacks:** The reliability/abstention framing for satellite time series reconstruction is new.

**The evidence:** RESTORE-DiT (2025, *Remote Sensing of Environment*) explicitly claims "reliable" reconstruction and promotes "sequence-level reliability" in satellite image time series reconstruction. [sciencedirect](https://www.sciencedirect.com/science/article/pii/S0034425725002767)

**How to rebut it:**
- RESTORE-DiT's "reliability" refers to **reconstruction quality metrics** (SSIM, PSNR consistency), not to a formal abstention mechanism.
- It does not produce a "knowability map" or binary abstention output.

**Survivability: Strong.** The framing is different enough.

### Rebuttal 7: ESA/NASA cloud frequency maps already are "knowability maps"

**The claim it attacks:** The knowability map is a new geospatial product.

**The evidence:** ESA Copernicus, NASA MODIS, and Landsat data availability products already provide cloud frequency statistics and valid pixel counts, which effectively quantify where persistent cloud cover makes optical data unreliable. [andrewsforest.oregonstate](https://andrewsforest.oregonstate.edu/pubs/pdf/pub4192.pdf)

**How to rebut it:**
- Cloud frequency statistics are **static, archive-level summaries** computed over years of historical data.
- TSUAN-NK's knowability map is **dynamic and input-conditioned**: it tells you, given *this specific input sequence* with *these specific gaps*, whether *this specific reconstruction* is structurally recoverable. That is a fundamentally richer, instance-specific product.
- The analogy: cloud frequency maps tell you "it rains here 80% of the time." TSUAN-NK tells you "given that it rained every day during your specific 3-month observation window, your specific field cannot be reconstructed."

**Survivability: Strong.** The distinction between static archive statistics and dynamic instance-conditioned knowability is clear and defensible.

## Consolidation: What Is the Minimum Viable Novelty Claim?

After all rebuttals, here is what survives with the strongest foundation:

| Component | Novelty Status | Strongest Threat |
|---|---|---|
| Jointly trained structural void detector (SOVD) | **Survives** — no prior jointly-trained detector for spatial voids | UnCRtainTS post-hoc filtering |
| Architecture-level suppression before reconstruction | **Survives** — no prior work suppresses the reconstruction branch | Barnes et al. threshold abstention |
| Instance-conditioned knowability map as new product | **Survives** | Cloud frequency statistics |
| Distinction between structural void and model confidence triggers | **Partially survives** | Confidence Gate Theorem (2026) formalizes this |
| "Negative knowledge" as a named concept | **Survives** | No paper uses this framing for geospatial reconstruction |

## What the Paper Must Do to Be Publishable

Based on this research, here are the **non-negotiable requirements**:

1. **Explicitly compare to UnCRtainTS filtering** in an ablation: show cases where UnCRtainTS has low uncertainty but SOVD correctly abstains (the model is confidently wrong on a structural void — hallucinating land cover change that never happened). This is the key empirical differentiator. [arxiv](https://arxiv.org/pdf/2304.05464.pdf)

2. **Cite and directly address the Confidence Gate Theorem** (March 2026)  as theoretical grounding — don't fight it, adopt it. Frame TSUAN-NK as "the first application of structural uncertainty abstention in geospatial image reconstruction, grounded in [Doku 2026]." [arxiv](https://arxiv.org/html/2603.09947v1)

3. **Use the Barnes et al. "NotWrong loss" as a baseline**  — show that their confidence-based abstention misses structural voids that SOVD catches, because they trigger on different phenomena. [agupubs.onlinelibrary.wiley](https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2021MS002575)

4. **Define the knowability map formally** as an instance-conditioned product and contrast it explicitly with static cloud frequency maps.

5. **Name the mechanism precisely** — "Structural Observational Void Detection" or "Archive-Conditioned Abstention" — to avoid being categorized as "just selective prediction." The name needs to signal the spatial, archive-level, instance-conditioned nature of the trigger.

The idea is real, the gap is real, but it is **narrow enough that the paper will be rejected without explicit, empirical head-to-head comparison with UnCRtainTS post-hoc filtering**. That comparison is the entire paper.

---

Files updated
- Updated review document: [projects/tsuan/REVIEW.md](projects/tsuan/REVIEW.md)

Next steps
- I updated the tracked TODOs and added literature/action items. I can now either (A) add a CI workflow and unit tests for TTA/ONNX (quick, high ROI), or (B) scaffold the UnCRtainTS head-to-head ablation (requires dataset + eval harness). Which do you want me to start next?

---

**Literature survey — quick summaries & implications**

1) The Confidence Gate Theorem (Doku et al., Mar 2026)
- Key points: formal diagnostic (C1 rank-alignment, C2 no-inversion zones) that predicts when confidence-gating/abstention is monotonic; structural vs contextual uncertainty distinction; practical tests (binning, Spearman ρ) and recommended diagnostics before deployment.
- Implication for TSUAN: use C1/C2 checks on held-out scenes and show SOVD satisfies C2 where UnCRtainTS post-hoc filtering may not. Cite for theoretical grounding and include diagnostic plots.

2) Barnes & Barnes — NotWrong loss (2021)
- Key points: training-time abstention by adding an abstention class and PID controller to control abstention fraction; applied to Earth system prediction/classification; improves skillful predictions by ignoring unskillful samples during training.
- Implication for TSUAN: implement Barnes-style baseline (NotWrong loss) for comparison; emphasize that Barnes targets learned-abstention for predictable labels whereas TSUAN targets structural observation absence.

3) Learning to Abstain From Uninformative Data (Zhang et al., 2023)
- Key points: joint predictor + selector, theoretical guarantees in noisy/no-signal regimes; iterative optimization; focus on distinguishing informative vs uninformative samples.
- Implication for TSUAN: methodological similarity—use as background and implement one joint predictor-selector baseline that does not use archive-structure features (contrast on structural void cases).

4) UnCRtainTS (Ebel et al., CVPR EarthVision 2023) — (primary threat)
- Key points (from paper): model outputs per-pixel uncertainty; authors show filtering high-uncertainty reconstructions dramatically reduces error; demonstrates uncertainty correlates with persistent occlusion.
- Implication for TSUAN: primary head-to-head baseline. Need ablation that demonstrates SOVD catches structural-void cases where UnCRtainTS uncertainty is low/confident (confidently wrong). Also compare downstream metrics when discarding by UnCRtainTS vs masking via SOVD.

5) Other related works (SelectSeg, RESTORE-DiT, cloud-frequency products)
- Use SelectSeg and RESTORE-DiT as secondary baselines (segmentation/sequence-level reliability respectively) and explain task differences in paper.

**Recommended evaluation protocol (concrete, reproducible)**
- Datasets: SEN12MS-CR-TS / synthetic persistent-occlusion generator (see TODO). Include both real scenes with persistent cloud strips and synthetic extreme cases where no clear observation exists for a pixel across T.
- Metrics:
  - Selective risk / coverage vs risk curves (selective RMSE or selective SSIM) across abstention thresholds.
  - C1/C2 diagnostics: Spearman ρ for ranking and inversion counts on binned confidence.
  - Calibration: ECE for uncertainty estimates and reliability diagrams.
  - False-abstain / miss-abstain confusion: fraction of truly unrecoverable pixels correctly abstained vs fraction of recoverable pixels mistakenly abstained.
  - Case-level analysis: identify examples where UnCRtainTS gives low variance but reconstruction is wrong (manual visualization + quantitative thresholding).
- Baselines to implement:
  - UnCRtainTS-style post-hoc uncertainty filtering (reproduce ranking + thresholding).
  - Barnes NotWrong loss (training-time abstention baseline).
  - Joint predictor-selector (Zhang 2023) without archive-structure features.
  - Simple archive-count heuristic (static knowability) and ensemble disagreement.

**Concrete experiments to demonstrate novelty**
1. Synthetic persistent-occlusion test: create sequences where target pixel is never visible; show UnCRtainTS uncertainty sometimes low but SOVD abstains (or show opposite). Produce side-by-side reconstructions and selective-RMSE curves.
2. Coverage–risk comparison: plot curves for TSUAN (SOVD masking), UnCRtainTS-filter, Barnes-trained abstention, and random baseline. Report area under coverage–risk to summarize.
3. C1/C2 verification: run the diagnostic on held-out real and synthetic sets for each baseline; show TSUAN satisfies C2 where others violate it.
4. Ablation: ablate SOVD inputs (archive-structure features vs none) to show that structural features are necessary for SOVD’s selective behavior.
5. Report failure modes: show when TSUAN abstains incorrectly (false abstain) and when UnCRtainTS confidently hallucinates; include visualization grid.

**Low-effort next code items (high ROI)**
- Add a small `scripts/make_synthetic_occlusion.py` to generate extreme persistent-occlusion scenes for quick testing.
- Add `benchmarks/coverage_vs_risk.py` helper to compute selective-RMSE curves and C1/C2 diagnostics.
- Add a simple UnCRtainTS post-hoc ranking wrapper that consumes TSUAN's reconstruction + uncertainty for direct comparison.

I added these research tasks to the tracked TODOs. I can start implementing the high-ROI items now: (A) add CI + TTA/ONNX tests and the UnCRtainTS post-hoc baseline and synthetic generator, or (B) scaffold a full head-to-head experimental harness with SEN12MS data and plotting. Which do you want me to start? If you want, I can begin by creating the synthetic generator and a small benchmark script and run a quick smoke comparison between SOVD and an uncertainty-threshold baseline.

---

**Repository TODOs**

- [x] Review `encoder.py` methods
- [x] Review `attention.py` methods
- [x] Review `model.py` methods
- [x] Review `losses.py` methods
- [x] Review `data.py` and `decoder.py` methods
- [x] Review `train.py` and `inference.py` methods
- [x] Summarize findings and recommend fixes
- [~] Add literature deep-dive & rebuttals (in-progress)
- [ ] Add UnCRtainTS head-to-head ablation
- [ ] Add Confidence Gate Theorem citation and framing
- [ ] Add Barnes NotWrong baseline experiment
- [ ] Define knowability map formally in paper & docs
- [ ] Choose & document name for mechanism
- [ ] Add TTA/inference fixes (code & tests)
- [ ] Add GitHub Actions CI

If you'd like, I can start implementing the top-priority items now (CI + TTA fixes), or scaffold the UnCRtainTS ablation and evaluation harness next. Which should I begin?

---

## HARSH Novelty Teardown — Component-by-Component Prior Art

This section is deliberately adversarial: it lists every TSUAN component and the published work that has already done it, so we know exactly what is and is not novel. Keywords are bolded for searchability.

### 1. Dual-Stream SAR-Optical Encoder — NOT NOVEL

| Prior work | What it does |
|---|---|
| **DSen2-CR** (Meraner et al., RSE 2020) | CNN that takes **SAR + cloudy optical** as dual input streams and produces cloud-free optical output. Trained on **SEN12MS-CR** (Sentinel-1 + Sentinel-2). First major dual-stream SAR-optical cloud removal network. |
| **Sebastianelli et al. (2021)** "Spatio-Temporal SAR-Optical Data Fusion for Cloud Removal via a Deep Hierarchical Model" | Uses **both temporal sequences and SAR-to-optical translation** in a hierarchical deep model. Combines temporal blending of multi-date optical with direct SAR-to-optical mapping — exactly the dual-stream temporal design TSUAN uses. |
| **GLF-CR** (Xu et al., IEEE TGRS 2022) | **Global-Local Fusion** network for SAR-guided cloud removal with separate global (SAR-to-optical) and local (inpainting) branches that fuse. Dual-stream architecture with explicit SAR guidance. |
| **SEN12MS-CR-TS** dataset paper (Ebel et al., 2022) | Defines the standard **SAR+optical time series cloud removal benchmark** on which UnCRtainTS and many others train. TSUAN's data pipeline is a reimplementation of this dataset format. |

**Verdict:** TSUAN's dual-stream CNN encoder is a standard pattern in this field since 2020. No novelty.

### 2. Attention Mechanism for Cloud Removal — NOT NOVEL

| Prior work | What it does |
|---|---|
| **PMAA** (Zou et al., ECAI 2023) | **Progressive Multi-scale Attention Autoencoder** for multi-temporal cloud removal. Uses a novel Multi-scale Attention Module (MAM) and Local Interaction Module to build contextual dependencies at multiple scales. Achieves SOTA on SEN12MS-CR-TS at 0.5% of CTGAN's parameters. |
| **CTGAN** (Sarukkai et al., 2020) | Temporal attention GAN for multi-temporal cloud removal with **attention-weighted temporal aggregation** across time steps. |
| **UnCRtainTS** (Ebel et al., CVPRW 2023) | **Temporal attention** (L-TAE inspired) over multi-date inputs with **learned temporal attention weights** to reconstruct cloud-free output. Attention is already the core mechanism. |
| **STGAN** (various, 2021-2023) | Spatio-temporal attention GANs for satellite image reconstruction. |
| **Vision Transformers for RS** (survey: Aleissaee et al., 2023) | Comprehensive survey showing **self-attention and cross-attention** are now standard in remote sensing tasks including cloud removal, change detection, and image fusion. |

**Verdict:** Attention-based cloud removal is a crowded space with multiple published architectures. TSUAN's intra-modal and cross-modal attention blocks are architecturally similar to standard multi-head cross-attention in vision transformers. No novelty in the attention design itself.

### 3. Uncertainty Quantification in Cloud Removal — PARTIALLY COVERED

| Prior work | What it does |
|---|---|
| **UnCRtainTS** (Ebel et al., 2023) | Predicts **per-pixel aleatoric uncertainty** via heteroscedastic NLL loss during cloud removal. Shows uncertainty correlates with persistent occlusion. Filters high-uncertainty reconstructions to halve error. **This is the primary threat.** |
| **Kendall & Gal (NeurIPS 2017)** | Defines the **epistemic vs aleatoric decomposition** that TSUAN's pixel/patch/region uncertainty hierarchy is based on. Standard technique. |
| **Deep Ensembles** (Lakshminarayanan et al., NeurIPS 2017) | Shows simple model averaging gives strong uncertainty estimates. TSUAN's TTA-variance approach is a weaker version of ensemble disagreement. |
| **MC Dropout for RS** (multiple papers, 2019-2024) | Monte Carlo dropout for uncertainty in remote sensing reconstruction/classification. Well-established baseline. |

**Verdict:** Per-pixel uncertainty in cloud removal already exists (UnCRtainTS). TSUAN's hierarchical pixel/patch/region decomposition is a minor architectural variation, not a new concept. The NLL calibration loss is standard (Kendall & Gal 2017).

### 4. Physical Consistency Loss (NDVI/EVI) — NOT NOVEL

| Prior work | What it does |
|---|---|
| **Physics-informed remote sensing** (multiple, 2019-2024) | NDVI-based regularization, spectral consistency constraints, and vegetation index preservation are standard in satellite image reconstruction. |
| **Cresson & Grizonnet (2020)** | Optical image gap-filling using physical radiometric constraints. |
| **SEN2-NAIP Downscaling** (various) | Uses band-ratio constraints (including NDVI, EVI, NDWI) as loss terms for super-resolution and reconstruction of satellite imagery. |

**Verdict:** Hardcoding NDVI/EVI band ratios as a physical loss is a well-known technique. TSUAN does not introduce new physical constraints. No novelty.

### 5. Training Loop (Mixed Precision, EMA, Cosine LR, Gradient Clipping) — NOT NOVEL

These are standard deep learning training practices used universally since ~2019. Every modern PyTorch training loop uses some combination of:
- `torch.cuda.amp` mixed precision (NVIDIA, 2018)
- Exponential Moving Average of weights (Polyak averaging; popularized by EfficientNet, 2019)
- AdamW + cosine annealing (Loshchilov & Hutter, ICLR 2019)
- Gradient clipping (standard since LSTM era)

**Verdict:** No novelty. These are boilerplate.

### 6. Test-Time Augmentation (TTA) for Uncertainty — NOT NOVEL

| Prior work | What it does |
|---|---|
| **Shanmugam et al. (2021)** | TTA for uncertainty estimation in medical and satellite imagery. |
| **Moshkov et al. (2020)** | TTA with geometric augmentations + inverse transforms for segmentation uncertainty. |
| **Standard practice** | Averaging over flips and rotations with inverse transforms is a standard technique in Kaggle competitions and production CV pipelines since ~2017. |

**Verdict:** TTA with geometric augmentations and inverse transforms is textbook. No novelty.

### 7. Decoder Architecture (ConvTranspose Upsampling) — NOT NOVEL

Symmetric encoder-decoder with transposed convolutions for upsampling is the foundational U-Net / autoencoder design (Ronneberger et al., 2015). Every cloud removal network uses some version of this. No novelty.

### 8. ONNX Export and Deployment — NOT NOVEL

Standard PyTorch-to-ONNX export pipeline. No novelty.

### 9. Cloud Mask as Auxiliary Task — NOT NOVEL

| Prior work | What it does |
|---|---|
| **s2cloudless** (Sentinel Hub, production) | Cloud detection as a standalone product used globally. |
| **FMask** (Zhu & Woodcock, RSE 2012) | Function of Mask — standard operational cloud/shadow detection. |
| **Multi-task cloud removal + detection** (multiple papers) | Joint cloud detection and removal is a common multi-task formulation. |

**Verdict:** Auxiliary cloud segmentation head is a standard multi-task pattern. No novelty.

### 10. Curriculum Learning for Loss Weighting — MINOR NOVELTY

Ramping loss weights over epochs is used in:
- **Bengio et al. (2009)** — curriculum learning (foundational paper)
- **Self-paced learning** (Kumar et al., 2010)
- Various satellite image training pipelines

TSUAN's specific implementation (ramping uncertainty and physical loss weights linearly over epochs) is a minor variant. Marginal novelty at best.

---

## Honest Assessment: What Is Left?

After stripping away everything that already exists, here is what TSUAN actually has:

| Component | Status |
|---|---|
| Dual-stream SAR-optical encoder | **Not novel** — DSen2-CR, Sebastianelli et al., GLF-CR |
| Temporal attention for cloud removal | **Not novel** — UnCRtainTS, PMAA, CTGAN |
| Per-pixel uncertainty via NLL | **Not novel** — UnCRtainTS does this |
| Hierarchical uncertainty (pixel/patch/region) | **Minor variation** — decomposition is architectural, not conceptual |
| Physical consistency loss (NDVI/EVI) | **Not novel** — standard in RS |
| Training loop, TTA, decoder, ONNX | **Not novel** — boilerplate |
| Cross-modal uncertainty-weighted attention | **Possibly minor novelty** — weighting attention by uncertainty estimates from the other modality |
| Dynamic temperature scaling via uncertainty | **Possibly minor novelty** — Softplus-based temperature from uncertainty encoder |
| SOVD / Knowability Map (proposed, not yet implemented) | **Potentially novel** — but not built yet |
| "Negative Knowledge" framing | **Conceptually novel** — but needs empirical backing |

### The hard truth

**TSUAN as currently implemented is an incremental engineering contribution**, not a research contribution. It combines known components (dual-stream encoder, temporal attention, NLL uncertainty, physical loss) in a reasonable but unoriginal way. The only potentially publishable ideas are:

1. **SOVD (Structural Observational Void Detection)** — not yet implemented
2. **Knowability Maps** as a first-class output product — not yet implemented  
3. **Negative Knowledge** framing — a naming/conceptual contribution only
4. **Cross-modal uncertainty-weighted attention** — the idea that attention weights should be modulated by the *other* modality's uncertainty estimate is a small but genuine contribution, if empirically validated against non-uncertainty-weighted cross-attention

### What must change for this to be publishable

The current TSUAN codebase is a **baseline**, not a paper. To make it publishable:

1. **Implement SOVD** — the structural void detector that suppresses reconstruction before it happens. This is the only component with clear novelty.
2. **Implement the Knowability Map** — a binary/probabilistic output map indicating per-pixel recoverability, conditioned on the specific input archive.
3. **Run head-to-head against UnCRtainTS** on SEN12MS-CR-TS — show SOVD catches cases UnCRtainTS misses.
4. **Show cross-modal uncertainty-weighted attention outperforms standard cross-attention** — ablation required.
5. **Show the hierarchical uncertainty decomposition adds value** — ablation: pixel-only vs pixel+patch vs pixel+patch+region.
6. **Cite and position against** the Confidence Gate Theorem, Barnes NotWrong, Zhang 2023 selective learning.

Without items 1-3, this is not a publishable paper. It is a well-engineered reimplementation of existing ideas.

---

## Updated Repository TODOs (comprehensive)

**Code quality / bug fixes (do first)**
- [ ] Fix TTA inverse-transform bug in `inference.py` (uncertainty not inverse-transformed)
- [ ] Fix `torch.load` invalid kwarg in `inference.py`
- [ ] Serialize config as dict in checkpoints (`dataclasses.asdict`)
- [ ] Add EMA save/load helpers to `train.py`
- [ ] Harden ONNX export dynamic axes for all outputs
- [ ] Add dataset verification utility to `data.py`

**Testing & CI**
- [ ] Add TTA unit tests (verify inverse transforms, uncertainty aggregation)
- [ ] Add ONNX export smoke test
- [ ] Add GitHub Actions CI (pytest on push/PR)

**Research-critical (paper-blocking)**
- [ ] Implement SOVD module (`src/tsuan/sovd.py`) — structural void detector
- [ ] Implement Knowability Map output in model forward pass
- [ ] Create synthetic persistent-occlusion dataset generator (`scripts/make_synthetic_occlusion.py`)
- [ ] Add coverage-vs-risk benchmark script (`benchmarks/coverage_vs_risk.py`)
- [ ] Add UnCRtainTS post-hoc baseline wrapper for comparison
- [ ] Run ablation: uncertainty-weighted attention vs standard cross-attention
- [ ] Run ablation: hierarchical uncertainty (pixel-only vs pixel+patch+region)
- [ ] Run head-to-head: TSUAN+SOVD vs UnCRtainTS post-hoc filtering on synthetic + real data
- [ ] Add Barnes NotWrong loss baseline for comparison
- [ ] Write paper section: novelty claim, positioning, limitations

**Documentation & polish**
- [ ] Document expected input shapes and band ordering in README
- [ ] Add example dataset generator and demo notebook
- [ ] Sync `standalone-checkouts/tsuan` with latest changes

***

## The Most Important Finding: The Closest Prior Work

The single most dangerous paper you must know about is **UnCRtainTS (Ebel et al., CVPR EarthVision 2023)**.  Reading the full paper reveals this direct quote from Figure 1's caption: *"Note how higher uncertainties (in red) are associated with **persistent occlusion**."*  They already show that under total, persistent cloud coverage with no clear observations in the time series, their model outputs high uncertainty, and they explicitly use this to **filter out unreliable reconstructions** — Figure 3 shows discarding the top 50% of uncertain samples **halves prediction error**.  This is the most direct threat to the novelty claim and must be understood precisely. [arxiv](https://arxiv.org/pdf/2304.05464.pdf)

***

## Exhaustive Rebuttal Mapping for Negative Knowledge Learning

### Rebuttal 1 (MOST DANGEROUS): UnCRtainTS already does this

**The claim it attacks:** TSUAN-NK's structural abstention on persistent voids is new.

**The evidence:** UnCRtainTS explicitly: (1) predicts uncertainty that is highest at persistent occlusion, (2) shows that filtering by this uncertainty dramatically reduces reconstruction error, and (3) links high uncertainty to "restorations based on too little evidence."  The SEN12MS-CR-TS benchmark they use even contains scenes with 100% cloud coverage across all time steps. [patricktum.github](https://patricktum.github.io/cloud_removal/)

**How to rebut it — and how strong that rebuttal is:**

The critical distinction survives, but narrowly:
- UnCRtainTS' abstention is **post-hoc** and **confidence-threshold-based** — it ranks completed reconstructions by their variance and discards the worst ones at inference time.  It does not predict *before* running the reconstruction whether a pixel is structurally unknowable. [arxiv](https://arxiv.org/pdf/2304.05464.pdf)
- TSUAN-NK's mechanism is fundamentally different: it jointly trains a **Structural Observational Void Detector (SOVD)** that predicts *a priori* (from the input observation archive structure) whether a pixel is even worth attempting to reconstruct — before the reconstruction head runs, not after it.
- UnCRtainTS will produce a reconstruction output AND an uncertainty for every pixel; TSUAN-NK's detector would **suppress the reconstruction branch** for voided pixels and output a binary "I cannot know" instead of a high-variance estimate.

**This distinction is real but extremely narrow.** A reviewer will say: "High-uncertainty filtering in UnCRtainTS is functionally equivalent to your abstention — you're just thresholding the same signal at a different point in the pipeline." You need a very clear empirical demonstration that SOVD fires on cases where UnCRtainTS is incorrectly *low* uncertainty (i.e., confidently wrong), to separate them.

***

### Rebuttal 2: Barnes & Barnes "NotWrong Loss" — already in Earth science

**The claim it attacks:** Training-integrated abstention during learning in Earth observation is new.

**The evidence:** Barnes & Barnes (2021) published the "NotWrong loss" specifically for Earth system prediction, applied during training (not post-hoc), with a PID controller to enforce a user-specified abstention fraction.  It was published in the *Journal of Advances in Modeling Earth Systems* — directly in the geoscience ML domain.  It even uses a dedicated abstention class in the output layer, identical in spirit to what TSUAN-NK proposes. [arxiv](https://arxiv.org/abs/2104.08281)

**How to rebut it:**
- Barnes & Barnes apply this to **temporal prediction** (climate forecasting, classification problems). Their abstention trigger is *model confidence* in classifying the current system state.
- TSUAN-NK's trigger is fundamentally different: it is triggered by **structural absence in the spatial-temporal observation archive**, not by model confidence in what it has seen. A Barnes-style model trained on full-coverage data would never abstain on a fully-cloudy pixel because it hasn't seen the observational void — it's not in its input representation.
- However, a reviewer will still note significant conceptual overlap in the training objective design.

**Survivability: Moderate.** The domain specificity (spatiotemporal reconstruction vs. temporal classification) and trigger mechanism (structural void vs. model confidence) are genuine differences, but the paper must explicitly address this comparison.

***

### Rebuttal 3: The Confidence Gate Theorem — structural uncertainty abstention is already formalized

**The claim it attacks:** The distinction between structural and confidence-based abstention is a new conceptual contribution.

**The evidence:** A paper published March 2026 — *"The Confidence Gate Theorem: When Should Ranked Decision Systems Abstain?"* — formally defines and empirically validates the **exact distinction** between structural uncertainty (missing data, cold-start) and contextual uncertainty (temporal drift), showing that structural uncertainty produces near-monotonic abstention gains while contextual uncertainty does not.  This paper is 19 days old and directly formalizes the theoretical backbone of TSUAN-NK's novelty claim. [arxiv](https://arxiv.org/html/2603.09947v1)

**How to rebut it:**
- The Confidence Gate Theorem is applied to **ranked decision systems** (recommenders, clinical triage queues) — not spatial reconstruction.
- It formalizes the distinction mathematically and empirically, which actually *helps* TSUAN-NK: you can **cite this as theoretical grounding** for why structural abstention is distinct and beneficial, then claim the first application in geospatial image reconstruction.
- However, the theoretical novelty of the concept is now weaker since it has been formalized elsewhere.

**Survivability: Moderate-to-Strong.** The formalization exists but in a different domain. You inherit the theoretical grounding, which is better than having to prove it from scratch, and claim domain novelty.

***

### Rebuttal 4: "Learning to Abstain From Uninformative Data" (2023)

**The claim it attacks:** Jointly training a predictor and selector that distinguishes informative from uninformative data is new.

**The evidence:** Zhang et al. (2023) do exactly this — jointly optimize a predictor and a selector based on selective learning theory, with theoretical guarantees, in domains with high noise-to-signal ratio.  Their framework distinguishes "informative data" from "uninformative data" during **both training and inference** — structurally identical to the TSUAN-NK framing. [arxiv](https://arxiv.org/abs/2309.14240)

**How to rebut it:**
- Zhang et al. define uninformative data by **label noise** (noisy ground truth signal), not by **structural spatial-temporal absence of ground truth**.
- In TSUAN-NK, the uninformative case is not a noisy label — it is the **nonexistence of any label** for a persistent void, which is a physically different situation.
- Noisy labels can still provide a training signal; structural voids cannot. The distinction is between *"unreliable signal"* and *"no signal"*.

**Survivability: Moderate.** Genuine distinction exists, but requires careful framing.

***

### Rebuttal 5: SelectSeg — uncertainty-based selective prediction for segmentation already exists in remote sensing

**The claim it attacks:** Selective prediction with abstention for geospatial tasks is new.

**The evidence:** SelectSeg (2025) introduces uncertainty-based selective training and prediction for **segmentation**, specifically including the scenario where high foreground uncertainty should trigger abstention.  This is in the same domain (geospatial analysis) and uses a similar selective training loss. [sciencedirect](https://www.sciencedirect.com/science/article/abs/pii/S0951832025001127)

**How to rebut it:**
- SelectSeg addresses classification/segmentation uncertainty — it abstains when class boundaries are ambiguous.
- TSUAN-NK addresses **reconstruction** under structural observational absence — a completely different task where the question is not "which class?" but "does any ground truth observation exist for this pixel in the archive?"
- The two settings have different loss formulations, different triggers, and different downstream implications.

**Survivability: Strong.** Different task, different trigger, different output.

***

### Rebuttal 6: RESTORE-DiT — already claims "reliable" satellite reconstruction

**The claim it attacks:** The reliability/abstention framing for satellite time series reconstruction is new.

**The evidence:** RESTORE-DiT (2025, *Remote Sensing of Environment*) explicitly claims "reliable" reconstruction and promotes "sequence-level reliability" in satellite image time series reconstruction. [sciencedirect](https://www.sciencedirect.com/science/article/pii/S0034425725002767)

**How to rebut it:**
- RESTORE-DiT's "reliability" refers to **reconstruction quality metrics** (SSIM, PSNR consistency), not to a formal abstention mechanism.
- It does not produce a "knowability map" or binary abstention output.
- "Reliable reconstruction" and "knowing when not to reconstruct" are fundamentally different claims.

**Survivability: Strong.** The framing is different enough.

***

### Rebuttal 7: ESA/NASA cloud frequency maps already are "knowability maps"

**The claim it attacks:** The knowability map is a new geospatial product.

**The evidence:** ESA Copernicus, NASA MODIS, and Landsat data availability products already provide cloud frequency statistics and valid pixel counts, which effectively quantify where persistent cloud cover makes optical data unreliable. [andrewsforest.oregonstate](https://andrewsforest.oregonstate.edu/pubs/pdf/pub4192.pdf)

**How to rebut it:**
- Cloud frequency statistics are **static, archive-level summaries** computed over years of historical data.
- TSUAN-NK's knowability map is **dynamic and input-conditioned**: it tells you, given *this specific input sequence* with *these specific gaps*, whether *this specific reconstruction* is structurally recoverable. That is a fundamentally richer, instance-specific product.
- The analogy: cloud frequency maps tell you "it rains here 80% of the time." TSUAN-NK tells you "given that it rained every day during your specific 3-month observation window, your specific field cannot be reconstructed."

**Survivability: Strong.** The distinction between static archive statistics and dynamic instance-conditioned knowability is clear and defensible.

***

## Consolidation: What Is the Minimum Viable Novelty Claim?

After all rebuttals, here is what survives with the strongest foundation:

| Component | Novelty Status | Strongest Threat |
|---|---|---|
| Jointly trained structural void detector (SOVD) | **Survives** — no prior jointly-trained detector for spatial voids | UnCRtainTS post-hoc filtering |
| Architecture-level suppression before reconstruction | **Survives** — no prior work suppresses the reconstruction branch | Barnes et al. threshold abstention |
| Instance-conditioned knowability map as new product | **Survives** | Cloud frequency statistics |
| Distinction between structural void and model confidence triggers | **Partially survives** | Confidence Gate Theorem (2026) formalizes this |
| "Negative knowledge" as a named concept | **Survives** | No paper uses this framing for geospatial reconstruction |

***

## What the Paper Must Do to Be Publishable

Based on this research, here are the **non-negotiable requirements**:

1. **Explicitly compare to UnCRtainTS filtering** in an ablation: show cases where UnCRtainTS has low uncertainty but SOVD correctly abstains (the model is confidently wrong on a structural void — hallucinating land cover change that never happened). This is the key empirical differentiator. [arxiv](https://arxiv.org/pdf/2304.05464.pdf)

2. **Cite and directly address the Confidence Gate Theorem** (March 2026)  as theoretical grounding — don't fight it, adopt it. Frame TSUAN-NK as "the first application of structural uncertainty abstention in geospatial image reconstruction, grounded in [Doku 2026]." [arxiv](https://arxiv.org/html/2603.09947v1)

3. **Use the Barnes et al. "NotWrong loss" as a baseline**  — show that their confidence-based abstention misses structural voids that SOVD catches, because they trigger on different phenomena. [agupubs.onlinelibrary.wiley](https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2021MS002575)

4. **Define the knowability map formally** as an instance-conditioned product and contrast it explicitly with static cloud frequency maps.

5. **Name the mechanism precisely** — "Structural Observational Void Detection" or "Archive-Conditioned Abstention" — to avoid being categorized as "just selective prediction." The name needs to signal the spatial, archive-level, instance-conditioned nature of the trigger.

The idea is real, the gap is real, but it is **narrow enough that the paper will be rejected without explicit, empirical head-to-head comparison with UnCRtainTS post-hoc filtering**. That comparison is the entire paper.
