# STRATA — References for Paper Submission

> Compiled reference list for the STRATA paper. 35 references organized by topic.
> BibTeX keys use `author_year_keyword` convention.

---

## 1. Conformal Prediction — Foundations

1. **Vovk, V., Gammerman, A., & Shafer, G. (2005).** *Algorithmic Learning in a Random World.* Springer.
   - Foundation of conformal prediction framework. Defines validity, exchangeability, and prediction regions.

2. **Shafer, G. & Vovk, V. (2008).** A tutorial on conformal prediction. *Journal of Machine Learning Research*, 9, 371–421.
   - Accessible tutorial covering inductive conformal prediction, nonconformity measures, and coverage guarantees.

3. **Papadopoulos, H., Proedrou, K., Vovk, V., & Gammerman, A. (2002).** Inductive confidence machines for regression. *Machine Learning and Applications (ECML)*, Springer, 345–356.
   - Introduces inductive (split) conformal prediction for regression, which STRATA builds upon.

4. **Lei, J., G'Sell, M., Rinaldo, A., Tibshirani, R. J., & Wasserman, L. (2018).** Distribution-free predictive inference for regression. *Journal of the American Statistical Association*, 113(523), 1094–1111.
   - Distribution-free prediction intervals framework. Establishes finite-sample coverage guarantees without distributional assumptions.

5. **Vovk, V. (2012).** Conditional validity of inductive conformal predictors. *Asian Conference on Machine Learning (ACML)*, PMLR 25, 475–490.
   - Mondrian conformal prediction: conditional validity by grouping. Underpins STRATA's per-type coverage guarantees.

---

## 2. Conformal Prediction — Advanced Methods

6. **Romano, Y., Patterson, E., & Candès, E. J. (2019).** Conformalized quantile regression. *Advances in Neural Information Processing Systems (NeurIPS)*, 32, 3543–3553.
   - CQR: combines quantile regression with conformal calibration for adaptive-width intervals. Implemented in STRATA's `CQRCalibrator`.

7. **Romano, Y., Sesia, M., & Candès, E. J. (2020).** Classification with valid and adaptive coverage. *Advances in Neural Information Processing Systems (NeurIPS)*, 33, 3581–3591.
   - Adaptive prediction sets for classification. Extends conformal methods to heterogeneous difficulty levels.

8. **Barber, R. F., Candès, E. J., Ramdas, A., & Tibshirani, R. J. (2023).** Conformal prediction beyond exchangeability. *Annals of Statistics*, 51(2), 816–845.
   - Extends conformal prediction to non-exchangeable settings, relevant to graph-structured data where node dependencies violate classical exchangeability.

9. **Angelopoulos, A. N. & Bates, S. (2023).** Conformal prediction: A gentle introduction. *Foundations and Trends in Machine Learning*, 16(4), 494–591.
   - Modern survey of conformal prediction methods, applications, and extensions.

10. **Papadopoulos, H. (2008).** Inductive conformal prediction: Theory and application to neural networks. *Tools in Artificial Intelligence*, IntechOpen, 315–330.
    - Normalized nonconformity scores and their role in producing locally adaptive prediction intervals.

---

## 3. Conformal Prediction on Graphs

11. **Zargarbashi, S. H., Antonelli, S., & Bojchevski, A. (2023).** Conformal prediction sets for graph neural networks. *International Conference on Machine Learning (ICML)*, PMLR 202, 12292–12312.
    - Conformal prediction adapted for GNNs, addressing challenges of node-level prediction with graph dependencies.

12. **Huang, K., Jin, Y., Candès, E. J., & Leskovec, J. (2024).** Uncertainty quantification over graph with conformalized graph neural networks. *Advances in Neural Information Processing Systems (NeurIPS)*, 36.
    - CF-GNN: conformalized GNN framework addressing exchangeability challenges in graph-structured predictions.

13. **Clarkson, J. (2023).** Distribution-free prediction sets for node classification. *International Conference on Artificial Intelligence and Statistics (AISTATS)*, PMLR 206, 1–18.
    - Distribution-free coverage guarantees for node classification on graphs. Addresses non-exchangeability of graph nodes.

---

## 4. Graph Neural Networks

14. **Kipf, T. N. & Welling, M. (2017).** Semi-supervised classification with graph convolutional networks. *International Conference on Learning Representations (ICLR)*.
    - Graph convolutional networks (GCN): foundational message-passing framework for node-level tasks.

15. **Veličković, P., Cucurull, G., Casanova, A., Romero, A., Liò, P., & Bengio, Y. (2018).** Graph attention networks. *International Conference on Learning Representations (ICLR)*.
    - GAT: attention-based neighbor aggregation in GNNs. Inspires STRATA's `AttentionCalibrator` design.

16. **Gilmer, J., Schoenholz, S. S., Riley, P. F., Vinyals, O., & Dahl, G. E. (2017).** Neural message passing for quantum chemistry. *International Conference on Machine Learning (ICML)*, PMLR 70, 1263–1272.
    - Message Passing Neural Networks (MPNN): general framework unifying GNN variants under message/update/readout operations.

17. **Schlichtkrull, M., Kipf, T. N., Bloem, P., van den Berg, R., Titov, I., & Welling, M. (2018).** Modeling relational data with graph convolutional networks. *European Semantic Web Conference (ESWC)*, Springer, 593–607.
    - R-GCN: relation-specific weight matrices for heterogeneous graphs. Directly underpins STRATA's `HeteroMessagePassingLayer` per-edge-type transforms.

18. **Wang, X., Ji, H., Shi, C., Wang, B., Ye, Y., Cui, P., & Yu, P. S. (2019).** Heterogeneous graph attention network. *The World Wide Web Conference (WWW)*, 2022–2032.
    - HAN: hierarchical attention for heterogeneous graphs with semantic-level and node-level attention.

19. **Hamilton, W. L., Ying, R., & Leskovec, J. (2017).** Inductive representation learning on large graphs. *Advances in Neural Information Processing Systems (NeurIPS)*, 30, 1025–1035.
    - GraphSAGE: sampling-based aggregation for inductive learning. Introduces mean/LSTM/pooling aggregators.

---

## 5. Uncertainty Quantification in Deep Learning

20. **Lakshminarayanan, B., Pritzel, A., & Blundell, C. (2017).** Simple and scalable predictive uncertainty estimation using deep ensembles. *Advances in Neural Information Processing Systems (NeurIPS)*, 30, 6402–6413.
    - Deep ensembles for epistemic uncertainty. Foundation for STRATA's `EnsembleHeteroGNN` variance-based uncertainty decomposition.

21. **Gal, Y. & Ghahramani, Z. (2016).** Dropout as a Bayesian approximation: Representing model uncertainty in deep learning. *International Conference on Machine Learning (ICML)*, PMLR 48, 1050–1059.
    - MC Dropout for approximate Bayesian inference. Alternative to ensembles for epistemic uncertainty in neural networks.

22. **Kendall, A. & Gal, Y. (2017).** What uncertainties do we need in Bayesian deep learning for computer vision? *Advances in Neural Information Processing Systems (NeurIPS)*, 30, 5574–5584.
    - Aleatoric vs. epistemic uncertainty decomposition. Heteroscedastic loss function used by STRATA's MetaCalibrator.

---

## 6. Infrastructure Resilience & Risk Assessment

23. **Ouyang, M. (2014).** Review on modeling and simulation of interdependent critical infrastructure systems. *Reliability Engineering & System Safety*, 121, 43–60.
    - Survey of interdependent infrastructure modeling approaches. Motivates STRATA's coupled power/water/telecom graph formulation.

24. **Rinaldi, S. M., Peerenboom, J. P., & Kelly, T. K. (2001).** Identifying, understanding, and analyzing critical infrastructure interdependencies. *IEEE Control Systems Magazine*, 21(6), 11–25.
    - Foundational framework for infrastructure interdependency classification (physical, cyber, geographic, logical). Motivates cross-utility edge types.

25. **Buldyrev, S. V., Parshani, R., Paul, G., Stanley, H. E., & Havlin, S. (2010).** Catastrophic cascade of failures in interdependent networks. *Nature*, 464(7291), 1025–1028.
    - Cascading failure theory in coupled networks. Mathematical foundation for STRATA's inter-layer failure propagation model.

---

## 7. Spatial Statistics

26. **Moran, P. A. P. (1950).** Notes on continuous stochastic phenomena. *Biometrika*, 37(1/2), 17–23.
    - Moran's I spatial autocorrelation statistic. Used in STRATA's `spatial_autocorrelation_test` diagnostic for detecting spatial clustering of conformal scores.

27. **Getis, A. & Ord, J. K. (1992).** The analysis of spatial association by use of distance statistics. *Geographical Analysis*, 24(3), 189–206.
    - Getis-Ord Gi* hotspot statistic. Implemented in STRATA's geo-integration for identifying infrastructure risk hotspots.

---

## 8. Statistical Testing

28. **Wald, A. & Wolfowitz, J. (1940).** On a test whether two samples are from the same population. *Annals of Mathematical Statistics*, 11(2), 147–162.
    - Wald-Wolfowitz runs test for detecting non-randomness/non-exchangeability in sequences. Used in STRATA's `nonexchangeability_test` diagnostic.

29. **Wilcoxon, F. (1945).** Individual comparisons by ranking methods. *Biometrics Bulletin*, 1(6), 80–83.
    - Wilcoxon signed-rank test for paired comparisons. Used in STRATA's diagnostics for pairwise method comparison across seeds.

30. **Friedman, M. (1937).** The use of ranks to avoid the assumption of normality implicit in the analysis of variance. *Journal of the American Statistical Association*, 32(200), 675–701.
    - Friedman rank test for multi-method comparison. Used in STRATA's `multi_method_friedman_test` diagnostic.

31. **Efron, B. & Tibshirani, R. J. (1993).** *An Introduction to the Bootstrap.* Chapman & Hall/CRC.
    - Bootstrap resampling for confidence intervals. Used throughout STRATA's diagnostics module for coverage and width CIs.

---

## 9. Attention Mechanisms & Meta-Learning

32. **Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A. N., Kaiser, Ł., & Polosukhin, I. (2017).** Attention is all you need. *Advances in Neural Information Processing Systems (NeurIPS)*, 30, 5998–6008.
    - Self-attention and scaled dot-product attention. Foundation for STRATA's `AttentionCalibrator` neighbor-difficulty weighting.

---

## 10. Calibration & Expected Calibration Error

33. **Guo, C., Pleiss, G., Sun, Y., & Weinberger, K. Q. (2017).** On calibration of modern neural networks. *International Conference on Machine Learning (ICML)*, PMLR 70, 1321–1330.
    - Expected Calibration Error (ECE) metric for neural network calibration. Underpins STRATA's calibration diagnostics.

34. **Naeini, M. P., Cooper, G. F., & Hauskrecht, M. (2015).** Obtaining well calibrated probabilities using Bayesian binning into quantiles. *AAAI Conference on Artificial Intelligence*, 29(1), 2901–2907.
    - Bayesian binning approach for calibration. Motivates binned calibration error evaluation in STRATA's metrics.

---

## 11. Kriging & Geostatistics

35. **Cressie, N. A. C. (1993).** *Statistics for Spatial Data (Revised Edition).* Wiley.
    - Ordinary kriging and spatial interpolation theory. Underpins STRATA's conformal kriging surface in `geo_integration.py`.
