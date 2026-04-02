# Runbook

## Purpose

Run TSUAN in quick-start inference mode, then expand to training or deployment export only after the tensor path is verified.

## Local Setup

```bash
pip install -e .[dev]
pytest -q
```

## Quick Inference Check

Use the small-config smoke path from the tests to confirm model construction, forward inference, and TTA aggregation all run.

## Training Setup

```bash
pip install -e .[dev,train]
```

Set `cfg.data.data_root` before training.

## Deployment Export

```bash
pip install -e .[dev,deploy]
```

Confirm ONNX export only after the basic forward path passes.

## Operational Notes

- Start with synthetic tensors before loading large real scenes.
- Validate uncertainty outputs alongside reconstructions, not in isolation.
- Keep GPU-heavy workflows out of default CI expectations.