# Demo Storyboard

## Reviewer Goal

Show a flood-forecasting workflow that moves from a real public stage series to a cleaner autoregressive forecast with scenario bands.

## Suggested Walkthrough

1. Start in the README to frame the project as a Python recreation of a flood-forecasting case study using a public South Texas analog gauge.
2. Open the preview asset to show raw and denoised hydrograph behavior at a glance.
3. Open the generated `outputs/charts/hydrograph-overview.png` and `outputs/charts/pmse-by-order.png` charts to compare the raw and denoised branches quickly.
4. Use `outputs/charts/lag-diagnostics.png` to discuss order selection with the ACF and PACF panels.
5. Highlight the Monte Carlo percentile bands and review-threshold exceedance probabilities from the holdout and threshold charts.
6. Open `outputs/review-summary.html` to show the entire review package in one artifact.
7. Open `outputs/cross-site-comparison.html` to focus the discussion on the second-gauge experiment and the denoising-versus-noise question.
8. Use `outputs/charts/wavelet-benefit-comparison.png` to compare the main gauge against Oso Creek and discuss whether denoising helps more on the noisier site.
9. Use `docs/case-study-walkthrough.md` when you want to present the project in article form rather than as a software demo.
10. Note that the workflow is packaged as a reusable class with tests rather than a one-off script.

## Talking Points

- The public USGS series makes the workflow reproducible without needing MATLAB or private hydrology archives.
- The denoised signal usually stabilizes the AR fit by reducing high-frequency noise.
- PMSE provides a direct comparison against the holdout flood window.
- Monte Carlo output makes the forecast more operational because it communicates uncertainty, not just a single line.