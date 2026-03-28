# STRATA — References for Paper Submission

> Compiled reference list for the STRATA paper. 66 references organized by topic.
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

---

## 12. Quantile Regression

36. **Koenker, R. & Bassett, G. (1978).** Regression quantiles. *Econometrica*, 46(1), 33–50.
    - Foundational paper introducing quantile regression. Underpins the quantile loss function used in CQR and STRATA's interval construction.

37. **Koenker, R. (2005).** *Quantile Regression.* Cambridge University Press.
    - Comprehensive treatment of quantile regression theory, asymptotics, and inference. Reference for the statistical foundations behind STRATA's CQR-based calibrators.

38. **Meinshausen, N. (2006).** Quantile regression forests. *Journal of Machine Learning Research*, 7, 983–999.
    - Extends random forests to estimate full conditional quantile functions. Demonstrates non-parametric quantile estimation relevant to ensemble-based interval prediction.

---

## 13. Heterogeneous GNNs — Advanced Architectures

39. **Hu, Z., Dong, Y., Wang, K., & Sun, Y. (2020).** Heterogeneous graph transformer. *The Web Conference (WWW)*, 2704–2710.
    - HGT: type-dependent mutual attention with relative temporal encoding for heterogeneous graphs. Advances beyond HAN with per-edge-type parameterized attention heads.

40. **Zhang, C., Song, D., Huang, C., Swami, A., & Chawla, N. V. (2019).** Heterogeneous graph neural network. *ACM SIGKDD Conference on Knowledge Discovery and Data Mining (KDD)*, 793–803.
    - HetGNN: heterogeneous content encoding with type-based neighbor sampling. Introduces grouped aggregation strategies for multi-typed node features.

41. **Yun, S., Jeong, M., Kim, R., Kang, J., & Kim, H. J. (2019).** Graph transformer networks. *Advances in Neural Information Processing Systems (NeurIPS)*, 32, 11983–11993.
    - GTN: learns to generate new graph structures (meta-paths) automatically from heterogeneous graphs via soft adjacency matrix composition.

---

## 14. Online & Adaptive Conformal Prediction

42. **Gibbs, I. & Candès, E. J. (2021).** Adaptive conformal inference under distribution shift. *Advances in Neural Information Processing Systems (NeurIPS)*, 34.
    - Online update rule for conformal thresholds under temporal distribution shift. Provides adaptive coverage guarantees without exchangeability, relevant to streaming infrastructure monitoring.

43. **Tibshirani, R. J., Foygel Barber, R., Candès, E. J., & Ramdas, A. (2019).** Conformal prediction under covariate shift. *Advances in Neural Information Processing Systems (NeurIPS)*, 32, 2530–2540.
    - Weighted conformal prediction using likelihood ratios to correct for covariate shift. Directly relevant to non-exchangeable graph nodes with heterogeneous feature distributions.

44. **Chernozhukov, V., Wüthrich, K., & Zhu, Y. (2021).** Distributional conformal prediction. *Proceedings of the National Academy of Sciences*, 118(48), e2107794118.
    - Extends conformal prediction to estimate full conditional distributions. Provides distribution-free guarantees on conditional coverage at any quantile level.

---

## 15. Graph Signal Processing

45. **Shuman, D. I., Narang, S. K., Frossard, P., Ortega, A., & Vandergheynst, P. (2013).** The emerging field of signal processing on graphs. *IEEE Signal Processing Magazine*, 30(3), 83–98.
    - Survey establishing graph signal processing foundations: graph Fourier transform, spectral filtering, and sampling on graphs. Theoretical basis for spectral GCN methods.

46. **Bruna, J., Zaremba, W., Szlam, A., & LeCun, Y. (2014).** Spectral networks and locally connected networks on graphs. *International Conference on Learning Representations (ICLR)*.
    - First deep learning model using spectral graph convolutions. Introduces graph-domain convolution via the graph Laplacian eigenbasis.

47. **Defferrard, M., Bresson, X., & Vandergheynst, P. (2016).** Convolutional neural networks on graphs with fast localized spectral filtering. *Advances in Neural Information Processing Systems (NeurIPS)*, 29, 3844–3852.
    - ChebNet: Chebyshev polynomial approximation to spectral graph convolutions, enabling localized filters without eigen-decomposition. Direct precursor to GCN (Kipf & Welling 2017).

---

## 16. Infrastructure Cascading Failures & Network Resilience

48. **Gao, J., Buldyrev, S. V., Stanley, H. E., & Havlin, S. (2012).** Networks formed from interdependent networks. *Nature Physics*, 8, 40–48.
    - Extends interdependent network percolation theory (Buldyrev et al. 2010) to networks-of-networks topology. Relevant to STRATA's multi-utility infrastructure graph modeling.

49. **Watts, D. J. (2002).** A simple model of global cascades on random networks. *Proceedings of the National Academy of Sciences*, 99(9), 5766–5771.
    - Analytical model of cascade propagation on random graphs with heterogeneous thresholds. Provides theoretical grounding for failure spread across infrastructure node types.

50. **Kivelä, M., Arenas, A., Barthelemy, M., Gleeson, J. P., Moreno, Y., & Porter, M. A. (2014).** Multilayer networks. *Journal of Complex Networks*, 2(3), 203–271.
    - Comprehensive review of multilayer/multiplex network theory. Formalizes inter-layer coupling relevant to STRATA's heterogeneous infrastructure topology.

51. **Albert, R., Albert, I., & Nakarado, G. L. (2004).** Structural vulnerability of the North American power grid. *Physical Review E*, 69(2), 025103.
    - Graph-theoretic analysis of power grid vulnerability to cascading failures. Demonstrates scale-free properties and targeted attack vulnerabilities in real infrastructure networks.

---

## 17. Distribution Shift & Covariate Shift

52. **Shimodaira, H. (2000).** Improving predictive inference under covariate shift by weighting the log-likelihood function. *Journal of Statistical Planning and Inference*, 90(2), 227–244.
    - Foundational importance weighting framework for covariate shift correction. Motivates reweighting strategies for non-exchangeable graph-structured data in STRATA.

53. **Sugiyama, M., Krauledat, M., & Müller, K.-R. (2007).** Covariate shift adaptation by importance weighted cross validation. *Journal of Machine Learning Research*, 8, 985–1005.
    - Practical density ratio estimation for covariate shift adaptation. Connects to STRATA's challenge of per-node-type distribution differences across train/calibration/test splits.

54. **Quiñonero-Candela, J., Sugiyama, M., Schwaighofer, A., & Lawrence, N. D. (2009).** *Dataset Shift in Machine Learning.* MIT Press.
    - Edited volume systematizing types of dataset shift (covariate, prior probability, concept shift). Provides taxonomy relevant to non-exchangeability sources in heterogeneous graph prediction.

---

## 18. Ensemble Methods & Predictive Uncertainty

55. **Ovadia, Y., Fertig, E., Ren, J., Nado, Z., Sculley, D., Nowozin, S., Dillon, J., Lakshminarayanan, B., & Snoek, J. (2019).** Can you trust your model's uncertainty? Evaluating predictive uncertainty under dataset shift. *Advances in Neural Information Processing Systems (NeurIPS)*, 32.
    - Large-scale empirical evaluation of uncertainty methods (ensembles, MC Dropout, variational) under distribution shift. Demonstrates deep ensembles' robustness advantage, supporting STRATA's `EnsembleHeteroGNN` design.

56. **Wilson, A. G. & Izmailov, P. (2020).** Bayesian deep learning and a probabilistic perspective of generalization. *Advances in Neural Information Processing Systems (NeurIPS)*, 33.
    - Argues deep ensembles provide implicit Bayesian model averaging. Connects ensemble diversity to posterior approximation quality, relevant to STRATA's variance-based uncertainty decomposition.

57. **Blundell, C., Cornebise, J., Kavukcuoglu, K., & Wierstra, D. (2015).** Weight uncertainty in neural networks. *International Conference on Machine Learning (ICML)*, PMLR 37, 1613–1622.
    - Bayes by Backprop: variational inference over network weights for epistemic uncertainty. Alternative to ensembles for Bayesian uncertainty estimation in neural network regressors.

---

## 19. Real-World Infrastructure Test Cases

58. **Birchfield, A. B., Xu, T., Gegner, K. M., Saha, K. S., & Overbye, T. J. (2017).** Grid structural characteristics as validation criteria for synthetic networks. *IEEE Transactions on Power Systems*, 32(4), 3258–3265.
    - ACTIVSg synthetic grid test cases (200/500/2000-bus) with realistic topology and parameters. Provides validated infrastructure benchmark for STRATA's real-world evaluation.

59. **Zimmerman, R. D., Murillo-Sánchez, C. E., & Thomas, R. J. (2011).** MATPOWER: Steady-state operations, planning, and analysis tools for power systems research and education. *IEEE Transactions on Power Systems*, 26(1), 12–19.
    - Open-source power system simulation platform with standard IEEE test cases. Provides infrastructure modeling environment for generating realistic node features and edge connectivity.

---

## 20. Fairness & Equity in Infrastructure Risk

60. **Cutter, S. L., Boruff, B. J., & Shirley, W. L. (2003).** Social vulnerability to environmental hazards. *Social Science Quarterly*, 84(2), 242–261.
    - Social Vulnerability Index (SoVI) framework for mapping populations with differential hazard exposure. Motivates equitable uncertainty quantification across infrastructure-dependent communities.

61. **Hardt, M., Price, E., & Srebro, N. (2016).** Equality of opportunity in supervised learning. *Advances in Neural Information Processing Systems (NeurIPS)*, 29, 3323–3331.
    - Formal framework for equalized odds and equal opportunity in prediction systems. Relevant to ensuring STRATA's per-type coverage guarantees do not systematically disadvantage certain infrastructure service areas.

62. **Mehrabi, N., Morstatter, F., Saxena, N., Lerman, K., & Galstyan, A. (2021).** A survey on bias and fairness in machine learning. *ACM Computing Surveys*, 54(6), 1–35.
    - Comprehensive survey of fairness definitions, bias sources, and mitigation strategies. Provides vocabulary and framework for evaluating distributional equity in STRATA's interval predictions.

---

## 21. GNN Expressiveness & Oversmoothing

63. **Xu, K., Hu, W., Leskovec, J., & Jegelka, S. (2019).** How powerful are graph neural networks? *International Conference on Learning Representations (ICLR)*.
    - GIN: proves most GNNs are at most as powerful as the Weisfeiler-Leman graph isomorphism test. Establishes theoretical expressiveness limits relevant to STRATA's heterogeneous message-passing design.

64. **Li, Q., Han, Z., & Wu, X.-M. (2018).** Deeper insights into graph convolutional networks for semi-supervised learning. *AAAI Conference on Artificial Intelligence*, 32, 3538–3545.
    - Analyzes oversmoothing in deep GCNs: as layers increase, node representations converge. Informs STRATA's choice of GNN depth and residual connection architecture.

---

## 22. Calibration & Conditional Coverage Limits

65. **Kuleshov, V., Fenner, N., & Ermon, S. (2018).** Accurate uncertainties for deep learning using calibrated regression. *International Conference on Machine Learning (ICML)*, PMLR 80, 2796–2804.
    - Post-hoc recalibration of neural network regression intervals using isotonic regression. Complementary approach to conformal calibration for improving prediction interval reliability.

66. **Foygel Barber, R., Candès, E. J., Ramdas, A., & Tibshirani, R. J. (2021).** The limits of distribution-free conditional predictive inference. *Information and Inference: A Journal of the IMA*, 10(2), 455–482.
    - Proves impossibility of exact conditional coverage without distributional assumptions. Establishes theoretical motivation for STRATA's approximate type-conditional coverage via Mondrian splits.
