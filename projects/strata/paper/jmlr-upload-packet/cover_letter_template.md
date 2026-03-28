Cover letter draft for JMLR submission

Matthew Powell
Independent Researcher
matthew.a.powell@outlook.com
March 27, 2026

Editor-in-Chief
Journal of Machine Learning Research

Dear Editor,

Please consider the enclosed manuscript, "STRATA: Conformal Prediction with Heterogeneous Message-Passing Calibration for Infrastructure Risk Assessment," for publication in the Journal of Machine Learning Research.

This submission studies conformal prediction on heterogeneous graphs and introduces Conformal Heterogeneous Message Passing (CHMP), a calibration strategy that rescales conformal scores using frozen training residuals aggregated over typed graph neighborhoods. The central methodological contribution is a way to adapt prediction intervals to local graph difficulty while preserving the logic of split-conformal calibration. In addition to the main CHMP method, the paper evaluates learned normalizers, ensemble-based uncertainty decomposition, streaming extensions, and diagnostics for calibration quality, conditional coverage, and spatial structure.

The manuscript emphasizes general machine-learning methodology for uncertainty quantification on heterogeneous graph-structured data, using coupled infrastructure networks as the motivating domain. Empirically, the paper includes synthetic multi-utility benchmarks and two public MATPOWER-based real-data benchmarks, ACTIVSg200 and IEEE 118, together with ablations over the target miscoverage level and a group-wise fairness audit. The real-data evidence is presented conservatively: CHMP matches the Mondrian baseline in average coverage on both public benchmarks, shows a small width reduction on ACTIVSg200, and does not show a consistent calibration advantage on IEEE 118.

Submission disclosures:

1. Previous publication overlap: this manuscript is not under simultaneous review elsewhere and has not been previously published.
2. Author consent: the listed author consents to submission and publication.
3. Conflicts of interest: the author has no conflicts of interest with the suggested action editors or reviewers listed below.
4. Funding: this work was conducted independently without external funding.

Suggested action editors, subject to conflict review:
1. Kyle Cranmer — probabilistic ML, approximate inference, geometric deep learning.
2. Jian Tang — graph neural networks, geometric deep learning.
3. Edo Airoldi — network data analysis, statistics.
4. Chris Oates — uncertainty quantification, Bayesian computation.
5. Michael Mahoney — graph algorithms, scientific machine learning.

Suggested reviewers, subject to conflict review:
1. William Hamilton — graph representation learning.
2. Marinka Zitnik — representation learning on networks and graphs.
3. Cedric Archambeau — uncertainty quantification and Bayesian inference.
4. Jie Chen — graph deep learning and kernel methods.
5. Eyke Hullermeier — uncertainty in machine learning.

Keywords:
conformal prediction; heterogeneous graphs; graph neural networks; uncertainty quantification; calibration

Key contributions:
- A conformal calibration method for heterogeneous graphs that uses typed neighborhood difficulty while preserving finite-sample split-conformal logic.
- A practical comparison of hand-crafted, learned, quantile-based, and ensemble-based calibration strategies.
- Additional public real-data evaluation on two MATPOWER-based graph benchmarks.
- Reproducibility assets including code, tests, benchmark scripts, supplementary bundle assembly, and draft JMLR LaTeX sources.

Supplementary materials include code, tests, data provenance, benchmark scripts, generated outputs, and a reproducibility bundle.

Sincerely,

Matthew Powell
