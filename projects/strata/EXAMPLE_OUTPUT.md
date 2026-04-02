# Example Output

Representative uncertainty-aware model summary for an infrastructure risk run.

```csv
asset_id,risk_mean,interval_low,interval_high,mondrian_group,covered
line_118_a,0.71,0.58,0.83,high_load,true
substation_24,0.43,0.30,0.57,urban_core,true
transformer_09,0.18,0.09,0.29,rural_edge,true
```

This is the key review artifact for STRATA: calibrated risk scores with uncertainty intervals that can be inspected asset by asset.