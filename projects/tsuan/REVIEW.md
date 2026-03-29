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
