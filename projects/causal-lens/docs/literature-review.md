# Literature Review

This document records the literature and software positioning for CausalLens.
The goal is to narrow the project claim to something the repository can defend, while articulating the genuine architectural novelty that makes the package publishable.

## Claim Boundary

CausalLens does not claim to invent new estimators. The implemented methods are established and well-cited. What is new is their integration:

**No existing Python package provides a unified, diagnostics-first API spanning observational cross-sectional estimation, panel methods, instrumental variables, local-polynomial regression discontinuity (sharp and fuzzy with robust bias-corrected inference), and structural bunching elasticity estimation — all with built-in manipulation testing, sensitivity analysis, and Monte Carlo validation.**

The defensible contribution has three layers:

1. **Cross-design integration.** CausalLens integrates observational estimators, DiD, synthetic control, IV/2SLS, sharp and fuzzy RD with CCT-style robust inference, McCrary manipulation testing, and structural bunching elasticity through a common result-object API. No single existing Python package covers this design space with integrated diagnostics.
2. **Diagnostics-first architecture.** Every estimator returns result objects that carry not just point estimates but also sensitivity measures, balance checks, manipulation tests, and validity diagnostics. These are part of the API contract, not notebook-side afterthoughts.
3. **Reviewable evidence stack.** The repository ships public benchmarks, reference-parity tests, cross-design Monte Carlo simulation studies, and manuscript-oriented exports so that every claim is testable.

This positions CausalLens for a *Journal of Statistical Software*, *Journal of Open Source Software (JOSS)*, or *Stata Journal*-style software paper, not a methods paper.

## Software Positioning

Several adjacent Python libraries occupy important parts of the causal-inference landscape. What follows is a feature-by-feature positioning showing what each covers and what CausalLens adds.

### DoWhy

DoWhy (Sharma & Kiciman, 2020) is strongest on identification, graph-based modeling, and refutation workflows. It provides a structured do-calculus-based pipeline from causal graphs to estimation. It does not implement local-polynomial RD, bunching, or structural elasticity estimation. CausalLens complements DoWhy by covering design-based quasi-experimental methods that DoWhy delegates to downstream estimators.

### EconML

EconML (Battocchi et al., 2019) is the strongest comparison for heterogeneous treatment effects, orthogonalization, forests, advanced IV, and ML-heavy CATE estimation. It exposes DML, DR learners, meta-learners, and policy learning. It does not include RD estimation, bunching analysis, or McCrary testing. CausalLens covers a different slice of the design space focused on quasi-experimental validity rather than heterogeneous-effect estimation.

### DoubleML

DoubleML (Bach et al., 2022) is a specialized benchmark for orthogonal score estimation and modern semiparametric inference. Its JMLR software-paper precedent is important because it shows that a publishable contribution can be about an object-oriented implementation of established methods. DoubleML does not cover RD, bunching, or panel methods. CausalLens is broader on identification designs but narrower on ML nuisance flexibility.

### causalml

causalml (Chen et al., 2020) emphasizes uplift modeling, heterogeneous treatment effects, synthetic benchmarking, and practitioner workflows. Like EconML, it targets ML-based treatment-effect heterogeneity and does not provide quasi-experimental design estimators.

### causallib

causallib (Shimoni et al., 2019) provides a scikit-learn-style ecosystem for observational causal estimation and evaluation. It is the closest comparison on modularity and diagnostics for weighting and standardization workflows, but it does not cover RD, bunching, or panel designs.

### rdrobust (R/Stata)

rdrobust (Calonico, Cattaneo & Titiunik, 2015; Calonico et al., 2017) is the methodological gold standard for local-polynomial RD. It provides sharp and fuzzy RD estimation, optimal bandwidth selection (Calonico, Cattaneo & Farrell, 2020), robust bias-corrected inference, and publication-quality RD plots. CausalLens implements the same CCT 2014 bias-correction approach but does not claim algorithmic parity with rdrobust's bandwidth optimization. Where CausalLens differs is integration: rdrobust is an RD-only tool, while CausalLens embeds RD alongside observational, panel, IV, and bunching estimators in one diagnostic-carrying API.

### bunching (R)

The R `bunching` package (Mavrokonstantis & Lockwood, 2020) implements the Chetty/Saez/Kleven bunching methodology with bootstrap inference, round-number bunching corrections, and extensive plotting. CausalLens implements the core Saez (2010) / Kleven (2016) structural elasticity formula with bootstrap CIs. The R package is deeper on bunching-specific features; CausalLens adds the integration value of combining bunching with RD, IV, and panel methods.

### rddensity (R/Stata)

rddensity (Cattaneo, Jansson & Ma, 2020) provides formal manipulation testing for RD designs using local polynomial density estimation, extending McCrary (2008). CausalLens implements a simpler kernel-weighted McCrary test as a built-in diagnostic on the RD estimator object, trading methodological depth for integration convenience.

### MatchIt, Synth, and sensemakr (R / R+Stata)

Focused software packages in the R ecosystem reinforce the same pattern. MatchIt (Ho, Imai, King & Stuart, 2011) is strong on matching-oriented preprocessing and balance review. Synth (Abadie, Diamond & Hainmueller, 2011) is a well-established synthetic-control implementation with a clear software-paper precedent. sensemakr (Cinelli, Ferwerda & Hazlett, 2020) packages omitted-variable-bias sensitivity analysis for regression settings. These are important comparators because they show that publishable causal software often succeeds by being deep, clear, and reproducible within one design family. CausalLens differs by prioritizing cross-design workflow integration over single-design depth.

### Summary Positioning Table

| Feature | DoWhy | EconML | DoubleML | causalml | causallib | rdrobust | CausalLens |
|---|---|---|---|---|---|---|---|
| Observational ATE/ATT | via backends | ✓ | ✓ | ✓ | ✓ | — | ✓ |
| Doubly robust / DML | via backends | ✓ | ✓ | ✓ | ✓ | — | ✓ |
| DiD / Synthetic control | — | — | — | — | — | — | ✓ |
| Staggered DiD | — | — | — | — | — | — | ✓ |
| IV / 2SLS | — | ✓ | — | — | — | — | ✓ |
| Sharp RD | — | — | — | — | — | ✓ | ✓ |
| Fuzzy RD (Wald) | — | — | — | — | — | ✓ | ✓ |
| Robust bias-corrected RD | — | — | — | — | — | ✓ | ✓ |
| McCrary / manipulation test | — | — | — | — | — | — | ✓ |
| Structural bunching elasticity | — | — | — | — | — | — | ✓ |
| OVB sensitivity (Cinelli-Hazlett) | — | — | — | — | — | — | ✓ |
| Built-in sensitivity analysis | refutations | — | — | — | — | — | ✓ |
| Cross-design diagnostics | — | — | — | — | — | — | ✓ |
| Cross-design Monte Carlo | — | — | — | — | — | — | ✓ |
| Unified result objects | — | — | — | — | — | — | ✓ |

This table is the core evidence for the publishable claim: no single Python package integrates all of these designs with diagnostic infrastructure.

## What CausalLens Can Reasonably Claim

Against that backdrop, the repository can make five specific claims.

1. **Design-space breadth with unified diagnostics.** CausalLens integrates observational cross-sectional estimators, difference-in-differences (including staggered adoption), synthetic control, instrumental variables, sharp and fuzzy local-polynomial RD with robust bias-corrected inference, McCrary manipulation testing, and structural bunching elasticity in one lightweight library with common result objects. No existing Python package covers this combination.
2. **Diagnostics-first API contract.** Every estimator returns result objects that include validity diagnostics (covariate balance, propensity overlap, first-stage F-statistics, manipulation tests, sensitivity bounds) as first-class fields rather than optional post-hoc computations.
3. **Modern sensitivity analysis.** The package provides E-values (VanderWeele & Ding 2017), Rosenbaum sensitivity bounds, and Cinelli & Hazlett (2020) omitted-variable bias analysis with robustness values and benchmark-calibrated partial-R² bounds, giving users multiple complementary lenses on unmeasured confounding.
4. **Cross-design diagnostic comparison.** The `compare_designs()` API collects assumption evidence from observational, DiD, IV, RD, and bunching analyses into a single sorted summary, supporting the kind of multi-design triangulation increasingly expected in applied causal research.
5. **Reviewable evidence stack.** The repository includes public benchmark datasets, reference-parity tests, cross-design Monte Carlo simulations covering all DGP families, and manuscript-oriented exports. Every quantitative claim in the software paper can be reproduced from the repository.

These are software-architecture and workflow claims supported by the code. They are not claims of new econometrics.

## Core Methods Literature

### Observational Identification And Estimation

- Rosenbaum, P. R., and Rubin, D. B. (1983). The central role of the propensity score in observational studies for causal effects. Biometrika, 70(1), 41-55.
- Imbens, G. W., and Wooldridge, J. M. (2009). Recent developments in the econometrics of program evaluation. Journal of Economic Literature, 47(1), 5-86.
- Lunceford, J. K., and Davidian, M. (2004). Stratification and weighting via the propensity score in estimation of causal treatment effects: a comparative study. Statistics in Medicine, 23(19), 2937-2960.
- Abadie, A., and Imbens, G. W. (2006). Large sample properties of matching estimators for average treatment effects. Econometrica, 74(1), 235-267.
- Imbens, G. W. (2004). Nonparametric estimation of average treatment effects under exogeneity: a review. Review of Economics and Statistics, 86(1), 4-29.

### Doubly Robust And Machine-Learning Estimation

- Chernozhukov, V., Chetverikov, D., Demirer, M., Duflo, E., Hansen, C., Newey, W., and Robins, J. (2018). Double/debiased machine learning for treatment and structural parameters. The Econometrics Journal, 21(1), C1-C68.
- Künzel, S. R., Sekhon, J. S., Bickel, P. J., and Yu, B. (2019). Metalearners for estimating heterogeneous treatment effects using machine learning. Proceedings of the National Academy of Sciences, 116(10), 4156-4165.
- Robins, J. M., Rotnitzky, A., and Zhao, L. P. (1994). Estimation of regression coefficients when some regressors are not always observed. Journal of the American Statistical Association, 89(427), 846-866.
- Bang, H., and Robins, J. M. (2005). Doubly robust estimation in missing data and causal inference models. Biometrics, 61(4), 962-973.

### Sensitivity Analysis

- VanderWeele, T. J., and Ding, P. (2017). Sensitivity analysis in observational research: introducing the E-value. Annals of Internal Medicine, 167(4), 268-274.
- Rosenbaum, P. R. (2002). Observational Studies. Springer.
- Cinelli, C., and Hazlett, C. (2020). Making sense of sensitivity: extending omitted variable bias. Journal of the Royal Statistical Society Series B, 82(1), 39-67.

### Difference-In-Differences And Panel Methods

- Angrist, J. D., and Pischke, J.-S. (2009). Mostly Harmless Econometrics. Princeton University Press.
- Callaway, B., and Sant'Anna, P. H. C. (2021). Difference-in-differences with multiple time periods. Journal of Econometrics, 225(2), 200-230.
- de Chaisemartin, C., and D'Haultfoeuille, X. (2020). Two-way fixed effects estimators with heterogeneous treatment effects. American Economic Review, 110(9), 2964-2996.

### Synthetic Control

- Abadie, A., Diamond, A., and Hainmueller, J. (2010). Synthetic control methods for comparative case studies. Journal of the American Statistical Association, 105(490), 493-505.
- Abadie, A. (2021). Using synthetic controls: feasibility, data requirements, and methodological aspects. Journal of Economic Literature, 59(2), 391-425.

### Instrumental Variables

- Angrist, J. D., Imbens, G. W., and Rubin, D. B. (1996). Identification of causal effects using instrumental variables. Journal of the American Statistical Association, 91(434), 444-455.
- Stock, J. H., and Yogo, M. (2005). Testing for weak instruments in linear IV regression. In Andrews, D. W. K., and Stock, J. H. (Eds.), Identification and Inference for Econometric Models, 80-108. Cambridge University Press.

## Regression Discontinuity Literature

### Foundational

- Thistlethwaite, D. L., and Campbell, D. T. (1960). Regression-discontinuity analysis: an alternative to the ex post facto experiment. Journal of Educational Psychology, 51(6), 309-317.
- Hahn, J., Todd, P., and van der Klaauw, W. (2001). Identification and estimation of treatment effects with a regression-discontinuity design. Econometrica, 69(1), 201-209.

### Practical Guides

- Imbens, G., and Lemieux, T. (2008). Regression discontinuity designs: a guide to practice. Journal of Econometrics, 142(2), 615-635.
- Lee, D. S., and Lemieux, T. (2010). Regression discontinuity designs in economics. Journal of Economic Literature, 48(2), 281-355.
- Cattaneo, M. D., Idrobo, N., and Titiunik, R. (2020). A Practical Introduction to Regression Discontinuity Designs: Foundations. Cambridge Elements in Quantitative and Computational Methods for the Social Sciences. Cambridge University Press.
- Cattaneo, M. D., Idrobo, N., and Titiunik, R. (2024). A Practical Introduction to Regression Discontinuity Designs: Extensions. Cambridge Elements in Quantitative and Computational Methods for the Social Sciences. Cambridge University Press.

### Robust Inference And Bandwidth Selection

- Calonico, S., Cattaneo, M. D., and Titiunik, R. (2014). Robust nonparametric confidence intervals for regression-discontinuity designs. Econometrica, 82(6), 2295-2326.
- Calonico, S., Cattaneo, M. D., and Farrell, M. H. (2020). Optimal bandwidth choice for robust bias corrected inference in regression discontinuity designs. The Econometrics Journal, 23(2), 192-210.
- Imbens, G. W., and Kalyanaraman, K. (2012). Optimal bandwidth choice for the regression discontinuity estimator. Review of Economic Studies, 79(3), 933-959.

### Fuzzy RD

- Hahn, J., Todd, P., and van der Klaauw, W. (2001). Identification and estimation of treatment effects with a regression-discontinuity design. Econometrica, 69(1), 201-209.
- Lee, D. S. (2008). Randomized experiments from non-random selection in U.S. House elections. Journal of Econometrics, 142(2), 675-697.
- Dong, Y. (2015). Regression discontinuity applications with rounding errors in the running variable. Journal of Applied Econometrics, 30(3), 422-446.

### Covariates In RD

- Calonico, S., Cattaneo, M. D., Farrell, M. H., and Titiunik, R. (2019). Regression discontinuity designs using covariates. Review of Economics and Statistics, 101(3), 442-451.

### Manipulation Testing

- McCrary, J. (2008). Manipulation of the running variable in the regression discontinuity design: a density test. Journal of Econometrics, 142(2), 698-714.
- Cattaneo, M. D., Jansson, M., and Ma, X. (2020). Simple local polynomial density estimators. Journal of the American Statistical Association, 115(531), 1449-1455.

### Software

- Calonico, S., Cattaneo, M. D., and Titiunik, R. (2015). rdrobust: An R package for robust nonparametric inference in regression-discontinuity designs. The R Journal, 7(1), 38-51.
- Calonico, S., Cattaneo, M. D., Farrell, M. H., and Titiunik, R. (2017). rdrobust: Software for regression discontinuity designs. The Stata Journal, 17(2), 372-404.

## Bunching Literature

### Foundational

- Saez, E. (2010). Do taxpayers bunch at kink points? American Economic Journal: Economic Policy, 2(3), 180-212.
- Chetty, R., Friedman, J. N., Olsen, T., and Pistaferri, L. (2011). Adjustment costs, firm responses, and micro vs. macro labor supply elasticities: evidence from Danish tax records. Quarterly Journal of Economics, 126(2), 749-804.
- Kleven, H. J., and Waseem, M. (2013). Using notches to uncover optimization frictions and structural elasticities: theory and evidence from Pakistan. Quarterly Journal of Economics, 128(2), 669-723.

### Methodology And Surveys

- Kleven, H. J. (2016). Bunching. Annual Review of Economics, 8, 435-464.
- Blomquist, S., and Newey, W. (2017). The bunching estimator cannot identify the taxable income elasticity. NBER Working Paper No. 24136.
- Bertanha, M., McCallum, A. H., and Seegert, N. (2023). Better bunching, nicer notching. Journal of Econometrics, 237(2), 105516.

### Applications

- Bastani, S., and Selin, H. (2014). Bunching and non-bunching at kink points of the Swedish tax schedule. Journal of Public Economics, 109, 36-49.
- Marx, B. M. (2022). Dynamic bunching estimation with panel data. NBER Working Paper No. 27424.

### Software

- Mavrokonstantis, P., and Lockwood, B. (2020). bunching: An R package for bunching estimation. Working paper.

## Software References

- Battocchi, K., Dillon, E., Hei, M., Lewis, G., Oka, P., Oprescu, M., and Syrgkanis, V. (2019). EconML: A Python package for ML-based heterogeneous treatment effects estimation.
- Bach, P., Chernozhukov, V., Kurz, M. S., and Spindler, M. (2022). DoubleML - An object-oriented implementation of double machine learning in Python. Journal of Machine Learning Research, 23(53), 1-6.
- Shimoni, Y., et al. (2019). An evaluation toolkit for causal inference. arXiv:1906.00442.
- Chen, H., Harinen, T., Lee, J.-Y., Yung, M., and Zhao, Z. (2020). CausalML: Python package for causal machine learning.
- Sharma, A., and Kiciman, E. (2020). DoWhy: An end-to-end library for causal inference. arXiv:2011.04216.

## Novelty Assessment

### What is genuinely new

The strongest publishable novelty claim for CausalLens is *architectural*: it unifies causal estimation across six identification strategies — observational adjustment, difference-in-differences (including staggered adoption), instrumental variables, regression discontinuity, and bunching — with a common diagnostic-carrying result object API. No existing Python package spans this design space with integrated diagnostics. Specifically:

1. **Cross-design diagnostic integration.** No existing Python package lets a user run an observational IPW estimate with E-value sensitivity, a fuzzy RD with McCrary manipulation test and robust bias-corrected inference, and a structural bunching elasticity estimate in one import. The `compare_designs()` API collects assumption evidence from all identification strategies into a single sorted summary for side-by-side review.

2. **Structural bunching in Python.** As of this writing, structural bunching elasticity estimation (Saez 2010 / Kleven 2016 formula with bootstrap CIs) is not available in any published Python package. The R `bunching` package provides this, but Python users must currently implement it manually. CausalLens fills this gap.

3. **McCrary manipulation testing integrated into the RD estimator.** Rather than requiring a separate package or manual density computation, the `RegressionDiscontinuity` object exposes `mccrary_test()` as a method, returning a structured result. This is a diagnostics-first design choice that existing Python RD implementations do not make.

4. **Cinelli & Hazlett (2020) omitted-variable bias sensitivity.** CausalLens implements the partial-R² OVB framework with robustness values, significance-level robustness values, and benchmark-calibrated bounds. This goes beyond E-values by quantifying how strong a confounder must be — relative to observed covariates — to explain away the treatment effect.

5. **Staggered-adoption difference-in-differences.** Following Callaway & Sant’Anna (2021), CausalLens computes group-time ATTs for each adoption cohort using never-treated or not-yet-treated controls, then aggregates them into an overall ATT with size-weighted averaging.

6. **Cross-design Monte Carlo simulation.** The simulation framework covers DGPs for observational, nonlinear, sharp RD, fuzzy RD, and bunching settings in one harness, enabling unified coverage/bias reporting across identification strategies.

### What is explicitly not claimed

- CausalLens does not claim parity with rdrobust on bandwidth optimization, RD plotting, or the full CCT inference pipeline.
- CausalLens does not claim parity with EconML or DoubleML on ML-based nuisance estimation or heterogeneous treatment effects.
- CausalLens does not claim parity with DoWhy on graph-based identification and refutation workflows.
- CausalLens does not claim the structural bunching implementation matches the depth of the R `bunching` package on round-number corrections, diffuse bunching, or notch designs.
- CausalLens does not claim parity with the `sensemakr` R package on OVB visualization (contour plots) or the full sensitivity statistics suite.
- CausalLens does not claim parity with the `did` R package on doubly-robust group-time ATTs or bootstrapped simultaneous confidence bands for staggered DiD.

### Publication venue fit

- **JOSS (Journal of Open Source Software):** Strong fit. JOSS values well-documented, tested, open-source scientific software with a clear statement of need. The cross-design integration and diagnostics-first API are a clear "statement of need" that existing packages do not address.
- **JSS (Journal of Statistical Software):** Good fit if accompanied by a longer methods-and-software paper that documents each estimator, shows benchmark results, and includes a replication study.
- **SoftwareX:** Good fit for a shorter paper emphasizing the software engineering and reproducibility aspects.
- **Journal of Systems and Software:** Weak current fit without a major rewrite. The project would need to be reframed as a software-engineering or systems paper centered on architecture, maintainability, workflow design, quality assurance, and engineering evaluation rather than as a statistical-software validation paper.

The practical implication is that the current draft and evidence stack are aligned to JSS or a software-paper venue, not to an Elsevier software-engineering venue.

## Practical Conclusion

The package can now support manuscript claims about:

1. a unified Python package integrating causal estimation across six identification strategies with built-in diagnostics — a combination not available in any existing Python package,
2. a Python implementation of structural bunching elasticity with bootstrap inference, filling a gap that previously required R or manual implementation,
3. robust bias-corrected RD inference with integrated McCrary manipulation testing,
4. Cinelli & Hazlett (2020) omitted-variable bias sensitivity with robustness values and benchmark-calibrated bounds,
5. staggered-adoption DiD with cohort-level group-time ATTs following Callaway & Sant’Anna (2021),
6. cross-design diagnostic comparison via a unified API that collects assumption evidence across all identification strategies,
7. a reviewable evidence stack including public benchmarks, reference-parity tests, and cross-design Monte Carlo simulation, and
8. a compact, diagnostics-first software workflow for applied causal-inference review.

The limitations section must acknowledge that individual estimator implementations are not as deep as dedicated single-design packages (rdrobust for RD, bunching for bunching, EconML for CATE), and that the package targets breadth of design integration rather than depth on any single method.