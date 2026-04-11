# Evaluation Artifact

Evaluation context for the Gulf Coast inundation lab.

## Methodology

The lab applies AWEIsh (Automated Water Extraction Index, shadow-reduced) to Landsat imagery for inundation-frequency mapping:

1. **AOI definition**: Gulf Coast study area polygon
2. **Landsat collection**: Multi-decadal Landsat 5/7/8/9 archive
3. **QA masking**: Cloud, cloud shadow, and fill pixel removal via QA band
4. **Water classification**: AWEIsh thresholding on each scene
5. **Frequency calculation**: Pixel-level inundation frequency across the image stack
6. **Validation**: Correlation with USGS gauge records where available

## Expected Output

| Artifact | Description |
| --- | --- |
| Inundation frequency map | Per-pixel fraction of scenes classified as water |
| AOI summary | Total area, inundation extent statistics, scene count |
| Gauge correlation summary | Pearson correlation between classified inundation extent and gauge stage |

## Validation Context

- Gauge correlation provides ground-truth context for the classification threshold
- A high correlation (r > 0.7) suggests the AWEIsh classification tracks real water-level variation
- Lower correlations may indicate cloud contamination, mixed pixels, or threshold sensitivity

## Limitations

- AWEIsh is a spectral index, not a hydraulic model — it detects surface water appearance, not flow
- Cloud masking removes scenes but does not correct for shadow misclassification
- The frequency calculation assumes all scenes in the stack are equally valid after QA masking
- Landsat's 30m resolution limits detection of narrow waterways and small ponds
- The local workflow operates on pre-exported assets, not live Earth Engine computation
