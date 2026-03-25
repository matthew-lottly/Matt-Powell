# References

Working reference ledger for CausalLens manuscript preparation.
Organized by method area. Each entry includes the citation, the CausalLens claim it supports, and notes on comparator software or journal-format requirements.

---

## General Causal Software

| Ref | Citation | Claim Supported | Comparator | Notes |
|-----|----------|----------------|------------|-------|
| S1 | Sharma, A., and Kiciman, E. (2020). DoWhy: An end-to-end library for causal inference. arXiv:2011.04216. | DoWhy does not cover RD, bunching, or structural elasticity. CausalLens fills a different design slice. | DoWhy | Verified arXiv preprint. |
| S2 | Battocchi, K., Dillon, E., Hei, M., Lewis, G., Oka, P., Oprescu, M., and Syrgkanis, V. (2019). EconML: A Python package for ML-based heterogeneous treatment effects estimation. | EconML targets HTE/DML, not quasi-experimental designs (RD, bunching). | EconML | Microsoft Research; docs at econml.azurewebsites.net. |
| S3 | Bach, P., Chernozhukov, V., Kurz, M. S., and Spindler, M. (2022). DoubleML — An object-oriented implementation of double machine learning in Python. Journal of Machine Learning Research, 23(53), 1–6. | DoubleML shows a JMLR software-paper precedent for wrapping established methods. Does not cover RD, bunching, or panel methods. | DoubleML | Published JMLR 23(53):1–6, 2022. |
| S4 | Chen, H., Harinen, T., Lee, J.-Y., Yung, M., and Zhao, Z. (2020). CausalML: Python package for causal machine learning. | causalml targets uplift/HTE, not quasi-experimental design estimators. | causalml | Uber open-source. |
| S5 | Shimoni, Y., Yanover, C., Karavani, E., and Goldstein, Y. (2019). An evaluation toolkit to guide model selection and cohort definition in causal inference. arXiv:1906.00442. | causallib is closest on modularity/diagnostics for weighting, but does not cover RD, bunching, or panel methods. | causallib | IBM Research. |
| S6 | Calonico, S., Cattaneo, M. D., and Titiunik, R. (2015). rdrobust: An R package for robust nonparametric inference in regression-discontinuity designs. The R Journal, 7(1), 38–51. | rdrobust is the RD gold standard but is a single-design tool; CausalLens integrates RD alongside other designs. | rdrobust (R) | Also available in Stata. |
| S7 | Calonico, S., Cattaneo, M. D., Farrell, M. H., and Titiunik, R. (2017). rdrobust: Software for regression discontinuity designs. The Stata Journal, 17(2), 372–404. | Stata companion to S6. | rdrobust (Stata) | |
| S8 | Cattaneo, M. D., Jansson, M., and Ma, X. (2020). Simple local polynomial density estimators. Journal of the American Statistical Association, 115(531), 1449–1455. | rddensity provides formal manipulation testing; CausalLens embeds a simpler McCrary test as an integrated diagnostic. | rddensity (R/Stata) | |
| S9 | Mavrokonstantis, P., and Lockwood, B. (2020). bunching: An R package for bunching estimation. Working paper. | R bunching package is deeper on bunching-specific features; CausalLens adds cross-design integration value. | bunching (R) | Citation status: working paper. Verify journal publication status before submission. |

---

## Observational Identification and Estimation

| Ref | Citation | Claim Supported | Notes |
|-----|----------|----------------|-------|
| O1 | Rosenbaum, P. R., and Rubin, D. B. (1983). The central role of the propensity score in observational studies for causal effects. Biometrika, 70(1), 41–55. | Foundational propensity-score identification. | |
| O2 | Imbens, G. W., and Wooldridge, J. M. (2009). Recent developments in the econometrics of program evaluation. Journal of Economic Literature, 47(1), 5–86. | Cross-sectional treatment-effect estimation survey. | |
| O3 | Lunceford, J. K., and Davidian, M. (2004). Stratification and weighting via the propensity score in estimation of causal treatment effects: a comparative study. Statistics in Medicine, 23(19), 2937–2960. | IPW variance derivation used in CausalLens SE correction. | |
| O4 | Abadie, A., and Imbens, G. W. (2006). Large sample properties of matching estimators for average treatment effects. Econometrica, 74(1), 235–267. | Matching estimator standard errors. | |
| O5 | Imbens, G. W. (2004). Nonparametric estimation of average treatment effects under exogeneity: a review. Review of Economics and Statistics, 86(1), 4–29. | General ATE estimation review. | |

---

## Doubly Robust and Machine-Learning Estimation

| Ref | Citation | Claim Supported | Notes |
|-----|----------|----------------|-------|
| D1 | Chernozhukov, V., Chetverikov, D., Demirer, M., Duflo, E., Hansen, C., Newey, W., and Robins, J. (2018). Double/debiased machine learning for treatment and structural parameters. The Econometrics Journal, 21(1), C1–C68. | DML/cross-fitting implementation basis. | |
| D2 | Künzel, S. R., Sekhon, J. S., Bickel, P. J., and Yu, B. (2019). Metalearners for estimating heterogeneous treatment effects using machine learning. Proceedings of the National Academy of Sciences, 116(10), 4156–4165. | T-learner and S-learner meta-learner implementations. | |
| D3 | Robins, J. M., Rotnitzky, A., and Zhao, L. P. (1994). Estimation of regression coefficients when some regressors are not always observed. Journal of the American Statistical Association, 89(427), 846–866. | Doubly robust estimation foundations. | |
| D4 | Bang, H., and Robins, J. M. (2005). Doubly robust estimation in missing data and causal inference models. Biometrics, 61(4), 962–973. | DR estimation practical properties. | |

---

## Sensitivity Analysis

| Ref | Citation | Claim Supported | Notes |
|-----|----------|----------------|-------|
| SA1 | VanderWeele, T. J., and Ding, P. (2017). Sensitivity analysis in observational research: introducing the E-value. Annals of Internal Medicine, 167(4), 268–274. | E-value implementation in CausalLens diagnostics. | |
| SA2 | Rosenbaum, P. R. (2002). Observational Studies. 2nd ed. Springer. | Rosenbaum bounds for matched-pair sensitivity. | |
| SA3 | Cinelli, C., and Hazlett, C. (2020). Making sense of sensitivity: extending omitted variable bias. Journal of the Royal Statistical Society Series B, 82(1), 39–67. | OVB partial-R² framework implemented in CausalLens `ovb_bounds()` function with robustness values and benchmark-calibrated bounds. | |

---

## Difference-in-Differences and Panel Methods

| Ref | Citation | Claim Supported | Notes |
|-----|----------|----------------|-------|
| P1 | Angrist, J. D., and Pischke, J.-S. (2009). Mostly Harmless Econometrics. Princeton University Press. | General DiD and IV identification framework. | |
| P2 | Callaway, B., and Sant'Anna, P. H. C. (2021). Difference-in-differences with multiple time periods. Journal of Econometrics, 225(2), 200–230. | Staggered DiD now implemented in CausalLens `StaggeredDiD` class with group-time ATT aggregation. | |
| P3 | de Chaisemartin, C., and D'Haultfoeuille, X. (2020). Two-way fixed effects estimators with heterogeneous treatment effects. American Economic Review, 110(9), 2964–2996. | Heterogeneous-treatment-effect DiD diagnostics. Motivates the staggered implementation. | |

---

## Synthetic Control

| Ref | Citation | Claim Supported | Notes |
|-----|----------|----------------|-------|
| SC1 | Abadie, A., Diamond, A., and Hainmueller, J. (2010). Synthetic control methods for comparative case studies. Journal of the American Statistical Association, 105(490), 493–505. | Synthetic control method implementation basis. | |
| SC2 | Abadie, A. (2021). Using synthetic controls: feasibility, data requirements, and methodological aspects. Journal of Economic Literature, 59(2), 391–425. | Updated survey and methodological review. | |

---

## Instrumental Variables

| Ref | Citation | Claim Supported | Notes |
|-----|----------|----------------|-------|
| IV1 | Angrist, J. D., Imbens, G. W., and Rubin, D. B. (1996). Identification of causal effects using instrumental variables. Journal of the American Statistical Association, 91(434), 444–455. | IV/LATE identification framework. | |
| IV2 | Stock, J. H., and Yogo, M. (2005). Testing for weak instruments in linear IV regression. In Andrews, D. W. K., and Stock, J. H. (Eds.), Identification and Inference for Econometric Models, 80–108. Cambridge University Press. | First-stage F-statistic and weak-instrument detection thresholds. | |

---

## Regression Discontinuity

### Foundational

| Ref | Citation | Claim Supported | Notes |
|-----|----------|----------------|-------|
| RD1 | Thistlethwaite, D. L., and Campbell, D. T. (1960). Regression-discontinuity analysis: an alternative to the ex post facto experiment. Journal of Educational Psychology, 51(6), 309–317. | RD design origin. | |
| RD2 | Hahn, J., Todd, P., and van der Klaauw, W. (2001). Identification and estimation of treatment effects with a regression-discontinuity design. Econometrica, 69(1), 201–209. | Sharp and fuzzy RD identification. | |

### Practical Guides

| Ref | Citation | Claim Supported | Notes |
|-----|----------|----------------|-------|
| RD3 | Imbens, G., and Lemieux, T. (2008). Regression discontinuity designs: a guide to practice. Journal of Econometrics, 142(2), 615–635. | Practitioner guidance on RD implementation. | |
| RD4 | Lee, D. S., and Lemieux, T. (2010). Regression discontinuity designs in economics. Journal of Economic Literature, 48(2), 281–355. | Comprehensive RD review. | |
| RD5 | Cattaneo, M. D., Idrobo, N., and Titiunik, R. (2020). A Practical Introduction to Regression Discontinuity Designs: Foundations. Cambridge Elements. Cambridge University Press. | Modern practical RD reference. | |
| RD6 | Cattaneo, M. D., Idrobo, N., and Titiunik, R. (2024). A Practical Introduction to Regression Discontinuity Designs: Extensions. Cambridge Elements. Cambridge University Press. | Extensions including covariates and fuzzy designs. | |

### Robust Inference and Bandwidth Selection

| Ref | Citation | Claim Supported | Notes |
|-----|----------|----------------|-------|
| RD7 | Calonico, S., Cattaneo, M. D., and Titiunik, R. (2014). Robust nonparametric confidence intervals for regression-discontinuity designs. Econometrica, 82(6), 2295–2326. | CCT bias-correction approach implemented in CausalLens RD estimator. | |
| RD8 | Calonico, S., Cattaneo, M. D., and Farrell, M. H. (2020). Optimal bandwidth choice for robust bias corrected inference in regression discontinuity designs. The Econometrics Journal, 23(2), 192–210. | MSE-optimal bandwidth. Not yet implemented in CausalLens; listed in roadmap. | |
| RD9 | Imbens, G. W., and Kalyanaraman, K. (2012). Optimal bandwidth choice for the regression discontinuity estimator. Review of Economic Studies, 79(3), 933–959. | IK bandwidth selection. | |

### Fuzzy RD

| Ref | Citation | Claim Supported | Notes |
|-----|----------|----------------|-------|
| RD10 | Lee, D. S. (2008). Randomized experiments from non-random selection in U.S. House elections. Journal of Econometrics, 142(2), 675–697. | Fuzzy RD application and methodology. | |
| RD11 | Dong, Y. (2015). Regression discontinuity applications with rounding errors in the running variable. Journal of Applied Econometrics, 30(3), 422–446. | Running-variable rounding issues. | |

### Covariates in RD

| Ref | Citation | Claim Supported | Notes |
|-----|----------|----------------|-------|
| RD12 | Calonico, S., Cattaneo, M. D., Farrell, M. H., and Titiunik, R. (2019). Regression discontinuity designs using covariates. Review of Economics and Statistics, 101(3), 442–451. | Covariate-adjusted RD. | |

### Manipulation Testing

| Ref | Citation | Claim Supported | Notes |
|-----|----------|----------------|-------|
| RD13 | McCrary, J. (2008). Manipulation of the running variable in the regression discontinuity design: a density test. Journal of Econometrics, 142(2), 698–714. | McCrary test implemented as integrated RD diagnostic. | |

---

## Bunching

### Foundational

| Ref | Citation | Claim Supported | Notes |
|-----|----------|----------------|-------|
| B1 | Saez, E. (2010). Do taxpayers bunch at kink points? American Economic Journal: Economic Policy, 2(3), 180–212. | Structural bunching elasticity formula basis. | |
| B2 | Chetty, R., Friedman, J. N., Olsen, T., and Pistaferri, L. (2011). Adjustment costs, firm responses, and micro vs. macro labor supply elasticities: evidence from Danish tax records. Quarterly Journal of Economics, 126(2), 749–804. | Extended bunching methodology with adjustment costs. | |
| B3 | Kleven, H. J., and Waseem, M. (2013). Using notches to uncover optimization frictions and structural elasticities: theory and evidence from Pakistan. Quarterly Journal of Economics, 128(2), 669–723. | Notch design methodology. CausalLens does not implement notch estimation. | |

### Methodology and Surveys

| Ref | Citation | Claim Supported | Notes |
|-----|----------|----------------|-------|
| B4 | Kleven, H. J. (2016). Bunching. Annual Review of Economics, 8, 435–464. | Structural elasticity formula used in CausalLens bunching estimator. | |
| B5 | Blomquist, S., and Newey, W. (2017). The bunching estimator cannot identify the taxable income elasticity. NBER Working Paper No. 24136. | Bunching identification limitations. Supports limitations disclosure. | |
| B6 | Bertanha, M., McCallum, A. H., and Seegert, N. (2023). Better bunching, nicer notching. Journal of Econometrics, 237(2), 105516. | Modern bunching methodology improvements. | |

### Applications

| Ref | Citation | Claim Supported | Notes |
|-----|----------|----------------|-------|
| B7 | Bastani, S., and Selin, H. (2014). Bunching and non-bunching at kink points of the Swedish tax schedule. Journal of Public Economics, 109, 36–49. | Applied bunching study. | |
| B8 | Marx, B. M. (2022). Dynamic bunching estimation with panel data. NBER Working Paper No. 27424. | Panel bunching methods. | |

---

## Benchmark Datasets

| Ref | Citation | Claim Supported | Notes |
|-----|----------|----------------|-------|
| BM1 | Dehejia, R. H., and Wahba, S. (1999). Causal effects in nonexperimental studies: reevaluating the evaluation of training programs. Journal of the American Statistical Association, 94(448), 1053–1062. | Lalonde/NSW benchmark dataset used in CausalLens validation. | |
| BM2 | Hernán, M. A., and Robins, J. M. (2020). Causal Inference: What If. Chapman & Hall/CRC. | NHEFS dataset and causal inference textbook reference values. | |

---

## Software-Paper Precedents

| Ref | Citation | Relevance | Notes |
|-----|----------|-----------|-------|
| SP1 | Bach et al. (2022) — see S3 above. | JMLR software-paper model: object-oriented wrapper of established methods is publishable. | |
| SP2 | Calonico et al. (2015) — see S6 above. | The R Journal software-paper model for a single-design tool. | |
| SP3 | Calonico et al. (2017) — see S7 above. | Stata Journal companion. | |

---

## Citation Status Log

References requiring verification or update before submission:

- **S9 (bunching R package):** Currently cited as a working paper. Check whether a journal version has appeared.
- **S5 (causallib):** arXiv preprint. Confirm no journal publication.
- **SA3 (Cinelli & Hazlett):** Now implemented. Include in submission.
- **P2, P3 (staggered DiD):** Staggered DiD now implemented. Include in submission.
- **RD8 (CCF 2020 bandwidth):** MSE-optimal bandwidth not yet implemented; cite to acknowledge roadmap gap.
