# Example Output

Representative flood forecast summary for a single station run.

```text
station_id: arroyo_demo_01
model_family: wavelet_ar
forecast_horizon_hours: 24
peak_stage_ft: 7.8
peak_time_utc: 2026-03-14T18:00:00Z
exceedance_probability_bankfull: 0.64
rmse_backtest_ft: 0.41
scenario_note: moderate-rain pulse with denoised upstream signal
```

This is the kind of artifact a reviewer should expect from a forecast batch: a clear peak estimate, timing, and exceedance risk.