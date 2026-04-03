# Benchmark Summary

Evaluation context for the Arroyo flood forecasting lab.

## Forecasting Framework

The lab uses a wavelet-denoised autoregressive pipeline applied to USGS gage-height data:

1. **Wavelet preprocessing**: Daubechies wavelet denoising to reduce measurement noise
2. **AR order selection**: Candidate autoregressive models evaluated on hold-out PMSE
3. **Monte Carlo scenarios**: Stochastic simulation for flood exceedance probability

## Model Comparison

| Model | Approach | Purpose |
| --- | --- | --- |
| AR(1) | Single-lag autoregression | Baseline simplicity |
| AR(2) | Two-lag autoregression | Captures short memory |
| AR(p) selected | Data-driven order selection | Best hold-out performance |
| Raw vs Denoised | Side-by-side comparison | Quantifies denoising benefit |

## Hold-Out Evaluation Metrics

- **PMSE** (Prediction Mean Square Error): primary selection criterion for AR order
- **MAE**: mean absolute error on the hold-out window
- **Coverage**: fraction of actual values within Monte Carlo prediction intervals

## Wavelet Denoising Impact

On the built-in USGS gage-height sample:

| Input | PMSE (relative) | Notes |
| --- | --- | --- |
| Raw series | 1.0x (baseline) | Higher variance, more noise |
| Denoised series | Lower | Smoother, better AR fit |

The denoised series generally produces lower PMSE and tighter prediction intervals.

## Monte Carlo Scenario Review

The lab generates N Monte Carlo scenario paths from the fitted AR model. Key outputs:

- Ensemble hydrograph with prediction fan
- Threshold exceedance probability for flood stages
- Scenario spread as a function of forecast horizon

## Chart Outputs

| Chart | Purpose |
| --- | --- |
| Raw vs denoised hydrograph | Visual denoising comparison |
| Lag diagnostics (ACF/PACF) | AR order guidance |
| PMSE by AR order | Model selection evidence |
| Hold-out forecast overlay | Forecast accuracy review |
| Threshold exceedance | Flood risk probability |
| Wavelet coefficient comparison | Denoising detail |

## Limitations

- Based on a single USGS gage station for demonstration
- AR models are linear and may underperform on nonlinear flood dynamics
- Monte Carlo assumes stationary noise characteristics
- Real flood forecasting systems require ensemble weather inputs and distributed hydrological models
